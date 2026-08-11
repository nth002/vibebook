from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from vibebookApiApp import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Auth APIs
    path('auth/send-otp/', views.SendOTPView.as_view(), name='send-otp'),
    path('auth/verify-otp/', views.VerifyOTPView.as_view(), name='verify-otp'),
    # path('auth/resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    
    # Post APIs
    path('posts/create/', views.CreatePostView.as_view(), name='create-post'),
    path('posts/all/', views.GetAllPostsView.as_view(), name='get-all-posts'),  # Get all posts

    path('posts/<str:post_id>/comment/', views.AddCommentView.as_view(), name='add-comment'),
    path('posts/<str:post_id>/like/', views.LikePostView.as_view(), name='like-post'),

    path('stories/create/', views.AddStoryView.as_view(), name='add-story'),
    path('stories/', views.GetAllStoriesView.as_view(), name='get-stories'),

    path('api/follow/<int:user_id>/', views.SendFriendRequestView.as_view(), name='send-friend-request'),
    path('api/friend-requests/', views.GetFriendRequestsView.as_view(), name='friend-requests'),
    path('api/unfollow/<int:user_id>/', views.UnfollowUserView.as_view(), name='unfollow'),
    path('api/friends/', views.GetFriendsListView.as_view(), name='friends-list'),
    path('api/accept-request/<int:user_id>/', views.AcceptFriendRequestView.as_view(), name='accept-request'),
    path('api/reject-request/<int:user_id>/', views.RejectFriendRequestView.as_view(), name='reject-request'),

    path('api/users/', views.GetAllUsersView.as_view(), name='all-users'),  # Add this
    path('api/update-profile/', views.UpdateProfileView.as_view(), name='update-profile'),
    path('api/profile/', views.GetProfileView.as_view(), name='profile'),

    path('api/posts/my/', views.GetMyPostsView.as_view(), name='my-posts'),

    path('api/notifications/', views.GetNotificationsView.as_view(), name='notifications'),
    path('api/notifications/<str:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark-read'),
    path('api/notifications/read-all/', views.MarkAllNotificationsReadView.as_view(), name='mark-all-read'),
    path('api/notifications/unread-count/', views.GetUnreadCountView.as_view(), name='unread-count'),

    path('api/messages/send/', views.SendMessageView.as_view(), name='send-message'),
    path('api/messages/<int:user_id>/', views.GetMessagesView.as_view(), name='get-messages'),
    path('api/messages/mark-read/', views.MarkMessageReadView.as_view(), name='mark-read'),
    path('api/messages/unread/', views.GetUnreadMessagesView.as_view(), name='unread'),
    path('api/messages/recent/', views.GetRecentChatsView.as_view(), name='recent-chats'),
    path('api/messages/<str:message_id>/delete/', views.DeleteMessageView.as_view(), name='delete-message'),
    path('api/messages/<int:user_id>/delete-chat/', views.DeleteChatHistoryView.as_view(), name='delete-chat'),

    path('api/memes/create/', views.CreateMemeView.as_view(), name='create-meme'),
    path('api/memes/', views.GetMemesView.as_view(), name='get-memes'),
    path('api/memes/<str:meme_id>/like/', views.LikeMemeView.as_view(), name='like-meme'),
    path('api/memes/<str:meme_id>/share/', views.ShareMemeView.as_view(), name='share-meme'),
    path('api/memes/liked/', views.GetLikedMemesView.as_view(), name='liked-memes'),
    
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)