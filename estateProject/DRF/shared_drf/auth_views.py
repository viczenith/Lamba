from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response

from estateApp.backends import MultipleUserMatch
from DRF.shared_drf.auth_serializers import CustomAuthTokenSerializer


class CustomAuthToken(ObtainAuthToken):
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_or_match = serializer.validated_data["user"]

        # Multi-role flow: return candidates; client must POST again with selected_user_id
        if isinstance(user_or_match, MultipleUserMatch):
            users = user_or_match.users
            payload_users = []
            for u in users:
                company = getattr(u, "company_profile", None)
                payload_users.append(
                    {
                        "id": u.id,
                        "email": u.email,
                        "full_name": getattr(u, "full_name", ""),
                        "role": getattr(u, "role", None),
                        "company": {
                            "id": company.id,
                            "name": getattr(company, "company_name", ""),
                            "slug": getattr(company, "slug", None),
                        }
                        if company
                        else None,
                    }
                )

            return Response(
                {
                    "requires_role_selection": True,
                    "multiple_users": payload_users,
                    "detail": "Multiple user roles found for these credentials. Select a role to continue.",
                },
                status=status.HTTP_409_CONFLICT,
            )

        user = user_or_match
        token, _created = Token.objects.get_or_create(user=user)

        company = getattr(user, "company_profile", None)
        return Response(
            {
                "token": token.key,
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": getattr(user, "full_name", ""),
                    "role": getattr(user, "role", None),
                    "company": {
                        "id": company.id,
                        "name": getattr(company, "company_name", ""),
                        "slug": getattr(company, "slug", None),
                    }
                    if company
                    else None,
                },
            }
        )
