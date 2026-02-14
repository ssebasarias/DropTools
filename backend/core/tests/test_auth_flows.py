# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from core.models import AuthToken, User
from core.services.auth_tokens import create_auth_token


class AuthFlowsTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_register_creates_unverified_user_and_no_session_token(self):
        payload = {
            "name": "Nuevo Usuario",
            "email": "nuevo@example.com",
            "password": "Str0ng!Pass123",
        }
        response = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("token", response.data)
        self.assertIn("detail", response.data)

        user = User.objects.get(email="nuevo@example.com")
        self.assertFalse(user.email_verified)
        self.assertTrue(AuthToken.objects.filter(user=user, purpose=AuthToken.PURPOSE_VERIFY_EMAIL).exists())

    def test_login_requires_verified_email(self):
        user = User.objects.create_user(
            username="sinverify@example.com",
            email="sinverify@example.com",
            password="Str0ng!Pass123",
            email_verified=False,
        )
        response = self.client.post(
            "/api/auth/login/",
            {"email": user.email, "password": "Str0ng!Pass123"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("verificar", response.data.get("error", "").lower())

    def test_verify_email_ok(self):
        user = User.objects.create_user(
            username="verify@example.com",
            email="verify@example.com",
            password="Str0ng!Pass123",
            email_verified=False,
        )
        raw_token = create_auth_token(user, AuthToken.PURPOSE_VERIFY_EMAIL, expires_in_seconds=300)

        response = self.client.post("/api/auth/verify-email/", {"token": raw_token}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("detail"), "Email verificado correctamente.")

        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        self.assertIsNotNone(user.email_verified_at)
        token_record = AuthToken.objects.filter(user=user, purpose=AuthToken.PURPOSE_VERIFY_EMAIL).latest("created_at")
        self.assertIsNotNone(token_record.used_at)

    def test_verify_email_expired_returns_410(self):
        user = User.objects.create_user(
            username="expired@example.com",
            email="expired@example.com",
            password="Str0ng!Pass123",
            email_verified=False,
        )
        raw_token = create_auth_token(user, AuthToken.PURPOSE_VERIFY_EMAIL, expires_in_seconds=-60)
        response = self.client.post("/api/auth/verify-email/", {"token": raw_token}, format="json")
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data.get("detail"), "Token expirado.")

    def test_verify_email_used_returns_409(self):
        user = User.objects.create_user(
            username="idempotent@example.com",
            email="idempotent@example.com",
            password="Str0ng!Pass123",
            email_verified=True,
            email_verified_at=timezone.now(),
        )
        raw_token = create_auth_token(user, AuthToken.PURPOSE_VERIFY_EMAIL, expires_in_seconds=300)
        token_record = AuthToken.objects.filter(user=user, purpose=AuthToken.PURPOSE_VERIFY_EMAIL).latest("created_at")
        token_record.used_at = timezone.now()
        token_record.save(update_fields=["used_at"])

        response = self.client.post("/api/auth/verify-email/", {"token": raw_token}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data.get("detail"), "Token ya utilizado.")

    def test_verify_email_invalid_returns_400(self):
        response = self.client.post("/api/auth/verify-email/", {"token": "invalid-token"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get("detail"), "Token inválido.")

    def test_password_reset_request_is_neutral(self):
        user = User.objects.create_user(
            username="reset@example.com",
            email="reset@example.com",
            password="Str0ng!Pass123",
            email_verified=True,
        )
        response_existing = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": user.email},
            format="json",
        )
        response_missing = self.client.post(
            "/api/auth/password-reset/request/",
            {"email": "nadie@example.com"},
            format="json",
        )
        self.assertEqual(response_existing.status_code, 200)
        self.assertEqual(response_missing.status_code, 200)
        self.assertEqual(response_existing.data.get("detail"), response_missing.data.get("detail"))
        self.assertTrue(AuthToken.objects.filter(user=user, purpose=AuthToken.PURPOSE_RESET_PASSWORD).exists())

    def test_password_reset_confirm_updates_password_and_revokes_api_tokens(self):
        user = User.objects.create_user(
            username="confirm@example.com",
            email="confirm@example.com",
            password="OldPass!123",
            email_verified=True,
        )
        old_api_token = Token.objects.create(user=user)
        raw_token = create_auth_token(user, AuthToken.PURPOSE_RESET_PASSWORD, expires_in_seconds=300)

        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw_token, "new_password": "Nuev0Pass!456"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("detail"), "Contraseña actualizada correctamente.")

        user.refresh_from_db()
        self.assertTrue(user.check_password("Nuev0Pass!456"))
        self.assertFalse(Token.objects.filter(key=old_api_token.key).exists())

        token_record = AuthToken.objects.filter(user=user, purpose=AuthToken.PURPOSE_RESET_PASSWORD).latest("created_at")
        self.assertIsNotNone(token_record.used_at)

    def test_password_reset_confirm_expired_returns_410(self):
        user = User.objects.create_user(
            username="expiredreset@example.com",
            email="expiredreset@example.com",
            password="OldPass!123",
            email_verified=True,
        )
        raw_token = create_auth_token(user, AuthToken.PURPOSE_RESET_PASSWORD, expires_in_seconds=-10)
        response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw_token, "new_password": "Nuev0Pass!456"},
            format="json",
        )
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.data.get("detail"), "Token expirado.")

    def test_password_reset_confirm_used_returns_409(self):
        user = User.objects.create_user(
            username="usedreset@example.com",
            email="usedreset@example.com",
            password="OldPass!123",
            email_verified=True,
        )
        raw_token = create_auth_token(user, AuthToken.PURPOSE_RESET_PASSWORD, expires_in_seconds=300)
        first_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw_token, "new_password": "Nuev0Pass!456"},
            format="json",
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"token": raw_token, "new_password": "OtraPass!789"},
            format="json",
        )
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.data.get("detail"), "Token ya utilizado.")
