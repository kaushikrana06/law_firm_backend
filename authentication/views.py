from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

import logging

from .serializers import (
    RegisterSerializer, AttorneyLoginSerializer, UserSerializer,
    EmailVerificationSerializer, CustomTokenObtainPairSerializer
)
from .models import CustomUser
from .permissions import IsOwnerOrReadOnly

logger = logging.getLogger(__name__)

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'message': 'User created successfully. Please check your email for verification.',
            'user_id': user.id,
            'is_verified': user.is_email_verified
        }, status=status.HTTP_201_CREATED)


class AttorneyLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        serializer = AttorneyLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        
        refresh = self.get_serializer_class().get_token(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        return self.request.user


class EmailVerificationView(generics.GenericAPIView):
    serializer_class = EmailVerificationSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        return Response({'message': 'Email verified successfully.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([UserRateThrottle])
def logout_view(request):
    refresh_token = request.data.get('refresh')
    if not refresh_token:
        return Response(
            {'error': 'Refresh token required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        # This automatically finds/creates the OutstandingToken and
        # inserts a row in the blacklist table.
        token = RefreshToken(refresh_token)
        token.blacklist()
    except TokenError:
        return Response(
            {'error': 'Invalid or expired token.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    logger.info(
        f"User {getattr(request.user, 'id', 'unknown')} logged out (refresh blacklisted)"
    )
    return Response({'message': 'Logged out successfully.'}, status=status.HTTP_205_RESET_CONTENT)


class CustomTokenRefreshView(TokenRefreshView):
    throttle_classes = [UserRateThrottle]

class CustomTokenVerifyView(TokenVerifyView):
    throttle_classes = [UserRateThrottle]

class ClientLoginView(TokenObtainPairView):
    pass    