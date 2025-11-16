from django.db import models
from django.contrib.auth.models import User

class Destination(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    img_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    travel_style = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    image = models.ImageField(upload_to='destinations/', blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        

class LikeRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    liked = models.BooleanField(default=False)
    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1-5 stars
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "destination")  # one record per user-destination

    def __str__(self):
        return f"{self.user.username} -> {self.destination.name} | Like: {self.liked} | Rating: {self.rating}"

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', default='avatars/default.png')
    bio = models.TextField(blank=True, null=True)

    def __str__(self):  # Fixed: Added proper indentation
        return f"{self.user.username}'s profile"

class UserItinerary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    destinations = models.ManyToManyField(Destination, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} by {self.user.username}"
    
class ItineraryItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField()
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.date})"


class ChatHistory(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    session_id = models.CharField(max_length=100)
    user_message = models.TextField()
    bot_response = models.TextField()
    intent = models.CharField(max_length=50)
    confidence = models.FloatField(default=1.0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat session {self.session_id} at {self.timestamp}"


class Transportation(models.Model):
    TRANSPORT_TYPES = [
        ('bus', 'Bus'),
        ('flight', 'Flight'),
        ('jeep', 'Jeep'),
        ('private', 'Private Vehicle'),
        ('car_rental', 'Car Rental'),
        ('taxi', 'Taxi'),
        # Add more if needed
    ]

    from_location = models.ForeignKey('Destination', on_delete=models.CASCADE, related_name='transport_from')
    to_location = models.ForeignKey('Destination', on_delete=models.CASCADE, related_name='transport_to')
    mode = models.CharField(max_length=20, choices=TRANSPORT_TYPES)
    duration = models.DurationField(help_text="Travel duration")
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.from_location} to {self.to_location} by {self.mode}"

    
class Hotel(models.Model):
    name = models.CharField(max_length=200)
    location = models.ForeignKey('Destination', on_delete=models.CASCADE, related_name='hotels')
    address = models.TextField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)  # e.g. 4.5
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    image = models.ImageField(upload_to='hotels/', blank=True, null=True)
    amenities = models.TextField(blank=True, null=True)  # e.g. Wi-Fi
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.location}"