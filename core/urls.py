from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('about/', views.about, name='about'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('contacts/', views.contacts, name='contacts'),
    path('blog/', views.blog, name='blog'),
    path('help-center/', views.help_center, name='help_center'),
    path('guides/', views.guides, name='guides'),
    
    # Authentication
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    
    # Profile
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Hotels
    path('hotels/', views.hotel_list, name='hotel_list'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    
    # Destinations & Planning
    path('destinations/', views.destinations, name='destinations'),
    path('planner/', views.planner_view, name='planner'),
    path('recommendations/', views.recommendations_view, name='recommendations'),
    
    # Chatbot
    path('chatbot/', views.chatbot_page, name='chatbot_page'),
    path('chat/', views.ChatAPIView.as_view(), name='chat'),
    path('health/', views.health_check, name='health_check'),
    
    # API endpoints
    path('api/weather/<str:location>/', views.weather_api, name='weather_api'),
    path('api/transport/<int:from_id>/<int:to_id>/', views.transport_api, name='transport_api'),
    
    # Itinerary management
    path('itinerary/add-item/', views.add_itinerary_item, name='add_itinerary_item'),
    path('itinerary/update-item/<int:item_id>/', views.update_itinerary_item, name='update_itinerary_item'),
    path('itinerary/delete-item/<int:item_id>/', views.delete_itinerary_item, name='delete_itinerary_item'),
    path('itinerary/items/', views.get_itinerary_items, name='get_itinerary_items'),
    path('itinerary/items/<int:item_id>/', views.get_itinerary_item, name='get_itinerary_item'),
    path('itinerary/create/', views.user_itinerary_view, name='user_itinerary_view'),
    
    # Smart Itinerary
    path('smart-itinerary/', views.smart_itinerary_view, name='smart_itinerary'),
    path('api/generate-itinerary/', views.generate_itinerary_api, name='generate_itinerary'),
]