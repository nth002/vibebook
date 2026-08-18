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

    # Date Invite APIs
    path('api/date-invite/send/', views.SendDateInviteView.as_view(), name='send-date-invite'),
    path('api/date-invites/', views.GetDateInvitesView.as_view(), name='get-date-invites'),
    path('api/date-invite/accept/<str:invite_id>/', views.AcceptDateInviteView.as_view(), name='accept-date-invite'),
    path('api/date-invite/reject/<str:invite_id>/', views.RejectDateInviteView.as_view(), name='reject-date-invite'),
    
    # Date Booking APIs
    path('api/date/book/', views.BookDateView.as_view(), name='book-date'),
    path('api/date/confirm/<str:booking_id>/', views.ConfirmDateBookingView.as_view(), name='confirm-date-booking'),
    path('api/date/bookings/', views.GetDateBookingsView.as_view(), name='get-date-bookings'),

    path('api/coffee-shops/', views.GetCoffeeShopsView.as_view(), name='get-coffee-shops'),


    path('api/ads/create/', views.CreateAdView.as_view(), name='create-ad'),
    path('api/ads/active/', views.GetActiveAdsView.as_view(), name='active-ads'),
    path('api/ads/all/', views.GetAllAdsView.as_view(), name='all-ads'),
    path('api/ads/dismiss/<str:ad_id>/', views.DismissAdView.as_view(), name='dismiss-ad'),
    path('api/ads/click/<str:ad_id>/', views.TrackAdClickView.as_view(), name='track-ad-click'),
    path('api/ads/update/<str:ad_id>/', views.UpdateAdView.as_view(), name='update-ad'),

    path('create_ad_page/', views.create_ad_page, name='create_ad_page'),
    path('', views.landing, name='landing'),
    path('view-ads/', views.view_ads_page, name='view_ads_page'),

    path('api/public/ads/create/', views.PublicCreateAdView.as_view(), name='public_create_ad'),
    path('api/public/ads/', views.PublicGetAllAdsView.as_view(), name='public_get_all_ads'),
    path('api/public/ads/<uuid:ad_id>/', views.PublicGetAdDetailView.as_view(), name='public_ad_detail'),
    path('api/public/ads/<uuid:ad_id>/view/', views.PublicTrackAdViewView.as_view(), name='public_track_view'),
    path('api/public/ads/<uuid:ad_id>/click/', views.PublicTrackAdClickView.as_view(), name='public_track_click'),
    path('api/public/ads/<uuid:ad_id>/stats/', views.PublicGetAdStatsView.as_view(), name='public_ad_stats'),
    

    
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)