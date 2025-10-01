from django.urls import path
from .views import (
    RegisterView, AttorneyLoginView, UserProfileView, EmailVerificationView,
    logout_view, CustomTokenRefreshView, CustomTokenVerifyView
)

app_name = 'authentication'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('attorney/login/', AttorneyLoginView.as_view(), name='attorney_login'),
    path('logout/', logout_view, name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('verify-email/', EmailVerificationView.as_view(), name='verify_email'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
]