"""
Cross-Company Client Portfolio Views (estateApp)
Allows clients to view all properties purchased across multiple companies
Linked by email address for cross-company tracking
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.http import JsonResponse
from decimal import Decimal

from .models import PlotAllocation, Company, CustomUser, ClientDashboard


@login_required
def client_cross_company_portfolio(request):
    """
    Display client's portfolio across all companies
    Uses email as the linking identifier
    """
    user = request.user
    
    # Check if user is a client
    if user.role != 'client':
        return redirect('dashboard')
    
    # Independent clients can see cross-company portfolio
    # Company-assigned clients see only their company's properties
    is_independent = not hasattr(user, 'company_profile') or user.company_profile is None
    
    if is_independent:
        # Get all allocations by email (cross-company)
        allocations = PlotAllocation.objects.filter(
            client_email=user.email
        ).select_related(
            'estate__company', 'estate', 'plot_size', 'plot_number', 'client'
        ).order_by('-date_allocated')
    else:
        # Company-assigned client sees only their company's properties
        allocations = PlotAllocation.objects.filter(
            client=user,
            company=user.company_profile
        ).select_related(
            'estate__company', 'estate', 'plot_size', 'plot_number'
        ).order_by('-date_allocated')
    
    # Group properties by company
    companies_data = {}
    total_properties = 0
    total_invested = Decimal('0.00')
    
    for allocation in allocations:
        company = allocation.estate.company
        if not company:
            continue
        
        company_id = company.id
        if company_id not in companies_data:
            companies_data[company_id] = {
                'company': company,
                'properties': [],
                'property_count': 0,
                'total_investment': Decimal('0.00')
            }
        
        # Calculate investment
        investment = getattr(allocation.plot_size_unit, 'price', Decimal('0.00')) if hasattr(allocation, 'plot_size_unit') else Decimal('0.00')
        
        companies_data[company_id]['properties'].append(allocation)
        companies_data[company_id]['property_count'] += 1
        companies_data[company_id]['total_investment'] += investment
        
        total_properties += 1
        total_invested += investment
    
    # Convert to list and sort by company name
    companies_list = sorted(companies_data.values(), key=lambda x: x['company'].company_name)
    
    context = {
        'is_independent_client': is_independent,
        'companies': companies_list,
        'total_companies': len(companies_list),
        'total_properties': total_properties,
        'total_invested': total_invested,
        'client_email': user.email,
    }
    
    return render(request, 'clients/cross_company_portfolio.html', context)


@login_required
def client_company_properties(request, company_id, user_slug=None):
    """
    Display properties from a specific company for the client
    """
    user = request.user
    
    if user.role != 'client':
        return redirect('dashboard')
    
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        return redirect('client-cross-company-portfolio')
    
    # Check if independent or company-assigned
    is_independent = not hasattr(user, 'company_profile') or user.company_profile is None
    
    if is_independent:
        # Get allocations by email
        allocations = PlotAllocation.objects.filter(
            client_email=user.email,
            estate__company=company
        ).select_related(
            'estate', 'plot_size', 'plot_number', 'client'
        ).prefetch_related('transactions').order_by('-date_allocated')
    else:
        # Company-assigned client
        allocations = PlotAllocation.objects.filter(
            client=user,
            estate__company=company
        ).select_related(
            'estate', 'plot_size', 'plot_number'
        ).prefetch_related('transactions').order_by('-date_allocated')
    
    # SECURITY: Verify client has properties with this company
    if not allocations.exists():
        from django.contrib import messages
        messages.error(request, "Access denied. You don't have properties with this company.")
        return redirect('client-cross-company-portfolio')
    
    # Calculate totals
    total_properties = allocations.count()
    total_invested = Decimal('0.00')
    
    # Get transactions for these allocations to calculate investment and appreciation
    from estateApp.models import Transaction, PropertyPrice
    transactions_with_appreciation = []
    appreciation_total = Decimal('0.00')
    growth_rates = []
    
    for allocation in allocations:
        try:
            transaction = Transaction.objects.select_related(
                'allocation__estate',
                'allocation__plot_size'
            ).filter(allocation=allocation).first()
            
            if transaction:
                total_invested += transaction.total_amount
                
                # Get current price from PropertyPrice model
                try:
                    # Find the plot size unit for this allocation
                    from estateApp.models import PlotSizeUnits
                    plot_size_unit = PlotSizeUnits.objects.filter(
                        estate_plot__estate=allocation.estate,
                        plot_size=allocation.plot_size
                    ).first()
                    
                    if plot_size_unit:
                        # Get current price
                        property_price = PropertyPrice.objects.filter(
                            estate=allocation.estate,
                            plot_unit=plot_size_unit
                        ).first()
                        
                        if property_price:
                            current_value = property_price.current
                        else:
                            # If no price record, use transaction amount
                            current_value = transaction.total_amount
                    else:
                        current_value = transaction.total_amount
                except:
                    current_value = transaction.total_amount
                
                # Calculate appreciation
                appreciation = current_value - transaction.total_amount
                abs_appreciation = abs(appreciation)
                
                # Calculate growth rate
                if transaction.total_amount > 0:
                    growth_rate = (appreciation / transaction.total_amount) * 100
                else:
                    growth_rate = 0
                
                abs_growth_rate = min(abs(growth_rate), 100)  # Cap at 100% for progress bar
                
                # Add calculated fields to transaction
                transaction.current_value = current_value
                transaction.appreciation = appreciation
                transaction.abs_appreciation = abs_appreciation
                transaction.growth_rate = growth_rate
                transaction.abs_growth_rate = abs_growth_rate
                
                transactions_with_appreciation.append(transaction)
                appreciation_total += appreciation
                growth_rates.append(growth_rate)
        except Exception as e:
            print(f"Error calculating appreciation for allocation {allocation.id}: {str(e)}")
            pass
    
    # Calculate average growth
    average_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0
    
    # Find highest growth property
    highest_growth_property = "N/A"
    highest_growth_rate = 0
    if transactions_with_appreciation:
        highest_transaction = max(transactions_with_appreciation, key=lambda t: t.growth_rate)
        highest_growth_property = highest_transaction.allocation.estate.name
        highest_growth_rate = highest_transaction.growth_rate
    
    context = {
        'company': company,
        'allocations': allocations,
        'total_properties': total_properties,
        'total_invested': total_invested,
        'is_independent_client': is_independent,
        'transactions': transactions_with_appreciation,
        'appreciation_total': appreciation_total,
        'average_growth': average_growth,
        'highest_growth_property': highest_growth_property,
        'highest_growth_rate': highest_growth_rate,
    }
    
    return render(request, 'client_side/company_properties.html', context)


@login_required
def client_portfolio_ajax(request):
    """
    AJAX endpoint to fetch portfolio data
    Returns JSON for dynamic loading
    """
    user = request.user
    
    if user.role != 'client':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    is_independent = not hasattr(user, 'company_profile') or user.company_profile is None
    
    if is_independent:
        allocations = PlotAllocation.objects.filter(
            client_email=user.email
        ).select_related('estate__company')
    else:
        allocations = PlotAllocation.objects.filter(
            client=user,
            company=user.company_profile
        ).select_related('estate__company')
    
    # Group by company
    companies = Company.objects.filter(
        estates__plot_allocations__client_email=user.email if is_independent else None,
        estates__plot_allocations__client=user if not is_independent else None
    ).distinct().annotate(
        properties_count=Count('estates__plot_allocations')
    ).values('id', 'company_name', 'logo', 'properties_count')
    
    companies_list = []
    for company in companies:
        companies_list.append({
            'id': company['id'],
            'name': company['company_name'],
            'logo_url': company['logo'] if company['logo'] else None,
            'properties_count': company['properties_count'],
        })
    
    return JsonResponse({
        'is_independent': is_independent,
        'companies': companies_list,
        'total_companies': len(companies_list),
    })


@login_required
def update_client_email_on_allocations(request):
    """
    Admin utility to populate client_email on existing PlotAllocations
    This ensures all allocations have email for cross-company tracking
    """
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    # Get allocations without client_email
    allocations = PlotAllocation.objects.filter(
        Q(client_email__isnull=True) | Q(client_email='')
    ).select_related('client')
    
    updated_count = 0
    for allocation in allocations:
        if allocation.client and allocation.client.email:
            allocation.client_email = allocation.client.email
            allocation.save(update_fields=['client_email'])
            updated_count += 1
    
    return JsonResponse({
        'success': True,
        'message': f'Updated {updated_count} allocations with client email',
        'updated_count': updated_count
    })
