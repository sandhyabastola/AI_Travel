from .models import Destination, UserProfile, Hotel
from django.contrib.auth.models import User
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def get_recommendations(user, num_recommendations=5):
    """
    Content-based filtering for destination recommendations
    """
    try:
        user_profile = user.userprofile
        
        # Get all destinations
        destinations = Destination.objects.all()
        
        # Create feature matrix
        destination_features = []
        for dest in destinations:
            features = f"{dest.category} {dest.region} {dest.difficulty_level} {dest.best_season}"
            destination_features.append(features)
        
        # User preferences
        user_preferences = f"{user_profile.travel_style} {user_profile.budget_range}"
        
        # TF-IDF Vectorization
        vectorizer = TfidfVectorizer(stop_words='english')
        feature_matrix = vectorizer.fit_transform(destination_features + [user_preferences])
        
        # Calculate similarity
        user_profile_vector = feature_matrix[-1]
        destination_vectors = feature_matrix[:-1]
        
        similarities = cosine_similarity(user_profile_vector, destination_vectors).flatten()
        
        # Get top recommendations
        top_indices = similarities.argsort()[-num_recommendations:][::-1]
        
        recommendations = []
        for idx in top_indices:
            dest = destinations[idx]
            recommendations.append({
                'destination': dest,
                'similarity_score': similarities[idx]
            })
        
        return recommendations
    
    except Exception as e:
        # Fallback to popular destinations
        popular_destinations = Destination.objects.filter(
            category__in=['city', 'mountain', 'cultural']
        )[:num_recommendations]
        
        return [{'destination': dest, 'similarity_score': 0.5} for dest in popular_destinations] 