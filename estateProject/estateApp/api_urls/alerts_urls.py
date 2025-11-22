"""
Alert Management API URLs
"""

from django.urls import path
from estateApp.api_views.alerts_views import (
    acknowledge_alert,
    dismiss_alert,
    resolve_alert,
    get_alerts,
    clear_dismissed_alerts,
)

app_name = 'alerts_api'

urlpatterns = [
    # Alert management endpoints
    path('acknowledge/', acknowledge_alert, name='acknowledge-alert'),
    path('dismiss/', dismiss_alert, name='dismiss-alert'),
    path('resolve/', resolve_alert, name='resolve-alert'),
    path('list/', get_alerts, name='get-alerts'),
    path('clear-dismissed/', clear_dismissed_alerts, name='clear-dismissed-alerts'),
]
