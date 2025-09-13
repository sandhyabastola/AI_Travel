import csv
import os
import re

class ContentBasedRecommendationSystem:
    def __init__(self):
        self.data = []
        self.load_data()

    def load_data(self):
        dataset_path = os.path.join(os.path.dirname(__file__), 'data', 'nepal_dataset.csv')
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

    # ------------------- Normalization helpers -------------------

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

    # ------------------- Scoring -------------------

    def _score_places(self, place, travel_style, weather, budget_amount,
                      destination=None, category=None):
        total_score = 0

        # --- Destination (strict filter, must match) ---
        if destination:
            dest = destination.lower()
            if (dest in place.get('location', '').lower() or 
                dest in place.get('district', '').lower()):
                total_score += 500  # strong weight for destination
            else:
                return 0  # reject if not in destination

        # --- Travel style (strong boost after destination) ---
        place_styles = re.split(r'[;,]', place.get('travel_style', '').lower())
        place_styles = [s.strip() for s in place_styles if s.strip()]
        if travel_style:
            if travel_style not in place_styles:
                return 0
            total_score += 200

        # --- Category (second strong boost) ---
        place_category = place.get('category', '').strip().lower()
        if category and place_category == category:
            total_score += 150

        # --- Weather (medium priority) ---
        place_weather = self.normalize_weather_input(place.get('weather', ''))
        weather_normalized = self.normalize_weather_input(weather)
        if weather_normalized != 'any':
            if place_weather == weather_normalized:
                total_score += 60
            elif weather_normalized in place_weather:
                total_score += 30

        # --- Budget (lowest priority) ---
        place_budget = place.get('budget_level', 'low').lower()
        user_budget = self.map_budget_amount_to_level(budget_amount)
        if place_budget == user_budget:
            total_score += 40
        elif place_budget in ("medium", "low") and user_budget == "high":
            total_score += 20

        return total_score

    # ------------------- Recommendation -------------------

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

        # Sort by score
        scored_places.sort(key=lambda x: x[0], reverse=True)

        return [place for _, place in scored_places[:top_k]]


# ------------------- Testing Harness -------------------

def test_recommender():
    recommender = ContentBasedRecommendationSystem()
    test_cases = [
        {"style": "adventure", "weather": "sunny", "budget": "2000", "destination": "Pokhara"},
        {"style": "cultural", "weather": "any", "budget": "500", "destination": "Janakpur", "category": "heritage"},
        {"style": "trekking", "weather": "snowy", "budget": "6000", "destination": "Mustang"},
        {"style": "relaxation", "weather": "sunny", "budget": "3000", "destination": "Ilam"},
        {"style": "wildlife", "weather": "rainy", "budget": "1000", "destination": "UnknownDistrict"},
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\nTest Case {i}: {case}")
        results = recommender.recommend(
            case.get("style"), case.get("weather"), case.get("budget"),
            destination=case.get("destination"), category=case.get("category"), top_k=3
        )
        if not results:
            print("❌ No recommendations found for this destination.")
        else:
            for res in results:
                print(f"- {res['name']} ({res['district']}) | Style: {res['travel_style']} | "
                      f"Weather: {res['weather']} | Budget: {res['budget_level']} | "
                      f"Category: {res['category']}")

if __name__ == "__main__":
    test_recommender()
