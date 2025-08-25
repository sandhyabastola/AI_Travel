import torch
from transformers import BertTokenizer, BertForSequenceClassification
import re
import os
import sys
import django
import random
import string

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(__file__)))  # add project base dir to path
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_travel.settings')
django.setup()

from core.weather import get_weather_data
from core.recommendation_model import get_recommendations
from difflib import get_close_matches


# Dynamically build the absolute path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'I:\\EXTRA\\Django\\Datasets\\bert_chatbot_model')

# Normalize and convert to absolute path
MODEL_PATH = os.path.normpath(os.path.abspath(MODEL_PATH))

# Load tokenizer and model
tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)

model.eval()

# Match index to intent labels (must match your training)
INTENTS = ["greeting", "farewell", "find_transport", "check_weather", "route", "recommendation", "trip_plan"]

# Load tokenizer and model as before
# tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
# model = BertForSequenceClassification.from_pretrained(MODEL_PATH)
# model.eval()

# Map BERT output indices to intent labels
INTENTS = ["get_weather", "find_transport", "plan_trip", "recommendation", "greeting", "farewell", "unknown"]

# Recommendation keywords
recommend_keywords = ["recommend", "suggest", "where to go", "places", "destination"]


def predict_intent_bert(user_input: str) -> str:
    """
    Hybrid intent predictor: 
    1. Rule-based checks for greetings/farewells
    2. Keyword-based fallback for weather/transport/trip
    3. Otherwise, BERT prediction
    """
    # Normalize input
    msg = user_input.lower().translate(str.maketrans('', '', string.punctuation)).strip()

    # Rule-based override for greeting
    if any(word in msg.split() for word in ["hi", "hello", "hey"]):
        return "greeting"

    # Rule-based override for farewell
    if msg in ["bye", "goodbye", "see you", "see ya"]:
        return "farewell"

    # Keyword-based fallback for weather/transport/trip before BERT
    if any(word in msg for word in ["weather", "temperature", "forecast"]):
        return "get_weather"
    if " from " in msg and " to " in msg:
        return "find_transport"
    if any(word in msg for word in ["plan", "trip", "itinerary", "visit", "travel"]):
        return "plan_trip"
    if any(word in msg for word in recommend_keywords):
        return "recommend_destination"

    # BERT prediction for everything else
    inputs = tokenizer(user_input, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        predicted_class = torch.argmax(probs, dim=-1).item()

    return INTENTS[predicted_class]


def extract_locations(message):
    known_locations = ["kathmandu", "pokhara", "biratnagar", "chitwan", "butwal", "dharan", "lalitpur"]
    words = re.findall(r'\w+', message.lower())
    found = [loc.capitalize() for loc in known_locations if loc in words]
    return found


def extract_time_reference(message):
    if "tomorrow" in message.lower():
        return "tomorrow"
    return "today"


def chatbot(message):
    msg_lower = message.lower()

    # Rule-based override: detect "to" in message -> transport
    if " to " in msg_lower:
        intent = "find_transport"
    else:
        intent = predict_intent_bert(message)

    # Handle intents
    if intent == "greeting":
        return random.choice([
            "Hello! How can I assist you with your travel today?",
            "Hi there! Where are you planning to go?"
        ])

    elif intent == "farewell":
        return random.choice([
            "Goodbye! Have a great journey! 😊",
            "See you soon! Safe travels. ✈️"
        ])

    elif intent == "find_transport":
        locations = extract_locations(message)
        if len(locations) < 2:
            return "Tell me your starting point and destination, like: 'from Kathmandu to Pokhara'."
        start, end = locations[0], locations[1]
        return f"To travel from {start} to {end}, you can take a tourist bus, domestic flight, or private vehicle."

    elif intent == "get_weather":
        location = extract_locations(message)
        when = extract_time_reference(message)
        if not location:
            return "Please tell me the city you'd like the weather for."
        weather_data = get_weather_data(location)
        if "error" in weather_data:
            return f"Sorry, I couldn't fetch weather info for {location}."
        forecast_entry = weather_data.get("forecast", [])[0]
        return f"{when.capitalize()} in {location}: {forecast_entry['description']}, {forecast_entry['temp']}°C at {forecast_entry['datetime'].split()[1]}."

    elif intent == "route":
        locations = extract_locations(message)
        if len(locations) < 2:
            return "Please specify the start and end locations for the route."
        start, end = locations[0], locations[1]
        return f"To get from {start} to {end}, you can take the following route: ..."

    elif intent == "recommendation":
        locations = extract_locations(message)
        if not locations:
            return "Which location are you interested in for recommendations?"
        return f"Here are some recommendations for {locations[0]}: ..."

    elif intent == "trip_plan":
        locations = extract_locations(message)
        time_reference = extract_time_reference(message)
        if not locations:
            return "Where are you planning to go?"
        if time_reference == "tomorrow":
            return f"Your trip to {locations[0]} is planned for tomorrow."
        return f"Your trip to {locations[0]} is planned for today."
    else:
        return "I'm not sure I understand. Can you rephrase your question?"


def recommend_reply(user_message):
    recommendations = get_recommendations(user_message)
    if not recommendations:
        return "Sorry, I couldn’t find suitable recommendations."

    reply = "Here are some destinations you might like:\n"
    for item in recommendations:
        reply += f"📍 {item['Destination Name']}: {item['Description'][:100]}...\n"
    return reply


def get_chatbot_response(message: str) -> str:
    if "recommend" in message.lower():
        return recommend_reply(message)
    return chatbot(message)


# Run chatbot
if __name__ == "__main__":
    print("AI Travel Assistant is ready! Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("YatriBot: Goodbye! Have a great journey! 😊")
            break
        response = chatbot(user_input)
        print("YatriBot:", response)
