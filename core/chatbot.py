import torch
from transformers import BertTokenizer, BertForSequenceClassification
import re
import os
import sys
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # add project base dir to path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_travel.settings')
django.setup()

from core.weather import get_weather_data
from core.recommendation_model import get_recommendations
from difflib import get_close_matches

# Dynamically build the absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'C:\\Users\\rayam\\Downloads\\bert_chatbot_model')

# Normalize and convert to absolute path
MODEL_PATH = os.path.normpath(os.path.abspath(MODEL_PATH))

# Load tokenizer and model
tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)

model.eval()

# Match index to intent labels (must match your training)
INTENT_LABELS = ["get_weather", "find_transport", "plan_trip", "recommend_destination", "greeting", "farewell", "unknown"]

def predict_intent_bert(message):
    inputs = tokenizer(message, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    logits = outputs.logits
    predicted_class_id = torch.argmax(logits, dim=1).item()
    return INTENT_LABELS[predicted_class_id]

def extract_location(message):
    known_locations = ["kathmandu", "pokhara", "biratnagar", "chitwan", "butwal", "dharan", "lalitpur"]
    words = re.findall(r'\w+', message.lower())
    matches = get_close_matches(" ".join(words), known_locations, n=1, cutoff=0.6)
    return matches[0].capitalize() if matches else None

def extract_time_reference(message):
    if "tomorrow" in message.lower():
        return "tomorrow"
    return "today"

def chatbot(message):
    intent = predict_intent_bert(message)

    if intent == "get_weather":
        location = extract_location(message)
        when = extract_time_reference(message)

        if not location:
            return "Please tell me the city you'd like the weather for."

        weather_data = get_weather_data(location)
        if "error" in weather_data:
            return f"Sorry, I couldn't fetch weather info for {location}."

        forecast = weather_data.get("forecast", [])
        if not forecast:
            return f"No forecast available for {location}."

        forecast_entry = forecast[3] if when == "tomorrow" and len(forecast) > 3 else forecast[0]
        return f"{when.capitalize()} in {location}: {forecast_entry['description']}, {forecast_entry['temp']}°C at {forecast_entry['datetime'].split()[1]}."

    elif intent == "find_transport":
        location = extract_location(message)
        if not location:
            return "Tell me your starting point and destination, like: 'from Kathmandu to Pokhara'."
        return f"To travel to {location}, you can take a tourist bus, domestic flight, or private vehicle. Let me know your starting point for more options."

    elif intent == "plan_trip":
        location = extract_location(message)
        if not location:
            return "Where would you like to plan your trip to?"
        return f"Planning a trip to {location}? I recommend visiting key attractions, booking a hotel in advance, and checking the weather. Want help building an itinerary?"

    elif intent == "recommend_destination":
        recommendations = get_recommendations(message)
        if not recommendations:
            return "Sorry, I couldn’t find suitable recommendations."
        reply = "Here are some destinations you might like:\n"
        for item in recommendations:
            reply += f"📍 {item['Destination Name']}: {item['Description'][:100]}...\n"
        return reply

    elif intent == "greeting":
        return "Hi there! I’m your AI Travel Assistant. How can I help with your trip?"

    elif intent == "farewell":
        return "Goodbye! Have a great journey! 😊"

    else:
        return "I'm not sure how to help with that yet. Try asking about weather, transport, or trip planning."
    
def get_chatbot_response(message):
    return chatbot(message)


# Debug mode for terminal testing
if __name__ == "__main__":
    while True:
        user_input = input("You: ")
        if user_input.lower() in ['exit', 'quit']:
            print("YatriBot: Goodbye!")
            break
        print("YatriBot:", chatbot(user_input))
