# settings.py
import os
from pathlib import Path
from datetime import timedelta
import cloudinary
import cloudinary.uploader
import cloudinary.api
import dj_database_url  # ✅ ADD THIS

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-here-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'vibebookApiApp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
]

ROOT_URLCONF = 'vibebookApi.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'vibebookApi.wsgi.application'

# ✅ PostgreSQL DATABASE CONFIGURATION (From your Render Screenshot)
DATABASES = {
    'default': dj_database_url.config(
        default='postgresql://vibebookuser:3Vi5PXHOAiciTDnUSBeYjaqchIJRqOcV@dpg-d9u4mtbm8hqs73eh7svg-a.oregon-postgres.render.com/vibebook',
        conn_max_age=600,
    )
}

# ✅ If you prefer manual config (without dj_database_url), use this instead:
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'vibebook',
#         'USER': 'vibebookuser',
#         'PASSWORD': '3V15PXHOAic1TDnUSBeYjaqchIJRq0cV',
#         'HOST': 'dpg-d9u4mtbm8hqs73eh7svg-a.singapore.render.com',
#         'PORT': '5432',
#     }
# }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# ✅ Email Configuration (Gmail)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587  # ✅ Changed to 587 for TLS (more secure)
EMAIL_USE_TLS = True  # ✅ Changed to True
EMAIL_USE_SSL = False
EMAIL_HOST_USER = 'noreply.vibebook@gmail.com'
EMAIL_HOST_PASSWORD = 'iwkp tvws vyot drma'
DEFAULT_FROM_EMAIL = 'noreply.vibebook@gmail.com'

# ✅ Cloudinary Configuration
cloudinary.config(
    cloud_name="qn9uvuof",
    api_key="831393533574731",
    api_secret="m3VZvUMGZuSTuc2BEsnPB-IBLFQ",
    secure=True
)