from django.utils import timezone
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
import requests
from django.urls import reverse

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .recommendation_engine import ContentBasedRecommendationSystem
from core.chatbot import get_chatbot_response, predict_intent_bert  # adjust import if needed
from core.models import ChatHistory  # if using chat history model

from core.models import Destination, UserItinerary, ChatHistory, UserProfile, Transportation, Hotel
from core.forms import UserItineraryForm, UserRegistrationForm, UserProfileForm
from core.itinerary import generate_itinerary
from core.weather import get_weather_data
from .models import UserItinerary  # adjust import if needed

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from core.models import UserItinerary
from .models import ItineraryItem
from django.db.models import Count
from datetime import datetime


context = {
  
    'generation_date': timezone.now().date(),  
}


@login_required
def profile(request):
    return render(request, 'profile.html')

@login_required
def edit_profile(request):
    return render(request, 'edit_profile.html')


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
        # Handle contact form submission
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        # Here you would typically save the message to the database or send an email
        
        messages.success(request, 'Thank you for contacting us!')
        return redirect('core:contacts')

    return render(request, 'contacts.html')


def blog(request):
    # Placeholder for blog functionality
    return render(request, 'blog.html')

def help_center(request):
    # Placeholder for help center functionality
    return render(request, 'help_center.html') 
def guides(request):
    # Placeholder for guides functionality
    return render(request, 'guides.html')
@login_required
def dashboard(request):
    user = request.user
    
    total_trips = UserItinerary.objects.filter(user=user).count()
    total_itinerary_items = ItineraryItem.objects.filter(user=user).count()
    
    # Get recent itinerary items
    recent_items = ItineraryItem.objects.filter(user=user).order_by('-created_at')[:10]
    
    # Get upcoming trips
    upcoming_trips = UserItinerary.objects.filter(
        user=user, 
        start_date__gte=timezone.now().date()
    ).order_by('start_date')[:5]
    
    # Get popular destinations from user's itineraries
    popular_destinations = UserItinerary.objects.filter(user=user).values(
        'destinations__name'
    ).annotate(count=Count('destinations')).order_by('-count')[:3]
    
    context = {
        'total_trips': total_trips,
        'total_itinerary_items': total_itinerary_items,
        'recent_items': recent_items,
        'upcoming_trips': upcoming_trips,
        'popular_destinations': popular_destinations,
        'user': user,
    }
    return render(request, 'dashboard.html', context) 

@login_required
@csrf_exempt
@require_http_methods(["POST"])
def add_itinerary_item(request):
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        title = data.get('title')
        description = data.get('description', '')
        time_str = data.get('time')
        
        if not title or not time_str:
            return JsonResponse({'success': False, 'error': 'Title and time are required'})
        
        # Parse time
        try:
            time_obj = datetime.strptime(time_str, '%H:%M').time()
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Invalid time format. Use HH:MM'})
        
        # Create the itinerary item
        item = ItineraryItem.objects.create(
            user=request.user,
            title=title,
            description=description,
            time=time_obj
        )
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'item': {
                    'id': item.id,
                    'title': item.title,
                    'description': item.description,
                    'time': item.time.strftime('%H:%M'),
                    'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
                }
            })
        else:
            messages.success(request, 'Itinerary item added successfully!')
            return redirect('core:dashboard')
            
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': str(e)})
        else:
            messages.error(request, f'Error adding item: {str(e)}')
            return redirect('core:dashboard')

# Replace your existing delete_itinerary with this enhanced version
@login_required
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_itinerary_item(request, item_id):
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
        item_title = item.title
        item.delete()
        
        if request.content_type == 'application/json' or request.method == 'DELETE':
            return JsonResponse({'success': True, 'message': f'Item "{item_title}" deleted successfully'})
        else:
            messages.success(request, f'Item "{item_title}" deleted successfully!')
            return redirect('core:dashboard')
            
    except Exception as e:
        if request.content_type == 'application/json' or request.method == 'DELETE':
            return JsonResponse({'success': False, 'error': str(e)})
        else:
            messages.error(request, f'Error deleting item: {str(e)}')
            return redirect('core:dashboard')

# Add this new view for updating itinerary items
@login_required
@csrf_exempt
@require_http_methods(["POST", "PUT"])
def update_itinerary_item(request, item_id):
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
        
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        # Update fields if provided
        if 'title' in data and data['title']:
            item.title = data['title']
        if 'description' in data:
            item.description = data['description']
        if 'time' in data and data['time']:
            try:
                item.time = datetime.strptime(data['time'], '%H:%M').time()
            except ValueError:
                return JsonResponse({'success': False, 'error': 'Invalid time format. Use HH:MM'})
        
        item.save()
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'item': {
                    'id': item.id,
                    'title': item.title,
                    'description': item.description,
                    'time': item.time.strftime('%H:%M'),
                    'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
                }
            })
        else:
            messages.success(request, 'Itinerary item updated successfully!')
            return redirect('core:dashboard')
            
    except Exception as e:
        if request.content_type == 'application/json':
            return JsonResponse({'success': False, 'error': str(e)})
        else:
            messages.error(request, f'Error updating item: {str(e)}')
            return redirect('core:dashboard')

# Add this new view to get all itinerary items for a user
@login_required
def get_itinerary_items(request):
    try:
        items = ItineraryItem.objects.filter(user=request.user).order_by('-created_at')
        items_data = []
        
        for item in items:
            items_data.append({
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'time': item.time.strftime('%H:%M'),
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            'success': True,
            'items': items_data,
            'total_count': len(items_data)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# Add this new view to get a single itinerary item
@login_required
def get_itinerary_item(request, item_id):
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'item': {
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'time': item.time.strftime('%H:%M'),
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# Enhanced edit_itinerary view to work better with your structure
def edit_itinerary(request, itinerary_id):
    try:
        itinerary = UserItinerary.objects.get(id=itinerary_id, user=request.user)
    except UserItinerary.DoesNotExist:
        messages.error(request, 'Itinerary not found.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        # Handle both JSON and form data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
            
        itinerary.title = data.get('title', itinerary.title)
        itinerary.notes = data.get('notes', itinerary.notes)
        
        # Handle date updates
        if data.get('start_date'):
            try:
                itinerary.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid start date format')
                
        if data.get('end_date'):
            try:
                itinerary.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid end date format')
        
        itinerary.save()
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True,
                'itinerary': {
                    'id': itinerary.id,
                    'title': itinerary.title,
                    'start_date': itinerary.start_date.strftime('%Y-%m-%d'),
                    'end_date': itinerary.end_date.strftime('%Y-%m-%d'),
                    'notes': itinerary.notes
                }
            })
        else:
            messages.success(request, 'Itinerary updated successfully!')
            return redirect('core:dashboard')
    
    context = {
        'itinerary': itinerary,
        'destinations': itinerary.destinations.all()
    }
    return render(request, 'edit_itinerary.html', context)







def hotel_list(request):
    query = request.GET.get('q')
    if query:
        hotels = Hotel.objects.filter(
            Q(name__icontains=query) | Q(location__icontains=query)
        )
    else:
        hotels = Hotel.objects.all()
    return render(request, 'hotels/hotel_list.html', {'hotels': hotels})

# Hotel detail view
def hotel_detail(request, hotel_id):
    hotel = get_object_or_404(Hotel, id=hotel_id)
    return render(request, 'hotels/hotel_detail.html', {'hotel': hotel})

def destinations(request):
    destinations = Destination.objects.all()
    categories = Destination.objects.values_list('category', flat=True).distinct()

    query = request.GET.get('q')
    category_filter = request.GET.get('category')

    if query:
        destinations = destinations.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) 
            
        )

    if category_filter:
        destinations = destinations.filter(category=category_filter)

    return render(request, 'destinations.html', {
        'destinations': destinations,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': query,
    })



def planner_view(request):
    """
    Display the planner form on GET.
    On POST, save form data to session and redirect to recommendations view.
    """
    if request.method == "POST":
        travel_style = request.POST.get('style', '').lower()
        weather = request.POST.get('weather', 'any')
        budget = request.POST.get('budget', '1000')

        request.session['form_data'] = {
            'style': travel_style,
            'weather': weather,
            'budget': budget,
            'destination': request.POST.get('destination', ''),
            'travel_route': request.POST.get('travel_route', ''),
            'start_date': request.POST.get('start_date', ''),
            'end_date': request.POST.get('end_date', ''),
        }
        return redirect(reverse('core:recommendations'))
    
    form_data = request.session.get('form_data', {})
    return render(request, 'planner.html', {'form_data': form_data})

def recommendations_view(request):
    """
    Retrieve form data from session, generate recommendations,
    enrich with weather and travel route info (API calls),
    and render the recommendations page.
    """
    form_data = request.session.get('form_data')
    if not form_data:
        return redirect('core:planner')

    rec_engine = ContentBasedRecommendationSystem()
    travel_style = form_data.get('style', 'wildlife')
    weather = form_data.get('weather', 'any')
    budget_amount = form_data.get('budget', '1000')
    recommendations = rec_engine.recommend(travel_style, weather, budget_amount)

    enriched_recommendations = []
    for place in recommendations:
        # Get extra info from your Destination dataset
        try:
            dest_obj = Destination.objects.get(name=place.get('name'))
            category = dest_obj.category
            place_name = dest_obj.place
            district = dest_obj.district
        except Destination.DoesNotExist:
            category = place.get('category', 'N/A')
            place_name = place.get('place', 'N/A')
            district = place.get('district', 'N/A')

        # Weather API integration
        location_query = district or place_name or place.get('name')
        weather_data = get_weather_data(location_query)
        weather_info = weather_data.get('forecast', 'N/A') if weather_data else 'N/A'

        # Google Maps API integration (placeholder)
        from_location = form_data.get('destination', '')
        to_location = place.get('name', '')
        route_info = "N/A"
        try:
            if from_location and to_location:
                maps_url = (
                    f"https://maps.googleapis.com/maps/api/directions/json"
                    f"?origin={from_location}&destination={to_location}&key=YOUR_GOOGLE_MAPS_API_KEY"
                )
                response = requests.get(maps_url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('routes'):
                        route_info = data['routes'][0].get('summary', 'Route found')
        except Exception:
            route_info = "N/A"

        enriched_recommendations.append({
            'name': place.get('name'),
            'img': place.get('img_url'),
            'description': place.get('description'),
            'budget': place.get('budget_level'),
            'travel_style': place.get('travel_style'),
            'weather': weather_info,
            'travel_route': route_info,
            'category': category,
            'place': place_name,
            'district': district,
        })

    return render(request, 'recommendations.html', {
        'recommendations': enriched_recommendations,
        'form_data': form_data,
    })

# ✅ Renders chatbot UI page
def chatbot_page(request):
    return render(request, 'chatbot.html')


# ✅ Handles chatbot AJAX POST request
@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')

            if not user_message:
                return JsonResponse({'error': 'Empty message'}, status=400)

            bot_response = get_chatbot_response(user_message)
            intent = predict_intent_bert(user_message)

            return JsonResponse({
                'response': bot_response,
                'intent': intent,
                'confidence': 1.0
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'POST request required'}, status=405)

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get("message", "")
            if not isinstance(message, str):
                return JsonResponse({'error': 'Invalid message'}, status=400)

            session_id = str(uuid.uuid4())
            intent = predict_intent_bert(message)
            bot_reply = get_chatbot_response(message)

            ChatHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                user_message=message,
                bot_response=bot_reply,
                intent=predict_intent_bert,
                confidence=1.0
            )

            return JsonResponse({
                'response': bot_reply,
                'intent': intent,
                'confidence': 1.0,
                'session_id': session_id
            })

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({"error": "POST request required"}, status=400)



@login_required
def user_itinerary_view(request):
    if request.method == 'POST':
        form = UserItineraryForm(request.POST)
        if form.is_valid():
            itinerary = form.save(commit=False)
            itinerary.user = request.user
            itinerary.save()
            form.save_m2m()
            return render(request, 'itinerary_success.html', {'itinerary': itinerary})
    else:
        form = UserItineraryForm()
    return render(request, 'smart_itinerary.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            messages.success(request, "Login successfully")
            return redirect('core:index')  # Replace with your home/dashboard
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


@login_required
def profile(request):
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
    else:
        form = UserProfileForm(instance=profile)

    user_itineraries = UserItinerary.objects.filter(user=request.user)

    return render(request, 'profile.html', {
        'form': form,
        'itineraries': user_itineraries
    })

def edit_profile(request):
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

    return render(request, 'edit_profile.html', {'form': form})

def weather_api(request, location):
    weather_data = get_weather_data(location)
    return JsonResponse(weather_data)


def transport_api(request, from_id, to_id):
    try:
        from_dest = Destination.objects.get(id=from_id)
        to_dest = Destination.objects.get(id=to_id)

        transport_options = Transportation.objects.filter(
            from_destination=from_dest,
            to_destination=to_dest
        )

        options = [{
            'type': transport.transport_type,
            'duration': transport.duration,
            'cost': str(transport.cost),
            'description': transport.description
        } for transport in transport_options]

        return JsonResponse({'options': options})
    except Destination.DoesNotExist:
        return JsonResponse({'error': 'Destination not found'}, status=404)
    
  
