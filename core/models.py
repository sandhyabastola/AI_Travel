from django.db import models
from django.contrib.auth.models import User

class Destination(models.Model):
    CATEGORY_CHOICES = [
        ('city', 'City'),
        ('mountain', 'Mountain'),
        ('nature', 'Nature'),
        ('cultural', 'Cultural'),
        ('adventure', 'Adventure'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    image = models.ImageField(upload_to='destinations/', blank=True, null=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    interests = models.CharField(max_length=200, blank=True)
    

    def __str__(self):
        return self.user.username


class UserItinerary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    destinations = models.ManyToManyField(Destination, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} by {self.user.username}"


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
        # Add more if needed
    ]

    from_destination = models.ForeignKey(Destination, related_name='transport_from', on_delete=models.CASCADE)
    to_destination = models.ForeignKey(Destination, related_name='transport_to', on_delete=models.CASCADE)
    transport_type = models.CharField(max_length=20, choices=TRANSPORT_TYPES)
    duration = models.DurationField()
    cost = models.DecimalField(max_digits=8, decimal_places=2)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.transport_type} from {self.from_destination} to {self.to_destination}"
    
class Hotel(models.Model):
    name = models.CharField(max_length=200)
    destination = models.ForeignKey('Destination', on_delete=models.CASCADE, related_name='hotels')
    address = models.TextField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)  # e.g. 4.5
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    contact_number = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.destination.name}"
