import json
import os
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from django.core.management import call_command
from django.test import Client, SimpleTestCase, TestCase

from datasources.errors import DataSourceTimeout


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


SAMPLE_POWER = (
    Path(__file__).resolve().parents[1]
    / "engine" / "tests" / "sample_power_iowa.csv"
)

ANALYZE_BODY = {
    "lat": 42.10,
    "lon": -93.45,
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


def _power_down(lat, lon):
    raise DataSourceTimeout("NASA POWER", "timed out")


class AnalyzeValidationTests(TestCase):
    """Bad requests are rejected with 400 before any NASA data is fetched."""

    def post(self, body):
        return self.client.post("/api/analyze/", json.dumps(body), content_type="application/json")

    def assert_rejected(self, field, **changes):
        res = self.post({**ANALYZE_BODY, **changes})
        self.assertEqual(res.status_code, 400, res.content[:300])
        self.assertIn(field, res.json()["errors"])

    def test_latitude_out_of_range(self):
        self.assert_rejected("lat", lat=95)

    def test_priority_out_of_range(self):
        self.assert_rejected("priorities", priorities={**ANALYZE_BODY["priorities"], "water": 9})

    def test_unknown_constraint_value(self):
        self.assert_rejected(
            "constraints", constraints={**ANALYZE_BODY["constraints"], "water_availability": "lots"}
        )

    def test_scenario_beyond_slider_range(self):
        self.assert_rejected("scenario", scenario={"rain_pct": -80, "temp_c": 0})

    def test_unknown_language(self):
        self.assert_rejected("lang", lang="fr")

    def test_get_is_not_allowed(self):
        self.assertEqual(self.client.get("/api/analyze/").status_code, 405)


@patch("api.views.get_soil", lambda lat, lon: (None, {"cache_hit": False}))
@patch("api.views.get_power_daily", _power_down)
class AnalyzeDataSourceDownTests(TestCase):
    """NASA POWER down: featured pins use the offline snapshot, other points get a clear 503."""

    def post(self, lat, lon):
        body = {**ANALYZE_BODY, "lat": lat, "lon": lon}
        return self.client.post("/api/analyze/", json.dumps(body), content_type="application/json")

    def test_clicked_point_without_cache_returns_503(self):
        res = self.post(0.5, 20.5)
        self.assertEqual(res.status_code, 503)
        self.assertIn("message", res.json())

    def test_featured_pin_falls_back_to_snapshot(self):
        res = self.post(31.30, 73.00)
        self.assertEqual(res.status_code, 200, res.content[:300])
        quality = res.json()["data_quality"]
        self.assertTrue(quality["fallback_used"])
        self.assertIn("SMAP", quality["sources"])


class ListEndpointTests(TestCase):
    def test_locations_lists_the_three_featured_pins(self):
        res = self.client.get("/api/locations/")
        self.assertEqual(res.status_code, 200)
        slugs = {pin["slug"] for pin in res.json()["results"]}
        self.assertEqual(slugs, {"sindh-hyderabad", "punjab-faisalabad", "iowa-central"})

    def test_crops_have_urdu_names_and_sources(self):
        res = self.client.get("/api/crops/")
        self.assertEqual(res.status_code, 200)
        crops = res.json()["results"]
        self.assertEqual(len(crops), 14)
        for crop in crops:
            self.assertTrue(crop["name_ur"], crop["slug"])
            self.assertTrue(crop["sources"], crop["slug"])


class SeedCommandTests(TestCase):
    def test_seed_commands_are_idempotent(self):
        from crops.models import Crop, CropCalendar, RotationTemplate
        from locations.models import Location, LocationCache

        for _ in range(2):
            call_command("seed_crops", stdout=open(os.devnull, "w"))
            call_command("load_prepulled", stdout=open(os.devnull, "w"))

        self.assertEqual(Crop.objects.count(), 14)
        self.assertEqual(CropCalendar.objects.count(), 19)
        self.assertTrue(RotationTemplate.objects.filter(key="current_alt_rice_wheat").exists())
        self.assertEqual(Location.objects.count(), 3)
        self.assertEqual(LocationCache.objects.filter(kind="power").count(), 3)


MOCK_ANALYSIS = json.loads(
    (Path(__file__).resolve().parents[2] / "docs" / "mock_analyze.json").read_text(encoding="utf-8")
)
AI_ANSWER = {"summary": "July is the risky month.", "points": [], "actions": [],
             "needs_expert": [], "confidence": "medium"}


class AiEndpointTests(TestCase):
    """/api/explain/ and /api/chat/: LLM answer when available, grounded template otherwise."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def post(self, url, body):
        return self.client.post(url, json.dumps(body), content_type="application/json")

    def assert_answer_shape(self, data):
        for key in ("summary", "points", "actions", "needs_expert", "confidence", "ai_used", "disclaimer"):
            self.assertIn(key, data)

    @patch("api.views.ask_llm", return_value=None)
    def test_explain_falls_back_to_template_without_llm(self, _):
        res = self.post("/api/explain/", {"section": "alerts", "analysis": MOCK_ANALYSIS})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assert_answer_shape(data)
        self.assertFalse(data["ai_used"])
        self.assertTrue(data["points"], "template answer is built from the analysis")

    @patch("api.views.ask_llm", return_value=AI_ANSWER)
    def test_explain_uses_llm_answer_and_trims_the_analysis(self, ask):
        res = self.post("/api/explain/", {"section": "water_balance", "analysis": MOCK_ANALYSIS, "lang": "ur"})
        data = res.json()
        self.assertTrue(data["ai_used"])
        self.assertEqual(data["summary"], AI_ANSWER["summary"])
        system, messages, schema = ask.call_args.args
        self.assertIn("deficit_mm", system)
        self.assertNotIn("why_suggested", system, "water balance does not need strategy text")
        self.assertIn("Urdu", system)
        self.assertIn("fertilizer", system)

    def test_explain_rejects_unknown_section(self):
        res = self.post("/api/explain/", {"section": "weather", "analysis": MOCK_ANALYSIS})
        self.assertEqual(res.status_code, 400)

    @patch("api.views.ask_llm", return_value=None)
    def test_explain_strategy_section(self, _):
        res = self.post("/api/explain/", {"section": "strategy:soil_builder", "analysis": MOCK_ANALYSIS})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["needs_expert"])

    @patch("api.views.ask_llm", return_value=AI_ANSWER)
    def test_chat_sends_history_to_llm(self, ask):
        history = [{"role": "user", "content": "Is July risky?"},
                   {"role": "assistant", "content": "Yes, July is dry."},
                   {"role": "user", "content": "What can I do?"}]
        res = self.post("/api/chat/", {"messages": history, "analysis": MOCK_ANALYSIS})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(ask.call_args.args[1], history)
        self.assertEqual(res.json()["reply"], AI_ANSWER["summary"])

    @patch("api.views.ask_llm", return_value=None)
    def test_chat_crop_question_without_llm(self, _):
        res = self.post("/api/chat/", {"message": "How much water does wheat need?"})
        data = res.json()
        self.assertFalse(data["ai_used"])
        self.assertIn("Wheat", data["summary"])

    def test_chat_rejects_history_not_ending_with_a_question(self):
        res = self.post("/api/chat/", {"messages": [{"role": "assistant", "content": "Hi"}]})
        self.assertEqual(res.status_code, 400)

    @patch("api.views.ask_llm", return_value=None)
    def test_ai_endpoints_are_rate_limited(self, _):
        from ai.ratelimit import AI_RATE_LIMIT

        body = {"message": "wheat"}
        for _ in range(AI_RATE_LIMIT):
            self.assertEqual(self.post("/api/chat/", body).status_code, 200)
        self.assertEqual(self.post("/api/chat/", body).status_code, 429)


class HealthTests(TestCase):
    def test_health_reports_database(self):
        res = self.client.get("/api/health/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["database"], "ok")


@patch("api.views.get_soil", lambda lat, lon: ({"available": True, "texture": "silt loam",
                                               "texture_group": "medium", "drainage_hint": "moderate",
                                               "erodibility_hint": "high", "organic_matter_pct": 3.0,
                                               "source": "ISRIC SoilGrids"}, {"cache_hit": True}))
@patch("api.views.get_power_daily", _sample_daily)
class SoilOverrideTests(TestCase):
    def analyze(self, **changes):
        body = {**ANALYZE_BODY, **changes}
        return self.client.post("/api/analyze/", json.dumps(body), content_type="application/json")

    def test_farmer_texture_replaces_soilgrids(self):
        data = self.analyze(overrides={"soil_texture": "clay"}).json()
        used, measured = data["soil"]["used"], data["soil"]["measured"]
        self.assertEqual(used["texture"], "clay")
        self.assertEqual(used["drainage_hint"], "slow")
        self.assertEqual(used["texture_source"], "farmer")
        self.assertEqual(used["organic_matter_pct"], 3.0, "SoilGrids values are kept")
        self.assertEqual(measured["texture"], "silt loam")

    def test_override_changes_the_erosion_score(self):
        silty = self.analyze().json()["strategies"][0]["scores"]["erosion_infiltration"]
        clay = self.analyze(overrides={"soil_texture": "clay"}).json()["strategies"][0]["scores"]["erosion_infiltration"]
        self.assertNotEqual(silty, clay)

    def test_unknown_texture_is_rejected(self):
        self.assertEqual(self.analyze(overrides={"soil_texture": "mud"}).status_code, 400)


class PinAlertTests(TestCase):
    def test_each_pin_has_an_alert_level(self):
        pins = self.client.get("/api/locations/").json()["results"]
        for pin in pins:
            summary = pin["alert_summary"]
            self.assertIsNotNone(summary, pin["slug"])
            self.assertIn(summary["worst"], ("low", "moderate", "high", "critical"))


class TemplateAnswerDedupTests(SimpleTestCase):
    def test_same_sentence_from_alert_and_evidence_is_shown_once(self):
        from ai.prompts import template_answer

        line = "July: Cotton at the flowering stage, while this area averages 17 days above 40 °C."
        analysis = {
            "alerts": [{"severity": "critical", "reason": line, "action": "Sow earlier."}],
            "strategies": [{"key": "current", "name": "Current", "scores": {"overall": 60},
                            "evidence": [{"text": line, "source": "NASA POWER"}]}],
            "data_quality": {"confidence": "medium"},
        }
        texts = [p["text"] for p in template_answer(analysis, "overview", "en")["points"]]
        self.assertEqual(texts.count(line), 1)


class EverydaySoilNamesTests(SimpleTestCase):
    def test_form_soil_names_are_accepted(self):
        from api.serializers import OverridesSerializer

        for given, expected in [("sandy", "sandy loam"), ("Sandy", "sandy loam"), ("loam", "loam"),
                                ("clay", "clay"), ("silt", "silt"), ("clay loam", "clay loam"),
                                ("", None), (None, None)]:
            s = OverridesSerializer(data={"soil_texture": given})
            self.assertTrue(s.is_valid(), (given, s.errors))
            self.assertEqual(s.validated_data.get("soil_texture"), expected)

    def test_unknown_soil_name_is_rejected(self):
        from api.serializers import OverridesSerializer

        self.assertFalse(OverridesSerializer(data={"soil_texture": "rocky moon dust"}).is_valid())
