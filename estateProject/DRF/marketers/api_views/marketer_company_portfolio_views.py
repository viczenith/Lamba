from datetime import datetime
from django.shortcuts import get_object_or_404
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from DRF.shared_drf.api_response import APIResponse
from DRF.marketers.serializers.marketer_company_portfolio_serializers import (
    MarketerCompanyPortfolioResponseSerializer,
)
from DRF.marketers.serializers.permissions import IsMarketerUser

from estateApp.models import (
    Transaction, MarketerCommission, Company,
    MarketerAffiliation, CompanyMarketerProfile, ClientUser, MarketerUser
)


class MarketerCompanyPortfolioAPIView(APIView):
    """
    GET /api/marketer/company/<company_id>/portfolio/
    Returns portfolio details for the marketer within the given company (transactions and client list).
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def get(self, request, company_id):
        user = request.user
        company = get_object_or_404(Company, id=company_id)

        # SECURITY: ensure marketer has access
        has_transactions = Transaction.objects.filter(marketer=user, company=company).exists()
        has_affiliation = MarketerAffiliation.objects.filter(marketer=user, company=company).exists()
        has_profile = CompanyMarketerProfile.objects.filter(marketer=user, company=company).exists()
        is_own_company = (hasattr(user, 'company_profile_id') and user.company_profile_id == company.id)
        if not (has_transactions or has_affiliation or has_profile or is_own_company):
            return APIResponse.forbidden('Access denied to this company portfolio')

        transactions_qs = Transaction.objects.filter(marketer=user, company=company).select_related('client', 'allocation__estate', 'allocation__plot_size')
        total_value = float(transactions_qs.aggregate(total=Sum('total_amount'))['total'] or 0)

        # Clients with details and their company-specific transactions
        client_ids = [c for c in transactions_qs.values_list('client_id', flat=True).distinct() if c]
        clients_payload = []
        for cid in client_ids:
            client = ClientUser.objects.filter(id=cid).first()
            client_txns = []
            for tx in transactions_qs.filter(client_id=cid).order_by('-transaction_date'):
                client_txns.append({
                    'id': tx.id,
                    'transaction_date': tx.transaction_date.isoformat(),
                    'status': tx.status,
                    'amount': float(tx.total_amount),
                    'allocation': {
                        'plot_number': tx.allocation.plot_number if getattr(tx, 'allocation', None) else None,
                        'plot_size': getattr(tx.allocation.plot_size, 'size', None) if getattr(tx, 'allocation', None) and getattr(tx.allocation, 'plot_size', None) else None,
                        'estate': {
                            'id': tx.allocation.estate.id if getattr(tx, 'allocation', None) and getattr(tx.allocation, 'estate', None) else None,
                            'name': tx.allocation.estate.estate_name if getattr(tx, 'allocation', None) and getattr(tx.allocation, 'estate', None) else None,
                        }
                    }
                })

            clients_payload.append({
                'id': cid,
                'full_name': client.full_name if client else None,
                'phone_number': client.phone_number if client else None,
                'profile_image': request.build_absolute_uri(client.profile_image.url) if client and getattr(client, 'profile_image', None) and hasattr(client.profile_image, 'url') else None,
                'email': client.email if client else None,
                'address': client.address if client else None,
                'date_registered': client.date_registered.isoformat() if client and getattr(client, 'date_registered', None) else None,
                'company_transactions': client_txns,
            })

        # header stats
        closed_deals = transactions_qs.count()
        commission = MarketerCommission.objects.filter(marketer=user, company=company).order_by('-effective_date').first()
        commission_rate = float(commission.rate) if commission and commission.rate else None
        # attempt to compute commission_earned using performance record if available
        commission_earned = None
        try:
            # prefer stored performance record if present
            from estateApp.models import MarketerPerformanceRecord
            perf = MarketerPerformanceRecord.objects.filter(marketer=user, specific_period=str(transactions_qs.first().transaction_date.year) if transactions_qs.exists() else None).first()
            if perf and getattr(perf, 'commission_earned', None) is not None:
                commission_earned = float(perf.commission_earned)
        except Exception:
            commission_earned = None
        if commission_earned is None and commission_rate is not None:
            commission_earned = float(total_value * (commission_rate / 100.0)) if total_value else 0.0

        # Leaderboard: compute top 3 performers for this company for the current year
        current_year = datetime.now().year
        year_str = str(current_year)

        affiliated_marketer_ids = set(MarketerAffiliation.objects.filter(company=company).values_list('marketer_id', flat=True))
        transaction_marketer_ids = set(Transaction.objects.filter(company=company).values_list('marketer_id', flat=True))
        all_marketer_ids = [m for m in (affiliated_marketer_ids | transaction_marketer_ids) if m is not None]

        marketer_sales = {}
        for mid in all_marketer_ids:
            yearly_sales = Transaction.objects.filter(marketer_id=mid, company=company, transaction_date__year=current_year).aggregate(total=Sum('total_amount'))['total'] or 0
            marketer_sales[mid] = float(yearly_sales)

        sorted_marketers = sorted(all_marketer_ids, key=lambda mid: (-marketer_sales.get(mid, 0), mid))

        top3 = []
        user_entry = None
        for idx, mid in enumerate(sorted_marketers[:3]):
            marketer = MarketerUser.objects.filter(id=mid).first()
            top3.append({
                'rank': idx + 1,
                'marketer': {
                    'id': mid,
                    'full_name': marketer.full_name if marketer else None,
                    'profile_image': request.build_absolute_uri(marketer.profile_image.url) if marketer and getattr(marketer, 'profile_image', None) and hasattr(marketer.profile_image, 'url') else None,
                }
            })

        # find current user's position if present
        if request.user.id in sorted_marketers:
            pos = sorted_marketers.index(request.user.id) + 1
            marketer = MarketerUser.objects.filter(id=request.user.id).first()
            user_entry = {
                'rank': pos,
                'marketer': {
                    'id': request.user.id,
                    'full_name': marketer.full_name if marketer else getattr(request.user, 'full_name', None),
                    'profile_image': request.build_absolute_uri(marketer.profile_image.url) if marketer and getattr(marketer, 'profile_image', None) and hasattr(marketer.profile_image, 'url') else None,
                }
            }

        payload = {
            'company_id': company.id,
            'company_name': company.company_name,
            'company_logo': request.build_absolute_uri(company.logo.url) if getattr(company, 'logo', None) and hasattr(company.logo, 'url') else None,
            'current_year': current_year,
            'top3': top3,
            'user_entry': user_entry,
            'clients': clients_payload,
            'closed_deals': closed_deals,
            'commission_rate': commission_rate,
            'commission_earned': commission_earned,
            'total_value': total_value,
            'transactions': [
                {
                    'id': tx.id,
                    'transaction_date': tx.transaction_date.isoformat(),
                    'client_id': tx.client_id,
                    'status': tx.status,
                    'amount': float(tx.total_amount),
                    'allocation': {
                        'plot_number': tx.allocation.plot_number if getattr(tx, 'allocation', None) else None,
                        'plot_size': getattr(tx.allocation.plot_size, 'size', None) if getattr(tx, 'allocation', None) and getattr(tx.allocation, 'plot_size', None) else None,
                        'estate': {
                            'id': tx.allocation.estate.id if getattr(tx, 'allocation', None) and getattr(tx.allocation, 'estate', None) else None,
                            'name': tx.allocation.estate.estate_name if getattr(tx, 'allocation', None) and getattr(tx.allocation, 'estate', None) else None,
                        }
                    }
                }
                for tx in transactions_qs.order_by('-transaction_date')[:500]
            ]
        }

        serializer = MarketerCompanyPortfolioResponseSerializer(payload, context={'request': request})
        return APIResponse.success(data=serializer.data, message='Portfolio retrieved')
