import pytest
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from unittest.mock import patch
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def user_data():
    return {
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'SecurePass123!',
        'password_confirm': 'SecurePass123!',
        'first_name': 'Test',
        'last_name': 'User'
    }

class TestAuthentication(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('auth:register')
        self.login_url = reverse('auth:login')
        self.profile_url = reverse('auth:profile')
        self.verify_url = reverse('auth:verify_email')
        self.refresh_url = reverse('auth:token_refresh')
        self.logout_url = reverse('auth:logout')

    @patch('authentication.models.send_mail')
    def test_user_registration(self, mock_send_mail):
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user_id', response.data)
        self.assertFalse(User.objects.get(id=response.data['user_id']).is_email_verified)
        mock_send_mail.assert_called_once()

    def test_registration_password_mismatch(self):
        invalid_data = self.user_data.copy()
        invalid_data['password_confirm'] = 'DifferentPass'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_success(self):
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.is_email_verified = True
        user.save()

        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_unverified_email(self):
        self.client.post(self.register_url, self.user_data)
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_profile_access(self):
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.is_email_verified = True
        user.save()
        
        login_data = {'email': self.user_data['email'], 'password': self.user_data['password']}
        login_response = self.client.post(self.login_url, login_data)
        access_token = login_response.data['access']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_profile_unauthenticated(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_email_verification(self):
        response = self.client.post(self.register_url, self.user_data)
        user = User.objects.get(id=response.data['user_id'])
        token = user.email_verification_token
        
        verify_data = {'token': token}
        response = self.client.post(self.verify_url, verify_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_email_verification_invalid_token(self):
        verify_data = {'token': 'invalid_token'}
        response = self.client.post(self.verify_url, verify_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('rest_framework_simplejwt.token_blacklist.models.BlacklistedToken.objects.get_or_create')
    def test_logout(self, mock_blacklist):
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email=self.user_data['email'])
        user.is_email_verified = True
        user.save()
        
        login_data = {'email': self.user_data['email'], 'password': self.user_data['password']}
        login_response = self.client.post(self.login_url, login_data)
        refresh_token = login_response.data['refresh']
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_response.data["access"]}')
        logout_data = {'refresh': refresh_token}
        response = self.client.post(self.logout_url, logout_data)
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
        mock_blacklist.assert_called_once()