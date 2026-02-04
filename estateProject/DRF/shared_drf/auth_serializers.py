from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from estateApp.models import Company, CustomUser


class CustomAuthTokenSerializer(serializers.Serializer):
    # Primary email field from HTML login form (name="username")
    username = serializers.EmailField(label=_("Email"), required=False)
    # Alias for username (used in role selection modal)
    user_email = serializers.EmailField(label=_("User Email"), required=False)
    # Password field
    password = serializers.CharField(
        label=_("Password"),
        style={"input_type": "password"},
        trim_whitespace=False,
    )
    # Role selection fields from HTML
    selected_user_id = serializers.IntegerField(required=False, allow_null=True)
    selected_role = serializers.IntegerField(required=False, allow_null=True)
    # Remember me checkbox
    remember_me = serializers.BooleanField(required=False, default=False)
    # Optional tracking fields from HTML (collect but don't validate)
    client_public_ip = serializers.CharField(required=False, allow_blank=True)
    _page_load_time = serializers.CharField(required=False, allow_blank=True)
    _timezone = serializers.CharField(required=False, allow_blank=True)
    _screen_res = serializers.CharField(required=False, allow_blank=True)
    # Honeypot fields (MUST be empty - any value indicates bot)
    honeypot = serializers.CharField(required=False, allow_blank=True)
    user_email_confirm = serializers.CharField(required=False, allow_blank=True)
    website_url = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Bot protection: honeypot fields MUST be empty. Any value indicates bot submission.
        for honeypot_field in ("honeypot", "user_email_confirm", "website_url"):
            val = attrs.get(honeypot_field, "").strip() if attrs.get(honeypot_field) else ""
            if val:  # If honeypot field has ANY value, reject as bot
                raise serializers.ValidationError(
                    {"non_field_errors": _("Bot detected.")},
                    code="authorization",
                )

        # Extract email from username or user_email field (HTML form uses name="username")
        email = (attrs.get("username") or attrs.get("user_email") or "").strip()
        password = (attrs.get("password") or "").strip()

        if not email or not password:
            msg = _("Must include email and password.")
            raise serializers.ValidationError(msg, code="authorization")

        # Role selection: user selected a specific role from multiple matches
        selected_user_id = attrs.get("selected_user_id") or attrs.get("selected_role")

        if selected_user_id is not None:
            # Validate the selected user directly with password
            qs = CustomUser.objects.filter(id=selected_user_id, email=email)
            user = qs.first()

            if not user or not user.check_password(password):
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")

            attrs["user"] = user
            return attrs

        # Normal authentication: attempt to authenticate with email and password
        user_or_match = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
        )
        if not user_or_match:
            msg = _("Unable to log in with provided credentials.")
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user_or_match
        return attrs
