import json
import re
from pathlib import Path

from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from .models import UserProfile


NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z\s.'-]{1,49}$")
VALID_ROLES = {"buyer", "seller"}
ASSETS_DIR = Path(__file__).resolve().parent.parent / "static" / "assets"


def _json_body(request):
    try:
        return json.loads(request.body.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _get_asset_image_options():
    if not ASSETS_DIR.exists():
        return []

    allowed_extensions = {".jpg", ".jpeg", ".png", ".svg", ".webp"}
    files = [
        asset.name
        for asset in ASSETS_DIR.iterdir()
        if asset.is_file() and asset.suffix.lower() in allowed_extensions
    ]
    return sorted(files, key=str.lower)


def _build_auth_payload(user):
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", "buyer")
    return {
        "token": f"session-{user.pk}",
        "user": {
            "id": user.pk,
            "name": (user.first_name or user.username).strip(),
            "email": user.email or user.username,
            "role": role,
        },
    }


def home(request):
    return render(
        request,
        "index.html",
        {"asset_image_options_json": json.dumps(_get_asset_image_options())},
    )


@csrf_exempt
def login_view(request):
    if request.method != "POST":
        return JsonResponse({"message": "Method not allowed."}, status=405)

    payload = _json_body(request)
    email = str(payload.get("email", "")).strip().lower()
    password = payload.get("password", "")

    if not email or not password:
        return JsonResponse({"message": "Please enter email and password."}, status=400)

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"message": "Enter a valid email address."}, status=400)

    user = authenticate(request, username=email, password=password)
    if not user:
        return JsonResponse({"message": "Login failed. Check email and password."}, status=401)

    login(request, user)
    response = _build_auth_payload(user)
    response["message"] = "Login successful."
    return JsonResponse(response)


@csrf_exempt
def register_view(request):
    if request.method != "POST":
        return JsonResponse({"message": "Method not allowed."}, status=405)

    payload = _json_body(request)
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = payload.get("password", "")
    role = str(payload.get("role", "")).strip().lower()

    if not name or not email or not password or not role:
        return JsonResponse({"message": "Please fill all fields."}, status=400)

    if role not in VALID_ROLES:
        return JsonResponse({"message": "Select a valid account type."}, status=400)

    if not NAME_PATTERN.fullmatch(name):
        return JsonResponse(
            {"message": "Enter a valid name using letters and spaces only."},
            status=400,
        )

    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"message": "Enter a valid email address."}, status=400)

    if len(password) < 6:
        return JsonResponse({"message": "Password must be at least 6 characters."}, status=400)

    try:
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=name,
        )
    except IntegrityError:
        return JsonResponse({"message": "An account with this email already exists."}, status=409)

    UserProfile.objects.update_or_create(user=user, defaults={"role": role})
    login(request, user)

    response = _build_auth_payload(user)
    response["message"] = "Account created successfully."
    return JsonResponse(response, status=201)


@csrf_exempt
def ai_suggest(request):
    if request.method != "POST":
        return JsonResponse({"message": "Method not allowed."}, status=405)

    payload = _json_body(request)
    prompt = str(payload.get("prompt", "")).strip()

    if not prompt:
        return JsonResponse({"message": "Please enter a prompt for suggestions."}, status=400)

    return JsonResponse(
        {
            "message": "AI suggestions are currently running in local demo mode.",
            "suggestions": [
                f"Focus on the best value options for: {prompt}",
                "Compare delivery speed, warranty, and final negotiated price.",
                "Shortlist 3 seller-ready options before requesting a deal.",
            ],
        }
    )
