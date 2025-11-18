from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    # Main pages
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('hotels/', views.hotel_list, name='hotel_list'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    path('destinations/', views.destinations, name='destinations'),
    path('planner/', views.planner, name='planner'),
    path('chatbot/chat-api/', views.chat_api, name='chat_api'),
    path("chatbot/api/", views.chatbot_api, name="chatbot_api"),
    path('chatbot/', views.chatbot_page, name='chatbot_page'),
    path('smart-itinerary/', views.smart_itinerary, name='smart_itinerary'),
    path('edit-itinerary/<int:itinerary_id>/', views.edit_itinerary, name='edit_itinerary'),
    path('download-itinerary-pdf/<int:itinerary_id>/', views.download_itinerary_pdf, name='download_itinerary_pdf'),
    path('profile/', views.profile, name='profile'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('weather/<str:location>/', views.weather_api, name='weather_api'),
    path('transport/<int:from_id>/<int:to_id>/', views.transport_api, name='transport_api'),
    path('about/', views.about, name='about'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('cookie-policy/', views.cookie_policy, name='cookie_policy'),
    path('contacts/', views.contacts, name='contacts'),
    path('blog/', views.blog, name='blog'),
    path('help-center/', views.help_center, name='help_center'),
    path('guides/', views.guides, name='guides'),
]
