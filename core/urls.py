from django.urls import path
from core import views

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('hotels/', views.hotel_list, name='hotel_list'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    path('destinations/', views.destinations, name='destinations'),
   path('planner/', views.planner_view, name='planner'),
    path('recommendations/', views.recommendations_view, name='recommendations'), 
    path('chatbot/chat-api/', views.chat_api, name='chat_api'),
    path("chatbot/api/", views.chatbot_api, name="chatbot_api"),
    path('chatbot/', views.chatbot_page, name='chatbot_page'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
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
    

    path('add-itinerary-item/', views.add_itinerary_item, name='add_itinerary_item'),
    path('update-itinerary-item/<int:item_id>/', views.update_itinerary_item, name='update_itinerary_item'),
    path('delete-itinerary-item/<int:item_id>/', views.delete_itinerary_item, name='delete_itinerary_item'),
    path('get-itinerary-items/', views.get_itinerary_items, name='get_itinerary_items'),
    path('get-itinerary-item/<int:item_id>/', views.get_itinerary_item, name='get_itinerary_item'),
    

    path('user-itinerary/', views.user_itinerary_view, name='user_itinerary_view'),

    
]
