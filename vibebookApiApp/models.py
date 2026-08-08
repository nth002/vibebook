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

class Notification(models.Model):
    """
    Matches notification_model.dart
    """
    class NotificationType(models.TextChoices):
        LIKE = 'like', 'Like'
        COMMENT = 'comment', 'Comment'
        FRIEND_REQUEST = 'friend_request', 'Friend Request'
        FRIEND_REQUEST_ACCEPTED = 'friend_request_accepted', 'Friend Request Accepted'
        SHARE = 'share', 'Share'
        MENTION = 'mention', 'Mention'
    
    id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField(max_length=500)
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Related objects
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    
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