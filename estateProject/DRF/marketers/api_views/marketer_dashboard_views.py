from django.utils import timezone
from django.db.models import Count
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework import permissions
from rest_framework.authentication import TokenAuthentication, SessionAuthentication

from datetime import timedelta, date
from dateutil.relativedelta import relativedelta

from estateApp.models import Transaction, ClientUser
from DRF.marketers.serializers.marketer_dashboard_serializers import DashboardFullSerializer
from DRF.shared_drf import APIResponse

from DRF.marketers.api_views.marketer_profile_views import IsMarketer


def _daterange(start_date, end_date):
    """Yield dates from start_date to end_date inclusive."""
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)


def _month_labels(start_date, months):
    """Return list of (year, month) tuples for months starting from start_date (inclusive)"""
    labels = []
    cur = start_date
    for _ in range(months):
        labels.append((cur.year, cur.month))
        cur = cur + relativedelta(months=+1)
    return labels


def _format_date_label(d):
    return d.strftime("%d %b %Y")


def _format_month_label(yr, m):
    return date(yr, m, 1).strftime("%b %Y")


def build_daily_block(marketer, start_date, end_date, company_ids=None):
    labels = []
    tx = []
    est = []
    cli = []

    for d in _daterange(start_date, end_date):
        labels.append(_format_date_label(d))

        tx_qs = Transaction.objects.filter(marketer=marketer, transaction_date=d)
        est_qs = Transaction.objects.filter(marketer=marketer, transaction_date=d, allocation__payment_type='full')
        client_qs = ClientUser.objects.filter(assigned_marketer=marketer, date_registered__date=d)

        if company_ids:
            tx_qs = tx_qs.filter(company_id__in=company_ids)
            est_qs = est_qs.filter(company_id__in=company_ids)
            client_qs = client_qs.filter(company_profile_id__in=company_ids)

        tx_count = tx_qs.count()
        est_count = est_qs.count()
        client_count = client_qs.count()

        tx.append(tx_count)
        est.append(est_count)
        cli.append(client_count)

    return {"labels": labels, "tx": tx, "est": est, "cli": cli}


def build_monthly_block(marketer, months_back=12, company_ids=None):
    today = timezone.localdate()
    first_of_month = date(today.year, today.month, 1) - relativedelta(months=months_back-1)
    month_tuples = _month_labels(first_of_month, months_back)

    labels = []
    tx = []
    est = []
    cli = []

    for yr, m in month_tuples:
        labels.append(_format_month_label(yr, m))
        start = date(yr, m, 1)
        end = start + relativedelta(months=+1) - timedelta(days=1)

        tx_qs = Transaction.objects.filter(marketer=marketer, transaction_date__range=(start, end))
        est_qs = Transaction.objects.filter(marketer=marketer, transaction_date__range=(start, end), allocation__payment_type='full')
        client_qs = ClientUser.objects.filter(assigned_marketer=marketer, date_registered__date__range=(start, end))

        if company_ids:
            tx_qs = tx_qs.filter(company_id__in=company_ids)
            est_qs = est_qs.filter(company_id__in=company_ids)
            client_qs = client_qs.filter(company_profile_id__in=company_ids)

        tx.append(tx_qs.count())
        est.append(est_qs.count())
        cli.append(client_qs.count())

    return {"labels": labels, "tx": tx, "est": est, "cli": cli}


def build_yearly_block(marketer, years_back=5, company_ids=None):
    today = timezone.localdate()
    start_year = today.year - (years_back - 1)
    labels = []
    tx = []
    est = []
    cli = []
    for yr in range(start_year, today.year + 1):
        labels.append(str(yr))
        start = date(yr, 1, 1)
        end = date(yr, 12, 31)

        tx_qs = Transaction.objects.filter(marketer=marketer, transaction_date__range=(start, end))
        est_qs = Transaction.objects.filter(marketer=marketer, transaction_date__range=(start, end), allocation__payment_type='full')
        client_qs = ClientUser.objects.filter(assigned_marketer=marketer, date_registered__year=yr)

        if company_ids:
            tx_qs = tx_qs.filter(company_id__in=company_ids)
            est_qs = est_qs.filter(company_id__in=company_ids)
            client_qs = client_qs.filter(company_profile_id__in=company_ids)

        tx.append(tx_qs.count())
        est.append(est_qs.count())
        cli.append(client_qs.count())

    return {"labels": labels, "tx": tx, "est": est, "cli": cli}


def build_alltime_block(marketer, company_ids=None):
    first_tx = Transaction.objects.filter(marketer=marketer)
    first_client = ClientUser.objects.filter(assigned_marketer=marketer)

    if company_ids:
        first_tx = first_tx.filter(company_id__in=company_ids)
        first_client = first_client.filter(company_profile_id__in=company_ids)

    first_tx = first_tx.order_by('transaction_date').first()
    first_client = first_client.order_by('date_registered').first()

    earliest = None
    if first_tx and first_client:
        earliest = min(first_tx.transaction_date, first_client.date_registered.date())
    elif first_tx:
        earliest = first_tx.transaction_date
    elif first_client:
        earliest = first_client.date_registered.date()

    if not earliest:
        today = timezone.localdate()
        return {"labels": [_format_date_label(today)], "tx": [0], "est": [0], "cli": [0]}

    start_year = earliest.year
    end_year = timezone.localdate().year
    labels = []
    tx = []
    est = []
    cli = []
    for yr in range(start_year, end_year + 1):
        labels.append(str(yr))
        start = date(yr, 1, 1)
        end = date(yr, 12, 31)

        tx_qs = Transaction.objects.filter(marketer=marketer, transaction_date__range=(start, end))
        est_qs = Transaction.objects.filter(marketer=marketer, transaction_date__range=(start, end), allocation__payment_type='full')
        client_qs = ClientUser.objects.filter(assigned_marketer=marketer, date_registered__year=yr)

        if company_ids:
            tx_qs = tx_qs.filter(company_id__in=company_ids)
            est_qs = est_qs.filter(company_id__in=company_ids)
            client_qs = client_qs.filter(company_profile_id__in=company_ids)

        tx.append(tx_qs.count())
        est.append(est_qs.count())
        cli.append(client_qs.count())

    return {"labels": labels, "tx": tx, "est": est, "cli": cli}


@method_decorator(cache_page(60 * 15), name='dispatch')
class MarketerDashboardAPIView(APIView):
    """
    Returns:
    {
      summary: { total_transactions, number_clients, total_companies },
      weekly: { labels, tx, est, cli },
      monthly: { labels, tx, est, cli },
      yearly: { labels, tx, est, cli },
      alltime: { labels, tx, est, cli },
      companies: [{ company_name, transactions, company_logo }]
    }
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (permissions.IsAuthenticated, IsMarketer)

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            marketer = user if getattr(user, 'role', '') == 'marketer' else None
            marketer_id = request.query_params.get('marketer_id')
            if (not marketer) and (marketer_id and (user.is_staff or user.is_superuser)):
                from estateApp.models import MarketerUser
                marketer = MarketerUser.objects.filter(pk=marketer_id).first()
            if not marketer:
                from estateApp.models import MarketerUser
                marketer = MarketerUser.objects.filter(pk=user.id).first()
            if not marketer:
                return APIResponse.not_found(
                    message='Marketer profile not found.',
                    error_code='MARKETER_NOT_FOUND'
                )
        except Exception:
            return APIResponse.server_error(
                message='Could not locate marketer.',
                error_code='MARKETER_LOOKUP_ERROR'
            )

        # Determine companies the marketer is affiliated with (same logic as server-rendered page)
        from estateApp.models import MarketerAffiliation, ClientMarketerAssignment

        affiliated_company_ids = list(
            MarketerAffiliation.objects.filter(marketer=marketer).values_list('company_id', flat=True)
        )
        # include marketer's primary company if present
        own_company_id = getattr(marketer, 'company_profile_id', None)
        if own_company_id and own_company_id not in affiliated_company_ids:
            affiliated_company_ids.append(own_company_id)
        # include companies where the marketer has transactions
        txn_company_ids = list(Transaction.objects.filter(marketer=marketer).values_list('company_id', flat=True).distinct())
        for cid in txn_company_ids:
            if cid and cid not in affiliated_company_ids:
                affiliated_company_ids.append(cid)

        # Summary counts scoped to affiliated companies
        total_transactions = Transaction.objects.filter(marketer=marketer, company_id__in=affiliated_company_ids).count()

        # Number of clients: union of direct assigned clients AND ClientMarketerAssignment records within affiliated companies
        direct_client_ids = set(
            ClientUser.objects.filter(
                assigned_marketer=marketer,
                company_profile_id__in=affiliated_company_ids
            ).values_list('id', flat=True)
        )
        assigned_client_ids = set(
            ClientMarketerAssignment.objects.filter(
                marketer=marketer,
                company_id__in=affiliated_company_ids
            ).values_list('client_id', flat=True)
        )
        number_clients = len([c for c in (direct_client_ids | assigned_client_ids) if c])

        # company-level breakdown (used by marketer_side bar chart)
        company_qs = (
            Transaction.objects
            .filter(marketer=marketer, company_id__in=affiliated_company_ids)
            .values(
                'allocation__estate__company__id',
                'allocation__estate__company__company_name',
                'allocation__estate__company__logo'
            )
            .annotate(transactions=Count('id'))
            .order_by('-transactions')[:20]
        )

        companies = []
        company_names = []
        company_transactions = []
        for row in company_qs:
            comp_id = row.get('allocation__estate__company__id')
            comp_name = row.get('allocation__estate__company__company_name') or ''
            # best-effort absolute logo URL via secure endpoint (fall back to None)
            logo_url = None
            try:
                if comp_id and getattr(request, 'build_absolute_uri', None):
                    from django.urls import reverse
                    logo_url = request.build_absolute_uri(
                        reverse('secure-company-logo', kwargs={'company_id': comp_id})
                    )
            except Exception:
                logo_url = None

            companies.append({
                'company_id': comp_id,
                'company_name': comp_name,
                'transactions': int(row.get('transactions', 0)),
                'company_logo': logo_url,
            })
            company_names.append(comp_name)
            company_transactions.append(int(row.get('transactions', 0)))

        total_companies = (
            Transaction.objects.filter(marketer=marketer, company_id__in=affiliated_company_ids)
            .values('allocation__estate__company').distinct().count()
        )

        summary = {
            "total_transactions": total_transactions,
            "number_clients": number_clients,
            "total_companies": total_companies,
        }

        today = timezone.localdate()
        start_week = today - timedelta(days=6)
        weekly = build_daily_block(marketer, start_week, today, company_ids=affiliated_company_ids)

        monthly = build_monthly_block(marketer, months_back=12, company_ids=affiliated_company_ids)

        yearly = build_yearly_block(marketer, years_back=5, company_ids=affiliated_company_ids)

        alltime = build_alltime_block(marketer, company_ids=affiliated_company_ids)

        payload = {
            "summary": summary,
            "weekly": weekly,
            "monthly": monthly,
            "yearly": yearly,
            "alltime": alltime,
            "companies": companies,
            "company_names": company_names,
            "company_transactions": company_transactions,
        }

        serializer = DashboardFullSerializer(payload)
        return APIResponse.success(
            data=serializer.data,
            message='Dashboard data retrieved'
        )


# MarketerChartRangeAPIView removed — the canonical dashboard API
# (MarketerDashboardAPIView) now returns `weekly`, `monthly`, `yearly` and
# `alltime` blocks. If a slim range-only endpoint is needed in future, add
# it back behind a clear feature flag.
