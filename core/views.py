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

from core.models import (
    Destination, UserItinerary, ItineraryItem, ChatHistory,
    UserProfile, Transportation, Hotel
)
from core.forms import UserItineraryForm, UserRegistrationForm, UserProfileForm
from core.itinerary import generate_itinerary
from core.weather import get_weather_data
from core.recommendation_engine import ContentBasedRecommendationSystem
from core.chatbot import get_chatbot_response, predict_intent_bert

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
        # Optionally save or send email
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
    profile = user.userprofile  # your profile model

    if request.method == "POST":
        # Avatar
        if 'avatar' in request.FILES:
            profile.avatar = request.FILES['avatar']

        # Name and Email
        user.first_name = request.POST.get('first_name', user.first_name)
        user.email = request.POST.get('email', user.email)

        # Bio
        profile.bio = request.POST.get('bio', profile.bio)

        # Save changes
        user.save()
        profile.save()

        return redirect('core:profile')  # redirect to profile page

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
    popular_destinations = UserItinerary.objects.filter(user=user).values('destinations__name').annotate(count=Count('destinations')).order_by('-count')[:3]

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
        date_str = data.get('date')
        budget_val = data.get('budget')

        if not title or not time_str:
            return JsonResponse({'success': False, 'error': 'Title and time are required'})

        # Parse time
        time_obj = datetime.strptime(time_str, '%H:%M').time()

        # Parse date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None

        # Parse budget
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
                'time': item.time.strftime('%H:%M'),
                'date': item.date.strftime('%Y-%m-%d') if item.date else '',
                'budget': str(item.budget) if item.budget else '',
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_itinerary_item(request, item_id):
    try:
        item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
        item_title = item.title
        item.delete()

        return JsonResponse({'success': True, 'message': f'Item "{item_title}" deleted successfully'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

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
                'time': item.time.strftime('%H:%M'),
                'date': item.date.strftime('%Y-%m-%d') if item.date else '',
                'budget': str(item.budget) if item.budget else '',
                'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def get_itinerary_items(request):
    items = ItineraryItem.objects.filter(user=request.user).order_by('-created_at')
    items_data = [{
        'id': item.id,
        'title': item.title,
        'description': item.description,
        'time': item.time.strftime('%H:%M'),
        'date': item.date.strftime('%Y-%m-%d') if item.date else '',
        'budget': str(item.budget) if item.budget else '',
        'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
    } for item in items]

    return JsonResponse({'success': True, 'items': items_data, 'total_count': len(items_data)})

@login_required
def get_itinerary_item(request, item_id):
    item = get_object_or_404(ItineraryItem, id=item_id, user=request.user)
    return JsonResponse({
        'success': True,
        'item': {
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'time': item.time.strftime('%H:%M'),
            'date': item.date.strftime('%Y-%m-%d') if item.date else '',
            'budget': str(item.budget) if item.budget else '',
            'created_at': item.created_at.strftime('%Y-%m-%d %H:%M')
        }
    })

# -------------------------------
# User Itinerary Form
# -------------------------------

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
    destinations = Destination.objects.all()
    categories = Destination.objects.values_list('category', flat=True).distinct()
    query = request.GET.get('q')
    category_filter = request.GET.get('category')

    if query:
        destinations = destinations.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if category_filter:
        destinations = destinations.filter(category=category_filter)

    return render(request, 'destinations.html', {
        'destinations': destinations,
        'categories': categories,
        'selected_category': category_filter,
        'search_query': query,
    })

# -------------------------------
# Planner & Recommendations
# -------------------------------

def planner_view(request):
    if request.method == "POST":
        request.session['form_data'] = {
            'style': request.POST.get('style', '').lower(),
            'weather': request.POST.get('weather', 'any'),
            'budget': request.POST.get('budget', '1000'),
            'destination': request.POST.get('destination', ''),
            'travel_route': request.POST.get('travel_route', ''),
            'start_date': request.POST.get('start_date', ''),
            'end_date': request.POST.get('end_date', ''),
        }
        return redirect('core:recommendations')
    form_data = request.session.get('form_data', {})
    return render(request, 'planner.html', {'form_data': form_data})

def recommendations_view(request):
    form_data = request.session.get('form_data')
    if not form_data:
        return redirect('core:planner')

    rec_engine = ContentBasedRecommendationSystem()
    recommendations = rec_engine.recommend(form_data.get('style', 'wildlife'), form_data.get('weather', 'any'), form_data.get('budget', '1000'))

    enriched_recommendations = []
    for place in recommendations:
        try:
            dest_obj = Destination.objects.get(name=place.get('name'))
            category = dest_obj.category
            place_name = dest_obj.place
            district = dest_obj.district
        except Destination.DoesNotExist:
            category = place.get('category', 'N/A')
            place_name = place.get('place', 'N/A')
            district = place.get('district', 'N/A')

        weather_data = get_weather_data(district or place_name or place.get('name'))
        weather_info = weather_data.get('forecast', 'N/A') if weather_data else 'N/A'

        route_info = "N/A"
        from_location = form_data.get('destination', '')
        to_location = place.get('name', '')
        try:
            if from_location and to_location:
                maps_url = f"https://maps.googleapis.com/maps/api/directions/json?origin={from_location}&destination={to_location}&key=YOUR_GOOGLE_MAPS_API_KEY"
                response = requests.get(maps_url)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('routes'):
                        route_info = data['routes'][0].get('summary', 'Route found')
        except:
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

# -------------------------------
# Chatbot
# -------------------------------

def chatbot_page(request):
    return render(request, 'chatbot.html')

@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message', '')
        if not user_message:
            return JsonResponse({'error': 'Empty message'}, status=400)

        bot_response = get_chatbot_response(user_message)
        intent = predict_intent_bert(user_message)

        return JsonResponse({'response': bot_response, 'intent': intent, 'confidence': 1.0})
    return JsonResponse({'error': 'POST request required'}, status=405)

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        message = data.get("message", "")
        session_id = str(uuid.uuid4())
        intent = predict_intent_bert(message)
        bot_reply = get_chatbot_response(message)

        ChatHistory.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_id=session_id,
            user_message=message,
            bot_response=bot_reply,
            intent=intent,
            confidence=1.0
        )

        return JsonResponse({'response': bot_reply, 'intent': intent, 'confidence': 1.0, 'session_id': session_id})

    return JsonResponse({"error": "POST request required"}, status=400)

# -------------------------------
# Weather & Transport API
# -------------------------------

def weather_api(request, location):
    weather_data = get_weather_data(location)
    return JsonResponse(weather_data)

def transport_api(request, from_id, to_id):
    try:
        from_dest = Destination.objects.get(id=from_id)
        to_dest = Destination.objects.get(id=to_id)

        transport_options = Transportation.objects.filter(from_destination=from_dest, to_destination=to_dest)
        options = [{'type': t.transport_type, 'duration': t.duration, 'cost': str(t.cost), 'description': t.description} for t in transport_options]

        return JsonResponse({'options': options})

    except Destination.DoesNotExist:
        return JsonResponse({'error': 'Destination not found'}, status=404)
