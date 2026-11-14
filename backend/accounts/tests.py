from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

User = get_user_model()

SIGNUP_URL = "/api/auth/signup/"
LOGIN_URL = "/api/auth/login/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"

PASSWORD = "Str0ng!Harvest2026"


class AuthTests(APITestCase):
    def signup(self, **overrides):
        body = {
            "full_name": "Abdul Rehman",
            "email": "Farmer@Example.com",
            "password": PASSWORD,
            "confirm_password": PASSWORD,
        }
        body.update(overrides)
        return self.client.post(SIGNUP_URL, body, format="json")

    def test_signup_creates_user_and_returns_token(self):
        res = self.signup()
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.data["status"], "success")
        self.assertEqual(res.data["user"]["email"], "farmer@example.com")
        self.assertEqual(res.data["user"]["full_name"], "Abdul Rehman")
        self.assertNotIn("password", res.data["user"])
        self.assertTrue(Token.objects.filter(key=res.data["token"]).exists())

    def test_signup_works_without_csrf_token(self):
        client = APIClient(enforce_csrf_checks=True)
        res = client.post(
            SIGNUP_URL,
            {"full_name": "A B", "email": "csrf@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 201)

    def test_signup_rejects_duplicate_email_case_insensitive(self):
        self.signup()
        res = self.signup(email="FARMER@example.com")
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data["status"], "error")
        self.assertIn("email", res.data["errors"])

    def test_signup_rejects_mismatched_passwords(self):
        res = self.signup(confirm_password="different-Pass1!")
        self.assertEqual(res.status_code, 400)
        self.assertIn("confirm_password", res.data["errors"])

    def test_signup_rejects_weak_password(self):
        res = self.signup(password="12345", confirm_password="12345")
        self.assertEqual(res.status_code, 400)
        self.assertIn("password", res.data["errors"])

    def test_signup_requires_fields(self):
        res = self.client.post(SIGNUP_URL, {}, format="json")
        self.assertEqual(res.status_code, 400)
        for field in ("full_name", "email", "password"):
            self.assertIn(field, res.data["errors"])

    def test_login_returns_same_token(self):
        token = self.signup().data["token"]
        res = self.client.post(
            LOGIN_URL,
            {"email": "farmer@EXAMPLE.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["token"], token)
        self.assertEqual(res.data["user"]["email"], "farmer@example.com")

    def test_login_wrong_password(self):
        self.signup()
        res = self.client.post(
            LOGIN_URL,
            {"email": "farmer@example.com", "password": "wrong"},
            format="json",
        )
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data["message"], "Invalid email or password.")

    def test_login_unknown_email(self):
        res = self.client.post(
            LOGIN_URL,
            {"email": "nobody@example.com", "password": PASSWORD},
            format="json",
        )
        self.assertEqual(res.status_code, 401)

    def test_me_requires_token(self):
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, 401)
        self.assertEqual(res.data["status"], "error")

    def test_me_and_logout_with_token(self):
        token = self.signup().data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["user"]["email"], "farmer@example.com")

        res = self.client.post(LOGOUT_URL)
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Token.objects.filter(key=token).exists())

        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, 401)