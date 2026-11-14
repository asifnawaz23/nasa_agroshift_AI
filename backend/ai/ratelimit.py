"""Per-IP rate limit for the AI endpoints (plan section 10: about 20 requests per 10 minutes).

Uses Django's cache (local memory by default, per Gunicorn worker), which is enough to stop a
runaway client from spending the LLM budget during the demo.
"""
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse

AI_RATE_LIMIT = 20
AI_RATE_WINDOW_S = 600


def client_ip(request) -> str:
    # Render puts the visitor's address first in X-Forwarded-For.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def ai_rate_limited(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.method == "POST":
            key = f"ai-rate:{client_ip(request)}"
            if cache.add(key, 1, AI_RATE_WINDOW_S):
                count = 1
            else:
                try:
                    count = cache.incr(key)
                except ValueError:  # expired between add and incr
                    cache.set(key, 1, AI_RATE_WINDOW_S)
                    count = 1
            if count > AI_RATE_LIMIT:
                return JsonResponse({
                    "status": "error",
                    "message": "Too many questions in a short time. Please wait a few minutes.",
                    "errors": {"rate_limit": [f"{AI_RATE_LIMIT} requests per {AI_RATE_WINDOW_S // 60} minutes."]},
                }, status=429)
        return view(request, *args, **kwargs)

    return wrapper
