# Replace your current recommender classes with these

from django.db.models import Q
from django.contrib.auth.models import User
from .models import Destination, LikeRating

class LocationBasedSearch:
    """Search destinations from database"""
    
    def search_by_location(self, query):
        """Search destinations in database"""
        print(f"Searching database for: '{query}'")
        
        if not query:
            # No search query = show all destinations (limit to 20)
            destinations = Destination.objects.all().order_by('name')[:20]
            print(f"No query - showing first 20 destinations")
        else:
            # Search by name, district, or description
            destinations = Destination.objects.filter(
                Q(name__icontains=query) |
                Q(district__icontains=query) |
                Q(description__icontains=query)
            ).order_by('name')
            print(f"Found {destinations.count()} destinations matching '{query}'")
        
        # Convert to list of dictionaries (for your template)
        results = []
        for dest in destinations:
            results.append({
                'id': dest.id,  # Real database ID!
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
            # Find the target destination
            target = Destination.objects.get(name__iexact=place_name)
            print(f"Found target destination: {target.name} in {target.district}")
        except Destination.DoesNotExist:
            print(f"Target destination '{place_name}' not found in database")
            return []
        
        # Find destinations in the same district (simple similarity)
        similar = Destination.objects.filter(
            district=target.district
        ).exclude(id=target.id).order_by('name')[:top_n]
        
        print(f"Found {similar.count()} similar destinations in {target.district}")
        
        # Convert to dictionary format
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
        
        # Get destinations user has liked
        liked_destinations = LikeRating.objects.filter(
            user=user, 
            liked=True
        ).values_list('destination_id', flat=True)
        
        print(f"User has liked {len(liked_destinations)} destinations")
        
        if not liked_destinations:
            # No likes yet - recommend popular destinations
            print("No likes found - showing popular destinations")
            recommendations = Destination.objects.all().order_by('name')[:top_n]
        else:
            # Get destinations user hasn't interacted with
            recommendations = Destination.objects.exclude(
                id__in=liked_destinations
            ).order_by('name')[:top_n]
        
        # Convert to dictionary format
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