"""
Alert Management API Views
Handles acknowledgement, dismissal, and resolution of subscription alerts
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import get_object_or_404
from estateApp.models import SubscriptionAlert, Company
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def acknowledge_alert(request):
    """
    Acknowledge a subscription alert.
    The alert will not show again until its status changes or is resolved.
    
    Request JSON:
    {
        "alert_id": 123
    }
    
    Response:
    {
        "success": true,
        "alert_id": 123,
        "acknowledged_at": "2025-11-20T10:00:00Z"
    }
    """
    try:
        alert_id = request.data.get('alert_id')
        
        if not alert_id:
            return Response(
                {'error': 'alert_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get company from request
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the alert and verify it belongs to this company
        alert = get_object_or_404(
            SubscriptionAlert,
            id=alert_id,
            company=company
        )
        
        # Update acknowledgement timestamp
        alert.acknowledged_at = timezone.now()
        alert.save()
        
        logger.info(f"Alert {alert_id} acknowledged by user {request.user.id}")
        
        return Response({
            'success': True,
            'alert_id': alert.id,
            'acknowledged_at': alert.acknowledged_at.isoformat(),
            'message': 'Alert acknowledged successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to acknowledge alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dismiss_alert(request):
    """
    Dismiss a subscription alert.
    Dismissible alerts will not show again today but may reappear if conditions change.
    
    Request JSON:
    {
        "alert_id": 123,
        "hide_until_date": "2025-11-21T00:00:00Z"  # Optional
    }
    
    Response:
    {
        "success": true,
        "alert_id": 123,
        "dismissed_at": "2025-11-20T10:00:00Z",
        "hide_until": "2025-11-21T00:00:00Z"
    }
    """
    try:
        alert_id = request.data.get('alert_id')
        
        if not alert_id:
            return Response(
                {'error': 'alert_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get company from request
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the alert and verify it belongs to this company
        alert = get_object_or_404(
            SubscriptionAlert,
            id=alert_id,
            company=company
        )
        
        # Check if alert is dismissible
        if alert.status == 'blocked':  # Blocking alerts can't be dismissed
            return Response(
                {'error': 'This alert cannot be dismissed'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Set dismissed timestamp
        alert.dismissed_at = timezone.now()
        
        # Set hide_until date if provided, otherwise until tomorrow
        hide_until = request.data.get('hide_until_date')
        if hide_until:
            try:
                alert.hide_until = timezone.make_aware(
                    timezone.datetime.fromisoformat(hide_until.replace('Z', '+00:00'))
                )
            except:
                # Default to 24 hours if parsing fails
                alert.hide_until = timezone.now() + timezone.timedelta(days=1)
        else:
            # Default: hide for 24 hours
            alert.hide_until = timezone.now() + timezone.timedelta(days=1)
        
        alert.save()
        
        logger.info(f"Alert {alert_id} dismissed by user {request.user.id}")
        
        return Response({
            'success': True,
            'alert_id': alert.id,
            'dismissed_at': alert.dismissed_at.isoformat(),
            'hide_until': alert.hide_until.isoformat(),
            'message': 'Alert dismissed successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error dismissing alert: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to dismiss alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resolve_alert(request):
    """
    Mark a subscription alert as resolved.
    Resolved alerts will not show unless the underlying condition occurs again.
    
    Request JSON:
    {
        "alert_id": 123,
        "resolution_note": "User upgraded to paid plan"  # Optional
    }
    
    Response:
    {
        "success": true,
        "alert_id": 123,
        "resolved_at": "2025-11-20T10:00:00Z",
        "status": "resolved"
    }
    """
    try:
        alert_id = request.data.get('alert_id')
        
        if not alert_id:
            return Response(
                {'error': 'alert_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get company from request
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the alert and verify it belongs to this company
        alert = get_object_or_404(
            SubscriptionAlert,
            id=alert_id,
            company=company
        )
        
        # Mark as resolved
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        
        # Optional: Store resolution note in details
        resolution_note = request.data.get('resolution_note')
        if resolution_note:
            alert.message += f"\n[RESOLVED: {resolution_note}]"
        
        alert.save()
        
        logger.info(f"Alert {alert_id} resolved by user {request.user.id}")
        
        return Response({
            'success': True,
            'alert_id': alert.id,
            'resolved_at': alert.resolved_at.isoformat(),
            'status': 'resolved',
            'message': 'Alert marked as resolved'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to resolve alert'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_alerts(request):
    """
    Get all active alerts for the current company.
    Filters out dismissed and resolved alerts by default.
    
    Query Parameters:
    - status: Filter by status (active, acknowledged, dismissed, resolved)
    - include_dismissed: Include dismissed alerts (true/false)
    - include_resolved: Include resolved alerts (true/false)
    
    Response:
    {
        "success": true,
        "count": 3,
        "alerts": [
            {
                "id": 123,
                "alert_type": "trial_expiry",
                "severity": "urgent",
                "message": "Your trial expires in 2 days",
                "created_at": "2025-11-18T10:00:00Z",
                "acknowledged_at": null,
                "dismissed_at": null,
                "resolved_at": null,
                "status": "active"
            }
        ]
    }
    """
    try:
        # Get company from request
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Base query
        alerts_qs = SubscriptionAlert.objects.filter(company=company).order_by('-created_at')
        
        # Filter by status if provided
        status_filter = request.query_params.get('status')
        if status_filter:
            alerts_qs = alerts_qs.filter(status=status_filter)
        else:
            # By default, exclude dismissed and resolved
            include_dismissed = request.query_params.get('include_dismissed', 'false').lower() == 'true'
            include_resolved = request.query_params.get('include_resolved', 'false').lower() == 'true'
            
            if not include_dismissed:
                alerts_qs = alerts_qs.exclude(status='dismissed')
            if not include_resolved:
                alerts_qs = alerts_qs.exclude(status='resolved')
        
        # Serialize alerts
        alerts_data = []
        for alert in alerts_qs:
            alerts_data.append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'message': alert.message,
                'created_at': alert.created_at.isoformat(),
                'acknowledged_at': alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                'dismissed_at': alert.dismissed_at.isoformat() if alert.dismissed_at else None,
                'resolved_at': alert.resolved_at.isoformat() if alert.resolved_at else None,
                'status': alert.status,
            })
        
        return Response({
            'success': True,
            'count': len(alerts_data),
            'alerts': alerts_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving alerts: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to retrieve alerts'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def clear_dismissed_alerts(request):
    """
    Clear all dismissed alerts that are no longer relevant.
    
    Response:
    {
        "success": true,
        "cleared_count": 5,
        "message": "Cleared 5 dismissed alerts"
    }
    """
    try:
        company = getattr(request, 'company', None)
        if not company:
            return Response(
                {'error': 'Company context not found'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Delete dismissed alerts that are past their hide_until date
        current_time = timezone.now()
        dismissed_alerts = SubscriptionAlert.objects.filter(
            company=company,
            status='dismissed',
            hide_until__lte=current_time
        )
        
        count = dismissed_alerts.count()
        dismissed_alerts.delete()
        
        logger.info(f"Cleared {count} dismissed alerts for company {company.id}")
        
        return Response({
            'success': True,
            'cleared_count': count,
            'message': f'Cleared {count} dismissed alerts'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error clearing dismissed alerts: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to clear dismissed alerts'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
