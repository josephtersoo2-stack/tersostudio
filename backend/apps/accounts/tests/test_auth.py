"""Comprehensive tests for Accounts and Authentication foundation."""
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token

from apps.organizations.models import Organization, OrganizationMembership

User = get_user_model()


class UserModelTests(TestCase):
    """Test suite for custom User model."""

    def test_create_user_successful(self):
        """Test creating a new standard user with normalized email."""
        email = "TestUser@Example.COM"
        password = "SecurePassword123!"
        user = User.objects.create_user(email=email, password=password, first_name="John", last_name="Doe")

        self.assertEqual(user.email, "testuser@example.com")
        self.assertTrue(user.check_password(password))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.full_name, "John Doe")

    def test_create_superuser_successful(self):
        """Test creating a superuser with staff and admin privileges."""
        email = "admin@example.com"
        password = "AdminPassword123!"
        admin_user = User.objects.create_superuser(email=email, password=password)

        self.assertEqual(admin_user.email, email)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)

    def test_create_user_without_email_fails(self):
        """Test that creating a user without email raises ValueError."""
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="password123")


class AuthenticationAPITests(TestCase):
    """Test suite for authentication REST endpoints."""

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse("auth_register")
        self.login_url = reverse("auth_login")
        self.logout_url = reverse("auth_logout")
        self.me_url = reverse("auth_me")

        self.user_data = {
            "email": "engineer@tersuite.com",
            "password": "StrongPassword123!",
            "first_name": "Alice",
            "last_name": "Smith",
        }

    def test_register_user_successful_and_provisions_personal_org(self):
        """Verify successful registration returns HTTP 201, token, and provisions personal org as OWNER."""
        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], "engineer@tersuite.com")
        self.assertEqual(data["user"]["full_name"], "Alice Smith")

        # Verify personal organization provisioned
        user = User.objects.get(email="engineer@tersuite.com")
        personal_org = Organization.objects.filter(created_by=user, is_personal=True).first()
        self.assertIsNotNone(personal_org)

        membership = OrganizationMembership.objects.filter(organization=personal_org, user=user).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, "OWNER")
        self.assertTrue(membership.is_active)

        # Verify membership in user payload
        self.assertIn("organization_memberships", data["user"])
        self.assertEqual(len(data["user"]["organization_memberships"]), 1)
        self.assertEqual(data["user"]["organization_memberships"][0]["role"], "OWNER")
        self.assertTrue(data["user"]["organization_memberships"][0]["is_personal"])

    def test_register_rollback_on_personal_org_failure(self):
        """Verify registration rolls back user creation atomically if org provisioning fails."""
        with patch("apps.accounts.serializers.ensure_personal_organization", side_effect=RuntimeError("Org creation failed")):
            response = self.client.post(self.register_url, self.user_data)
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        self.assertFalse(User.objects.filter(email=self.user_data["email"]).exists())
        self.assertFalse(Organization.objects.filter(slug__icontains="engineer").exists())

    def test_register_duplicate_email_fails(self):
        """Verify registering existing email returns validation error."""
        self.client.post(self.register_url, self.user_data)
        response = self.client.post(self.register_url, self.user_data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_short_password_fails(self):
        """Verify registration fails when password is shorter than 8 characters."""
        payload = {
            "email": "short@tersuite.com",
            "password": "short",
        }
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_successful(self):
        """Verify login returns token and user payload."""
        User.objects.create_user(
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

        response = self.client.post(
            self.login_url,
            {
                "email": self.user_data["email"],
                "password": self.user_data["password"],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("token", data)
        self.assertIn("user", data)

    def test_login_invalid_credentials_fails(self):
        """Verify login fails with wrong password."""
        User.objects.create_user(
            email=self.user_data["email"],
            password=self.user_data["password"],
        )

        response = self.client.post(
            self.login_url,
            {
                "email": self.user_data["email"],
                "password": "WrongPassword!",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_current_user_authenticated_with_memberships(self):
        """Verify /api/v1/auth/me/ returns authenticated user data with active organization memberships."""
        # Use registration endpoint to create user with personal org
        reg_response = self.client.post(self.register_url, self.user_data)
        token_key = reg_response.json()["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["user"]["email"], "engineer@tersuite.com")
        self.assertEqual(data["user"]["first_name"], "Alice")
        self.assertIn("organization_memberships", data["user"])
        self.assertEqual(len(data["user"]["organization_memberships"]), 1)
        self.assertEqual(data["user"]["organization_memberships"][0]["role"], "OWNER")

    def test_current_user_unauthenticated_fails(self):
        """Verify /api/v1/auth/me/ returns HTTP 401 when unauthenticated."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_revokes_token(self):
        """Verify /api/v1/auth/logout/ deletes the active token."""
        user = User.objects.create_user(
            email=self.user_data["email"],
            password=self.user_data["password"],
        )
        token, _ = Token.objects.get_or_create(user=user)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(key=token.key).exists())
