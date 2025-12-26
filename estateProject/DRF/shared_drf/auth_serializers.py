from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from estateApp.models import Company, CustomUser


class CustomAuthTokenSerializer(serializers.Serializer):
    email = serializers.EmailField(label=_("Email"))
    password = serializers.CharField(
        label=_("Password"),
        style={"input_type": "password"},
        trim_whitespace=False,
    )
    selected_user_id = serializers.IntegerField(required=False)
    login_slug = serializers.SlugField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")
        selected_user_id = attrs.get("selected_user_id")
        login_slug = attrs.get("login_slug")

        if not email or not password:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code="authorization")

        company = None
        if login_slug:
            company = Company.objects.filter(slug=login_slug).first()
            if company is None:
                raise serializers.ValidationError(
                    {"login_slug": _("Invalid tenant/company.")},
                    code="authorization",
                )

        # If role selection step is used, validate selected user directly.
        if selected_user_id is not None:
            qs = CustomUser.objects.filter(id=selected_user_id, email=email)
            if company is not None:
                qs = qs.filter(company_profile=company)
            user = qs.first()

            if not user or not user.check_password(password):
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")

            attrs["user"] = user
            return attrs

        # Normal step: attempt to authenticate.
        user_or_match = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password,
            company=company,
        )
        if not user_or_match:
            msg = _("Unable to log in with provided credentials.")
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user_or_match
        return attrs
