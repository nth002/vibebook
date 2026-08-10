from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import uuid
import secrets  # <-- Add this import




class OTP(models.Model):
    email = models.EmailField()
    otp = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'otps'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f'{self.email} - {self.otp}'
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def can_retry(self):
        return self.attempts < 3
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        super().save(*args, **kwargs)

class User(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)

    bio = models.TextField(blank=True, null=True, max_length=500)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    cover_image = models.ImageField(upload_to='covers/', blank=True, null=True)

    friends = models.ManyToManyField('self', symmetrical=True, blank=True)
    friend_requests = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='received_requests',
        blank=True
    )

    is_online = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return self.full_name


class UserToken(models.Model):
    """
    Simple token model for authentication
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tokens')
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.email} - {self.token[:10]}...'
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            from django.utils import timezone
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)


class Post(models.Model):
    """
    Matches post_model.dart
    """
    post_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(max_length=5000)
    images = models.JSONField(default=list, blank=True)  # List of image URLs
    
    # Engagement (matches Flutter PostModel)
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    shares = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'posts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.full_name}: {self.content[:50]}'
    
    @property
    def like_count(self):
        return self.likes.count()
    
    @property
    def comment_count(self):
        return self.comments.count()

class Comment(models.Model):
    """
    Matches CommentModel in post_model.dart
    """
    comment_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=2000)
    user_profile_image = models.URLField(blank=True, null=True)  # For quick display
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'comments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post']),
            models.Index(fields=['user']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f'{self.user.full_name}: {self.content[:50]}'
    
    @property
    def like_count(self):
        return self.likes.count()

class Message(models.Model):
    """
    Matches message_model.dart
    """
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        AUDIO = 'audio', 'Audio'
        FILE = 'file', 'File'
    
    message_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    content = models.TextField()
    message_type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    
    # Status (matches Flutter MessageModel)
    is_read = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    
    # Timestamps
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'receiver']),
            models.Index(fields=['-timestamp']),
            models.Index(fields=['is_read']),
        ]
    
    def __str__(self):
        return f'{self.sender.full_name} -> {self.receiver.full_name}'

class Story(models.Model):
    """
    Matches story_model.dart
    """
    story_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    image_url = models.URLField()  # Matches Flutter's imageUrl
    user_profile_image = models.URLField(blank=True, null=True)  # For quick display
    
    # Viewers (matches Flutter viewers list)
    viewers = models.ManyToManyField(User, related_name='viewed_stories', blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'stories'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f'{self.user.full_name} - {self.created_at}'
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @property
    def viewer_count(self):
        return self.viewers.count()


class CallHistory(models.Model):
    """
    For call_screen.dart - Video and audio calls
    """
    class CallType(models.TextChoices):
        AUDIO = 'audio', 'Audio'
        VIDEO = 'video', 'Video'
    
    class CallStatus(models.TextChoices):
        MISSED = 'missed', 'Missed'
        ANSWERED = 'answered', 'Answered'
        REJECTED = 'rejected', 'Rejected'
        ENDED = 'ended', 'Ended'
    
    call_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4)
    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='outgoing_calls')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incoming_calls')
    call_type = models.CharField(max_length=10, choices=CallType.choices)
    call_status = models.CharField(max_length=10, choices=CallStatus.choices, default=CallStatus.ENDED)
    duration = models.IntegerField(default=0)  # Duration in seconds
    channel_name = models.CharField(max_length=255, blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'call_history'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['caller']),
            models.Index(fields=['receiver']),
            models.Index(fields=['-started_at']),
        ]
    
    def __str__(self):
        return f'{self.caller.full_name} -> {self.receiver.full_name} ({self.call_type})'

class UserDevice(models.Model):
    """
    For push notifications and device management
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device_token = models.CharField(max_length=255, unique=True)
    device_type = models.CharField(max_length=20, choices=[('android', 'Android'), ('ios', 'iOS')])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_devices'
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['device_token']),
        ]
    
    def __str__(self):
        return f'{self.user.full_name} - {self.device_type}'


class VibeMatch(models.Model):
    """
    VibeMatch Model - For matching users based on mood
    Matches Flutter VibeMatchModel
    """
    class Mood(models.TextChoices):
        HAPPY = 'happy', 'Happy'
        MOTIVATED = 'motivated', 'Motivated'
        CALM = 'calm', 'Calm'
        EXCITED = 'excited', 'Excited'
        GRATEFUL = 'grateful', 'Grateful'
        CONFIDENT = 'confident', 'Confident'
        ADVENTUROUS = 'adventurous', 'Adventurous'
        ROMANTIC = 'romantic', 'Romantic'
        FUN = 'fun', 'Fun'
        CHILL = 'chill', 'Chill'

    class LookingFor(models.TextChoices):
        FRIENDSHIP = 'friendship', 'Friendship'
        DATING = 'dating', 'Dating'
        RELATIONSHIP = 'relationship', 'Relationship'
        ACTIVITY_PARTNER = 'activityPartner', 'Activity Partner'
        CHAT = 'chat', 'Just Chat'
        NETWORKING = 'networking', 'Networking'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'
        OTHER = 'other', 'Other'
        PREFER_NOT_TO_SAY = 'prefer_not_to_say', 'Prefer not to say'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vibe_matches')
    mood = models.CharField(max_length=20, choices=Mood.choices, default=Mood.HAPPY)
    bio = models.TextField(blank=True, null=True, max_length=500)
    interests = models.JSONField(default=list, blank=True)  # List of interests
    age = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.PREFER_NOT_TO_SAY)
    looking_for = models.CharField(max_length=20, choices=LookingFor.choices, default=LookingFor.FRIENDSHIP)
    match_percentage = models.FloatField(default=0.0)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    is_liked = models.BooleanField(default=False)
    is_matched = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vibe_matches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['mood']),
            models.Index(fields=['is_matched']),
        ]

    def __str__(self):
        return f"{self.user.full_name} - {self.mood}"


class VibeMatchLike(models.Model):
    """
    Track likes between users in VibeMatch
    """
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vibe_likes_sent')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vibe_likes_received')
    is_super_like = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'vibe_match_likes'
        unique_together = ['from_user', 'to_user']

    def __str__(self):
        return f"{self.from_user.full_name} -> {self.to_user.full_name}"


# ============================================
# COFFEE DATE MODELS
# ============================================

class CoffeeShop(models.Model):
    """
    Coffee Shop Model for Coffee Date Feature
    """
    class Ambiance(models.TextChoices):
        LUXURY = 'luxury', 'Luxury'
        COZY = 'cozy', 'Cozy'
        MODERN = 'modern', 'Modern'
        VINTAGE = 'vintage', 'Vintage'

    class PriceLevel(models.TextChoices):
        MODERATE = '$$', 'Moderate'
        EXPENSIVE = '$$$', 'Expensive'
        VERY_EXPENSIVE = '$$$$', 'Very Expensive'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    image = models.URLField(max_length=500)
    address = models.TextField()
    distance = models.CharField(max_length=50)
    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    amenities = models.JSONField(default=list, blank=True)  # List of amenities
    opening_hours = models.JSONField(default=list, blank=True)  # List of opening hours
    is_luxury = models.BooleanField(default=True)
    ambiance = models.CharField(max_length=20, choices=Ambiance.choices, default=Ambiance.LUXURY)
    price_level = models.CharField(max_length=10, choices=PriceLevel.choices, default=PriceLevel.EXPENSIVE)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coffee_shops'

    def __str__(self):
        return self.name


class CoffeeDate(models.Model):
    """
    Coffee Date Booking Model
    Matches Flutter CoffeeDateModel
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    match_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='coffee_dates')
    match_user_name = models.CharField(max_length=255)
    coffee_shop = models.ForeignKey(CoffeeShop, on_delete=models.CASCADE, related_name='coffee_dates')
    coffee_shop_name = models.CharField(max_length=255)
    coffee_shop_image = models.URLField(max_length=500)
    address = models.TextField()
    distance = models.CharField(max_length=50)
    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    amenities = models.JSONField(default=list, blank=True)
    opening_hours = models.JSONField(default=list, blank=True)
    date_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coffee_dates'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['match_user', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"{self.match_user_name} - {self.coffee_shop_name}"


# ============================================
# MEME MODELS
# ============================================

class Meme(models.Model):
    """
    Meme Model - For meme sharing and coin earning
    Matches Flutter MemeModel
    """
    class Category(models.TextChoices):
        ALL = 'all', 'All'
        FUNNY = 'funny', 'Funny'
        PROGRAMMING = 'programming', 'Programming'
        MOTIVATIONAL = 'motivational', 'Motivational'
        TECHNOLOGY = 'technology', 'Technology'
        ANIMALS = 'animals', 'Animals'
        DATING = 'dating', 'Dating'
        SCHOOL = 'school', 'School'
        WORK = 'work', 'Work'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    image_url = models.URLField(max_length=500)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.FUNNY)
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_memes')
    uploader_name = models.CharField(max_length=255)
    uploader_image = models.URLField(max_length=500, blank=True, null=True)
    is_liked = models.BooleanField(default=False)  # For current user
    coins = models.IntegerField(default=0)  # Coins earned from this meme
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'memes'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['likes']),
        ]

    def __str__(self):
        return f"{self.title} - {self.category}"


class MemeLike(models.Model):
    """
    Track meme likes and coin earnings
    """
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meme_likes')
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, related_name='meme_likes')
    coins_earned = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meme_likes'
        unique_together = ['user', 'meme']

    def __str__(self):
        return f"{self.user.full_name} liked {self.meme.title}"


class MemeComment(models.Model):
    """
    Comments on Memes
    """
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meme_comments')
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, related_name='meme_comments')
    content = models.TextField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'meme_comments'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.full_name}: {self.content[:50]}"

class Notification(models.Model):
    """
    Notification Model - For all features
    """
    class NotificationType(models.TextChoices):
        LIKE = 'like', 'Like'
        COMMENT = 'comment', 'Comment'
        FRIEND_REQUEST = 'friend_request', 'Friend Request'
        FRIEND_REQUEST_ACCEPTED = 'friend_request_accepted', 'Friend Request Accepted'
        SHARE = 'share', 'Share'
        MENTION = 'mention', 'Mention'
        VIBE_MATCH = 'vibe_match', 'Vibe Match'
        COFFEE_DATE = 'coffee_date', 'Coffee Date'
        MEME_LIKE = 'meme_like', 'Meme Like'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField(max_length=500)
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Related objects
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey('Comment', on_delete=models.CASCADE, null=True, blank=True)
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, null=True, blank=True)
    vibe_match = models.ForeignKey(VibeMatch, on_delete=models.CASCADE, null=True, blank=True)
    coffee_date = models.ForeignKey(CoffeeDate, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['is_read']),
            models.Index(fields=['notification_type']),
        ]

    def __str__(self):
        return f'{self.user.full_name}: {self.message[:50]}'