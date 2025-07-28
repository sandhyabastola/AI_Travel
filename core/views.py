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
from django.shortcuts import render, get_object_or_404
from django.db.models import Q

from core.chatbot import get_chatbot_response, predict_intent_bert  # adjust import if needed
from core.models import ChatHistory  # if using chat history model

from core.models import Destination, UserItinerary, ChatHistory, UserProfile, Transportation, Hotel
from core.forms import UserItineraryForm, UserRegistrationForm, UserProfileForm
from core.itinerary import generate_itinerary
from core.weather import get_weather_data
from .models import UserItinerary  # adjust import if needed

from django.http import JsonResponse

context = {
  
    'generation_date': timezone.now().date(),  
}

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

def smart_itinerary(request):
    try:
        itinerary = UserItinerary.objects.get(user=request.user)
        destinations = itinerary.destinations.all()
        travel_dates = f"{itinerary.start_date} – {itinerary.end_date}"
    except UserItinerary.DoesNotExist:
        itinerary = None
        destinations = []
        travel_dates = "Not available"

    context = {
        'itinerary': itinerary,
        'destinations': destinations,
        'travel_dates': travel_dates,
        'generation_date': timezone.now().date(),
    }

    return render(request, 'smart_itinerary.html', context)



def edit_itinerary(request, itinerary_id):
    try:
        itinerary = UserItinerary.objects.get(id=itinerary_id, user=request.user)
    except UserItinerary.DoesNotExist:
        messages.error(request, 'Itinerary not found.')
        return redirect('core:dashboard')

    if request.method == 'POST':
        form = UserItineraryForm(request.POST, instance=itinerary)
        if form.is_valid():
            form.save()
            messages.success(request, 'Itinerary updated successfully!')
            return redirect('core:dashboard')
    else:
        form = UserItineraryForm(instance=itinerary)

    return render(request, 'edit_itinerary.html', {'form': form, 'itinerary': itinerary})

def download_itinerary_pdf(request, itinerary_id):
    try:
        itinerary = UserItinerary.objects.get(id=itinerary_id, user=request.user)
    except UserItinerary.DoesNotExist:
        messages.error(request, 'Itinerary not found.')
        return redirect('core:dashboard')

    # Generate PDF logic here (not implemented in this snippet)
    # For example, you could use a library like ReportLab or WeasyPrint

    messages.success(request, 'PDF downloaded successfully!')
    return redirect('core:dashboard')

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
    
  
