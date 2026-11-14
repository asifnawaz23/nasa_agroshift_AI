from django.test import Client, TestCase


class CsrfTests(TestCase):
    """The frontend sends plain JSON POSTs with no CSRF token; these must not get 403."""

    def setUp(self):
        # enforce_csrf_checks=True makes the test client behave like a real browser
        self.client = Client(enforce_csrf_checks=True)

    def post_json(self, url, body):
        return self.client.post(url, body, content_type="application/json")

    def test_analyze_is_not_blocked_by_csrf(self):
        # Empty body fails validation (400) before any NASA data is fetched
        res = self.post_json("/api/analyze/", {})
        self.assertNotEqual(res.status_code, 403)
        self.assertEqual(res.status_code, 400)

    def test_explain_is_not_blocked_by_csrf(self):
        analysis = {"strategies": [{"key": "current", "name": "Current", "scores": {"overall": 60}}]}
        res = self.post_json("/api/explain/", {"analysis": analysis})
        self.assertEqual(res.status_code, 200)

    def test_chat_is_not_blocked_by_csrf(self):
        res = self.post_json("/api/chat/", {"message": "Tell me about wheat"})
        self.assertEqual(res.status_code, 200)