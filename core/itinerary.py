from .models import UserItinerary, Destination, Transportation, Hotel
from datetime import datetime, timedelta
import json

def generate_itinerary(user_itinerary):
    """
    Generate AI-powered itinerary based on user preferences
    """
    destinations = user_itinerary.destinations.all()
    start_date = user_itinerary.start_date
    end_date = user_itinerary.end_date
    total_days = (end_date - start_date).days
    
    if total_days <= 0:
        return {'error': 'Invalid date range'}
    
    # Calculate days per destination
    days_per_destination = max(1, total_days // len(destinations))
    
    itinerary_plan = []
    current_date = start_date
    
    for i, destination in enumerate(destinations):
        # Calculate stay duration
        if i == len(destinations) - 1:
            # Last destination gets remaining days
            stay_days = (end_date - current_date).days
        else:
            stay_days = days_per_destination
        
        # Get transportation options
        transport_options = []
        if i > 0:
            prev_destination = destinations[i-1]
            transport_options = Transportation.objects.filter(
                from_destination=prev_destination,
                to_destination=destination
            )
        
        # Get accommodation options
        hotels = Hotel.objects.filter(destination=destination)
        
        # Generate daily activities
        daily_activities = generate_daily_activities(destination, stay_days)
        
        destination_plan = {
            'destination': destination,
            'arrival_date': current_date.strftime('%Y-%m-%d'),
            'departure_date': (current_date + timedelta(days=stay_days)).strftime('%Y-%m-%d'),
            'stay_days': stay_days,
            'transport_options': transport_options,
            'recommended_hotels': hotels[:3],  # Top 3 hotels
            'daily_activities': daily_activities,
            'estimated_cost': calculate_estimated_cost(destination, stay_days, user_itinerary.budget)
        }
        
        itinerary_plan.append(destination_plan)
        current_date += timedelta(days=stay_days)
    
    return {
        'itinerary_plan': itinerary_plan,
        'total_estimated_cost': sum(plan['estimated_cost'] for plan in itinerary_plan),
        'recommendations': generate_travel_tips(destinations)
    }

def generate_daily_activities(destination, stay_days):
    """
    Generate suggested daily activities for a destination
    """
    activities_map = {
        'city': [
            'Visit historical sites and museums',
            'Explore local markets',
            'Try traditional cuisine',
            'Cultural walking tour'
        ],
        'mountain': [
            'Trekking and hiking',
            'Mountain viewpoints',
            'Local village visits',
            'Photography sessions'
        ],
        'national_park': [
            'Wildlife safari',
            'Bird watching',
            'Jungle walks',
            'Cultural programs'
        ],
        'religious': [
            'Temple visits',
            'Meditation sessions',
            'Religious ceremonies',
            'Spiritual discussions'
        ]
    }
    
    base_activities = activities_map.get(destination.category, [
        'Explore the area',
        'Local sightseeing',
        'Cultural activities',
        'Relaxation time'
    ])
    
    daily_activities = []
    for day in range(stay_days):
        day_activities = []
        for activity in base_activities[:min(3, len(base_activities))]:
            day_activities.append(activity)
        
        daily_activities.append({
            'day': day + 1,
            'activities': day_activities
        })
    
    return daily_activities

def calculate_estimated_cost(destination, stay_days, total_budget):
    """
    Calculate estimated cost for a destination
    """
    base_cost = float(destination.avg_cost_per_day) * stay_days
    return min(base_cost, float(total_budget) * 0.8)  # Cap at 80% of total budget

def generate_travel_tips(destinations):
    """
    Generate travel tips based on destinations
    """
    tips = []
