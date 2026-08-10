import os
import uuid
import random
import threading
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, OTP, Post, UserToken, Comment, Story, Notification, Message
from django.shortcuts import get_object_or_404
from django.db.models import Q  # ✅ Add this import at the top




def get_user_from_token(request):
    """
    Get user from Authorization header
    """
    auth_header = request.headers.get('Authorization')
    
    if not auth_header:
        return None
    
    # Remove 'Bearer ' prefix
    token = auth_header
    if token.startswith('Bearer '):
        token = token[7:]
    
    try:
        token_obj = UserToken.objects.get(token=token, is_active=True)
        if token_obj.is_expired():
            token_obj.is_active = False
            token_obj.save()
            return None
        return token_obj.user
    except UserToken.DoesNotExist:
        return None

def send_email_directly(recipient_email, subject, body):
    """
    Send email directly using smtplib - bypasses Django's email backend
    """
    try:
        # Email configuration
        sender_email = settings.EMAIL_HOST_USER
        password = settings.EMAIL_HOST_PASSWORD
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = subject
        
        # Attach body
        message.attach(MIMEText(body, "plain"))
        
        # Create SSL context
        context = ssl.create_default_context()
        
        # Connect to Gmail SMTP server
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            # Login
            server.login(sender_email, password)
            # Send email
            server.send_message(message)
        
        print(f"Email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"Error sending email directly: {e}")
        return False


def notify_action(action_type, recipient, sender=None, post=None, comment=None, custom_message=None):
    """
    Universal notification function for all actions
    
    Usage:
        notify_action('like', post.user, user, post=post)
        notify_action('comment', post.user, user, post=post, comment=comment)
        notify_action('friend_request', target_user, current_user)
        notify_action('friend_request_accepted', sender, current_user)
        notify_action('mention', mentioned_user, user, post=post)
    
    Args:
        action_type: 'like', 'comment', 'friend_request', 'friend_request_accepted', 'share', 'mention'
        recipient: User object who will receive the notification
        sender: User object who triggered the notification
        post: Post object (optional)
        comment: Comment object (optional)
        custom_message: Custom message (optional)
    """
    if not recipient or (sender and recipient == sender):
        return None
    
    return create_notification(
        user=recipient,
        notification_type=action_type,
        sender=sender,
        post=post,
        comment=comment,
        message=custom_message
    )

# Add this helper function after your imports
def create_notification(user, notification_type, sender=None, post=None, comment=None, message=None):
    """
    Create a notification for a user
    
    Args:
        user: The user who will receive the notification
        notification_type: 'like', 'comment', 'friend_request', 'friend_request_accepted', 'share', 'mention'
        sender: The user who triggered the notification (optional)
        post: The post related to the notification (optional)
        comment: The comment related to the notification (optional)
        message: Custom message (optional - will auto-generate if not provided)
    
    Returns:
        Notification object or None
    """
    try:
        # Don't send notification to self
        if sender and user == sender:
            return None
        
        # Auto-generate message based on type
        if not message:
            sender_name = sender.full_name if sender else "Someone"
            
            messages = {
                'like': f"{sender_name} liked your post.",
                'comment': f"{sender_name} commented on your post.",
                'friend_request': f"{sender_name} sent you a friend request.",
                'friend_request_accepted': f"{sender_name} accepted your friend request.",
                'share': f"{sender_name} shared your post.",
                'mention': f"{sender_name} mentioned you in a post.",
                'post_like': f"{sender_name} liked your post.",
                'comment_like': f"{sender_name} liked your comment.",
                'friend_online': f"{sender_name} is now online.",
            }
            message = messages.get(notification_type, f"{sender_name} interacted with you.")
        
        # Create notification
        notification = Notification.objects.create(
            id=str(uuid.uuid4()),
            user=user,
            message=message,
            notification_type=notification_type,
            sender=sender,
            post=post,
            comment=comment,
            is_read=False,
            timestamp=timezone.now()
        )
        
        return notification
        
    except Exception as e:
        print(f"Error creating notification: {e}")
        return None

class SendOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp = str(random.randint(100000, 999999))
        
        # Delete old OTPs
        OTP.objects.filter(email=email).delete()
        
        # Create new OTP
        OTP.objects.create(
            email=email,
            otp=otp,
            expires_at=timezone.now() + timezone.timedelta(minutes=5)
        )
        
        def send_otp_email():
            subject = 'Your VibeBook Verification Code'
            body = f'''
                Hello,

                Your verification code is: {otp}

                This code will expire in 5 minutes.

                If you didn't request this code, please ignore this email.

                Best regards,
                VibeBook Team
            '''
            success = send_email_directly(email, subject, body)
            if success:
                print(f"OTP sent successfully to {email}")
            else:
                print(f"Failed to send OTP to {email}")
        
        # Send email in background thread
        thread = threading.Thread(target=send_otp_email)
        thread.daemon = True
        thread.start()
        
        return Response({
            'success': True, 
            'message': 'OTP sent successfully', 
            'email': email
        }, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        otp = request.data.get('otp')
        
        if not email or not otp:
            return Response({'error': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            otp_obj = OTP.objects.filter(email=email).latest('created_at')
        except OTP.DoesNotExist:
            return Response({'error': 'OTP not found'}, status=status.HTTP_400_BAD_REQUEST)
        
        if otp_obj.is_expired():
            otp_obj.delete()
            return Response({'error': 'OTP expired'}, status=status.HTTP_400_BAD_REQUEST)
        
        if otp_obj.attempts >= 3:
            otp_obj.delete()
            return Response({'error': 'Too many failed attempts'}, status=status.HTTP_400_BAD_REQUEST)
        
        if otp != otp_obj.otp:
            otp_obj.attempts += 1
            otp_obj.save()
            return Response({'error': f'Invalid OTP. {3 - otp_obj.attempts} attempts remaining.'}, status=status.HTTP_400_BAD_REQUEST)
        
        otp_obj.is_verified = True
        otp_obj.save()
        
        return Response({'success': True, 'message': 'OTP verified successfully'}, status=status.HTTP_200_OK)

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        full_name = request.data.get('full_name')
        email = request.data.get('email')
        password = request.data.get('password')
        confirm_password = request.data.get('confirm_password')

        if not full_name:
            return Response(
                {'error': 'Full name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not password:
            return Response(
                {'error': 'Password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not confirm_password:
            return Response(
                {'error': 'Confirm password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != confirm_password:
            return Response(
                {'error': 'Passwords do not match'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'User with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            OTP.objects.get(
                email=email,
                is_verified=True
            )
        except OTP.DoesNotExist:
            return Response(
                {'error': 'Please verify your email with OTP first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        username = email.split('@')[0]

        if User.objects.filter(username=username).exists():
            username = f"{username}_{random.randint(1000, 9999)}"

        try:
            user = User.objects.create(
                email=email,
                username=username,
                full_name=full_name,

                # IMPORTANT:
                # Never store plain-text passwords
                password=password,

                is_active=True,
            )

            OTP.objects.filter(email=email).delete()

            def send_welcome_email():
                subject = 'Welcome to VibeBook!'

                body = f'''
                    Hello {full_name},

                    Welcome to VibeBook! 🎉

                    Your account has been successfully created.

                    Account Details:
                    ----------------
                    Name: {full_name}
                    Email: {email}
                    Password: {password}

                    You can now log in to your VibeBook account and start connecting with your community.

                    Thank you for joining VibeBook!

                    Best regards,
                    VibeBook Team
                    '''

                success = send_email_directly(
                    email,
                    subject,
                    body
                )

                if success:
                    print(f"Welcome email sent successfully to {email}")
                else:
                    print(f"Failed to send welcome email to {email}")

            # Send email in background thread
            thread = threading.Thread(
                target=send_welcome_email
            )
            thread.daemon = True
            thread.start()

            return Response({
                'success': True,
                'message': 'Account created successfully!',
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'email': user.email,
                    'username': user.username,
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Registration failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({'error': 'Email and password required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if not user.is_active:
            return Response({'error': 'Account is deactivated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if password != user.password:
            return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Update user status
        user.is_online = True
        user.last_seen = timezone.now()
        user.save()
        
        # Delete old tokens
        UserToken.objects.filter(user=user, is_active=True).update(is_active=False)
        
        # Create new token
        token = UserToken.objects.create(user=user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'username': user.username,
            },
            'token': token.token
        }, status=status.HTTP_200_OK)


class UpdateProfileView(APIView):
    """
    API to update user profile (profile image, cover image, bio, full name)
    URL: /api/update-profile/
    Method: PUT or PATCH
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: form-data or JSON
    """
    permission_classes = [AllowAny]
    
    def put(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get data from request
        full_name = request.data.get('full_name')
        bio = request.data.get('bio')
        profile_image = request.FILES.get('profile_image')
        cover_image = request.FILES.get('cover_image')
        
        # Update fields if provided
        if full_name:
            user.full_name = full_name
        
        if bio is not None:  # Allow empty bio
            user.bio = bio
        
        # Handle profile image upload (same way as post images)
        if profile_image:
            # Create user folder structure
            user_folder = os.path.join('profiles', user.username)
            full_user_folder = os.path.join(settings.MEDIA_ROOT, user_folder)
            if not os.path.exists(full_user_folder):
                os.makedirs(full_user_folder)
            
            # Generate unique filename
            filename = f"profile_{uuid.uuid4()}.{profile_image.name.split('.')[-1]}"
            file_path = os.path.join(full_user_folder, filename)
            
            # Save the file
            default_storage.save(file_path, ContentFile(profile_image.read()))
            
            # Delete old profile image if exists
            if user.profile_image and user.profile_image.name:
                old_path = os.path.join(settings.MEDIA_ROOT, user.profile_image.name)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Set the new profile image path
            user.profile_image = os.path.join(user_folder, filename)
        
        # Handle cover image upload (same way as post images)
        if cover_image:
            # Create user folder structure
            user_folder = os.path.join('covers', user.username)
            full_user_folder = os.path.join(settings.MEDIA_ROOT, user_folder)
            if not os.path.exists(full_user_folder):
                os.makedirs(full_user_folder)
            
            # Generate unique filename
            filename = f"cover_{uuid.uuid4()}.{cover_image.name.split('.')[-1]}"
            file_path = os.path.join(full_user_folder, filename)
            
            # Save the file
            default_storage.save(file_path, ContentFile(cover_image.read()))
            
            # Delete old cover image if exists
            if user.cover_image and user.cover_image.name:
                old_path = os.path.join(settings.MEDIA_ROOT, user.cover_image.name)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            # Set the new cover image path
            user.cover_image = os.path.join(user_folder, filename)
        
        # Save the user
        user.save()
        
        # Build response data
        base_url = f"{request.scheme}://{request.get_host()}"
        
        return Response({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {
                'id': user.id,
                'full_name': user.full_name,
                'username': user.username,
                'email': user.email,
                'bio': user.bio,
                'profile_image': f"{base_url}{settings.MEDIA_URL}{user.profile_image}" if user.profile_image else None,
                'cover_image': f"{base_url}{settings.MEDIA_URL}{user.cover_image}" if user.cover_image else None,
                'is_online': user.is_online,
                'last_seen': user.last_seen,
                'created_at': user.created_at
            }
        }, status=status.HTTP_200_OK)
    
    def patch(self, request):
        """
        Partial update - same as PUT but only updates provided fields
        """
        return self.put(request)


class GetProfileView(APIView):
    """
    API to get logged in user's complete profile details
    URL: /api/profile/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        base_url = f"{request.scheme}://{request.get_host()}"
        
        return Response({
            'success': True,
            'data': {
                'id': user.id,
                'uid': str(user.uid),
                'full_name': user.full_name,
                'username': user.username,
                'email': user.email,
                'bio': user.bio,
                'profile_image': f"{base_url}{settings.MEDIA_URL}{user.profile_image}" if user.profile_image else None,
                'cover_image': f"{base_url}{settings.MEDIA_URL}{user.cover_image}" if user.cover_image else None,
                'is_online': user.is_online,
                'is_active': user.is_active,
                'last_seen': user.last_seen,
                'created_at': user.created_at,
                'friends_count': user.friends.count(),
                'pending_requests_count': user.friend_requests.count()
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    def post(self, request):
        try:
            return Response({
                'success': True,
                'message': 'Logged out successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class CreatePostView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required. Please provide valid token.'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        content = request.data.get('content')
        images = request.FILES.getlist('images')
        
        if not content:
            return Response({'error': 'Content is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        image_urls = []
        post_id = str(uuid.uuid4())[:8]
        
        if images:
            user_folder = os.path.join('UserPostImages', user.username)
            full_user_folder = os.path.join(settings.MEDIA_ROOT, user_folder)
            if not os.path.exists(full_user_folder):
                os.makedirs(full_user_folder)
            
            post_folder = os.path.join(full_user_folder, post_id)
            if not os.path.exists(post_folder):
                os.makedirs(post_folder)
            
            for image in images:
                filename = f"{uuid.uuid4()}.{image.name.split('.')[-1]}"
                file_path = os.path.join(post_folder, filename)
                default_storage.save(file_path, ContentFile(image.read()))
                image_urls.append(os.path.join(user_folder, post_id, filename))
        
        post = Post.objects.create(
            user=user,
            content=content,
            images=image_urls,
            post_id=post_id
        )
        
        # Check for mentions in post content
        import re
        mentioned_usernames = re.findall(r'@(\w+)', content)
        if mentioned_usernames:
            mentioned_users = User.objects.filter(username__in=mentioned_usernames)
            for mentioned_user in mentioned_users:
                if mentioned_user != user:
                    create_notification(
                        user=mentioned_user,
                        notification_type='mention',
                        sender=user,
                        post=post,
                        message=f"{user.full_name} mentioned you in a post."
                    )
        
        return Response({
            'success': True,
            'message': 'Post created successfully',
            'post': {
                'post_id': post.post_id,
                'content': post.content,
                'images': image_urls,
                'created_at': post.created_at,
            }
        }, status=status.HTTP_201_CREATED)


class GetAllPostsView(APIView):
    """
    API to get all posts with comments, likes, and full details
    URL: /api/posts/all/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    Query Params: page (optional), limit (optional)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            base_url = f"{request.scheme}://{request.get_host()}"
            
            posts = Post.objects.all().order_by('-created_at')
            
            # Pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            start = (page - 1) * limit
            end = start + limit
            
            total_posts = posts.count()
            paginated_posts = posts[start:end]
            
            posts_data = []
            for post in paginated_posts:
                # Build full image URLs
                image_urls = []
                full_image_urls = []
                for img_path in post.images:
                    if img_path:
                        image_urls.append(f"{settings.MEDIA_URL}{img_path}")
                        full_image_urls.append(f"{base_url}{settings.MEDIA_URL}{img_path}")
                
                # Get all comments for this post
                comments = post.comments.all().order_by('-created_at')
                comments_data = []
                for comment in comments:
                    comments_data.append({
                        'comment_id': comment.comment_id,
                        'user': {
                            'id': comment.user.id,
                            'full_name': comment.user.full_name,
                            'username': comment.user.username,
                            'profile_image': f"{base_url}{settings.MEDIA_URL}{comment.user.profile_image}" if comment.user.profile_image else None,
                        },
                        'content': comment.content,
                        'user_profile_image': comment.user_profile_image,
                        'likes_count': comment.likes.count(),
                        'is_liked': comment.likes.filter(id=user.id).exists(),
                        'created_at': comment.created_at.isoformat(),
                    })
                
                posts_data.append({
                    'id': post.id,
                    'post_id': post.post_id,
                    'user': {
                        'id': post.user.id,
                        'full_name': post.user.full_name,
                        'username': post.user.username,
                        'profile_image': f"{base_url}{settings.MEDIA_URL}{post.user.profile_image}" if post.user.profile_image else None,
                    },
                    'content': post.content,
                    'images': image_urls,
                    'image_urls': full_image_urls,
                    'likes_count': post.likes.count(),
                    'is_liked': post.likes.filter(id=user.id).exists(),
                    'shares': post.shares,
                    'comments': comments_data,
                    'total_likes': post.likes.count(),
                    'total_comments': post.comments.count(),
                    'created_at': post.created_at.isoformat(),
                    'updated_at': post.updated_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'message': 'Posts fetched successfully',
                'data': {
                    'posts': posts_data,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_posts': total_posts,
                        'total_pages': (total_posts + limit - 1) // limit,
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch posts: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetMyPostsView(APIView):
    """
    API to get posts of the logged-in user only
    URL: /api/posts/my/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    Query Params: page (optional), limit (optional)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            base_url = f"{request.scheme}://{request.get_host()}"
            
            # Get only posts of the logged-in user
            posts = Post.objects.filter(user=user).order_by('-created_at')
            
            # Pagination
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            start = (page - 1) * limit
            end = start + limit
            
            total_posts = posts.count()
            paginated_posts = posts[start:end]
            
            posts_data = []
            for post in paginated_posts:
                # Build full image URLs
                image_urls = []
                full_image_urls = []
                for img_path in post.images:
                    if img_path:
                        image_urls.append(f"{settings.MEDIA_URL}{img_path}")
                        full_image_urls.append(f"{base_url}{settings.MEDIA_URL}{img_path}")
                
                # Get all comments for this post
                comments = post.comments.all().order_by('-created_at')
                comments_data = []
                for comment in comments:
                    comments_data.append({
                        'comment_id': comment.comment_id,
                        'user': {
                            'id': comment.user.id,
                            'full_name': comment.user.full_name,
                            'username': comment.user.username,
                            'profile_image': f"{base_url}{settings.MEDIA_URL}{comment.user.profile_image}" if comment.user.profile_image else None,
                        },
                        'content': comment.content,
                        'user_profile_image': comment.user_profile_image,
                        'likes_count': comment.likes.count(),
                        'is_liked': comment.likes.filter(id=user.id).exists(),
                        'created_at': comment.created_at.isoformat(),
                    })
                
                posts_data.append({
                    'id': post.id,
                    'post_id': post.post_id,
                    'user': {
                        'id': post.user.id,
                        'full_name': post.user.full_name,
                        'username': post.user.username,
                        'profile_image': f"{base_url}{settings.MEDIA_URL}{post.user.profile_image}" if post.user.profile_image else None,
                    },
                    'content': post.content,
                    'images': image_urls,
                    'image_urls': full_image_urls,
                    'likes_count': post.likes.count(),
                    'is_liked': post.likes.filter(id=user.id).exists(),
                    'shares': post.shares,
                    'comments': comments_data,
                    'total_likes': post.likes.count(),
                    'total_comments': post.comments.count(),
                    'created_at': post.created_at.isoformat(),
                    'updated_at': post.updated_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'message': 'Your posts fetched successfully',
                'data': {
                    'posts': posts_data,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total_posts': total_posts,
                        'total_pages': (total_posts + limit - 1) // limit if total_posts > 0 else 0,
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch posts: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class LikePostView(APIView):
    """
    API to like/unlike a post
    URL: /api/posts/<post_id>/like/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: {} (empty)
    """
    permission_classes = [AllowAny]
    
    def post(self, request, post_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            post = Post.objects.get(post_id=post_id)
        except Post.DoesNotExist:
            return Response(
                {'error': 'Post not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user already liked the post
        if post.likes.filter(id=user.id).exists():
            # Unlike
            post.likes.remove(user)
            return Response({
                'success': True,
                'message': 'Post unliked successfully',
                'data': {
                    'post_id': post.post_id,
                    'likes_count': post.likes.count(),
                    'is_liked': False
                }
            }, status=status.HTTP_200_OK)
        else:
            # Like
            post.likes.add(user)
            
            # Send notification to post owner (if not the same user)
            if post.user != user:
                create_notification(
                    user=post.user,
                    notification_type='like',
                    sender=user,
                    post=post
                )
            
            return Response({
                'success': True,
                'message': 'Post liked successfully',
                'data': {
                    'post_id': post.post_id,
                    'likes_count': post.likes.count(),
                    'is_liked': True
                }
            }, status=status.HTTP_200_OK)

class AddCommentView(APIView):
    """
    API to add comment to a post
    URL: /api/posts/<post_id>/comment/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: {"content": "This is a comment"}
    """
    permission_classes = [AllowAny]
    
    def post(self, request, post_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        content = request.data.get('content')
        
        if not content:
            return Response(
                {'error': 'Comment content is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(content) > 2000:
            return Response(
                {'error': 'Comment cannot exceed 2000 characters'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            post = Post.objects.get(post_id=post_id)
        except Post.DoesNotExist:
            return Response(
                {'error': 'Post not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Create comment
        comment = Comment.objects.create(
            post=post,
            user=user,
            content=content,
            user_profile_image=user.profile_image.url if user.profile_image else None
        )
        
        # Send notification to post owner (if not the same user)
        if post.user != user:
            create_notification(
                user=post.user,
                notification_type='comment',
                sender=user,
                post=post,
                comment=comment
            )
        
        # Check for mentions in comment
        import re
        mentioned_usernames = re.findall(r'@(\w+)', content)
        if mentioned_usernames:
            mentioned_users = User.objects.filter(username__in=mentioned_usernames)
            for mentioned_user in mentioned_users:
                if mentioned_user != user and mentioned_user != post.user:
                    create_notification(
                        user=mentioned_user,
                        notification_type='mention',
                        sender=user,
                        post=post,
                        comment=comment,
                        message=f"{user.full_name} mentioned you in a comment."
                    )
        
        base_url = f"{request.scheme}://{request.get_host()}"
        
        return Response({
            'success': True,
            'message': 'Comment added successfully',
            'data': {
                'comment_id': comment.comment_id,
                'user': {
                    'id': user.id,
                    'full_name': user.full_name,
                    'username': user.username,
                    'profile_image': f"{base_url}{settings.MEDIA_URL}{user.profile_image}" if user.profile_image else None,
                },
                'content': comment.content,
                'user_profile_image': comment.user_profile_image,
                'likes_count': comment.likes.count(),
                'is_liked': False,
                'created_at': comment.created_at.isoformat(),
            }
        }, status=status.HTTP_201_CREATED)


class AddStoryView(APIView):
    """
    API to add a story with image upload
    URL: /api/stories/create/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body (form-data):
        image: [file] (required - image file)
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        image_file = request.FILES.get('image')
        
        if not image_file:
            return Response(
                {'error': 'Image file is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create user folder: UserStories/username/
            user_folder = os.path.join('UserStories', user.username)
            full_user_folder = os.path.join(settings.MEDIA_ROOT, user_folder)
            if not os.path.exists(full_user_folder):
                os.makedirs(full_user_folder)
            
            # Generate unique filename and story ID
            story_id = str(uuid.uuid4())[:8]
            filename = f"{uuid.uuid4()}.{image_file.name.split('.')[-1]}"
            file_path = os.path.join(full_user_folder, filename)
            
            # Save file
            default_storage.save(file_path, ContentFile(image_file.read()))
            
            # Store relative path for database
            uploaded_image_path = os.path.join(user_folder, filename)
            
            # Create story
            story = Story.objects.create(
                user=user,
                image_url=uploaded_image_path,  # Store relative path
                user_profile_image=user.profile_image.url if user.profile_image else None
            )
            
            base_url = f"{request.scheme}://{request.get_host()}"
            
            return Response({
                'success': True,
                'message': 'Story added successfully',
                'data': {
                    'story_id': story.story_id,
                    'user': {
                        'id': user.id,
                        'full_name': user.full_name,
                        'username': user.username,
                        'profile_image': f"{base_url}{settings.MEDIA_URL}{user.profile_image}" if user.profile_image else None,
                    },
                    'image_url': f"{base_url}{settings.MEDIA_URL}{uploaded_image_path}",
                    'user_profile_image': story.user_profile_image,
                    'viewers_count': story.viewers.count(),
                    'is_expired': story.is_expired,
                    'created_at': story.created_at.isoformat(),
                    'expires_at': story.expires_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to add story: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetAllStoriesView(APIView):
    """
    API to get all active stories
    URL: /api/stories/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            base_url = f"{request.scheme}://{request.get_host()}"
            
            # Get all active stories (not expired)
            stories = Story.objects.filter(
                expires_at__gt=timezone.now()
            ).order_by('-created_at')
            
            stories_data = []
            for story in stories:
                # Check if current user has viewed this story
                is_viewed = story.viewers.filter(id=user.id).exists()
                
                # Build full image URL
                image_url = story.image_url
                if image_url and not image_url.startswith('http'):
                    image_url = f"{base_url}{settings.MEDIA_URL}{image_url}"
                
                stories_data.append({
                    'story_id': story.story_id,
                    'user': {
                        'id': story.user.id,
                        'full_name': story.user.full_name,
                        'username': story.user.username,
                        'profile_image': f"{base_url}{settings.MEDIA_URL}{story.user.profile_image}" if story.user.profile_image else None,
                    },
                    'image_url': image_url,
                    'user_profile_image': story.user_profile_image,
                    'viewers_count': story.viewers.count(),
                    'is_viewed': is_viewed,
                    'is_expired': story.is_expired,
                    'created_at': story.created_at.isoformat(),
                    'expires_at': story.expires_at.isoformat(),
                })
            
            return Response({
                'success': True,
                'message': 'Stories fetched successfully',
                'data': {
                    'stories': stories_data,
                    'total_stories': len(stories_data),
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch stories: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendFriendRequestView(APIView):
    """
    API to send friend request
    URL: /api/follow/<user_id>/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: None
    """
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        target_user = get_object_or_404(User, id=user_id)
        current_user = user
        
        # Check if trying to follow self
        if current_user == target_user:
            return Response(
                {"error": "You cannot send a friend request to yourself"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if already friends
        if current_user in target_user.friends.all():
            return Response(
                {"error": "You are already friends with this user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if friend request already sent
        if current_user in target_user.friend_requests.all():
            return Response(
                {"error": "Friend request already sent"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if they have sent you a request (mutual follow)
        if target_user in current_user.friend_requests.all():
            # Accept automatically
            current_user.friends.add(target_user)
            target_user.friends.add(current_user)
            target_user.friend_requests.remove(current_user)
            
            # Send notification for mutual friend
            create_notification(
                user=target_user,
                notification_type='friend_request_accepted',
                sender=current_user
            )
            
            return Response({
                "message": "You are now friends!",
                "status": "mutual_friends"
            }, status=status.HTTP_200_OK)
        
        # Send friend request - Add current_user to target_user's friend_requests
        target_user.friend_requests.add(current_user)
        
        # Send notification to target user
        create_notification(
            user=target_user,
            notification_type='friend_request',
            sender=current_user
        )
        
        return Response({
            "message": f"Friend request sent to {target_user.full_name}",
            "status": "request_sent"
        }, status=status.HTTP_201_CREATED)



class GetFriendRequestsView(APIView):
    """
    API to get all pending friend requests for the authenticated user
    URL: /api/friend-requests/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        current_user = user
        pending_requests = current_user.friend_requests.all()
        
        data = []
        for friend_user in pending_requests:
            data.append({
                "id": friend_user.id,
                "full_name": friend_user.full_name,
                "username": friend_user.username,
                "profile_image": friend_user.profile_image.url if friend_user.profile_image else None,
                "bio": friend_user.bio,
                "is_online": friend_user.is_online
            })
        
        return Response({
            "count": pending_requests.count(),
            "requests": data
        }, status=status.HTTP_200_OK)


class UnfollowUserView(APIView):
    """
    API to unfollow/remove a friend
    URL: /api/unfollow/<user_id>/
    Method: DELETE
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def delete(self, request, user_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        target_user = get_object_or_404(User, id=user_id)
        current_user = user
        
        # Check if they are friends
        if target_user not in current_user.friends.all():
            return Response(
                {"error": "You are not friends with this user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Remove from friends
        current_user.friends.remove(target_user)
        target_user.friends.remove(current_user)
        
        return Response({
            "message": f"Unfollowed {target_user.full_name}",
            "status": "unfollowed"
        }, status=status.HTTP_200_OK)


class GetFriendsListView(APIView):
    """
    API to get all friends of the authenticated user
    URL: /api/friends/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        current_user = user
        friends = current_user.friends.all()
        
        data = []
        for friend_user in friends:
            data.append({
                "id": friend_user.id,
                "full_name": friend_user.full_name,
                "username": friend_user.username,
                "profile_image": friend_user.profile_image.url if friend_user.profile_image else None,
                "bio": friend_user.bio,
                "is_online": friend_user.is_online,
                "last_seen": friend_user.last_seen
            })
        
        return Response({
            "count": friends.count(),
            "friends": data
        }, status=status.HTTP_200_OK)

class AcceptFriendRequestView(APIView):
    """
    API to accept a friend request
    URL: /api/accept-request/<user_id>/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: None
    """
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        sender = get_object_or_404(User, id=user_id)
        current_user = user
        
        # Check if request exists
        if sender not in current_user.friend_requests.all():
            return Response(
                {"error": "No friend request from this user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Accept the friend request
        current_user.friends.add(sender)
        sender.friends.add(current_user)
        current_user.friend_requests.remove(sender)
        
        # Send notification to sender
        create_notification(
            user=sender,
            notification_type='friend_request_accepted',
            sender=current_user,
            message=f"{current_user.full_name} accepted your friend request."
        )
        
        return Response({
            "message": f"You are now friends with {sender.full_name}",
            "status": "accepted"
        }, status=status.HTTP_200_OK)


class RejectFriendRequestView(APIView):
    """
    API to reject a friend request
    URL: /api/reject-request/<user_id>/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: None
    """
    permission_classes = [AllowAny]
    
    def post(self, request, user_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        sender = get_object_or_404(User, id=user_id)
        current_user = user
        
        # Check if request exists
        if sender not in current_user.friend_requests.all():
            return Response(
                {"error": "No friend request from this user"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reject the friend request - Just remove from friend_requests
        current_user.friend_requests.remove(sender)
        
        return Response({
            "message": f"Friend request from {sender.full_name} rejected",
            "status": "rejected"
        }, status=status.HTTP_200_OK)


class GetAllUsersView(APIView):
    """
    API to get all users from database
    URL: /api/users/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get all users except the current user
        all_users = User.objects.exclude(id=user.id)
        
        data = []
        for db_user in all_users:
            # Check if current user is friends with this user
            is_friend = db_user in user.friends.all()
            
            # Check if friend request already sent by current user to this user
            request_sent = user in db_user.friend_requests.all()
            
            # Check if this user sent a request to current user
            request_received = db_user in user.friend_requests.all()
            
            data.append({
                "id": db_user.id,
                "uid": str(db_user.uid),
                "full_name": db_user.full_name,
                "username": db_user.username,
                "email": db_user.email,
                "bio": db_user.bio,
                "profile_image": db_user.profile_image.url if db_user.profile_image else None,
                "cover_image": db_user.cover_image.url if db_user.cover_image else None,
                "is_online": db_user.is_online,
                "last_seen": db_user.last_seen,
                "is_friend": is_friend,
                "friend_request_sent": request_sent,
                "friend_request_received": request_received,
                "created_at": db_user.created_at
            })
        
        return Response({
            "count": all_users.count(),
            "users": data
        }, status=status.HTTP_200_OK)


class GetNotificationsView(APIView):
    """
    API to get all notifications for the authenticated user
    URL: /api/notifications/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    Query Params: page (optional), limit (optional)
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            page = int(request.GET.get('page', 1))
            limit = int(request.GET.get('limit', 20))
            offset = (page - 1) * limit
            
            # Get notifications for user
            notifications = Notification.objects.filter(user=user).order_by('-timestamp')[offset:offset+limit]
            total_count = Notification.objects.filter(user=user).count()
            unread_count = Notification.objects.filter(user=user, is_read=False).count()
            
            data = []
            for notification in notifications:
                data.append({
                    'id': notification.id,
                    'message': notification.message,
                    'notification_type': notification.notification_type,
                    'is_read': notification.is_read,
                    'timestamp': notification.timestamp.isoformat(),
                    'sender': {
                        'id': notification.sender.id if notification.sender else None,
                        'full_name': notification.sender.full_name if notification.sender else None,
                        'username': notification.sender.username if notification.sender else None,
                        'profile_image': notification.sender.profile_image.url if notification.sender and notification.sender.profile_image else None,
                    } if notification.sender else None,
                    'post_id': notification.post.post_id if notification.post else None,
                    'comment_id': notification.comment.comment_id if notification.comment else None,
                })
            
            return Response({
                'success': True,
                'data': {
                    'notifications': data,
                    'unread_count': unread_count,
                    'pagination': {
                        'current_page': page,
                        'per_page': limit,
                        'total': total_count,
                        'total_pages': (total_count + limit - 1) // limit if total_count > 0 else 0,
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': f'Failed to fetch notifications: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkNotificationReadView(APIView):
    """
    API to mark a notification as read
    URL: /api/notifications/<notification_id>/read/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def post(self, request, notification_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save()
            
            return Response({
                'success': True,
                'message': 'Notification marked as read'
            }, status=status.HTTP_200_OK)
            
        except Notification.DoesNotExist:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MarkAllNotificationsReadView(APIView):
    """
    API to mark all notifications as read
    URL: /api/notifications/read-all/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        count = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        
        return Response({
            'success': True,
            'message': f'{count} notifications marked as read'
        }, status=status.HTTP_200_OK)


class GetUnreadCountView(APIView):
    """
    API to get unread notification count
    URL: /api/notifications/unread-count/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        count = Notification.objects.filter(user=user, is_read=False).count()
        
        return Response({
            'success': True,
            'unread_count': count
        }, status=status.HTTP_200_OK)


class SendMessageView(APIView):
    """
    API to send a message to another user
    URL: /api/messages/send/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: {
        "receiver_id": 2,
        "content": "Hello!",
        "message_type": "text"  // optional: text, image, video, audio, file
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        receiver_id = request.data.get('receiver_id')
        content = request.data.get('content')
        message_type = request.data.get('message_type', 'text')
        
        # Validation
        if not receiver_id:
            return Response(
                {'error': 'Receiver ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not content:
            return Response(
                {'error': 'Message content is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if receiver exists
        try:
            receiver = User.objects.get(id=receiver_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'Receiver not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if they are friends
        if receiver not in user.friends.all():
            return Response(
                {'error': 'You can only message friends'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Validate message type
        valid_types = ['text', 'image', 'video', 'audio', 'file']
        if message_type not in valid_types:
            return Response(
                {'error': f'Invalid message type. Must be one of: {valid_types}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create message
        message = Message.objects.create(
            sender=user,
            receiver=receiver,
            content=content,
            message_type=message_type,
            is_delivered=False,
            is_read=False,
        )
        
        # You can add notification here (optional)
        # create_notification(
        #     user=receiver,
        #     notification_type='message',
        #     sender=user,
        #     message=f"{user.full_name} sent you a message"
        # )
        
        return Response({
            'success': True,
            'message': 'Message sent successfully',
            'data': {
                'message_id': str(message.message_id),
                'sender_id': message.sender.id,
                'receiver_id': message.receiver.id,
                'content': message.content,
                'message_type': message.message_type,
                'is_delivered': message.is_delivered,
                'is_read': message.is_read,
                'timestamp': message.timestamp.isoformat(),
            }
        }, status=status.HTTP_201_CREATED)


class GetMessagesView(APIView):
    """
    API to get messages between two users (logged in user and another user)
    URL: /api/messages/<user_id>/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    Query Params: limit (optional), before (optional)
    """
    permission_classes = [AllowAny]
    
    def get(self, request, user_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get the other user
        other_user = get_object_or_404(User, id=user_id)
        
        # Check if they are friends
        if other_user not in user.friends.all():
            return Response(
                {'error': 'You can only view messages with friends'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Pagination
        limit = int(request.GET.get('limit', 50))
        before = request.GET.get('before')  # ISO format datetime
        
        # Build query
        query = Q(
            Q(sender=user, receiver=other_user) |
            Q(sender=other_user, receiver=user)
        )
        
        # Filter by before timestamp (for pagination) - DO THIS BEFORE SLICING
        if before:
            try:
                before_datetime = datetime.fromisoformat(before.replace('Z', '+00:00'))
                query &= Q(timestamp__lt=before_datetime)
            except ValueError:
                pass
        
        # Get messages with ordering (DO NOT SLICE YET)
        messages = Message.objects.filter(query).order_by('-timestamp')
        
        # Mark unread messages as read - DO THIS BEFORE SLICING
        unread_messages = messages.filter(sender=other_user, is_read=False)
        unread_messages.update(is_read=True)
        
        # NOW apply the slice for pagination
        messages = messages[:limit]
        
        # Convert to list and reverse for chronological order
        messages_list = list(messages)
        messages_list.reverse()
        
        data = []
        for msg in messages_list:
            data.append({
                'message_id': str(msg.message_id),
                'sender_id': msg.sender.id,
                'sender_name': msg.sender.full_name,
                'sender_username': msg.sender.username,
                'sender_profile_image': msg.sender.profile_image.url if msg.sender.profile_image else None,
                'receiver_id': msg.receiver.id,
                'content': msg.content,
                'message_type': msg.message_type,
                'is_delivered': msg.is_delivered,
                'is_read': msg.is_read,
                'timestamp': msg.timestamp.isoformat(),
            })
        
        # Check if there are more messages
        has_more = Message.objects.filter(query).order_by('-timestamp').count() > limit
        
        return Response({
            'success': True,
            'data': {
                'messages': data,
                'total_count': len(data),
                'has_more': has_more,
                'other_user': {
                    'id': other_user.id,
                    'full_name': other_user.full_name,
                    'username': other_user.username,
                    'profile_image': other_user.profile_image.url if other_user.profile_image else None,
                    'is_online': other_user.is_online,
                    'last_seen': other_user.last_seen.isoformat() if other_user.last_seen else None,
                }
            }
        }, status=status.HTTP_200_OK)


class MarkMessageReadView(APIView):
    """
    API to mark messages as read
    URL: /api/messages/mark-read/
    Method: POST
    Headers: Authorization: Bearer YOUR_TOKEN
    Body: {"sender_id": 2}  // mark all messages from this sender as read
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        sender_id = request.data.get('sender_id')
        
        if not sender_id:
            return Response(
                {'error': 'Sender ID is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get sender
        sender = get_object_or_404(User, id=sender_id)
        
        # Mark all unread messages from this sender as read
        count = Message.objects.filter(
            sender=sender,
            receiver=user,
            is_read=False
        ).update(is_read=True)
        
        return Response({
            'success': True,
            'message': f'{count} messages marked as read',
            'count': count
        }, status=status.HTTP_200_OK)


class GetUnreadMessagesView(APIView):
    """
    API to get unread message count
    URL: /api/messages/unread/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get count of unread messages for this user
        unread_count = Message.objects.filter(
            receiver=user,
            is_read=False
        ).count()
        
        # Get unread messages grouped by sender
        unread_by_sender = Message.objects.filter(
            receiver=user,
            is_read=False
        ).values('sender__id', 'sender__full_name', 'sender__username', 'sender__profile_image') \
         .annotate(count=models.Count('id')) \
         .order_by('-count')
        
        return Response({
            'success': True,
            'data': {
                'total_unread': unread_count,
                'by_sender': list(unread_by_sender)
            }
        }, status=status.HTTP_200_OK)


class GetRecentChatsView(APIView):
    """
    API to get recent chat list (conversations with friends who have messages)
    URL: /api/messages/recent/
    Method: GET
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get all friends
        friends = user.friends.all()
        
        # Get latest message with each friend
        recent_chats = []
        for friend in friends:
            # Get the latest message between user and friend
            latest_message = Message.objects.filter(
                Q(sender=user, receiver=friend) |
                Q(sender=friend, receiver=user)
            ).order_by('-timestamp').first()
            
            if latest_message:
                # Get unread count for messages from this friend
                unread_count = Message.objects.filter(
                    sender=friend,
                    receiver=user,
                    is_read=False
                ).count()
                
                recent_chats.append({
                    'friend': {
                        'id': friend.id,
                        'full_name': friend.full_name,
                        'username': friend.username,
                        'profile_image': friend.profile_image.url if friend.profile_image else None,
                        'is_online': friend.is_online,
                        'last_seen': friend.last_seen.isoformat() if friend.last_seen else None,
                    },
                    'last_message': {
                        'message_id': str(latest_message.message_id),
                        'content': latest_message.content,
                        'message_type': latest_message.message_type,
                        'is_read': latest_message.is_read,
                        'is_delivered': latest_message.is_delivered,
                        'timestamp': latest_message.timestamp.isoformat(),
                        'sender_id': latest_message.sender.id,
                    },
                    'unread_count': unread_count
                })
            else:
                # Friend with no messages yet
                recent_chats.append({
                    'friend': {
                        'id': friend.id,
                        'full_name': friend.full_name,
                        'username': friend.username,
                        'profile_image': friend.profile_image.url if friend.profile_image else None,
                        'is_online': friend.is_online,
                        'last_seen': friend.last_seen.isoformat() if friend.last_seen else None,
                    },
                    'last_message': None,
                    'unread_count': 0
                })
        
        # Sort by latest message timestamp
        recent_chats.sort(
            key=lambda x: x['last_message']['timestamp'] if x['last_message'] else '',
            reverse=True
        )
        
        return Response({
            'success': True,
            'data': recent_chats
        }, status=status.HTTP_200_OK)


class DeleteMessageView(APIView):
    """
    API to delete a message (for both users)
    URL: /api/messages/<message_id>/delete/
    Method: DELETE
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def delete(self, request, message_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get message
        try:
            message = Message.objects.get(message_id=message_id)
        except Message.DoesNotExist:
            return Response(
                {'error': 'Message not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is sender or receiver
        if message.sender != user and message.receiver != user:
            return Response(
                {'error': 'You are not authorized to delete this message'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete the message
        message.delete()
        
        return Response({
            'success': True,
            'message': 'Message deleted successfully'
        }, status=status.HTTP_200_OK)


class DeleteChatHistoryView(APIView):
    """
    API to delete entire chat history with a user
    URL: /api/messages/<user_id>/delete-chat/
    Method: DELETE
    Headers: Authorization: Bearer YOUR_TOKEN
    """
    permission_classes = [AllowAny]
    
    def delete(self, request, user_id):
        user = get_user_from_token(request)
        
        if not user:
            return Response(
                {'error': 'Authentication required'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        other_user = get_object_or_404(User, id=user_id)
        
        # Delete all messages between these two users
        deleted_count = Message.objects.filter(
            Q(sender=user, receiver=other_user) |
            Q(sender=other_user, receiver=user)
        ).delete()
        
        return Response({
            'success': True,
            'message': f'Deleted {deleted_count[0]} messages',
            'count': deleted_count[0]
        }, status=status.HTTP_200_OK)