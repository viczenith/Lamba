from __future__ import annotations

try:
    from celery import shared_task  # type: ignore
    HAS_CELERY = True
except ModuleNotFoundError:  # pragma: no cover - fallback for environments without Celery
    import functools

    HAS_CELERY = False

    def shared_task(*decorator_args, **decorator_kwargs):
        """Lightweight stand-in for celery.shared_task when Celery is unavailable."""

        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            # mimic the Celery API surface used inside the project
            wrapper.delay = lambda *args, **kwargs: func(*args, **kwargs)
            wrapper.apply_async = lambda args=None, kwargs=None, **opts: func(*(args or ()), **(kwargs or {}))
            wrapper.is_immediate = True
            return wrapper

        if decorator_args and callable(decorator_args[0]) and not decorator_kwargs:
            return decorator(decorator_args[0])
        return decorator


import logging
from dataclasses import dataclass
from typing import Iterable, Sequence

from django.db import transaction
from django.utils import timezone

from estateApp.models import Notification, NotificationDispatch, UserNotification
from estateApp.ws_utils import broadcast_user_notification
from DRF.shared_drf.push_service import send_user_notification_push


logger = logging.getLogger(__name__)

if not HAS_CELERY:
    logger.warning("Celery not available; notification tasks will run synchronously in-process")


BATCH_SIZE = 10_000


@dataclass
class NotificationBatch:
    notification_id: int
    user_ids: Sequence[int]


def _dispatch_notification_batch(dispatch_id: int, notification_id: int, user_ids: Iterable[int]) -> dict:
    user_ids = list(dict.fromkeys(int(uid) for uid in user_ids))
    if not user_ids:
        return {"created": 0}

    try:
        with transaction.atomic():
            notification = Notification.objects.select_for_update().get(pk=notification_id)
            dispatch = NotificationDispatch.objects.select_for_update().get(pk=dispatch_id)

            user_notifications = [
                UserNotification(user_id=user_id, notification=notification)
                for user_id in user_ids
            ]
            created = UserNotification.objects.bulk_create(
                user_notifications,
                ignore_conflicts=True,
            )

            now_ts = timezone.now()
            if dispatch.started_at is None:
                dispatch.started_at = now_ts
            dispatch.status = NotificationDispatch.STATUS_PROCESSING
            dispatch.processed_batches += 1
            created_count = len(created)
            if created_count:
                dispatch.processed_recipients += created_count
            dispatch.updated_at = now_ts
            dispatch.save(update_fields=[
                'status',
                'processed_batches',
                'processed_recipients',
                'started_at',
                'updated_at',
            ])

    except Exception as exc:
        NotificationDispatch.objects.filter(pk=dispatch_id).update(
            status=NotificationDispatch.STATUS_FAILED,
            last_error=str(exc)[:2000],
            finished_at=timezone.now(),
            updated_at=timezone.now(),
        )
        raise

    dispatch = NotificationDispatch.objects.get(pk=dispatch_id)

    for entry in created:
        try:
            broadcast_user_notification(entry)
        except Exception as exc:
            logger.warning("Failed to broadcast notification %s to user %s: %s", notification_id, entry.user_id, exc, exc_info=True)

        try:
            send_user_notification_push(entry)
        except Exception as exc:
            logger.warning("Failed to send push notification %s to user %s: %s", notification_id, entry.user_id, exc, exc_info=True)

    if dispatch.total_recipients > 0 and dispatch.processed_recipients >= dispatch.total_recipients:
        dispatch.mark_completed()
    elif dispatch.total_batches > 0 and dispatch.processed_batches >= dispatch.total_batches:
        dispatch.mark_completed()

    return {"created": len(created)}


def _dispatch_notification_stream(dispatch_id: int, notification_id: int, user_ids: Iterable[int]) -> dict:
    created_total = 0
    chunk: list[int] = []
    dispatch = NotificationDispatch.objects.get(pk=dispatch_id)
    dispatch.mark_processing()

    for uid in user_ids:
        chunk.append(int(uid))
        if len(chunk) >= BATCH_SIZE:
            result = _dispatch_notification_batch(dispatch_id, notification_id, chunk)
            created_total += result.get("created", 0)
            chunk.clear()

    if chunk:
        result = _dispatch_notification_batch(dispatch_id, notification_id, chunk)
        created_total += result.get("created", 0)

    if dispatch.total_recipients == 0:
        dispatch.mark_completed()

    return {"created": created_total}


@shared_task(name="notifications.dispatch_notification_batch")
def dispatch_notification_batch(dispatch_id: int, notification_id: int, user_ids: Iterable[int]) -> dict:
    return _dispatch_notification_batch(dispatch_id, notification_id, user_ids)


@shared_task(name="notifications.dispatch_notification_stream")
def dispatch_notification_stream(dispatch_id: int, notification_id: int, user_ids: Iterable[int]) -> dict:
    return _dispatch_notification_stream(dispatch_id, notification_id, user_ids)


def dispatch_notification_stream_sync(dispatch_id: int, notification_id: int, user_ids: Iterable[int]) -> dict:
    """Synchronous helper used when Celery workers/broker are unavailable."""
    return _dispatch_notification_stream(dispatch_id, notification_id, user_ids)


def is_celery_worker_available(timeout: float = 2.0) -> bool:
    """Return True if a Celery worker responds within *timeout* seconds."""
    if not HAS_CELERY:
        return False

    try:
        app = dispatch_notification_stream.app  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover - fallback during runtime oddities
        from celery import current_app as app  # type: ignore  # noqa: WPS433

    try:
        inspector = app.control.inspect(timeout=timeout)  # type: ignore[attr-defined]
        if not inspector:
            return False
        ping = inspector.ping()
        return bool(ping)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.debug("Celery inspector ping failed: %s", exc, exc_info=True)
        return False


# ============================================================================
# EMAIL NOTIFICATION TASKS (Phase 1 - Critical)
# ============================================================================

@shared_task(name="notifications.send_affiliation_approval_email")
def send_affiliation_approval_email(affiliation_id: int) -> dict:
    """Send approval notification to marketer"""
    try:
        from estateApp.models import MarketerAffiliation
        from estateApp.notifications.email_service import EmailService
        
        affiliation = MarketerAffiliation.objects.get(pk=affiliation_id)
        success = EmailService.send_affiliation_approval_email(affiliation)
        
        return {
            'status': 'success' if success else 'failed',
            'affiliation_id': affiliation_id,
            'marketer_email': affiliation.marketer.email,
        }
    except Exception as exc:
        logger.error(f"Failed to send affiliation approval email: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(name="notifications.send_affiliation_rejection_email")
def send_affiliation_rejection_email(affiliation_id: int, reason: str = "") -> dict:
    """Send rejection notification to marketer"""
    try:
        from estateApp.models import MarketerAffiliation
        from estateApp.notifications.email_service import EmailService
        
        affiliation = MarketerAffiliation.objects.get(pk=affiliation_id)
        success = EmailService.send_affiliation_rejection_email(affiliation, reason)
        
        return {
            'status': 'success' if success else 'failed',
            'affiliation_id': affiliation_id,
            'marketer_email': affiliation.marketer.email,
        }
    except Exception as exc:
        logger.error(f"Failed to send affiliation rejection email: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(name="notifications.send_commission_approved_email")
def send_commission_approved_email(commission_id: int) -> dict:
    """Send commission approval notification"""
    try:
        from estateApp.models import MarketerEarnedCommission
        from estateApp.notifications.email_service import EmailService
        
        commission = MarketerEarnedCommission.objects.get(pk=commission_id)
        success = EmailService.send_commission_approved_email(commission)
        
        return {
            'status': 'success' if success else 'failed',
            'commission_id': commission_id,
            'amount': float(commission.commission_amount),
        }
    except Exception as exc:
        logger.error(f"Failed to send commission approved email: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(name="notifications.send_commission_payment_email")
def send_commission_payment_email(commission_id: int, payment_reference: str) -> dict:
    """Send payment confirmation to marketer"""
    try:
        from estateApp.models import MarketerEarnedCommission
        from estateApp.notifications.email_service import EmailService
        
        commission = MarketerEarnedCommission.objects.get(pk=commission_id)
        success = EmailService.send_commission_payment_email(commission, payment_reference)
        
        return {
            'status': 'success' if success else 'failed',
            'commission_id': commission_id,
            'payment_reference': payment_reference,
        }
    except Exception as exc:
        logger.error(f"Failed to send commission payment email: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(name="notifications.send_invoice_email")
def send_invoice_email(invoice_id: int) -> dict:
    """Send invoice to company admin"""
    try:
        from estateApp.models import Invoice
        from estateApp.notifications.email_service import EmailService
        
        invoice = Invoice.objects.get(pk=invoice_id)
        success = EmailService.send_invoice_email(invoice)
        
        return {
            'status': 'success' if success else 'failed',
            'invoice_id': invoice_id,
            'company': str(invoice.company),
        }
    except Exception as exc:
        logger.error(f"Failed to send invoice email: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(name="notifications.send_trial_expiration_warnings")
def send_trial_expiration_warnings() -> dict:
    """Send trial expiration warnings to companies (runs daily)"""
    try:
        from datetime import timedelta
        from django.utils import timezone
        from estateApp.models import Company
        from estateApp.notifications.email_service import EmailService
        
        # Find companies with trials expiring in 3, 7, and 14 days
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        week_from_now = now + timedelta(days=7)
        two_weeks_from_now = now + timedelta(days=14)
        month_from_now = now + timedelta(days=30)
        
        companies_to_warn = Company.objects.filter(
            subscription_status='trial',
            trial_ends_at__gte=tomorrow,
            trial_ends_at__lte=month_from_now,
        )
        
        sent_count = 0
        for company in companies_to_warn:
            days_remaining = (company.trial_ends_at - now).days
            if days_remaining in [3, 7, 14, 30]:  # Send on these days
                if EmailService.send_trial_expiration_warning_email(company, days_remaining):
                    sent_count += 1
        
        return {
            'status': 'success',
            'companies_warned': sent_count,
        }
    except Exception as exc:
        logger.error(f"Failed to send trial expiration warnings: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}


@shared_task(name="notifications.send_subscription_renewal_reminders")
def send_subscription_renewal_reminders() -> dict:
    """Send subscription renewal reminders (runs daily)"""
    try:
        from datetime import timedelta
        from django.utils import timezone
        from estateApp.models import Company
        from estateApp.notifications.email_service import EmailService
        
        now = timezone.now()
        
        # Find companies with subscriptions expiring in 7 days
        week_from_now = now + timedelta(days=7)
        
        companies_expiring_soon = Company.objects.filter(
            subscription_status='active',
            subscription_ends_at__gte=now,
            subscription_ends_at__lte=week_from_now,
        )
        
        sent_count = 0
        for company in companies_expiring_soon:
            days_until_renewal = (company.subscription_ends_at - now).days
            if EmailService.send_subscription_renewal_email(company, days_until_renewal):
                sent_count += 1
        
        return {
            'status': 'success',
            'companies_reminded': sent_count,
        }
    except Exception as exc:
        logger.error(f"Failed to send subscription renewal reminders: {exc}", exc_info=True)
        return {'status': 'failed', 'error': str(exc)}