import math
from datetime import datetime
from decimal import Decimal
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from DRF.shared_drf.api_response import APIResponse
from DRF.marketers.serializers.marketer_company_serializers import (
    MarketerMyCompaniesResponseSerializer,
)
from DRF.marketers.serializers.marketer_company_serializers import (
    MarketerCompanyItemSerializer,
    CompanyMiniSerializer,
    TargetSerializer,
)
from DRF.marketers.serializers.permissions import IsMarketerUser

from estateApp.models import (
    Transaction, MarketerTarget, MarketerCommission, Company,
    MarketerAffiliation, CompanyMarketerProfile, MarketerUser, ClientUser
)


class MarketerMyCompaniesAPIView(APIView):
    """
    GET /api/marketer/my-companies/
    Returns the list of companies relevant to the authenticated marketer along with
    per-company metrics used by the marketer-side `my_companies.html` template.
    """
    authentication_classes = (TokenAuthentication, SessionAuthentication)
    permission_classes = (IsAuthenticated, IsMarketerUser)

    def get(self, request):
        user = request.user
        # gather company ids from transactions, affiliations and profile
        transaction_company_ids = set(Transaction.objects.filter(marketer=user).values_list('company', flat=True))
        affiliation_company_ids = set(MarketerAffiliation.objects.filter(marketer=user).values_list('company_id', flat=True))
        profile_company_ids = set(CompanyMarketerProfile.objects.filter(marketer=user).values_list('company_id', flat=True))
        own_company_id = getattr(user, 'company_profile_id', None)

        all_company_ids = transaction_company_ids | affiliation_company_ids | profile_company_ids
        if own_company_id:
            all_company_ids.add(own_company_id)
        all_company_ids = [c for c in all_company_ids if c is not None]

        companies_qs = Company.objects.filter(id__in=all_company_ids)
        current_year = datetime.now().year
        year_str = str(current_year)

        # Precompute ranks similar to the template's logic
        company_ranks = {}
        for comp_id in all_company_ids:
            affiliated_marketer_ids = set(MarketerAffiliation.objects.filter(company_id=comp_id).values_list('marketer_id', flat=True))
            transaction_marketer_ids = set(Transaction.objects.filter(company_id=comp_id).values_list('marketer_id', flat=True).distinct())
            all_marketer_ids = [m for m in (affiliated_marketer_ids | transaction_marketer_ids) if m is not None]
            if not all_marketer_ids:
                company_ranks[comp_id] = {'position': None, 'total': 0, 'label': ''}
                continue
            marketer_sales = {}
            for mid in all_marketer_ids:
                yearly_sales = Transaction.objects.filter(marketer_id=mid, company_id=comp_id, transaction_date__year=current_year).aggregate(total=Sum('total_amount'))['total'] or 0
                marketer_sales[mid] = float(yearly_sales)
            sorted_marketers = sorted(all_marketer_ids, key=lambda mid: (-marketer_sales.get(mid, 0), mid))
            total_marketers = len(sorted_marketers)
            position = None
            for idx, mid in enumerate(sorted_marketers):
                if mid == user.id:
                    position = idx + 1
                    break
            rank_label = ''
            if position:
                if position == 1:
                    rank_label = '🥇 #1'
                elif position == 2:
                    rank_label = '🥈 #2'
                elif position == 3:
                    rank_label = '🥉 #3'
                elif position <= 5:
                    rank_label = f'Top 5 (#{position})'
                elif position <= 10:
                    rank_label = f'Top 10 (#{position})'
                elif position <= 20:
                    rank_label = f'Top 20 (#{position})'
                else:
                    rank_label = f'#{position}'
            company_ranks[comp_id] = {'position': position, 'total': total_marketers, 'label': rank_label}

        companies_payload = []
        today = datetime.now().date()
        current_month = today.strftime('%Y-%m')
        current_quarter = f"{today.year}-Q{math.ceil(today.month / 3)}"

        for comp in companies_qs:
            closed_deals = Transaction.objects.filter(marketer=user, company=comp).count()

            # commission
            commission = (MarketerCommission.objects.filter(marketer=user, company=comp, effective_date__lte=today).order_by('-effective_date').first())
            commission_rate = float(commission.rate) if commission and commission.rate else None

            # yearly target
            specific_tgt = MarketerTarget.objects.filter(marketer=user, company=comp, period_type='annual', specific_period=year_str).first()
            global_tgt = MarketerTarget.objects.filter(marketer=None, company=comp, period_type='annual', specific_period=year_str).first()
            yearly_target = specific_tgt or global_tgt
            total_year_sales = float(Transaction.objects.filter(marketer=user, company=comp, transaction_date__year=current_year).aggregate(total=Sum('total_amount'))['total'] or 0)
            yearly_target_achievement = None
            if yearly_target and getattr(yearly_target, 'target_amount', None):
                if yearly_target.target_amount > 0:
                    yearly_target_achievement = min(100, (total_year_sales / yearly_target.target_amount) * 100)

            # monthly/quarterly
            monthly_target = (MarketerTarget.objects.filter(marketer=user, company=comp, period_type='monthly', specific_period=current_month).first() or
                              MarketerTarget.objects.filter(marketer=None, company=comp, period_type='monthly', specific_period=current_month).first())
            quarterly_target = (MarketerTarget.objects.filter(marketer=user, company=comp, period_type='quarterly', specific_period=current_quarter).first() or
                                MarketerTarget.objects.filter(marketer=None, company=comp, period_type='quarterly', specific_period=current_quarter).first())

            monthly_sales = float(Transaction.objects.filter(marketer=user, company=comp, transaction_date__year=today.year, transaction_date__month=today.month).aggregate(total=Sum('total_amount'))['total'] or 0)

            quarter_start_month = (math.ceil(today.month / 3) - 1) * 3 + 1
            quarterly_sales = float(Transaction.objects.filter(marketer=user, company=comp, transaction_date__year=today.year, transaction_date__month__gte=quarter_start_month, transaction_date__month__lte=quarter_start_month + 2).aggregate(total=Sum('total_amount'))['total'] or 0)

            monthly_achievement = None
            quarterly_achievement = None
            if monthly_target and getattr(monthly_target, 'target_amount', None) and monthly_target.target_amount > 0:
                monthly_achievement = min(100, (monthly_sales / monthly_target.target_amount) * 100)
            if quarterly_target and getattr(quarterly_target, 'target_amount', None) and quarterly_target.target_amount > 0:
                quarterly_achievement = min(100, (quarterly_sales / quarterly_target.target_amount) * 100)

            client_ids = Transaction.objects.filter(marketer=user, company=comp).values_list('client_id', flat=True).distinct()
            client_count = len([c for c in client_ids if c is not None])
            has_transactions = closed_deals > 0
            rank_info = company_ranks.get(comp.id, {'position': None, 'total': 0, 'label': ''})

            companies_payload.append({
                'company': {
                    'id': comp.id,
                    'company_name': comp.company_name,
                    'logo_url': request.build_absolute_uri(comp.logo.url) if comp.logo else None,
                    'initial': comp.company_name[:1].upper() if comp.company_name else None,
                    'location': comp.location if getattr(comp, 'location', None) else None,
                },
                'closed_deals': closed_deals,
                'commission_rate': commission_rate,
                'yearly_target_achievement': yearly_target_achievement,
                'yearly_target': {'period_type': 'annual', 'specific_period': year_str, 'target_amount': float(yearly_target.target_amount)} if yearly_target and getattr(yearly_target, 'target_amount', None) else None,
                'total_year_sales': total_year_sales,
                'monthly_target': {'period_type': 'monthly', 'specific_period': current_month, 'target_amount': float(monthly_target.target_amount)} if monthly_target and getattr(monthly_target, 'target_amount', None) else None,
                'quarterly_target': {'period_type': 'quarterly', 'specific_period': current_quarter, 'target_amount': float(quarterly_target.target_amount)} if quarterly_target and getattr(quarterly_target, 'target_amount', None) else None,
                'monthly_sales': monthly_sales,
                'quarterly_sales': quarterly_sales,
                'monthly_achievement': monthly_achievement,
                'quarterly_achievement': quarterly_achievement,
                'current_month': current_month,
                'current_quarter': current_quarter,
                'client_count': client_count,
                'has_transactions': has_transactions,
                'rank_position': rank_info['position'],
                'rank_total': rank_info['total'],
                'rank_label': rank_info['label'],
            })

        serializer = MarketerMyCompaniesResponseSerializer({'companies': companies_payload, 'current_year': current_year}, context={'request': request})
        return APIResponse.success(data=serializer.data, message='Marketer companies retrieved')
