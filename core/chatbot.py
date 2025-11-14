import os
import pandas as pd
import torch
import re
import numpy as np
import requests
from transformers import BertTokenizer, BertForSequenceClassification
from django.conf import settings

class WeatherAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    def get_weather(self, city_name, country_code="NP"):
        try:
            geo_url = "http://api.openweathermap.org/geo/1.0/direct"
            geo_params = {
                'q': f"{city_name},{country_code}",
                'limit': 1,
                'appid': self.api_key
            }
            
            geo_response = requests.get(geo_url, params=geo_params)
            if geo_response.status_code != 200:
                return None, f"Error fetching location: {geo_response.status_code}"
            
            geo_data = geo_response.json()
            if not geo_data:
                return None, f"Location '{city_name}' not found in Nepal"
            
            lat = geo_data[0]['lat']
            lon = geo_data[0]['lon']
            
            weather_params = {
                'lat': lat,
                'lon': lon,
                'appid': self.api_key,
                'units': 'metric'
            }
            
            weather_response = requests.get(self.base_url, params=weather_params)
            if weather_response.status_code != 200:
                return None, f"Error fetching weather: {weather_response.status_code}"
            
            weather_data = weather_response.json()
            return self._format_weather_data(weather_data, city_name), None
            
        except Exception as e:
            return None, f"API Error: {str(e)}"
    
    def _format_weather_data(self, data, city_name):
        main = data['main']
        weather = data['weather'][0]
        wind = data.get('wind', {})
        
        weather_icon = self._get_weather_icon(weather['main'])
        
        return {
            'city': city_name.title(),
            'temperature': round(main['temp']),
            'feels_like': round(main['feels_like']),
            'humidity': main['humidity'],
            'pressure': main['pressure'],
            'wind_speed': wind.get('speed', 0),
            'description': weather['description'].title(),
            'icon': weather_icon,
            'main': weather['main']
        }
    
    def _get_weather_icon(self, weather_main):
        icons = {
            'Clear': '☀️',
            'Clouds': '☁️',
            'Rain': '🌧️',
            'Drizzle': '🌦️',
            'Thunderstorm': '⛈️',
            'Snow': '❄️',
            'Mist': '🌫️',
            'Fog': '🌫️',
            'Haze': '🌫️'
        }
        return icons.get(weather_main, '🌤️')