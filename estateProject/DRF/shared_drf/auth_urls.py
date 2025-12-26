from django.urls import path

from DRF.shared_drf.auth_views import CustomAuthToken


urlpatterns = [
    path("api-token-auth/", CustomAuthToken.as_view(), name="api_token_auth"),
]
