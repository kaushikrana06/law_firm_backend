from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import CustomUser
import logging

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_email_verified', 'last_activity')
        read_only_fields = ('id', 'last_activity')

    def validate_email(self, value: str) -> str:
        if CustomUser.objects.filter(email=value).exclude(id=self.instance.id if self.instance else 0).exists():
            raise serializers.ValidationError("Email already in use.")
        return value

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password], min_length=12)
    password_confirm = serializers.CharField(write_only=True, label='Password Confirmation')
    email = serializers.EmailField()

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password_confirm', 'first_name', 'last_name')

    def validate(self, attrs: dict) -> dict:
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data: dict) -> CustomUser:
        validated_data.pop('password_confirm')
        user = CustomUser.objects.create_user(**validated_data)
        user.is_staff = True             
        user.save(update_fields=["is_staff"])
        user.send_email_verification()
        logger.info(f"User registered: {user.id}")
        return user

class AttorneyLoginSerializer(serializers.Serializer):
    username = serializers.CharField(allow_blank=True, required=False)
    email = serializers.EmailField(allow_blank=True, required=True)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict):
        identifier = attrs.get('email') or attrs.get('username')
        if not identifier:
            raise serializers.ValidationError("Username or email is required.")
        user = authenticate(username=identifier, password=attrs['password'])
        if user:
            if not user.is_active or user.is_deleted:
                raise serializers.ValidationError("Account is inactive or deleted.")
            if not user.is_email_verified:
                raise serializers.ValidationError("Please verify your email before logging in.")
            if not (user.is_staff or user.is_superuser):
                raise serializers.ValidationError("This login is for attorneys/admins only.")
            return user
        raise serializers.ValidationError("Invalid credentials.")

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['is_verified'] = user.is_email_verified
        token["user_type"] = "ADMIN" if user.is_superuser else ("ATTORNEY" if user.is_staff else "CLIENT")
        return token

class EmailVerificationSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=255)

    def validate_token(self, value: str) -> str:
        try:
            user = CustomUser.objects.get(email_verification_token=value)
            if not user.verify_email(value):
                raise serializers.ValidationError("Invalid or expired token.")
            return value
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid token.")
        
class ClientLoginSerializer(serializers.Serializer):
    pass