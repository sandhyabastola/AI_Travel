import csv
import math
import os

class ContentBasedRecommendationSystem:
    def __init__(self):
        self.data = []
        self.feature_matrix = []
        self.load_data()

    def load_data(self):
        dataset_path = os.path.join(os.path.dirname(__file__), 'data', 'nepal_dataset.csv')
        with open(dataset_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            self.data = [row for row in reader]
        self.prepare_features()

    def prepare_features(self):
        style_options = ['wildlife', 'relaxation', 'cultural', 'trekking', 'adventure', 'family-friendly', 'budget']
        weather_options = ['sunny', 'warm', 'cold', 'rainy']
        budget_options = ['low', 'medium', 'high']

        one_hot_matrix = []
        for place in self.data:
            # Split travel_style (handle multiple values)
            styles = [s.strip().lower().replace('_', '-') for s in place['travel_style'].split(';')]

            style_vector = [1 if s in styles else 0 for s in style_options]

            # Single values
            weather = place['weather'].strip().lower()
            weather_vector = [1 if weather == w else 0 for w in weather_options]

            budget = place['budget_level'].strip().lower()
            budget_vector = [1 if budget == b else 0 for b in budget_options]

            one_hot = style_vector + weather_vector + budget_vector
            one_hot_matrix.append(one_hot)

        self.feature_matrix = one_hot_matrix

    def cosine_similarity(self, v1, v2):
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        return dot / (norm1 * norm2 + 1e-10)

    def map_budget_amount_to_level(self, amount):
        try:
            amount = float(amount)
        except:
            return 'low'  # default fallback
        if amount <= 1000:
            return 'low'
        elif 1000 < amount <= 3000:
            return 'medium'
        else:
            return 'high'

    def recommend(self, travel_style, weather, budget_amount, top_k=5):
        style_options = ['wildlife', 'relaxation', 'cultural', 'trekking', 'adventure', 'family-friendly', 'budget']
        weather_options = ['sunny', 'warm', 'cold', 'rainy']
        budget_options = ['low', 'medium', 'high']

        travel_style = travel_style.strip().lower().replace('_', '-')
        weather = weather.strip().lower()
        budget_level = self.map_budget_amount_to_level(budget_amount)

        style_vector = [1 if travel_style == s else 0 for s in style_options]
        weather_vector = [1 if weather == w else 0 for w in weather_options]
        budget_vector = [1 if budget_level == b else 0 for b in budget_options]

        input_vector = style_vector + weather_vector + budget_vector

        similarities = [
            (self.cosine_similarity(input_vector, vector), i)
            for i, vector in enumerate(self.feature_matrix)
        ]
        similarities.sort(reverse=True)

        return [self.data[i] for _, i in similarities[:top_k]]
