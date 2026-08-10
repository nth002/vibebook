# VibeBook - Social Media API

VibeBook is a Django REST API-based social media platform that allows users to connect, share posts, and interact with each other.

## 🚀 Features

- **User Authentication**
  - Email-based OTP verification
  - Secure login with token authentication
  - User registration with email verification

- **Social Features**
  - Send/accept/reject friend requests
  - View friend lists
  - Unfollow/remove friends
  - View all users with friendship status

- **Posts**
  - Create posts with text and images
  - View all posts (paginated)
  - View only your posts
  - Like/unlike posts
  - Add comments to posts

- **User Profile**
  - Update profile information
  - Upload profile and cover images
  - View user profiles

## 🛠️ Tech Stack

- **Backend**: Django 4.x, Django REST Framework
- **Database**: PostgreSQL / SQLite (development)
- **Authentication**: Token Authentication
- **Email**: SMTP (Gmail) / Console (development)
- **Image Storage**: Django Media Storage
- **Task Queue**: Threading for async email

## 📦 Installation

### Prerequisites
- Python 3.8+
- pip
- Virtual environment (recommended)

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/vibebook.git
cd vibebook