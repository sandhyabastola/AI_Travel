import requests
from django.conf import settings
import json

def get_weather_data(location):
    """
    Get weather data for a specific location in Nepal
    """
    try:
        # OpenWeatherMap API
        api_key = settings.WEATHER_API_KEY
        base_url = "http://api.openweathermap.org/data/2.5/weather"
        
        params = {
            'q': f"{location},Nepal",
            'appid': api_key,
            'units': 'metric'
        }
        
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'location': location,
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'description': data['weather'][0]['description'],
                'icon': data['weather'][0]['icon'],
                'wind_speed': data['wind']['speed']
            }
        else:
            return {
                'error': f'Weather data not available for {location}',
                'location': location
            }
    
    except Exception as e:
        return {
            'error': f'Error fetching weather data: {str(e)}',
            'location': location
        }