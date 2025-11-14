import os
import pandas as pd
import torch
import re
import numpy as np
import requests
import csv
from transformers import BertTokenizer, BertForSequenceClassification
from django.conf import settings
from django.db.models import Q
from django.contrib.auth.models import User

# Import your models (adjust import path as needed)
try:
    from your_app.models import Destination, LikeRating
except ImportError:
    # Fallback for when models aren't available
    class Destination:
        pass
    class LikeRating:
        pass

class ContentBasedRecommendationSystem:
    def __init__(self):
        self.data = []
        self.load_data()

    def load_data(self):
        dataset_path = os.path.join(settings.DATA_DIR, 'nepal_dataset.csv')
        try:
            with open(dataset_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                unique_places = set()
                for row in reader:
                    name = row.get('name', '').strip()
                    if not name or name in unique_places:
                        continue
                    unique_places.add(name)

                    self.data.append({
                        'place_id': row.get('place_id', '').strip(),
                        'name': name,
                        'category': row.get('category', '').strip().lower(),
                        'travel_style': row.get('travel_style', '').strip().lower(),
                        'weather': row.get('weather', '').strip().lower(),
                        'budget_level': row.get('budget_level', '').strip().lower(),
                        'description': row.get('description', '').strip(),
                        'img_url': row.get('img_url', '').strip(),
                        'district': row.get('district', '').strip(),
                        'location': row.get('location', '').strip(),
                    })
            print(f"✅ Loaded {len(self.data)} places for recommendations")
        except Exception as e:
            print(f"❌ Error loading recommendation data: {e}")

    def normalize_weather_input(self, weather_str):
        if not weather_str:
            return "any"
        weather_str = str(weather_str).lower()

        if "sun" in weather_str or "clear" in weather_str:
            return "sunny"
        elif "rain" in weather_str or "shower" in weather_str:
            return "rainy"
        elif "snow" in weather_str or "cold" in weather_str:
            return "snowy"
        elif "cloud" in weather_str or "overcast" in weather_str:
            return "cloudy"
        elif "warm" in weather_str or "mild" in weather_str:
            return "warm"
        return "any"

    def map_budget_amount_to_level(self, amount):
        if not amount:
            return 'low'
        if isinstance(amount, str):
            amount = re.sub(r'[^\d.]', '', amount)
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            return 'low'

        if amount <= 1500:
            return 'low'
        elif amount <= 4000:
            return 'medium'
        return 'high'

    def _score_places(self, place, travel_style, weather, budget_amount,
                      destination=None, category=None):
        total_score = 0

        # Destination filter
        if destination:
            dest = destination.lower()
            if (dest in place.get('location', '').lower() or 
                dest in place.get('district', '').lower()):
                total_score += 500
            else:
                return 0

        # Travel style
        place_styles = re.split(r'[;,]', place.get('travel_style', '').lower())
        place_styles = [s.strip() for s in place_styles if s.strip()]
        if travel_style:
            if travel_style not in place_styles:
                return 0
            total_score += 200

        # Category
        place_category = place.get('category', '').strip().lower()
        if category and place_category == category:
            total_score += 150

        # Weather
        place_weather = self.normalize_weather_input(place.get('weather', ''))
        weather_normalized = self.normalize_weather_input(weather)
        if weather_normalized != 'any':
            if place_weather == weather_normalized:
                total_score += 60
            elif weather_normalized in place_weather:
                total_score += 30

        # Budget
        place_budget = place.get('budget_level', 'low').lower()
        user_budget = self.map_budget_amount_to_level(budget_amount)
        if place_budget == user_budget:
            total_score += 40
        elif place_budget in ("medium", "low") and user_budget == "high":
            total_score += 20

        return total_score

    def recommend(self, travel_style, weather, budget_amount,
                  destination=None, travel_route=None, category=None, top_k=5):
        scored_places = []

        for place in self.data:
            score = self._score_places(
                place, travel_style, weather, budget_amount,
                destination, category
            )
            if score > 0:
                scored_places.append((score, place))

        scored_places.sort(key=lambda x: x[0], reverse=True)
        return [place for _, place in scored_places[:top_k]]


class LocationBasedSearch:
    """Search destinations from database"""
    
    def search_by_location(self, query):
        """Search destinations in database"""
        print(f"Searching database for: '{query}'")
        
        if not query:
            destinations = Destination.objects.all().order_by('name')[:20]
            print(f"No query - showing first 20 destinations")
        else:
            destinations = Destination.objects.filter(
                Q(name__icontains=query) |
                Q(district__icontains=query) |
                Q(description__icontains=query)
            ).order_by('name')
            print(f"Found {destinations.count()} destinations matching '{query}'")
        
        results = []
        for dest in destinations:
            results.append({
                'id': dest.id,
                'name': dest.name,
                'location': dest.district or '',
                'district': dest.district or '',
                'description': dest.description or '',
                'img_url': dest.img_url or '',
            })
        
        print(f"Returning {len(results)} results")
        return results


class ContentBasedRecommender:
    """Find similar destinations from database"""
    
    def recommend_similar(self, place_name, top_n=5):
        """Find destinations similar to the given place"""
        print(f"Looking for recommendations similar to: '{place_name}'")
        
        try:
            target = Destination.objects.get(name__iexact=place_name)
            print(f"Found target destination: {target.name} in {target.district}")
        except Destination.DoesNotExist:
            print(f"Target destination '{place_name}' not found in database")
            return []
        
        similar = Destination.objects.filter(
            district=target.district
        ).exclude(id=target.id).order_by('name')[:top_n]
        
        print(f"Found {similar.count()} similar destinations in {target.district}")
        
        results = []
        for dest in similar:
            results.append({
                'id': dest.id,
                'name': dest.name,
                'location': dest.district or '',
                'district': dest.district or '',
                'description': dest.description or '',
                'img_url': dest.img_url or '',
            })
        
        return results


class UserBasedRecommender:
    """User recommendations based on likes"""
    
    @staticmethod
    def recommend_from_likes(user: User, top_n=5):
        """Recommend destinations based on user's liked places"""
        print(f"Getting recommendations for user: {user.username}")
        
        liked_destinations = LikeRating.objects.filter(
            user=user, 
            liked=True
        ).values_list('destination_id', flat=True)
        
        print(f"User has liked {len(liked_destinations)} destinations")
        
        if not liked_destinations:
            recommendations = Destination.objects.all().order_by('name')[:top_n]
        else:
            recommendations = Destination.objects.exclude(
                id__in=liked_destinations
            ).order_by('name')[:top_n]
        
        results = []
        for dest in recommendations:
            results.append({
                'id': dest.id,
                'name': dest.name,
                'location': dest.district or '',
                'district': dest.district or '',
                'description': dest.description or '',
                'img_url': dest.img_url or '',
            })
        
        print(f"Returning {len(results)} user recommendations")
        return results


class WeatherAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
    
    def get_weather(self, city_name, country_code="NP"):
        """Get current weather data from OpenWeather API"""
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
        """Format weather data for display"""
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
        """Convert weather condition to emoji"""
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


class ChatBotEngine:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.tokenizer, self.model, self.device = self._load_model_and_tokenizer()
        self.hotel_df, self.travel_df, self.weather_df = self._load_datasets()
        self.weather_api = WeatherAPI(settings.OPENWEATHER_API_KEY)
        self.recommendation_engine = ContentBasedRecommendationSystem()
        self.location_search = LocationBasedSearch()
        self.content_recommender = ContentBasedRecommender()
        
    def _load_model_and_tokenizer(self):
        """Load the trained model and tokenizer"""
        try:
            model_path = os.path.join(settings.DATA_DIR, 'chatbot_model')
            
            if not os.path.exists(model_path):
                print("Using rule-based system (AI model not found)")
                return None, None, None
                
            tokenizer = BertTokenizer.from_pretrained(model_path)
            model = BertForSequenceClassification.from_pretrained(model_path)
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            model.to(device)
            model.eval()
            print("AI Model loaded successfully!")
            return tokenizer, model, device
        except Exception as e:
            print(f"Using rule-based system: {e}")
            return None, None, None

    def _load_datasets(self):
        """Load all required datasets"""
        try:
            data_dir = settings.DATA_DIR
            
            hotel_df = pd.read_csv(os.path.join(data_dir, 'nepal_hotels.csv'))
            travel_df = pd.read_csv(os.path.join(data_dir, 'nepal_travel_dataset.csv'))
            weather_df = pd.read_csv(os.path.join(data_dir, 'nepal_destinations.csv'))
            
            if 'travel_route' in travel_df.columns:
                travel_df = travel_df[travel_df['travel_route'].notna() & (travel_df['travel_route'] != '')]
            
            print("All datasets loaded successfully!")
            return hotel_df, travel_df, weather_df
            
        except Exception as e:
            print(f"Error loading datasets: {e}")
            hotel_df = pd.DataFrame({
                'HotelName': ['Yak & Yeti Hotel', 'Hotel Annapurna'],
                'City': ['Kathmandu', 'Kathmandu'],
                'Price': [15000, 8000],
                'Type': ['Luxury', 'Business']
            })
            travel_df = pd.DataFrame({
                'district': ['Kathmandu', 'Pokhara'],
                'attraction': ['Thamel', 'Lakeside'],
                'travel_route': ['Kathmandu to Pokhara', 'Pokhara to Kathmandu'],
                'budget': [1200, 1200]
            })
            return hotel_df, travel_df, None

    def preprocess_text(self, text):
        """Preprocess text for better intent recognition"""
        text_lower = text.lower().strip()
        
        corrections = {
            'westher': 'weather',
            'pakbara': 'pokhara',
            'katmandu': 'kathmandu',
            'kathmandu': 'kathmandu',
            'chitwan': 'chitwan',
            'lumbini': 'lumbini',
            'nagarkot': 'nagarkot',
            'fuel': 'hotel',
            'final': 'find',
            'transport': 'transport',
            'route': 'route',
            'travel': 'travel',
            'recommend': 'recommend',
            'suggest': 'suggest',
            'places': 'places',
            'visit': 'visit'
        }
        
        words = text_lower.split()
        corrected_words = [corrections.get(word, word) for word in words]
        return ' '.join(corrected_words)
    
    def rule_based_intent_detection(self, text):
        """Enhanced rule-based intent detection"""
        processed_text = self.preprocess_text(text)
        
        patterns = {
            'hotel_search': [
                r'.*hotel.*', r'.*stay.*', r'.*accommodation.*', 
                r'.*book.*room.*', r'.*find.*hotel.*'
            ],
            'weather': [
                r'.*weather.*', r'.*temperature.*', r'.*rain.*', 
                r'.*sunny.*', r'.*climate.*', r'.*how.*hot.*'
            ],
            'transport': [
                r'.*transport.*', r'.*travel.*', r'.*route.*', 
                r'.*how.*get.*', r'.*from.*to.*', r'.*go.*to.*'
            ],
            'recommendation': [
                r'.*recommend.*', r'.*suggest.*', r'.*places.*to.*visit.*',
                r'.*what.*see.*', r'.*where.*go.*', r'.*best.*places.*',
                r'.*top.*attractions.*', r'.*must.*see.*', r'.*popular.*places.*'
            ],
            'greeting': [
                r'^hello.*', r'^hi.*', r'^namaste.*', r'^hey.*'
            ],
            'farewell': [
                r'.*bye.*', r'.*goodbye.*', r'.*see you.*', r'.*thank you.*'
            ]
        }
        
        intent_scores = {}
        for intent, intent_patterns in patterns.items():
            score = sum(1 for pattern in intent_patterns if re.search(pattern, processed_text, re.IGNORECASE))
            intent_scores[intent] = score
        
        best_intent = max(intent_scores, key=intent_scores.get)
        return best_intent if intent_scores[best_intent] > 0 else 'general_query'

    def extract_recommendation_params(self, text):
        """Extract parameters for recommendations from user input"""
        processed_text = self.preprocess_text(text)
        
        params = {
            'travel_style': None,
            'weather': None,
            'budget': None,
            'destination': None,
            'category': None
        }
        
        # Extract travel style
        styles = ['adventure', 'cultural', 'trekking', 'relaxation', 'wildlife', 'religious', 'historical']
        for style in styles:
            if style in processed_text:
                params['travel_style'] = style
                break
        
        # Extract budget
        budget_match = re.search(r'(\d+)\s*(rs|npr|rupees)?', processed_text)
        if budget_match:
            params['budget'] = budget_match.group(1)
        
        # Extract destination
        location_match = re.search(r'in\s+([a-zA-Z\s]+)', processed_text)
        if location_match:
            params['destination'] = location_match.group(1).strip().title()
        
        # Extract category
        categories = ['heritage', 'temple', 'museum', 'park', 'lake', 'mountain']
        for category in categories:
            if category in processed_text:
                params['category'] = category
                break
        
        return params

    def handle_recommendation_query(self, user_input):
        """Handle travel recommendations"""
        params = self.extract_recommendation_params(user_input)
        
        print(f"Recommendation params: {params}")
        
        # Get recommendations
        recommendations = self.recommendation_engine.recommend(
            travel_style=params['travel_style'],
            weather=params['weather'],
            budget_amount=params['budget'],
            destination=params['destination'],
            category=params['category'],
            top_k=5
        )
        
        if not recommendations:
            return "❌ No matching places found. Try different criteria."
        
        response = "🌟 Recommendations: "
        rec_list = []
        for i, place in enumerate(recommendations, 1):
            rec_list.append(f"{i}. {place['name']} ({place['district']})")
        response += " | ".join(rec_list)
        
        return response

    def predict_intent(self, text):
        """Predict the intent of user input"""
        return self.rule_based_intent_detection(text)

    def extract_location(self, text, label):
        """Extract location from user input"""
        processed_text = self.preprocess_text(text)
        
        if label == "hotel_search":
            patterns = [
                r'hotel.*in\s+([a-zA-Z\s]+)',
                r'stay.*in\s+([a-zA-Z\s]+)',
                r'accommodation.*in\s+([a-zA-Z\s]+)',
                r'find.*hotel.*in\s+([a-zA-Z\s]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, processed_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip().title()
            return "Kathmandu"
        
        elif label == "weather":
            patterns = [
                r'weather.*in\s+([a-zA-Z\s]+)',
                r'temperature.*in\s+([a-zA-Z\s]+)',
                r'how.*weather.*in\s+([a-zA-Z\s]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, processed_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip().title()
            return "Pokhara"
        
        elif label == "transport":
            patterns = [
                r'from\s+([a-zA-Z\s]+)\s+to\s+([a-zA-Z\s]+)',
                r'travel.*from\s+([a-zA-Z\s]+)\s+to\s+([a-zA-Z\s]+)',
                r'go.*from\s+([a-zA-Z\s]+)\s+to\s+([a-zA-Z\s]+)'
            ]
            for pattern in patterns:
                match = re.search(pattern, processed_text, re.IGNORECASE)
                if match:
                    from_loc = match.group(1).strip().title()
                    to_loc = match.group(2).strip().title()
                    return (from_loc, to_loc)
            return (None, None)
        
        return None

    def handle_hotel_search(self, location):
        """Handle hotel search queries"""
        if self.hotel_df is None:
            return "❌ Hotel database unavailable."
            
        location_clean = location.strip().title()
        
        hotels_in_location = self.hotel_df[
            self.hotel_df['City'].str.lower().str.strip() == location_clean.lower().strip()
        ]
        
        if hotels_in_location.empty:
            hotels_in_location = self.hotel_df[
                self.hotel_df['City'].str.lower().str.contains(location_clean.lower().strip())
            ]
        
        if hotels_in_location.empty:
            return f"❌ No hotels found in {location_clean}."
        
        hotels = hotels_in_location.head(3)
        hotel_list = [f"{row['HotelName']} (NPR {row.get('Price', 'N/A')})" for _, row in hotels.iterrows()]
        return f"🏨 Hotels in {location_clean}: " + " | ".join(hotel_list)

    def handle_weather_query(self, location):
        """Handle weather queries using OpenWeather API"""
        location_clean = location.strip().title()
        
        weather_data, error = self.weather_api.get_weather(location_clean)
        
        if weather_data:
            return f"{weather_data['icon']} {location_clean}: {weather_data['description']}, {weather_data['temperature']}°C, Feels like {weather_data['feels_like']}°C, Humidity {weather_data['humidity']}%"
        else:
            if self.weather_df is not None:
                weather_info = self.weather_df[
                    self.weather_df['District'].str.lower().str.strip() == location_clean.lower().strip()
                ]
                
                if not weather_info.empty:
                    row = weather_info.iloc[0]
                    return f"🌤️ {location_clean}: {row.get('Weather', 'N/A')}, {row.get('Temperature (°C)', row.get('Temperature', 'N/A'))}°C"
            
            return f"❌ Weather data for {location_clean} unavailable."

    def handle_transport_query(self, from_loc, to_loc):
        """Handle transport queries using travel dataset"""
        if self.travel_df is None or 'travel_route' not in self.travel_df.columns:
            return "❌ Transport database unavailable."
            
        from_loc_clean = from_loc.strip().title()
        to_loc_clean = to_loc.strip().title()
        
        matching_routes = []
        
        for _, row in self.travel_df.iterrows():
            if pd.notna(row.get('travel_route')):
                route = str(row['travel_route'])
                if (from_loc_clean.lower() in route.lower() and 
                    to_loc_clean.lower() in route.lower()):
                    matching_routes.append(row)
        
        if not matching_routes:
            return f"❌ No routes from {from_loc_clean} to {to_loc_clean}."
        
        route = matching_routes[0]
        return f"🗺️ {from_loc_clean}→{to_loc_clean}: {route.get('travel_route', 'N/A')} | Budget: NPR {route.get('budget', 'N/A')}"

    def get_response(self, user_input):
        """Get bot response based on user input"""
        intent = self.predict_intent(user_input)
        
        print(f"DEBUG: User: '{user_input}' -> Intent: {intent}")
        
        def safe_extract_location(input_text, intent_type):
            loc = self.extract_location(input_text, intent_type)
            if isinstance(loc, tuple):
                if not loc[0] or not loc[1]:
                    return None
                return loc
            else:
                if not loc:
                    return None
                return loc

        # Handle different intents
        if intent == "hotel_search":
            location = safe_extract_location(user_input, intent)
            if not location:
                return "❌ Specify location: 'Find hotels in Pokhara'", intent
            return self.handle_hotel_search(location), intent

        elif intent == "weather":
            location = safe_extract_location(user_input, intent)
            if not location:
                return "❌ Specify location: 'Weather in Kathmandu'", intent
            return self.handle_weather_query(location), intent

        elif intent == "transport":
            locations = safe_extract_location(user_input, intent)
            if not locations or len(locations) != 2:
                return "❌ Specify both locations: 'Transport from Kathmandu to Pokhara'", intent
            from_loc, to_loc = locations
            return self.handle_transport_query(from_loc, to_loc), intent

        elif intent == "recommendation":
            return self.handle_recommendation_query(user_input), intent

        elif intent == "greeting":
            greetings = [
                "👋 Namaste! I'm YatriBot - I help with hotels, weather, transport & recommendations in Nepal!",
                "🙏 Namaste! Ask me about places to visit, hotels, weather, or transport in Nepal!",
                "🏔️ Hello! I can recommend places, find hotels, check weather, and plan routes in Nepal!"
            ]
            return np.random.choice(greetings), intent

        elif intent == "farewell":
            farewells = [
                "👋 Dhanyabad! Have a wonderful journey!",
                "🙏 Goodbye! Enjoy your travels in Nepal!",
                "🏔️ Farewell! Stay safe and enjoy Nepal's beauty!"
            ]
            return np.random.choice(farewells), intent

        else:
            if any(word in user_input.lower() for word in ['hotel', 'stay', 'accommodation']):
                return "🏨 Specify location: 'Find hotels in Kathmandu'", "hotel_search"
            elif any(word in user_input.lower() for word in ['weather', 'temperature', 'rain']):
                return "🌤️ Specify location: 'Weather in Pokhara'", "weather"
            elif any(word in user_input.lower() for word in ['transport', 'travel', 'route', 'from', 'to']):
                return "🗺️ Specify both locations: 'Travel from Kathmandu to Pokhara'", "transport"
            elif any(word in user_input.lower() for word in ['recommend', 'suggest', 'places', 'visit', 'see']):
                return "🌟 Try: 'Recommend adventure places in Pokhara with 2000 budget'", "recommendation"
            else:
                return "😕 I help with travel recommendations, hotels, weather, and transport in Nepal.", "general_query"