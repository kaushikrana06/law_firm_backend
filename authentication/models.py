from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
import logging

logger = logging.getLogger(__name__)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)
    email_verification_expires = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        return f"{self.username} ({self.email})"

    def send_email_verification(self) -> None:
        if self.is_email_verified:
            return
        
        token = get_random_string(64)
        self.email_verification_token = token
        self.email_verification_expires = timezone.now() + timezone.timedelta(hours=24)
        self.save(update_fields=['email_verification_token', 'email_verification_expires'])
        
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{token}/"
        subject = 'Verify your email address'
        message = f'Please click this link to verify your email: {verification_url}'
        
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.email])
            logger.info(f"Verification email sent to {self.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {self.email}: {e}")

    def verify_email(self, token: str) -> bool:
        if self.is_email_verified or self.email_verification_expires < timezone.now():
            return False
        
        if self.email_verification_token == token:
            self.is_email_verified = True
            self.email_verification_token = None
            self.email_verification_expires = None
            self.save(update_fields=['is_email_verified', 'email_verification_token', 'email_verification_expires'])
            logger.info(f"Email verified for user {self.id}")
            return True
        return False

    def soft_delete(self) -> None:
        self.is_active = False
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_active', 'deleted_at'])
        logger.info(f"User {self.id} soft deleted")

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None