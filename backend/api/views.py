from django.http import JsonResponse
from django.utils import timezone


def health_check(request):
    return JsonResponse(
        {
            "status": "success",
            "message": "FieldShift Planner API is running.",
            "timestamp": timezone.now().isoformat(),
        }
    )