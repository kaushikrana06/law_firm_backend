from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.template import TemplateDoesNotExist
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import secrets
from django.utils.crypto import get_random_string
import logging

logger = logging.getLogger(__name__)

class CustomUserManager(UserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email must be set")
        email = self.normalize_email(email)
        # ensure we have a username even if not provided
        username = extra_fields.pop("username", None) or email.split("@")[0]
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    is_email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=255, blank=True, null=True)
    email_verification_expires = models.DateTimeField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(blank=True, null=True)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = CustomUserManager()
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self) -> str:
        return f"{self.username} ({self.email})"

    def send_email_verification(self) -> None:
        token = secrets.token_urlsafe(48)
        self.email_verification_token = token
        self.save(update_fields=["email_verification_token"])
        verify_url = f"{settings.BACKEND_VERIFY_URL}?token={token}"

        subject = "Verify your email address"
        context = {
            "user": self,
            "verify_url": verify_url,
            "project_name": "Your App Name",
        }

        try:
            html_body = render_to_string("email/verification_email.html", context)
        except TemplateDoesNotExist:
            # Fallback inline HTML
            html_body = (
                f"<p>Hi {self.first_name or self.username},</p>"
                f"<p>Please verify your email:</p>"
                f"<p><a href='{verify_url}'>Verify Email</a></p>"
                f"<p>If the button doesn’t work, copy this link: {verify_url}</p>"
            )

        text_body = strip_tags(html_body)

        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[self.email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)


    def verify_email(self, token: str) -> bool:
        if self.is_email_verified:
            return False
        if self.email_verification_expires and self.email_verification_expires < timezone.now():
            return False
        if token and secrets.compare_digest(token, (self.email_verification_token or "")):
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
    
class Attorney(CustomUser):
    class Meta:
        proxy = True
        verbose_name = "Attorney"
        verbose_name_plural = "Attorneys"    