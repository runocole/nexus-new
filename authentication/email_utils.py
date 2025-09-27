import random
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from authentication.models import User

def generate_verification_code():
    """Generate a 6-digit numeric verification code"""
    return str(random.randint(100000, 999999))

def send_verification_email(user: User, code: str):
    """Send email verification code to user"""
    subject = "Verify your email address"
    message = f"""
    Hello {user.username},

    Use the following verification code to activate your account:

    {code}

    This code will expire in 10 minutes.

    If you didn’t request this, you can ignore this email.
    """
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

def send_password_reset_email(user: User, token: str):
    """Send password reset email with token link"""
    reset_link = f"{settings.FRONTEND_URL}/reset-password/{token}"
    subject = "Password Reset Request"
    message = f"""
    Hello {user.username},

    You requested a password reset. Click the link below:

    {reset_link}

    This link will expire in 30 minutes.

    If you didn’t request this, you can ignore this email.
    """
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]

    send_mail(subject, message, from_email, recipient_list, fail_silently=False)
