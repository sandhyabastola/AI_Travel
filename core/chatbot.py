import torch
from transformers import BertTokenizer, BertForSequenceClassification

# Load the model and tokenizer once when Django starts
MODEL_PATH = "bert-base-uncased"  # Or path to your fine-tuned model
tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)

# Set device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()

# Map label IDs to intent names
id2label = {
    0: "destination_info",
    1: "greeting",
    2: "hotel_search",
    3: "itinerary",
    4: "recommendation",
    5: "route_search",
    6: "transport",
    7: "weather"
}

# Responses mapped to intent
responses = {
    "greeting": "Hello! How can I help you with your travel plans in Nepal?",
    "destination_info": "Sure! Which destination are you interested in?",
    "hotel_search": "Let me find some hotels for you...",
    "itinerary": "I can help you plan your itinerary. Where would you like to go?",
    "recommendation": "I recommend visiting Pokhara and Lumbini for your first trip!",
    "route_search": "Please tell me your start and end locations.",
    "transport": "We support bus, flight, and private vehicle info.",
    "weather": "Let me fetch the weather details for you."
}


def predict_intent(text):
    """Predict intent class for a given user input."""
    if not isinstance(text, str):
        raise ValueError("Input must be a string")
    
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    inputs = {key: val.to(device) for key, val in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted = torch.argmax(logits, dim=1).item()
        # Calculate softmax confidence
        probs = torch.softmax(logits, dim=1)
        confidence = probs[0, predicted].item()

    return id2label.get(predicted, "unknown"), confidence


def chatbot(message):
    """Main chatbot response function."""
    if not isinstance(message, str):
        raise ValueError("Expected string input")
    
    intent, confidence = predict_intent(message)
    response = responses.get(intent, "Sorry, I didn’t understand that. Could you rephrase?")

    return {
        "response": response,
        "intent": intent,
        "confidence": confidence
    }
