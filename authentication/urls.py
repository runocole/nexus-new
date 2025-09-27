from django.urls import path
from .views import (
    MyTokenObtainPairView,
    EmailUsernameTokenObtainPairView,
    CreateUserView,
    UserProfileView,
    ChangePasswordView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    PasswordResetConfirmView,
    EmailVerificationRequestView,
    EmailVerificationConfirmView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # JWT Auth
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/', EmailUsernameTokenObtainPairView.as_view(), name='login_with_email_or_username'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # User management
    path('users/', CreateUserView.as_view(), name='create_user'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('changepassword/', ChangePasswordView.as_view(), name='change_password'),

    # Password reset
    path('password-reset/request/', PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('password-reset/verify/', PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('password-reset/confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Email verification
    path('email/verify/request/', EmailVerificationRequestView.as_view(), name='email_verification_request'),
    path('email/verify/confirm/', EmailVerificationConfirmView.as_view(), name='email_verification_confirm'),
]
