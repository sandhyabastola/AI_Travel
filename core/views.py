import logging
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from datetime import datetime
import json
import uuid
import requests
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View

# Import your custom modules
from core.models import (
    Destination, UserItinerary, ItineraryItem, ChatHistory,
    UserProfile, Transportation, Hotel
)
from core.forms import UserItineraryForm, UserRegistrationForm, UserProfileForm
from core.itinerary import generate_itinerary
from core.utils import ChatBotEngine
from core.weather import get_weather_data
from core.recommendation_engine import ContentBasedRecommendationSystem

# Get logger
logger = logging.getLogger(__name__)

# -------------------------------
# Basic pages
# -------------------------------

def index(request):
    featured_destinations = Destination.objects.filter(category__in=['city', 'mountain'])[:6]
    return render(request, 'index.html', {'destinations': featured_destinations})

def about(request):
    return render(request, 'about.html')

def privacy(request):
    return render(request, 'privacy.html')

def terms(request):
    return render(request, 'terms.html')

def cookie_policy(request):
    return render(request, 'cookie_policy.html')

def contacts(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        messages.success(request, 'Thank you for contacting us!')
        return redirect('core:contacts')
    return render(request, 'contacts.html')

def blog(request):
    return render(request, 'blog.html')

def help_center(request):
    return render(request, 'help_center.html')

def guides(request):
    return render(request, 'guides.html')

# -------------------------------
# Authentication
# -------------------------------

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Login successfully")
            return redirect('core:index')
        else:
            messages.error(request, "Invalid username or password")
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('core:profile')
    else:
        form = UserRegistrationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('core:index')

# -------------------------------
# Profile
# -------------------------------

@login_required
def profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('core:profile')
    else:
        form = UserProfileForm(instance=profile)

    user_itineraries = UserItinerary.objects.filter(user=request.user)

    return render(request, 'profile.html', {
        'form': form,
        'itineraries': user_itineraries
    })

@login_required
def edit_profile(request):
    user = request.user
    try:
        profile = user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    if request.method == "POST":
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']
        user.first_name = request.POST.get('first_name', user.first_name)
        user.email = request.POST.get('email', user.email)
        profile.bio = request.POST.get('bio', profile.bio)
        user.save()
        profile.save()
        messages.success(request, 'Profile updated successfully!')
        return redirect('core:profile')

    context = {
        'user': user,
        'profile': profile
    }
    return render(request, 'edit_profile.html', context)

# -------------------------------
# Dashboard & Itinerary CRUD
# -------------------------------

@login_required
def dashboard(request):
    user = request.user
    total_trips = UserItinerary.objects.filter(user=user).count()
    total_itinerary_items = ItineraryItem.objects.filter(user=user).count()
    recent_items = ItineraryItem.objects.filter(user=user).order_by('-created_at')[:10]
    upcoming_trips = UserItinerary.objects.filter(user=user, start_date__gte=timezone.now().date()).order_by('start_date')[:5]
    
    popular_destinations = Destination.objects.filter(
        useritinerary__user=user
    ).annotate(
        count=Count('useritinerary')
    ).order_by('-count')[:3]

    context = {
        'total_trips': total_trips,
        'total_itinerary_items': total_itinerary_items,
        'recent_items': recent_items,
        'upcoming_trips': upcoming_trips,
        'popular_destinations': popular_destinations,
        'user': user,
    }
    return render(request, 'dashboard.html', context)

# Itinerary Item Management Views
@login_required
@csrf_exempt
@require_http_methods(["POST"])
def add_itinerary_item(request):
    """Add a new itinerary item"""
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        title = data.get('title')
        description = data.get('description', '')
        time_str = data.get('time')
        date_str = data.get('date')
        budget_val = data.get('budget')

        if not title:
            return JsonResponse({'success': False, 'error': 'Title is required'})

        time_obj = datetime.strptime(time_str, '%H:%M').time() if time_str else None
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
        budget_decimal = float(budget_val) if budget_val else None

        item = ItineraryItem.objects.create(
            user=request.user,
            title=title,
            description=description,
            time=time_obj,
            date=date_obj,
            budget=budget_decimal
        )

        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'time': item.time.strftime('%H:%M') if item.time else '',
                'date': item.date.strftime('%Y-%m-%d') if item.date else '',
                'budget': str(item.budget) if item.budget else '',
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Error adding itinerary item: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_itinerary_item(request, item_id):
    """Delete an itinerary item"""
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
        item_title = item.title
        item.delete()
        return JsonResponse({'success': True, 'message': f'Item "{item_title}" deleted successfully'})

    except Exception as e:
        logger.error(f"Error deleting itinerary item: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_itinerary_item(request, item_id):
    """Update an existing itinerary item"""
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)

        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST

        if 'title' in data and data['title']:
            item.title = data['title']
        if 'description' in data:
            item.description = data['description']
        if 'time' in data and data['time']:
            item.time = datetime.strptime(data['time'], '%H:%M').time()
        if 'date' in data and data['date']:
            item.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        if 'budget' in data and data['budget']:
            item.budget = float(data['budget'])

        item.save()

        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'time': item.time.strftime('%H:%M') if item.time else '',
                'date': item.date.strftime('%Y-%m-%d') if item.date else '',
                'budget': str(item.budget) if item.budget else '',
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })

    except Exception as e:
        logger.error(f"Error updating itinerary item: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_itinerary_items(request):
    """Get all itinerary items for the user"""
    try:
        items = ItineraryItem.objects.filter(user=request.user).order_by('date', 'time')
        
        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'time': item.time.strftime('%H:%M') if item.time else '',
                'date': item.date.strftime('%Y-%m-%d') if item.date else '',
                'budget': str(item.budget) if item.budget else '',
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'items': items_data
        })
        
    except Exception as e:
        logger.error(f"Error getting itinerary items: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_itinerary_item(request, item_id):
    """Get specific itinerary item"""
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
        
        item_data = {
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'time': item.time.strftime('%H:%M') if item.time else '',
            'date': item.date.strftime('%Y-%m-%d') if item.date else '',
            'budget': str(item.budget) if item.budget else '',
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
        }
        
        return JsonResponse({
            'success': True,
            'item': item_data
        })
        
    except Exception as e:
        logger.error(f"Error getting itinerary item: {e}")
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def user_itinerary_view(request):
    """Create or view user itinerary"""
    if request.method == 'POST':
        form = UserItineraryForm(request.POST)
        if form.is_valid():
            itinerary = form.save(commit=False)
            itinerary.user = request.user
            itinerary.save()
            
            destinations = form.cleaned_data.get('destinations')
            if destinations:
                itinerary.destinations.set(destinations)
            
            messages.success(request, 'Itinerary created successfully!')
            return redirect('core:smart_itinerary')
    else:
        form = UserItineraryForm()
    
    user_itineraries = UserItinerary.objects.filter(user=request.user)
    
    return render(request, 'smart_itinerary.html', {
        'form': form,
        'itineraries': user_itineraries
    })

# Smart Itinerary Views
@login_required
def smart_itinerary_view(request):
    """Render the smart itinerary page"""
    return render(request, 'smart_itinerary.html')

@login_required
@csrf_exempt
def generate_itinerary_api(request):
    """API endpoint to generate itinerary"""
    if request.method == 'POST':
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST
                
            user_id = data.get('user_id') or request.user.id
            
            user_itinerary = UserItinerary.objects.filter(user_id=user_id).first()
            
            if not user_itinerary:
                return JsonResponse({'error': 'No itinerary found for user'}, status=404)
            
            itinerary_result = generate_itinerary(user_itinerary)
            itinerary_result['user_budget'] = float(user_itinerary.budget)
            
            return JsonResponse(itinerary_result)
            
        except Exception as e:
            logger.error(f"Error generating itinerary: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

# -------------------------------
# Hotels
# -------------------------------

def hotel_list(request):
    query = request.GET.get('q')
    if query:
        hotels = Hotel.objects.filter(Q(name__icontains=query) | Q(location__icontains=query))
    else:
        hotels = Hotel.objects.all()
    return render(request, 'hotels/hotel_list.html', {'hotels': hotels})

def hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    return render(request, 'hotels/hotel_detail.html', {'hotel': hotel})

# -------------------------------
# Destinations
# -------------------------------

def destinations(request):
    search_query = request.GET.get('q', '').strip()
    
    if search_query:
        search_results = Destination.objects.filter(
            Q(name__icontains=search_query) | 
            Q(district__icontains=search_query) |
            Q(place__icontains=search_query)
        )[:10]
        search_results = [{
            'id': dest.id,
            'name': dest.name,
            'district': dest.district,
            'place': dest.place,
            'category': dest.category,
            'description': dest.description
        } for dest in search_results]
    else:
        search_results = []

    content_recommendations = []
    user_recommendations = []
    ratings = [1, 2, 3, 4, 5]

    return render(request, 'destinations.html', {
        'search_query': search_query,
        'destinations': search_results,
        'recommendations': content_recommendations,
        'user_recommendations': user_recommendations,
        'ratings': ratings,
    })

# -------------------------------
# Planner & Recommendations
# -------------------------------

def planner_view(request):
    if request.method == "POST":
        travel_style = request.POST.get('style', '').lower()
        weather = request.POST.get('weather', 'any')
        budget = request.POST.get('budget', '1000')

        request.session['form_data'] = {
            'style': travel_style,
            'weather': weather,
            'budget': budget,
            'category': request.POST.get('category', '').lower(),
            'destination': request.POST.get('destination', ''),
            'travel_route': request.POST.get('travel_route', ''),
            'start_date': request.POST.get('start_date', ''),
            'end_date': request.POST.get('end_date', ''),
        }
        return redirect(reverse('core:recommendations'))
    
    form_data = request.session.get('form_data', {})
    return render(request, 'planner.html', {'form_data': form_data})

def recommendations_view(request):
    form_data = request.session.get('form_data')
    if not form_data:
        return redirect('core:planner')

    try:
        rec_engine = ContentBasedRecommendationSystem()
        travel_style = form_data.get('style', 'wildlife')
        category = form_data.get('category', 'national park')
        weather = form_data.get('weather', 'any')
        budget_amount = form_data.get('budget', '1000')
        destination = form_data.get('destination', '')  
        travel_route = form_data.get('travel_route', '')  
        
        recommendations = rec_engine.recommend(
            travel_style=travel_style,      
            weather=weather,                
            budget_amount=budget_amount,    
            destination=destination,        
            travel_route=travel_route,      
            top_k=5
        )

        enriched_recommendations = []
        for place in recommendations:
            category = place.get('category', 'N/A')
            place_name = place.get('name', 'N/A')
            district = place.get('district', 'N/A')

            location_query = district or place_name
            weather_data = get_weather_data(location_query)
            weather_info = weather_data.get('forecast', 'N/A') if weather_data else 'N/A'

            from_location = form_data.get('destination', '')
            to_location = place.get('location', '') or place.get('name', '')
            route_info = "N/A"
            
            if from_location and to_location and from_location.strip() and to_location.strip():
                try:
                    from django.conf import settings
                    maps_url = (
                        f"https://maps.googleapis.com/maps/api/directions/json"
                        f"?origin={from_location}&destination={to_location}&key={getattr(settings, 'MAPS_API_KEY', '')}"
                    )
                    response = requests.get(maps_url)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('routes'):
                            route = data['routes'][0]['legs'][0]
                            distance = route.get('distance', {}).get('text', 'Unknown distance')
                            duration = route.get('duration', {}).get('text', 'Unknown duration')
                            route_info = f"{distance}, {duration}"
                except Exception as e:
                    logger.error(f"Error fetching route info: {e}")
                    route_info = "Route information unavailable"

            enriched_recommendations.append({
                'name': place.get('name', 'N/A'),
                'img': place.get('img_url', ''),
                'description': place.get('description', 'No description available'),
                'budget': place.get('budget_level', 'N/A'),
                'travel_style': place.get('travel_style', 'N/A'),
                'weather': weather_info,
                'travel_route': route_info,
                'category': category,
                'place': place_name,
                'district': district,
                'location': place.get('location', ''),
            })

        return render(request, 'recommendations.html', {
            'recommendations': enriched_recommendations,
            'form_data': form_data,
        })
        
    except Exception as e:
        logger.error(f"Error in recommendations view: {e}")
        messages.error(request, "Error generating recommendations. Please try again.")
        return redirect('core:planner')

# -------------------------------
# Chatbot
# -------------------------------

def chatbot_page(request):
    return render(request, 'chatbot.html')

@method_decorator(csrf_exempt, name='dispatch')
class ChatAPIView(View):
    """Handle chat messages via AJAX - COMPLETELY FIXED VERSION"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_input = data.get('message', '').strip()
            
            if not user_input:
                return JsonResponse({
                    'success': False,
                    'error': 'Message cannot be empty'
                })
            
            chatbot = ChatBotEngine.get_instance()
            response, intent = chatbot.get_response(user_input)
            
            # Handle specific intents with better responses
            if intent == "recommendation":
                response = self.handle_recommendation_intent(user_input)
            elif intent == "weather":
                response = self.handle_weather_intent(user_input)
            elif intent == "hotel_search":
                response = self.handle_hotel_intent(user_input)
            elif intent == "transport":
                response = self.handle_transport_intent(user_input)
            
            # NO CHATHISTORY SAVING - COMPLETELY REMOVED
            # This fixes the "unexpected keyword arguments" error
            
            print(f"✅ Chat response generated: {intent}")
            
            return JsonResponse({
                'success': True,
                'response': response,
                'intent': intent
            })
            
        except Exception as e:
            logger.error(f"Error in chat API: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Sorry, I encountered an error. Please try again.'
            })
    
    def extract_location(self, text):
        """Extract location from user message"""
        locations = ['pokhara', 'kathmandu', 'chitwan', 'lumbini', 'nagarkot', 'mustang', 
                    'bhaktapur', 'patan', 'thamel', 'lakeside', 'annapurna', 'everest']
        text_lower = text.lower()
        
        for location in locations:
            if location in text_lower:
                return location.title()
        return None
    
    def handle_recommendation_intent(self, user_input):
        """Handle recommendation requests"""
        try:
            from core.recommendation_engine import ContentBasedRecommendationSystem
            
            location = self.extract_location(user_input)
            
            if 'adventure' in user_input.lower():
                travel_style = 'adventure'
            elif 'cultural' in user_input.lower() or 'heritage' in user_input.lower():
                travel_style = 'cultural'
            elif 'religious' in user_input.lower() or 'temple' in user_input.lower():
                travel_style = 'religious'
            elif 'wildlife' in user_input.lower():
                travel_style = 'wildlife'
            else:
                travel_style = 'adventure'
            
            if location:
                # Get actual recommendations
                rec_engine = ContentBasedRecommendationSystem()
                recommendations = rec_engine.recommend(
                    travel_style=travel_style,
                    weather='any',
                    budget_amount='5000',
                    destination=location,
                    travel_route='',
                    top_k=3
                )
                
                if recommendations and len(recommendations) > 0:
                    response = f"🏔️ **Top {travel_style} places in {location}:**\n\n"
                    for i, rec in enumerate(recommendations, 1):
                        response += f"**{i}. {rec.get('name', 'Unknown')}**\n"
                        response += f"   📍 {rec.get('district', 'Nepal')}\n"
                        response += f"   💰 {rec.get('budget_level', 'Medium')} budget\n"
                        response += f"   🎯 {rec.get('travel_style', 'Adventure')}\n"
                        if rec.get('weather'):
                            response += f"   🌤️ {rec.get('weather')}\n"
                        response += "\n"
                    
                    response += "🔍 **Want more details?** Visit our **Travel Planner** for personalized recommendations with routes and hotels!"
                else:
                    response = f"🏔️ For amazing {travel_style} experiences in {location}, check our **Travel Planner** section!"
            else:
                response = f"🏔️ I'd love to recommend {travel_style} destinations! Please specify a location like Kathmandu, Pokhara, or Chitwan."
                
            return response
                
        except Exception as e:
            logger.error(f"Error in recommendation intent: {e}")
            return "🏔️ For the best travel recommendations, please check out our **Travel Planner** section!"
    
    def handle_weather_intent(self, user_input):
        """Handle weather queries"""
        location = self.extract_location(user_input)
        if location:
            try:
                from core.weather import get_weather_data
                weather_data = get_weather_data(location)
                if weather_data:
                    temp = weather_data.get('temperature', 'N/A')
                    desc = weather_data.get('description', 'N/A')
                    humidity = weather_data.get('humidity', 'N/A')
                    return f"🌤️ **Weather in {location}:**\n\n• **Condition:** {desc}\n• **Temperature:** {temp}°C\n• **Humidity:** {humidity}%"
                else:
                    return f"🌤️ **{location} Weather:**\n\nI can't fetch live weather right now. {location} generally has mild temperatures (15-25°C)."
            except Exception as e:
                logger.error(f"Weather intent error: {e}")
                return f"🌤️ **{location} Climate:**\n\n• **Spring:** 15-25°C, perfect weather\n• **Summer:** 20-30°C\n• **Autumn:** 10-20°C\n• **Winter:** 5-15°C"
        else:
            return "🌤️ Please specify a location like Kathmandu, Pokhara, or Chitwan for weather information!"
    
    def handle_hotel_intent(self, user_input):
        """Handle hotel search queries with data from chatbot's hotel_df"""
        location = self.extract_location(user_input)
        
        if location:
            try:
                chatbot = ChatBotEngine.get_instance()
                
                if chatbot.hotel_df is not None:
                    # Filter hotels for the location
                    location_hotels = chatbot.hotel_df[
                        chatbot.hotel_df['City'].str.lower().str.contains(location.lower())
                    ].head(5)  # Get top 5 hotels
                    
                    if not location_hotels.empty:
                        response = f"🏨 **Top hotels in {location}:**\n\n"
                        
                        for i, (_, hotel) in enumerate(location_hotels.iterrows(), 1):
                            response += f"**{i}. {hotel.get('HotelName', 'Hotel')}**\n"
                            response += f"   📍 {hotel.get('City', location)}\n"
                            response += f"   💰 NPR {hotel.get('Price', 'Price on request')}\n"
                            response += f"   ⭐ {hotel.get('Type', 'Hotel')}\n\n"
                        
                        response += "🔍 **Want more options?** Visit our **Hotels** section!"
                        
                    else:
                        response = self.get_fallback_hotel_info(location)
                else:
                    response = self.get_fallback_hotel_info(location)
                    
                return response
                
            except Exception as e:
                logger.error(f"Error in hotel intent: {e}")
                return self.get_fallback_hotel_info(location)
        
        else:
            return "🏨 **Hotel Search**\n\nPlease specify a location to see hotel recommendations!"
    
    def get_fallback_hotel_info(self, location):
        """Provide fallback hotel information when database is unavailable"""
        hotel_info = {
            'Kathmandu': {
                'budget': ['Thamel Hotel', 'Kathmandu Guest House', 'Hotel Moonlight'],
                'midrange': ['Hotel Annapurna', 'Hotel Shanker', 'Radisson Hotel'],
                'luxury': ['Yak & Yeti', 'Hyatt Regency', 'Dwarika\'s Hotel'],
                'prices': 'NPR 1,500 - 25,000'
            },
            'Pokhara': {
                'budget': ['Hotel Barahi', 'Pokhara Grand', 'Trek-O-Tel'],
                'midrange': ['Fish Tail Lodge', 'Temple Tree Resort', 'Waterfront Resort'],
                'luxury': ['The Pavilions Himalayas', 'Tiger Mountain Pokhara'],
                'prices': 'NPR 1,200 - 20,000'
            },
            'Chitwan': {
                'budget': ['Jungle Safari Lodge', 'Green Park', 'Wildlife Camp'],
                'midrange': ['Tiger Palace', 'River Side Spring', 'Chitwan Forest Resort'],
                'luxury': ['Temple Tiger', 'Meghauli Serai'],
                'prices': 'NPR 1,000 - 15,000'
            }
        }
        
        if location in hotel_info:
            info = hotel_info[location]
            response = f"🏨 **Popular hotels in {location}:**\n\n"
            response += "💰 **Budget** (NPR 1,000-4,000):\n"
            for hotel in info['budget'][:2]:
                response += f"• {hotel}\n"
            
            response += "\n💰 **Mid-range** (NPR 4,000-8,000):\n"
            for hotel in info['midrange'][:2]:
                response += f"• {hotel}\n"
            
            response += "\n💰 **Luxury** (NPR 8,000+):\n"
            for hotel in info['luxury'][:2]:
                response += f"• {hotel}\n"
            
            response += f"\n🔍 **Price range:** {info['prices']} per night\n"
            response += "Visit our **Hotels** section for complete listings!"
            
        else:
            response = f"🏨 **Hotels in {location}:**\n\n"
            response += "💰 **Price ranges:**\n"
            response += "• Budget: NPR 1,000 - 4,000\n"
            response += "• Mid-range: NPR 4,000 - 8,000\n"
            response += "• Luxury: NPR 8,000 - 25,000+\n\n"
            response += "🔍 Check our **Hotels** section for specific options!"
        
        return response
    
    def handle_transport_intent(self, user_input):
        """Handle transport queries"""
        locations = ['pokhara', 'kathmandu', 'chitwan', 'lumbini', 'nagarkot']
        found_locations = []
        text_lower = user_input.lower()
        
        for loc in locations:
            if loc in text_lower:
                found_locations.append(loc.title())
        
        if len(found_locations) >= 2:
            from_loc, to_loc = found_locations[0], found_locations[1]
            return f"🚍 **Transport: {from_loc} → {to_loc}**\n\n• **Bus:** 6-8 hours, NPR 800-1500\n• **Taxi:** 5-7 hours, NPR 5000-8000\n• **Best option:** Tourist bus for comfort"
        else:
            return "🚍 Please specify your route like 'Kathmandu to Pokhara' for transport information!"

def health_check(request):
    """Health check endpoint"""
    try:
        chatbot = ChatBotEngine.get_instance()
        
        health_status = {
            'status': 'healthy',
            'model_loaded': chatbot.model is not None,
            'hotels_data_loaded': chatbot.hotel_df is not None,
            'travel_data_loaded': chatbot.travel_df is not None,
            'weather_data_loaded': chatbot.weather_df is not None,
            'hotels_count': len(chatbot.hotel_df) if chatbot.hotel_df is not None else 0,
            'travel_routes_count': len(chatbot.travel_df) if chatbot.travel_df is not None else 0,
        }
        
        return JsonResponse(health_status)
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return JsonResponse({'status': 'unhealthy', 'error': str(e)}, status=500)

# -------------------------------
# API Endpoints
# -------------------------------

def weather_api(request, location):
    """Weather API endpoint"""
    try:
        weather_data = get_weather_data(location)
        
        if weather_data:
            return JsonResponse({
                'success': True,
                'location': location,
                'weather': weather_data
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Weather data not available for {location}'
            }, status=404)
            
    except Exception as e:
        logger.error(f"Weather API error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def transport_api(request, from_id, to_id):
    """Transport API endpoint"""
    try:
        transport_options = Transportation.objects.filter(
            from_location_id=from_id,
            to_location_id=to_id
        )
        
        transport_data = []
        for transport in transport_options:
            transport_data.append({
                'id': transport.id,
                'mode': transport.mode,
                'duration': str(transport.duration),
                'cost': str(transport.cost),
                'from_location': transport.from_location.name if transport.from_location else '',
                'to_location': transport.to_location.name if transport.to_location else '',
                'description': transport.description
            })
        
        if not transport_data:
            try:
                from_location = get_object_or_404(Destination, id=from_id)
                to_location = get_object_or_404(Destination, id=to_id)
                
                transport_data = [
                    {
                        'mode': 'bus',
                        'duration': '6 hours',
                        'cost': '1200.00',
                        'from_location': from_location.name,
                        'to_location': to_location.name,
                        'description': 'Regular bus service'
                    },
                    {
                        'mode': 'taxi',
                        'duration': '5 hours',
                        'cost': '8000.00',
                        'from_location': from_location.name,
                        'to_location': to_location.name,
                        'description': 'Private taxi service'
                    }
                ]
            except Destination.DoesNotExist:
                transport_data = []
        
        return JsonResponse({
            'success': True,
            'from_id': from_id,
            'to_id': to_id,
            'transport_options': transport_data
        })
        
    except Exception as e:
        logger.error(f"Transport API error: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)