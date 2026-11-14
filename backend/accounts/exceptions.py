from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Wrap DRF errors (e.g. 401 Not authenticated) in the project's error envelope."""
    response = exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    if isinstance(data, dict) and "detail" in data:
        message, errors = str(data["detail"]), {}
    else:
        message, errors = "Request failed.", data

    response.data = {"status": "error", "message": message, "errors": errors}
    return response