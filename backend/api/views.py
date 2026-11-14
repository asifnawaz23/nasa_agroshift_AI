
import json

from django.http import JsonResponse
from django.utils import timezone

from .serializers import AnalyzeRequestSerializer


def health_check(request):
    return JsonResponse(
        {
            "status": "success",
            "message": "FieldShift Planner API is running.",
            "timestamp": timezone.now().isoformat(),
        }
    )


def _error_response(message, errors=None, status=400):
    return JsonResponse(
        {
            "status": "error",
            "message": message,
            "errors": errors or {},
        },
        status=status,
    )


def analyze(request):
    if request.method != "POST":
        return _error_response(
            "Method not allowed.",
            status=405,
        )

    try:
        request_data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response(
            "Request body must contain valid JSON.",
            {"body": ["Invalid JSON."]},
        )

    if not isinstance(request_data, dict):
        return _error_response(
            "Request body must be a JSON object.",
            {"body": ["Expected a JSON object."]},
        )

    serializer = AnalyzeRequestSerializer(data=request_data)

    if not serializer.is_valid():
        return _error_response(
            "Request validation failed.",
            serializer.errors,
        )

    return _error_response(
        "Analysis pipeline is not implemented yet.",
        status=501,
    )
