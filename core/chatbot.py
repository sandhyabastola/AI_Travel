import os
import sys
import re
import random
import string
import difflib
import torch
import pandas as pd
from transformers import BertTokenizer, BertForSequenceClassification
import django
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Django setup ---
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_travel.settings')

try:
    django.setup()
    from core.weather import get_weather_data
except ImportError:
    logger.warning("Weather module not found. Weather functionality will be limited.")
    
    def get_weather_data(city):
        return {"error": "Weather service unavailable"}


class TravelChatbot:
    def __init__(self):
        self.base_dir = BASE_DIR
        self.intents = [
            "greeting", "farewell", "find_transport", "get_weather",
            "route", "recommendation", "trip_plan", "hotel_info", "unknown"
        ]
        
        # Keywords for different intents
        self.recommend_keywords = ["recommend", "suggest", "where to go", "places", 
                                 "destination", "visit", "tourist", "attraction"]
        self.hotel_keywords = ["hotel", "accommodation", "stay", "lodge", "resort"]
        self.transport_keywords = ["transport", "bus", "flight", "taxi", "travel"]
        
        # Initialize model and data
        self.load_model()
        self.load_datasets()
        self.setup_districts()
        
    def load_model(self):
        """Load BERT model with error handling"""
        try:
            # Your specific model path first, then fallback options
            possible_paths = [
                Path(r"I:\7th sem\Final Year Project\Datasets\bert_chatbot_model"),  # Your specific path
                Path(self.base_dir / "models" / "bert_chatbot_model"),  # Relative path option 1
                Path(self.base_dir / "bert_chatbot_model"),  # Current directory
                Path("I:/7th sem/Final Year Project/Datasets/bert_chatbot_model"),  # Alternative forward slash
            ]
            
            model_path = None
            for path in possible_paths:
                try:
                    if path.exists():
                        model_path = path
                        logger.info(f"Found BERT model at: {path}")
                        break
                except Exception as path_error:
                    logger.debug(f"Could not access path {path}: {path_error}")
                    continue
                    
            if model_path:
                logger.info(f"Loading BERT model from: {model_path}")
                self.tokenizer = BertTokenizer.from_pretrained(str(model_path))
                self.model = BertForSequenceClassification.from_pretrained(str(model_path))
                self.model.eval()
                logger.info("BERT model loaded successfully")
                
                # Set device (GPU if available)
                if torch.cuda.is_available():
                    self.model = self.model.cuda()
                    logger.info("Model moved to GPU")
                else:
                    logger.info("Using CPU for model inference")
                    
            else:
                logger.warning("BERT model not found at any of the specified paths. Using rule-based classification only.")
                logger.info("Searched paths:")
                for path in possible_paths:
                    logger.info(f"  - {path}")
                self.tokenizer = None
                self.model = None
                
        except Exception as e:
            logger.error(f"Error loading BERT model: {e}")
            self.tokenizer = None
            self.model = None
    
    def load_datasets(self):
        """Load all CSV datasets with error handling"""
        datasets = {
            'recommendations': 'data/nepal_dataset.csv',
            'destinations': 'core/data/nepal_destinations.csv',
            'hotels': 'core/data/nepal_hotels.csv',
            'transport': 'core/data/nepal_transport_dataset.csv',
            'travel': 'core/data/nepal_travel_dataset.csv'
        }
        
        self.datasets = {}
        
        for name, path in datasets.items():
            try:
                full_path = self.base_dir / path
                if full_path.exists():
                    self.datasets[name] = pd.read_csv(full_path)
                    logger.info(f"Loaded {name} dataset: {len(self.datasets[name])} records")
                else:
                    logger.warning(f"Dataset not found: {path}")
                    self.datasets[name] = pd.DataFrame()
            except Exception as e:
                logger.error(f"Error loading {name} dataset: {e}")
                self.datasets[name] = pd.DataFrame()
    
    def setup_districts(self):
        """Setup Nepali districts for location extraction"""
        self.nepali_districts = [
            # Koshi Province
            "Bhojpur", "Dhankuta", "Ilam", "Jhapa", "Khotang", "Morang", 
            "Okhaldhunga", "Panchthar", "Sankhuwasabha", "Solukhumbu", 
            "Sunsari", "Taplejung", "Terhathum", "Udayapur",
            
            # Madhesh Province
            "Bara", "Dhanusha", "Mahottari", "Parsa", "Rautahat", 
            "Saptari", "Sarlahi", "Siraha",
            
            # Bagmati Province
            "Bhaktapur", "Chitwan", "Dhading", "Dolakha", "Kathmandu", 
            "Kavrepalanchok", "Lalitpur", "Makwanpur", "Nuwakot", 
            "Ramechhap", "Rasuwa", "Sindhuli", "Sindhupalchok",
            
            # Gandaki Province
            "Baglung", "Gorkha", "Kaski", "Lamjung", "Manang", "Mustang", 
            "Myagdi", "Nawalpur", "Parbat", "Syangja", "Tanahun",
            
            # Lumbini Province
            "Arghakhanchi", "Banke", "Bardiya", "Dang", "Eastern Rukum", 
            "Gulmi", "Kapilvastu", "Parasi", "Palpa", "Pyuthan", 
            "Rolpa", "Rupandehi",
            
            # Karnali Province
            "Dailekh", "Dolpa", "Humla", "Jajarkot", "Jumla", "Kalikot", 
            "Mugu", "Salyan", "Surkhet", "Western Rukum",
            
            # Sudurpashchim Province
            "Achham", "Baitadi", "Bajhang", "Bajura", "Dadeldhura", 
            "Darchula", "Doti", "Kailali", "Kanchanpur"
        ]
        
        # Popular cities and tourist destinations
        self.popular_places = [
            "Pokhara", "Chitwan", "Lumbini", "Everest Base Camp", "Annapurna", 
            "Bandipur", "Gorkha", "Janakpur", "Biratnagar", "Nepalgunj",
            "Butwal", "Hetauda", "Dharan", "Itahari", "Bharatpur"
        ]
        
        self.all_locations = self.nepali_districts + self.popular_places
        self.all_locations_lower = [loc.lower() for loc in self.all_locations]
    
    def normalize_location(self, token: str):
        """Normalize location names with fuzzy matching"""
        token = token.strip().lower()
        if not token:
            return None, False
            
        # Exact match
        if token in self.all_locations_lower:
            idx = self.all_locations_lower.index(token)
            return self.all_locations[idx], True
            
        # Fuzzy match
        matches = difflib.get_close_matches(token, self.all_locations_lower, n=1, cutoff=0.75)
        if matches:
            idx = self.all_locations_lower.index(matches[0])
            return self.all_locations[idx], True
            
        return token.capitalize(), False
    
    def extract_locations(self, message: str):
        """Extract locations from user message"""
        msg = message.lower()
        
        # Pattern: "from X to Y"
        pattern1 = re.search(r'from\s+([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)', msg)
        if pattern1:
            loc1, _ = self.normalize_location(pattern1.group(1).strip())
            loc2, _ = self.normalize_location(pattern2.group(2).strip())
            return [loc1, loc2]
        
        # Pattern: "X to Y"
        pattern2 = re.search(r'([a-zA-Z\s]+?)\s+to\s+([a-zA-Z\s]+)', msg)
        if pattern2:
            loc1, _ = self.normalize_location(pattern2.group(1).strip())
            loc2, _ = self.normalize_location(pattern2.group(2).strip())
            return [loc1, loc2]
        
        # Find all potential locations in the message
        words = re.findall(r'\w+', msg)
        locations = []
        
        # Check for compound location names (2-3 words)
        for i in range(len(words)):
            for j in range(2, 4):  # Check 2-3 word combinations
                if i + j <= len(words):
                    compound = " ".join(words[i:i+j])
                    loc, matched = self.normalize_location(compound)
                    if matched and loc not in locations:
                        locations.append(loc)
        
        # Check individual words
        for word in words:
            if len(word) > 2:  # Avoid very short words
                loc, matched = self.normalize_location(word)
                if matched and loc not in locations:
                    locations.append(loc)
        
        return locations
    
    def predict_intent_bert(self, user_input: str) -> str:
        """BERT-based intent prediction (for backward compatibility)"""
        return self.predict_intent(user_input)
    
    def predict_intent(self, user_input: str) -> str:
        """Predict intent using rules and BERT model"""
        msg = user_input.lower().strip()
        
        # Rule-based classification first (for common patterns)
        if any(word in msg for word in ["hi", "hello", "hey", "namaste"]):
            return "greeting"
        
        if any(word in msg for word in ["bye", "goodbye", "see you", "thanks", "thank you"]):
            return "farewell"
        
        if any(word in msg for word in ["weather", "temperature", "forecast", "climate"]):
            return "get_weather"
        
        if any(word in msg for word in self.hotel_keywords):
            return "hotel_info"
        
        if " from " in msg and " to " in msg:
            return "find_transport"
        
        if re.search(r'\b\w+\s+to\s+\w+\b', msg):
            return "find_transport"
        
        if any(word in msg for word in self.recommend_keywords):
            return "recommendation"
        
        trip_indicators = ["want to go", "visit", "go to", "travel to", "planning to", "trip"]
        if any(phrase in msg for phrase in trip_indicators):
            return "trip_plan"
        
        # Use BERT model if available
        if self.model and self.tokenizer:
            try:
                # Tokenize input
                inputs = self.tokenizer(
                    user_input, 
                    return_tensors="pt", 
                    truncation=True, 
                    padding=True, 
                    max_length=128
                )
                
                # Move inputs to same device as model
                if torch.cuda.is_available() and hasattr(self.model, 'device'):
                    inputs = {key: val.cuda() for key, val in inputs.items()}
                
                # Get prediction
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
                    predicted_class = torch.argmax(probs, dim=-1).item()
                    confidence = torch.max(probs).item()
                
                # Use BERT prediction if confidence is high enough
                if confidence > 0.6 and predicted_class < len(self.intents):
                    logger.debug(f"BERT prediction: {self.intents[predicted_class]} (confidence: {confidence:.3f})")
                    return self.intents[predicted_class]
                else:
                    logger.debug(f"Low confidence BERT prediction, using rule-based fallback")
                    
            except Exception as e:
                logger.error(f"Error in BERT prediction: {e}")
        
        return "unknown"
    
    def get_transport_info(self, origin, destination):
        """Get transport information between two locations"""
        if self.datasets['transport'].empty:
            return f"🚌 General transport options from {origin} to {destination}:\n" \
                   "• Tourist Bus: Comfortable for long distances\n" \
                   "• Local Bus: Budget-friendly option\n" \
                   "• Private Taxi: Door-to-door service\n" \
                   "• Domestic Flight: Available for major cities"
        
        # Search transport dataset
        transport_df = self.datasets['transport']
        
        # Try to find specific routes
        routes = transport_df[
            (transport_df['origin'].str.contains(origin, case=False, na=False)) &
            (transport_df['destination'].str.contains(destination, case=False, na=False))
        ]
        
        if routes.empty:
            # Search for either origin or destination
            routes = transport_df[
                (transport_df['origin'].str.contains(origin, case=False, na=False)) |
                (transport_df['destination'].str.contains(destination, case=False, na=False)) |
                (transport_df['route'].str.contains(f"{origin}|{destination}", case=False, na=False))
            ]
        
        if not routes.empty:
            response = f"🚌 Transport options from {origin} to {destination}:\n"
            for _, route in routes.head(3).iterrows():
                mode = route.get('transport_mode', 'Bus')
                duration = route.get('duration', 'N/A')
                cost = route.get('cost', 'N/A')
                response += f"• {mode}: Duration {duration}, Cost: Rs. {cost}\n"
            return response
        else:
            return f"🚌 Popular transport from {origin} to {destination}:\n" \
                   "• Tourist Bus: 6-12 hours depending on distance\n" \
                   "• Private Car: Faster but more expensive\n" \
                   "• Domestic Flight: Available between major cities"
    
    def get_hotel_recommendations(self, location):
        """Get hotel recommendations for a location"""
        if self.datasets['hotels'].empty:
            return f"🏨 I don't have specific hotel data for {location}, but I recommend checking:\n" \
                   "• Booking.com\n• Hotels.com\n• Local travel agencies"
        
        hotels_df = self.datasets['hotels']
        
        # Search for hotels in the location
        location_hotels = hotels_df[
            hotels_df['location'].str.contains(location, case=False, na=False) |
            hotels_df['city'].str.contains(location, case=False, na=False) |
            hotels_df['district'].str.contains(location, case=False, na=False)
        ]
        
        if not location_hotels.empty:
            response = f"🏨 Recommended hotels in {location}:\n"
            for _, hotel in location_hotels.head(3).iterrows():
                name = hotel.get('hotel_name', 'Unknown Hotel')
                category = hotel.get('category', 'Standard')
                price = hotel.get('price_range', 'N/A')
                response += f"• {name} ({category}) - Price: {price}\n"
            return response
        else:
            return f"🏨 No specific hotel data found for {location}. Try searching for accommodations in nearby major cities."
    
    def get_destination_recommendations(self, user_message):
        """Enhanced recommendation system"""
        if self.datasets['recommendations'].empty and self.datasets['destinations'].empty:
            return "Sorry, I don't have destination data available right now."
        
        # Combine recommendation and destination datasets
        recommendations = []
        
        if not self.datasets['recommendations'].empty:
            recommendations.append(self.datasets['recommendations'])
        
        if not self.datasets['destinations'].empty:
            recommendations.append(self.datasets['destinations'])
        
        if recommendations:
            combined_df = pd.concat(recommendations, ignore_index=True)
        else:
            return "No destination data available."
        
        # Extract preferences from user message
        message_lower = user_message.lower()
        
        # Category preferences
        categories = {
            'adventure': ['adventure', 'trekking', 'hiking', 'mountain', 'climbing'],
            'cultural': ['culture', 'temple', 'heritage', 'historical', 'traditional'],
            'nature': ['nature', 'wildlife', 'forest', 'park', 'scenic'],
            'religious': ['religious', 'pilgrimage', 'temple', 'monastery', 'spiritual'],
            'recreational': ['fun', 'entertainment', 'recreational', 'leisure']
        }
        
        # Budget preferences
        budget_keywords = {
            'budget': ['budget', 'cheap', 'affordable', 'low cost'],
            'luxury': ['luxury', 'expensive', 'premium', 'high end'],
            'mid-range': ['moderate', 'mid range', 'average']
        }
        
        # Extract location preferences
        locations = self.extract_locations(user_message)
        
        # Filter recommendations
        filtered_df = combined_df.copy()
        
        # Filter by location if specified
        if locations:
            location_filter = pd.Series([False] * len(filtered_df))
            for loc in locations:
                location_filter |= (
                    filtered_df['location'].str.contains(loc, case=False, na=False) |
                    filtered_df['district'].str.contains(loc, case=False, na=False) |
                    filtered_df.get('Destination Name', pd.Series()).str.contains(loc, case=False, na=False)
                )
            filtered_df = filtered_df[location_filter]
        
        # Filter by category
        for category, keywords in categories.items():
            if any(keyword in message_lower for keyword in keywords):
                if 'category' in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df['category'].str.contains(category, case=False, na=False)
                    ]
                break
        
        # Filter by budget
        for budget, keywords in budget_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                if 'budget_level' in filtered_df.columns:
                    filtered_df = filtered_df[
                        filtered_df['budget_level'].str.contains(budget, case=False, na=False)
                    ]
                break
        
        # If no results after filtering, get random popular destinations
        if filtered_df.empty:
            filtered_df = combined_df.sample(min(5, len(combined_df)))
        
        # Generate response
        response = "🏔️ Here are some destinations you might love:\n\n"
        
        for _, dest in filtered_df.head(5).iterrows():
            name = dest.get('Destination Name') or dest.get('destination_name', 'Unknown')
            location = dest.get('location', dest.get('district', 'Nepal'))
            description = dest.get('description', dest.get('Description', 'A beautiful destination'))
            category = dest.get('category', 'Tourist Spot')
            
            # Truncate description
            if len(description) > 150:
                description = description[:150] + "..."
            
            response += f"📍 **{name}** ({location})\n"
            response += f"   Category: {category}\n"
            response += f"   {description}\n\n"
        
        return response
    
    def get_weather_info(self, locations, time_ref="today"):
        """Get weather information for locations"""
        if not locations:
            return "Please specify a location for weather information."
        
        location = locations[0]
        weather_data = get_weather_data(location)
        
        if not weather_data or "error" in weather_data:
            return f"Sorry, I couldn't fetch current weather data for {location}. " \
                   f"Please check online weather services."
        
        try:
            forecast = weather_data.get("forecast", [{}])[0]
            temperature = forecast.get('temp', 'N/A')
            description = forecast.get('description', 'No description available')
            datetime = forecast.get('datetime', 'Unknown time')
            
            return f"🌤️ Weather in {location} ({time_ref}):\n" \
                   f"Temperature: {temperature}°C\n" \
                   f"Conditions: {description}\n" \
                   f"Time: {datetime}"
        except Exception as e:
            logger.error(f"Error parsing weather data: {e}")
            return f"Weather data for {location} is currently unavailable."
    
    def chatbot(self, message: str) -> str:
        """Main chatbot method (for backward compatibility)"""
        return self.get_response(message)
    
    def get_response(self, message: str) -> str:
        """Main method to get chatbot response"""
        intent = self.predict_intent(message)
        locations = self.extract_locations(message)
        
        if intent == "greeting":
            greetings = [
                "Namaste! 🙏 I'm your AI travel assistant for Nepal. How can I help you today?",
                "Hello! 👋 Ready to explore Nepal? I can help with destinations, transport, hotels, and weather!",
                "Hi there! ✈️ I'm here to help you plan your perfect Nepal adventure!"
            ]
            return random.choice(greetings)
        
        elif intent == "farewell":
            farewells = [
                "Dhanyabad! 🙏 Have an amazing journey! Safe travels!",
                "Goodbye! 👋 Enjoy your adventure in beautiful Nepal! ✈️",
                "See you soon! 🌄 May your travels be filled with wonderful memories!"
            ]
            return random.choice(farewells)
        
        elif intent == "find_transport":
            if len(locations) < 2:
                return "🚌 Please tell me your starting point and destination. " \
                       "For example: 'transport from Kathmandu to Pokhara'"
            return self.get_transport_info(locations[0], locations[1])
        
        elif intent == "get_weather":
            time_ref = "tomorrow" if "tomorrow" in message.lower() else "today"
            return self.get_weather_info(locations, time_ref)
        
        elif intent == "hotel_info":
            if not locations:
                return "🏨 Please specify a location for hotel recommendations. " \
                       "For example: 'hotels in Pokhara'"
            return self.get_hotel_recommendations(locations[0])
        
        elif intent == "recommendation":
            return self.get_destination_recommendations(message)
        
        elif intent == "trip_plan":
            if not locations:
                return "🗺️ Where are you planning to go? I can help you plan your trip!"
            
            location = locations[0]
            time_ref = "tomorrow" if "tomorrow" in message.lower() else "today"
            
            response = f"🎯 Planning your trip to {location}:\n\n"
            
            # Add destination info
            if not self.datasets['destinations'].empty:
                dest_info = self.datasets['destinations'][
                    self.datasets['destinations']['location'].str.contains(location, case=False, na=False)
                ]
                if not dest_info.empty:
                    dest = dest_info.iloc[0]
                    response += f"📍 About {location}: {dest.get('description', 'A wonderful destination')}\n\n"
            
            response += "I can help you with:\n"
            response += f"🏨 Hotels in {location}\n"
            response += f"🚌 Transport to {location}\n"
            response += f"🌤️ Weather forecast\n"
            response += f"📸 Popular attractions\n\n"
            response += "What specific information would you like?"
            
            return response
        
        else:
            return "🤔 I'm not quite sure what you're looking for. I can help you with:\n" \
                   "• Destination recommendations\n" \
                   "• Transport information\n" \
                   "• Hotel suggestions\n" \
                   "• Weather updates\n" \
                   "• Trip planning\n\n" \
                   "Try asking something like 'recommend places in Kathmandu' or 'transport from Pokhara to Chitwan'"


# Initialize the chatbot
chatbot = TravelChatbot()

# Backward compatibility functions for Django views
def predict_intent_bert(user_input: str) -> str:
    """For backward compatibility with existing Django views"""
    return chatbot.predict_intent_bert(user_input)

def get_chatbot_response(message: str) -> str:
    """Main function to get chatbot response"""
    try:
        return chatbot.get_response(message)
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return "Sorry, I encountered an error. Please try rephrasing your question."

def recommend_reply(user_message: str):
    """For backward compatibility"""
    return chatbot.get_destination_recommendations(user_message)

def extract_locations(message: str):
    """For backward compatibility"""
    return chatbot.extract_locations(message)

def extract_time_reference(message: str):
    """For backward compatibility"""
    return "tomorrow" if "tomorrow" in message.lower() else "today"

# Original function name for backward compatibility
def chatbot_func(message: str) -> str:
    return get_chatbot_response(message)

# Command line interface
if __name__ == "__main__":
    print("🏔️ Nepal AI Travel Assistant is ready! Type 'exit' to quit.\n")
    print("Try asking about:")
    print("- Destinations: 'recommend places in Kathmandu'")
    print("- Transport: 'bus from Kathmandu to Pokhara'")
    print("- Hotels: 'hotels in Pokhara'")
    print("- Weather: 'weather in Chitwan'")
    print("- Trip planning: 'plan trip to Everest Base Camp'\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in ["exit", "quit", "bye"]:
                print("YatriBot: Dhanyabad! Have a great journey! 🙏")
                break
            
            if user_input:
                print("YatriBot:", get_chatbot_response(user_input))
            print()  # Add blank line for readability
            
        except KeyboardInterrupt:
            print("\nYatriBot: Goodbye! Safe travels! 👋")
            break
        except Exception as e:
            print(f"Error: {e}")