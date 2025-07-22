from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('destinations/', views.destinations, name='destinations'),
    path('planner/', views.planner, name='planner'),
    path('chatbot/', views.chatbot_view, name='chatbot'),
    path('chat-api/', views.chat_api, name='chat_api'),
    path('generate-itinerary/', views.generate_itinerary, name='generate_itinerary'),
    path('profile/', views.profile, name='profile'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('weather/<str:location>/', views.weather_api, name='weather_api'),
    path('transport/<int:from_id>/<int:to_id>/', views.transport_api, name='transport_api'),
    path('about/', views.about, name='about'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
]
