"""
Company Admin Dashboard Subscription Management Views & Templates
Integrates subscription billing, usage, and renewal interfaces
"""

# ============================================================================
# DJANGO VIEWS - Add to estateApp/views.py
# ============================================================================

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from .subscription_billing_models import (
    SubscriptionBillingModel, BillingHistory, SubscriptionFeatureAccess
)
from .subscription_ui_templates import get_subscription_context


@login_required
def subscription_dashboard(request, company_slug):
    """Main subscription management dashboard for company admins"""
    try:
        company = CustomUser.objects.get(slug=company_slug).company
    except:
        return redirect('admin_dashboard')
    
    # Check permissions
    if not is_company_admin(request.user, company):
        return redirect('admin_dashboard')
    
    billing = get_object_or_404(SubscriptionBillingModel, company=company)
    billing.refresh_status()
    
    # Get recent transactions
    transactions = billing.transaction_history.all()[:10]
    
    # Get feature usage
    feature_limits = company.get_feature_limits()
    usage_stats = company.get_usage_stats()
    
    context = {
        'company': company,
        'billing': billing,
        'transactions': transactions,
        'feature_limits': feature_limits,
        'usage_stats': usage_stats,
        **get_subscription_context(company)
    }
    
    return render(request, 'admin/subscription_dashboard.html', context)


@login_required
def subscription_upgrade(request, company_slug):
    """Plan upgrade interface"""
    try:
        company = CustomUser.objects.get(slug=company_slug).company
    except:
        return redirect('admin_dashboard')
    
    if not is_company_admin(request.user, company):
        return redirect('admin_dashboard')
    
    from .models import SubscriptionPlan
    
    billing = company.billing
    current_plan = billing.current_plan
    all_plans = SubscriptionPlan.objects.all()
    
    context = {
        'company': company,
        'billing': billing,
        'current_plan': current_plan,
        'available_plans': all_plans,
        **get_subscription_context(company)
    }
    
    return render(request, 'admin/subscription_upgrade.html', context)


@login_required
def subscription_renew(request, company_slug):
    """Subscription renewal interface"""
    try:
        company = CustomUser.objects.get(slug=company_slug).company
    except:
        return redirect('admin_dashboard')
    
    if not is_company_admin(request.user, company):
        return redirect('admin_dashboard')
    
    billing = company.billing
    
    context = {
        'company': company,
        'billing': billing,
        'renewal_amount': billing.get_current_amount(),
        'payment_methods': ['stripe', 'paystack'],
        **get_subscription_context(company)
    }
    
    return render(request, 'admin/subscription_renew.html', context)


@login_required
def billing_history(request, company_slug):
    """Detailed billing history and invoices"""
    try:
        company = CustomUser.objects.get(slug=company_slug).company
    except:
        return redirect('admin_dashboard')
    
    if not is_company_admin(request.user, company):
        return redirect('admin_dashboard')
    
    billing = company.billing
    transactions = billing.transaction_history.all()
    
    context = {
        'company': company,
        'billing': billing,
        'transactions': transactions,
        **get_subscription_context(company)
    }
    
    return render(request, 'admin/billing_history.html', context)


@login_required
@require_POST
def initiate_payment(request, company_slug):
    """Initiate payment for upgrade/renewal"""
    try:
        company = CustomUser.objects.get(slug=company_slug).company
    except:
        return JsonResponse({'status': 'error', 'message': 'Company not found'}, status=404)
    
    if not is_company_admin(request.user, company):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    plan_tier = request.POST.get('plan_tier')
    billing_cycle = request.POST.get('billing_cycle', 'monthly')
    payment_method = request.POST.get('payment_method', 'stripe')
    
    from .models import SubscriptionPlan
    
    try:
        new_plan = SubscriptionPlan.objects.get(tier=plan_tier)
    except:
        return JsonResponse({'status': 'error', 'message': 'Invalid plan'}, status=400)
    
    billing = company.billing
    amount = new_plan.annual_price if billing_cycle == 'annual' else new_plan.monthly_price
    
    # TODO: Integrate with Stripe/Paystack
    # For now, return payment details for frontend to process
    
    return JsonResponse({
        'status': 'success',
        'payment_info': {
            'company_id': company.id,
            'plan': plan_tier,
            'amount': str(amount),
            'currency': 'NGN',
            'billing_cycle': billing_cycle,
            'payment_method': payment_method
        }
    })


@login_required
def subscription_api_status(request, company_slug):
    """API endpoint returning current subscription status (JSON)"""
    try:
        company = CustomUser.objects.get(slug=company_slug).company
    except:
        return JsonResponse({'error': 'Company not found'}, status=404)
    
    if not is_company_admin(request.user, company):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    billing = company.billing
    billing.refresh_status()
    
    return JsonResponse({
        'status': billing.status,
        'is_trial': billing.is_trial(),
        'is_active': billing.is_active(),
        'is_grace_period': billing.is_grace_period(),
        'is_expired': billing.is_expired(),
        'days_remaining': billing.get_days_remaining(),
        'hours_remaining': billing.get_hours_remaining(),
        'expiration': billing.get_expiration_datetime().isoformat() if billing.get_expiration_datetime() else None,
        'warning_level': billing.get_warning_level(),
        'warning_message': billing.get_warning_message(),
        'restrictions': billing.get_access_restrictions(),
    })


def is_company_admin(user, company):
    """Check if user is admin of the company"""
    return user.is_company_admin and user.company == company


# ============================================================================
# URL PATTERNS - Add to estateApp/urls.py
# ============================================================================

"""
Include these URL patterns in your main urls.py:

from estateApp import views

urlpatterns = [
    # ... existing patterns ...
    
    # Subscription Management Routes
    path('admin/company/<slug:company_slug>/subscription/', 
         views.subscription_dashboard, name='subscription_dashboard'),
    path('admin/company/<slug:company_slug>/subscription/upgrade/', 
         views.subscription_upgrade, name='subscription_upgrade'),
    path('admin/company/<slug:company_slug>/subscription/renew/', 
         views.subscription_renew, name='subscription_renew'),
    path('admin/company/<slug:company_slug>/billing/history/', 
         views.billing_history, name='billing_history'),
    path('admin/company/<slug:company_slug>/billing/initiate-payment/', 
         views.initiate_payment, name='initiate_payment'),
    path('api/company/<slug:company_slug>/subscription/status/', 
         views.subscription_api_status, name='subscription_api_status'),
]
"""


# ============================================================================
# TEMPLATE: subscription_dashboard.html
# ============================================================================

SUBSCRIPTION_DASHBOARD_TEMPLATE = '''
{% extends 'admin/base.html' %}
{% load static %}

{% block title %}Subscription Management{% endblock %}

{% block content %}
<div class="subscription-dashboard">
    <!-- Warning Banner -->
    {% include 'components/subscription_warning_banner.html' %}
    
    <!-- Page Header -->
    <div class="page-header mb-4">
        <div class="row align-items-center">
            <div class="col">
                <h1 class="h2">
                    <i class="fas fa-credit-card"></i> Subscription Management
                </h1>
                <p class="text-muted">View and manage your {{ company.company_name }} subscription</p>
            </div>
            <div class="col-auto">
                {% if billing.is_active %}
                    <a href="{% url 'subscription_upgrade' company.slug %}" class="btn btn-primary">
                        <i class="fas fa-arrow-up"></i> Upgrade
                    </a>
                {% else %}
                    <a href="{% url 'subscription_renew' company.slug %}" class="btn btn-success">
                        <i class="fas fa-refresh"></i> Renew
                    </a>
                {% endif %}
            </div>
        </div>
    </div>
    
    <!-- Main Cards Grid -->
    <div class="row mb-4">
        <!-- Current Plan Card -->
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card plan-card">
                <div class="card-body">
                    <h6 class="card-title">Current Plan</h6>
                    <h4 class="card-value">{{ plan_name }}</h4>
                    <p class="text-muted">
                        ₦{{ amount|floatformat:0 }}/{{ billing_cycle }}
                    </p>
                </div>
            </div>
        </div>
        
        <!-- Status Card -->
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card status-card">
                <div class="card-body">
                    <h6 class="card-title">Status</h6>
                    <div class="status-badge status-{{ subscription_status }}">
                        {{ subscription_status|upper }}
                    </div>
                    {% if is_trial %}
                        <small class="text-muted">Free Trial Active</small>
                    {% endif %}
                </div>
            </div>
        </div>
        
        <!-- Expiration Card -->
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card expiration-card">
                <div class="card-body">
                    <h6 class="card-title">Expires In</h6>
                    <h4 class="card-value countdown-large">
                        {{ days_remaining }} days
                    </h4>
                    <small class="text-muted">
                        {{ expiration_datetime|date:"M d, Y" }}
                    </small>
                </div>
            </div>
        </div>
        
        <!-- Quick Actions Card -->
        <div class="col-md-6 col-lg-3 mb-3">
            <div class="card actions-card">
                <div class="card-body">
                    <h6 class="card-title">Actions</h6>
                    <div class="btn-group-vertical w-100">
                        <a href="#" class="btn btn-sm btn-outline-primary">
                            <i class="fas fa-file-invoice"></i> View Invoices
                        </a>
                        <a href="#" class="btn btn-sm btn-outline-secondary">
                            <i class="fas fa-gear"></i> Settings
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Feature Usage Section -->
    <div class="row mb-4">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <h5 class="card-title mb-0">Feature Usage</h5>
                </div>
                <div class="card-body">
                    <div class="row">
                        {% for feature, limit in feature_limits.items %}
                        <div class="col-md-4 mb-3">
                            <div class="usage-item">
                                <div class="d-flex justify-content-between mb-2">
                                    <span class="feature-name">{{ feature|title }}</span>
                                    <span class="feature-usage">
                                        {{ usage_stats|get_item:feature }}/{{ limit }}
                                    </span>
                                </div>
                                <div class="progress" style="height: 8px;">
                                    {% with percentage=usage_stats|get_item:feature|divide:limit|multiply:100 %}
                                    <div class="progress-bar" 
                                         style="width: {{ percentage }}%"
                                         role="progressbar"
                                         {% if percentage > 80 %}style="background-color: #dc3545;"{% endif %}>
                                    </div>
                                    {% endwith %}
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Recent Transactions -->
    <div class="row">
        <div class="col-12">
            <div class="card">
                <div class="card-header">
                    <div class="d-flex justify-content-between align-items-center">
                        <h5 class="card-title mb-0">Recent Transactions</h5>
                        <a href="{% url 'billing_history' company.slug %}" class="btn btn-sm btn-outline-primary">
                            View All
                        </a>
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>Invoice</th>
                                <th>Date</th>
                                <th>Amount</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for transaction in transactions %}
                            <tr>
                                <td><code>{{ transaction.invoice_number }}</code></td>
                                <td>{{ transaction.billing_date|date:"M d, Y" }}</td>
                                <td>₦{{ transaction.amount }}</td>
                                <td>
                                    <span class="badge badge-{{ transaction.state }}">
                                        {{ transaction.state|upper }}
                                    </span>
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-outline-secondary">
                                        <i class="fas fa-download"></i>
                                    </button>
                                </td>
                            </tr>
                            {% empty %}
                            <tr>
                                <td colspan="5" class="text-center text-muted py-4">
                                    No transactions yet
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Countdown Modal -->
    {% include 'components/subscription_countdown_modal.html' %}
</div>

<style>
.subscription-dashboard { padding: 20px; }

.plan-card, .status-card, .expiration-card, .actions-card {
    border: none;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    transition: all 0.3s ease;
}

.plan-card:hover, .status-card:hover, .expiration-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
}

.card-value { color: #2c3e50; margin: 10px 0; }
.countdown-large { font-size: 28px; font-weight: 700; }

.status-badge {
    display: inline-block;
    padding: 8px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 12px;
}

.status-trial { background: #e3f2fd; color: #1565c0; }
.status-active { background: #e8f5e9; color: #2e7d32; }
.status-grace { background: #fff3e0; color: #e65100; }
.status-expired { background: #ffebee; color: #c62828; }

.usage-item { padding: 10px 0; }
.feature-name { font-weight: 500; color: #333; }
.feature-usage { font-weight: 600; color: #666; }

@media (max-width: 768px) {
    .page-header .col-auto { margin-top: 10px; }
}
</style>

<!-- Countdown Timer Script -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    // Refresh countdown every second
    const updateCountdown = () => {
        const expirationTime = new Date('{{ expiration_datetime|date:"c" }}').getTime();
        const now = new Date().getTime();
        const distance = expirationTime - now;
        
        if (distance < 0) return;
        
        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        document.querySelector('.countdown-large').textContent = days + ' days';
    };
    
    updateCountdown();
    setInterval(updateCountdown, 60000); // Update every minute
});
</script>
{% endblock %}
'''


# ============================================================================
# TEMPLATE: subscription_upgrade.html
# ============================================================================

SUBSCRIPTION_UPGRADE_TEMPLATE = '''
{% extends 'admin/base.html' %}
{% load static %}

{% block title %}Upgrade Plan{% endblock %}

{% block content %}
<div class="upgrade-container">
    <!-- Warning Banner -->
    {% include 'components/subscription_warning_banner.html' %}
    
    <!-- Header -->
    <div class="page-header mb-4">
        <h1 class="h2"><i class="fas fa-arrow-up"></i> Upgrade Your Plan</h1>
        <p class="text-muted">Choose a plan that suits your growing business needs</p>
    </div>
    
    <!-- Plans Comparison -->
    <div class="pricing-cards-container">
        {% for plan in available_plans %}
        <div class="pricing-card {% if plan == current_plan %}current-plan{% endif %}">
            {% if plan == current_plan %}
            <div class="badge badge-primary">Current Plan</div>
            {% endif %}
            
            <div class="plan-header">
                <h5>{{ plan.name }}</h5>
                <p class="text-muted">{{ plan.description }}</p>
            </div>
            
            <div class="plan-pricing">
                <span class="currency">₦</span>
                <span class="amount">{{ plan.monthly_price|floatformat:0 }}</span>
                <span class="period">/month</span>
            </div>
            
            <div class="plan-features">
                <h6>Features:</h6>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> {{ plan.max_plots }} Properties</li>
                    <li><i class="fas fa-check"></i> {{ plan.max_agents }} Clients</li>
                    <li><i class="fas fa-check"></i> {{ plan.max_api_calls_daily }}/day API Calls</li>
                    {% if plan.features %}
                        {% for feature, value in plan.features.items %}
                        <li><i class="fas fa-check"></i> {{ feature|title }}: {{ value }}</li>
                        {% endfor %}
                    {% endif %}
                </ul>
            </div>
            
            {% if plan != current_plan %}
            <button class="btn btn-primary w-100 mt-3" 
                    onclick="selectPlan('{{ plan.tier }}')">
                Upgrade to {{ plan.name }}
            </button>
            {% else %}
            <button class="btn btn-secondary w-100 mt-3" disabled>
                Current Plan
            </button>
            {% endif %}
        </div>
        {% endfor %}
    </div>
    
    <!-- Payment Form (hidden by default) -->
    <div id="payment-form" class="mt-4" style="display: none;">
        <div class="card">
            <div class="card-header">
                <h5 class="card-title mb-0">Complete Your Upgrade</h5>
            </div>
            <div class="card-body">
                <form id="upgrade-form" method="post" action="{% url 'initiate_payment' company.slug %}">
                    {% csrf_token %}
                    
                    <input type="hidden" name="plan_tier" id="selected-plan" value="">
                    
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="billing-cycle" class="form-label">Billing Cycle</label>
                            <select class="form-select" name="billing_cycle" id="billing-cycle">
                                <option value="monthly">Monthly</option>
                                <option value="annual" selected>Annual (Save 20%)</option>
                            </select>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label for="payment-method" class="form-label">Payment Method</label>
                            <select class="form-select" name="payment_method" id="payment-method">
                                <option value="stripe">Stripe</option>
                                <option value="paystack">Paystack</option>
                            </select>
                        </div>
                    </div>
                    
                    <button type="submit" class="btn btn-primary btn-lg w-100">
                        <i class="fas fa-credit-card"></i> Proceed to Payment
                    </button>
                </form>
            </div>
        </div>
    </div>
    
    <!-- Countdown Modal -->
    {% include 'components/subscription_countdown_modal.html' %}
</div>

<style>
.upgrade-container { padding: 20px; }

.pricing-cards-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.pricing-card {
    border: 2px solid #e9ecef;
    border-radius: 12px;
    padding: 25px;
    position: relative;
    transition: all 0.3s ease;
    background: white;
}

.pricing-card:hover {
    border-color: #007bff;
    box-shadow: 0 8px 20px rgba(0,123,255,0.1);
    transform: translateY(-4px);
}

.pricing-card.current-plan {
    border-color: #007bff;
    background: linear-gradient(135deg, #f0f7ff 0%, #e3f2fd 100%);
}

.badge-primary {
    position: absolute;
    top: 15px;
    right: 15px;
}

.plan-header { text-align: center; margin-bottom: 20px; }
.plan-header h5 { margin-bottom: 8px; font-weight: 600; }

.plan-pricing {
    text-align: center;
    padding: 20px 0;
    border-top: 1px solid #e9ecef;
    border-bottom: 1px solid #e9ecef;
    margin-bottom: 20px;
}

.plan-pricing .currency { font-size: 18px; }
.plan-pricing .amount { font-size: 36px; font-weight: 700; }
.plan-pricing .period { font-size: 14px; color: #666; }

.feature-list {
    list-style: none;
    padding: 0;
    margin-bottom: 20px;
}

.feature-list li {
    padding: 8px 0;
    color: #555;
    font-size: 14px;
}

.feature-list i { color: #28a745; margin-right: 8px; }
</style>

<script>
function selectPlan(tier) {
    document.getElementById('selected-plan').value = tier;
    document.getElementById('payment-form').style.display = 'block';
    document.getElementById('payment-form').scrollIntoView({ behavior: 'smooth' });
}

document.getElementById('upgrade-form').addEventListener('submit', function(e) {
    e.preventDefault();
    
    const formData = new FormData(this);
    
    fetch(this.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            // Redirect to payment gateway
            // window.location.href = data.payment_url;
            alert('Proceeding to payment...');
        } else {
            alert('Error: ' + data.message);
        }
    });
});
</script>
{% endblock %}
'''
