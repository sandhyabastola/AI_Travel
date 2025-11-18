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
from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from core.chatbot import get_chatbot_response, predict_intent_bert  # adjust import if needed
from core.models import ChatHistory  # if using chat history model

from core.models import Destination, UserItinerary, ChatHistory, UserProfile, Transportation, Hotel
from core.forms import UserItineraryForm, UserRegistrationForm, UserProfileForm
from core.itinerary import generate_itinerary
from core.utils import ChatBotEngine
from core.weather import get_weather_data
from .models import UserItinerary  # adjust import if needed

from django.http import JsonResponse

context = {
  
    'generation_date': timezone.now().date(),  
}

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
        
        # Here you would typically save the message to the database or send an email
        
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
    try:
        profile = request.user.userprofile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=request.user)

    if request.method == 'POST':
        form = UserItineraryForm(request.POST)
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
    """Transport API endpoint"""
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
    
  
