import re
from .weather import get_weather_data
from transformers import pipeline

classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

INTENTS = {
    "get_weather": "Ask about the weather",
    "find_transport": "Ask for transport options",
    "plan_trip": "Ask help with planning trip",
    "greeting": "Say hello",
    "farewell": "Say goodbye",
    "unknown": "Something else"
}

def predict_intent(message):
    labels = list(INTENTS.keys())
    hypothesis_templates = [INTENTS[label] for label in labels]
    result = classifier(message, hypothesis_templates)
    best_index = result['scores'].index(max(result['scores']))
    predicted_intent = labels[best_index]
    return predicted_intent


def extract_location(message):
    known_locations = ["kathmandu", "pokhara", "biratnagar", "chitwan", "butwal", "dharan", "lalitpur"]
    for loc in known_locations:
        if loc in message.lower():
            return loc.capitalize()
    return None


def extract_time_reference(message):
    if "tomorrow" in message.lower():
        return "tomorrow"
    return "today"

def chatbot(message):
    intent = predict_intent(message)

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
        return f"To travel to {location}, you can take a tourist bus, domestic flight, or private vehicle. Let me know your starting point to give more details."

    elif intent == "plan_trip":
        location = extract_location(message)
        if not location:
            return "Where would you like to plan your trip to?"
        return f"Planning a trip to {location}? I recommend visiting key attractions, booking a hotel in advance, and checking the weather forecast. Want help building a full itinerary?"

    elif intent == "greeting":
        return "Hi there! I’m your AI Travel Assistant. How can I help with your trip?"

    elif intent == "farewell":
        return "Goodbye! Have a great journey. 😊"

    else:
        return "I'm not sure how to help with that yet, but I'm learning. Try asking about weather, transport, or trip planning."
