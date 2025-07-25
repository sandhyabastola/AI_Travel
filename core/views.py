from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import uuid
from django.db.models import Q


from .models import Destination, UserItinerary, ChatHistory, UserProfile, Transportation
from .forms import UserItineraryForm, UserRegistrationForm, UserProfileForm
from .itinerary import generate_itinerary
from .weather import get_weather_data
from .chatbot import predict_intent, chatbot


def index(request):
    featured_destinations = Destination.objects.filter(category__in=['city', 'mountain'])[:6]
    return render(request, 'index.html', {'destinations': featured_destinations})


def dashboard(request):
    return render(request, 'dashboard.html')

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



@login_required
def planner(request):
    if request.method == 'POST':
        form = UserItineraryForm(request.POST)
        if form.is_valid():
            itinerary = form.save(commit=False)
            itinerary.user = request.user
            itinerary.save()
            form.save_m2m()

            ai_itinerary = generate_itinerary(itinerary)

            return render(request, 'planner_result.html', {
                'itinerary': itinerary,
                'ai_suggestions': ai_itinerary
            })
    else:
        form = UserItineraryForm()

    return render(request, 'planner.html', {'form': form})


def chatbot_view(request):
    return render(request, 'chatbot.html')


@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get("message", "")
            if not isinstance(message, str):
                raise ValueError("Expected string input")

            session_id = str(uuid.uuid4())
            intent = predict_intent(message)
            bot_reply = chatbot(message)

            ChatHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=session_id,
                user_message=message,
                bot_response=bot_reply,
                intent=intent,
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
    return render(request, 'generate_itinerary.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('core:index')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


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
    
  
