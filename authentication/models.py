from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
import uuid
from .manager import UserManager
from phonenumber_field.modelfields import PhoneNumberField
from django.core.validators import EmailValidator, RegexValidator
import secrets
from django.utils import timezone
from datetime import timedelta


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(max_length=250, unique=True)
    email = models.EmailField(
        unique=True,
        validators=[EmailValidator(message="Enter a valid email address")]
    )
    phone_number = PhoneNumberField(
        unique=True,
        error_messages={
            'invalid': 'Enter a valid phone number (e.g. +1234567890)'
        }
    )
    is_active = models.BooleanField(default=False)  # inactive until email verified
    is_admin = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'phone_number']

    def __str__(self):
        return self.username

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_staff(self):
        return self.is_admin


class PasswordResetToken(models.Model):
    """Store tokens for password reset"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_hex(32)  # 64 chars hex
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if the token is valid (not expired and not used)"""
        return not self.used and self.expires_at > timezone.now()

    class Meta:
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]


class EmailVerificationCode(models.Model):
    """Store 6-digit verification codes for onboarding"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_codes')
    code = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(
                regex=r'^\d{6}$',
                message="Verification code must be exactly 6 digits"
            )
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def is_valid(self):
        """Check if the code is valid (not expired and not used)"""
        return not self.used and self.expires_at > timezone.now()

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['user']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.code}"
