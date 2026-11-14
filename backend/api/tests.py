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

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd

SAMPLE_POWER = (
    Path(__file__).resolve().parents[1]
    / "engine" / "tests" / "sample_power_iowa.csv"
)

ANALYZE_BODY = {
    "lat": 42.0,
    "lon": -93.6,
    "current_rotation": None,
    "priorities": {"water": 4, "soil": 5, "income": 3, "erosion": 4, "pest": 2},
    "constraints": {
        "water_availability": "rainfed",
        "equipment": "standard",
        "market_pref": "balanced",
    },
    "scenario": {"rain_pct": 0, "temp_c": 0},
    "lang": "en",
}


def _sample_daily(lat, lon):
    daily = pd.read_csv(SAMPLE_POWER, parse_dates=["date"])
    return daily, {"cache_hit": True, "fallback_used": False, "fetched_at": None}


@patch("api.views.get_soil", lambda lat, lon: (None, {"cache_hit": False}))
@patch("api.views.get_power_daily", _sample_daily)
class AnalyzeResponseTests(TestCase):
    """Offline /api/analyze/ checks: NASA POWER is replaced by the Iowa sample file."""

    def analyze(self, **changes):
        body = {**ANALYZE_BODY, **changes}
        res = self.client.post(
            "/api/analyze/", json.dumps(body), content_type="application/json"
        )
        self.assertEqual(res.status_code, 200, res.content[:500])
        return res.json()

    def test_strategies_have_scores_and_five_explanation_parts(self):
        data = self.analyze()

        self.assertEqual(
            [s["key"] for s in data["strategies"]],
            ["current", "water_saver", "soil_builder"],
        )
        for strategy in data["strategies"]:
            for part in ("why_suggested", "evidence", "benefits", "info_gaps", "local_review"):
                self.assertIn(part, strategy)
            self.assertIn("overall", strategy["scores"])

    def test_climate_has_twelve_monthly_rows_and_no_scenario_by_default(self):
        data = self.analyze()
        baseline = data["climate"]["baseline"]

        self.assertEqual([row["month"] for row in baseline["monthly"]], list(range(1, 13)))
        for key in ("precip_mm", "et0_mm", "deficit_mm", "heat_days", "dry_spell_prob"):
            self.assertIn(key, baseline["monthly"][6])
        self.assertEqual(baseline["basis"], "historical")
        self.assertIsNone(data["climate"]["scenario"])
        self.assertIn(data["data_quality"]["confidence"], ("high", "medium", "low"))

    def test_hotter_drier_scenario_changes_climate_and_scores(self):
        data = self.analyze(scenario={"rain_pct": -30, "temp_c": 3})
        baseline = data["climate"]["baseline"]
        scenario = data["climate"]["scenario"]

        self.assertEqual(scenario["basis"], "simulated")
        self.assertLess(scenario["annual_rainfall_mm"], baseline["annual_rainfall_mm"])
        self.assertGreater(scenario["average_temperature_c"], baseline["average_temperature_c"])
        for strategy in data["strategies"]:
            self.assertIsNotNone(strategy["baseline_scores"])

    def test_vulnerable_months_have_reasons_and_crops(self):
        data = self.analyze(scenario={"rain_pct": -30, "temp_c": 3})

        self.assertTrue(data["vulnerable_months"], "a hot, dry scenario should flag months")
        for item in data["vulnerable_months"]:
            self.assertIn(item["month"], range(1, 13))
            self.assertTrue(item["reasons"])
            self.assertTrue(item["crops"])
            self.assertTrue(item["sensitive_stages"])

    def test_urdu_request_returns_urdu_explanations(self):
        data = self.analyze(lang="ur")
        why = data["strategies"][1]["why_suggested"]

        self.assertTrue(any("\u0600" <= ch <= "\u06ff" for ch in why))
