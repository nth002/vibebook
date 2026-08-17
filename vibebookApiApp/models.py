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
    profile_image = models.CharField(max_length=500, blank=True, null=True)
    cover_image =  models.CharField(max_length=500, blank=True, null=True)

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

    coins = models.IntegerField(default=0)


    class Meta:
        db_table = "users"

    def __str__(self):
        return self.full_name

    def add_coins(self, amount):
        """Add coins to user"""
        self.coins += amount
        self.save()
        return self.coins

    def deduct_coins(self, amount):
        """Deduct coins from user"""
        if self.coins >= amount:
            self.coins -= amount
            self.save()
            return True
        return False

    def get_coins(self):
        """Get current coin balance"""
        return self.coins


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



class Meme(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    image_url = models.URLField(max_length=500)
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, default='funny')
    likes = models.IntegerField(default=0)
    comments = models.IntegerField(default=0)
    shares = models.IntegerField(default=0)
    uploader = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memes')
    uploader_name = models.CharField(max_length=200)
    uploader_image = models.CharField(max_length=500, null=True, blank=True)
    coins = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']

class MemeLike(models.Model):
    id = models.CharField(max_length=36, primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meme_likes')
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE, related_name='meme_likes')  # ✅ Changed to 'meme_likes'
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'meme']


class CoffeeShop(models.Model):
    """
    Coffee Shop Model - Static list of restaurants and coffee shops
    """
    class Ambiance(models.TextChoices):
        LUXURY = 'luxury', 'Luxury'
        COZY = 'cozy', 'Cozy'
        MODERN = 'modern', 'Modern'
        VINTAGE = 'vintage', 'Vintage'
        ROMANTIC = 'romantic', 'Romantic'
        OUTDOOR = 'outdoor', 'Outdoor'
        ROOFTOP = 'rooftop', 'Rooftop'

    class PriceLevel(models.TextChoices):
        BUDGET = '₹', 'Budget'
        MODERATE = '₹₹', 'Moderate'
        EXPENSIVE = '₹₹₹', 'Expensive'
        VERY_EXPENSIVE = '₹₹₹₹', 'Very Expensive'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255)
    image = models.URLField(max_length=500, blank=True, null=True)
    address = models.TextField()
    city = models.CharField(max_length=100, default='')
    distance = models.CharField(max_length=50, blank=True, null=True)
    rating = models.FloatField(default=0.0)
    review_count = models.IntegerField(default=0)
    
    # Features
    amenities = models.JSONField(default=list, blank=True)
    opening_hours = models.JSONField(default=list, blank=True)
    
    # Meta
    is_luxury = models.BooleanField(default=True)
    ambiance = models.CharField(max_length=20, choices=Ambiance.choices, default=Ambiance.LUXURY)
    price_level = models.CharField(max_length=10, choices=PriceLevel.choices, default=PriceLevel.EXPENSIVE)
    
    # Location
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'coffee_shops'
        ordering = ['-rating', 'name']

    def __str__(self):
        return self.name

class DateInvite(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'
        CONFIRMED = 'confirmed', 'Confirmed'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_date_invites')
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_date_invites')
    message = models.TextField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Date details
    date_time = models.DateTimeField(null=True, blank=True)
    coffee_shop = models.ForeignKey('CoffeeShop', on_delete=models.SET_NULL, null=True, blank=True)
    coffee_shop_name = models.CharField(max_length=255, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    special_requests = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'date_invites'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', '-created_at']),
            models.Index(fields=['receiver', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.sender.full_name} -> {self.receiver.full_name} ({self.status})"


class DateBooking(models.Model):
    """
    Date Booking Model - For confirmed date bookings
    """
    class Status(models.TextChoices):
        PENDING_CONFIRMATION = 'pending_confirmation', 'Pending Confirmation'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    date_invite = models.ForeignKey(DateInvite, on_delete=models.CASCADE, related_name='bookings')
    booked_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='date_bookings')
    coffee_shop = models.ForeignKey('CoffeeShop', on_delete=models.CASCADE)
    coffee_shop_name = models.CharField(max_length=255)
    address = models.TextField()
    date_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_CONFIRMATION)
    special_requests = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'date_bookings'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booked_by', '-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['date_time']),
        ]

    def __str__(self):
        return f"{self.booked_by.full_name} - {self.coffee_shop_name} ({self.status})"

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

class Advertisement(models.Model):
    """
    Advertisement Model - For displaying ads in the feed
    """
    class AdType(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        CAROUSEL = 'carousel', 'Carousel'

    class AdStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        EXPIRED = 'expired', 'Expired'

    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    
    # Ad Content
    title = models.CharField(max_length=255)
    description = models.TextField(max_length=1000, blank=True, null=True)
    image_url = models.URLField(max_length=500000)
    video_url = models.URLField(max_length=500, blank=True, null=True)
    ad_type = models.CharField(max_length=20, choices=AdType.choices, default=AdType.IMAGE)
    
    # Brand/Company
    brand_name = models.CharField(max_length=255)
    brand_logo = models.URLField(max_length=500, blank=True, null=True)
    brand_color = models.CharField(max_length=7, default='#1877F2')  # Hex color code
    
    # Call to Action
    cta_text = models.CharField(max_length=50, default='Learn More')
    cta_url = models.URLField(max_length=500, blank=True, null=True)
    cta_action = models.CharField(max_length=50, blank=True, null=True)  # For deep linking
    
    # Targeting
    target_audience = models.JSONField(default=dict, blank=True)  # Age, location, interests
    target_gender = models.CharField(max_length=20, blank=True, null=True)
    target_age_min = models.IntegerField(null=True, blank=True)
    target_age_max = models.IntegerField(null=True, blank=True)
    target_location = models.CharField(max_length=255, blank=True, null=True)
    
    # Scheduling
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Status
    status = models.CharField(max_length=20, choices=AdStatus.choices, default=AdStatus.DRAFT)
    is_active = models.BooleanField(default=True)
    
    # Engagement
    impressions = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    ctr = models.FloatField(default=0.0)  # Click-through rate
    
    # Budget
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Creator/Advertiser
    advertiser = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ads')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'advertisements'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['is_active']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.brand_name} - {self.title[:50]}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.end_date
    
    @property
    def is_scheduled(self):
        from django.utils import timezone
        return timezone.now() < self.start_date
    
    @property
    def is_running(self):
        from django.utils import timezone
        return self.is_active and self.start_date <= timezone.now() <= self.end_date
    
    def increment_impressions(self):
        self.impressions += 1
        self.save()
    
    def increment_clicks(self):
        self.clicks += 1
        if self.impressions > 0:
            self.ctr = (self.clicks / self.impressions) * 100
        self.save()
    
    def get_color_code(self):
        """Convert hex color to Color value for Flutter"""
        return self.brand_color.lstrip('#')


class AdImpression(models.Model):
    """
    Track individual ad impressions
    """
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='impression_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_impressions')
    viewed_at = models.DateTimeField(auto_now_add=True)
    viewed_duration = models.IntegerField(default=0)  # seconds
    is_skipped = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ad_impressions'
        ordering = ['-viewed_at']
        unique_together = ['ad', 'user']
    
    def __str__(self):
        return f"{self.ad.brand_name} - {self.user.full_name}"


class AdClick(models.Model):
    """
    Track ad clicks
    """
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='click_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_clicks')
    clicked_at = models.DateTimeField(auto_now_add=True)
    clicked_url = models.URLField(max_length=500, blank=True, null=True)
    
    class Meta:
        db_table = 'ad_clicks'
        ordering = ['-clicked_at']
    
    def __str__(self):
        return f"{self.ad.brand_name} - {self.user.full_name}"


class AdDismiss(models.Model):
    """
    Track when users dismiss/skip ads
    """
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    ad = models.ForeignKey(Advertisement, on_delete=models.CASCADE, related_name='dismiss_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ad_dismisses')
    dismissed_at = models.DateTimeField(auto_now_add=True)
    dismiss_reason = models.CharField(max_length=100, blank=True, null=True)  # 'skipped', 'not_interested', etc.
    
    class Meta:
        db_table = 'ad_dismisses'
        ordering = ['-dismissed_at']
    
    def __str__(self):
        return f"{self.ad.brand_name} - {self.user.full_name}"