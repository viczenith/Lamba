"""
Subscription Warning Banner and Countdown Modal Templates
Reusable components for subscription lifecycle UI
"""

# ============================================================================
# HTML TEMPLATE: Warning Banner (Insert in admin dashboard base template)
# ============================================================================

SUBSCRIPTION_WARNING_BANNER_HTML = """
{% if warning_message %}
<div class="subscription-warning-banner subscription-warning-{{ warning_message.level }}">
    <div class="banner-content">
        <div class="banner-icon">
            <i class="fas {{ warning_message.icon }}"></i>
        </div>
        <div class="banner-text">
            <h5 class="banner-title">{{ warning_message.title }}</h5>
            <p class="banner-message">{{ warning_message.message }}</p>
        </div>
        <div class="banner-actions">
            <button class="btn btn-sm btn-{{ warning_message.level }}" 
                    data-action="{{ warning_message.cta_action }}"
                    onclick="handleSubscriptionAction('{{ warning_message.cta_action }}')">
                {{ warning_message.cta }}
            </button>
            <button class="btn btn-sm btn-outline-secondary" 
                    onclick="dismissSubscriptionBanner()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    </div>
    
    {% if countdown_enabled %}
    <div class="banner-countdown">
        <span id="countdown-timer">
            <span id="days">0</span>d 
            <span id="hours">0</span>h 
            <span id="minutes">0</span>m 
            <span id="seconds">0</span>s
        </span>
    </div>
    {% endif %}
</div>

<style>
/* Warning Banner Styles */
.subscription-warning-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px 20px;
    margin-bottom: 20px;
    border-radius: 8px;
    border-left: 5px solid;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    animation: slideDown 0.3s ease-in-out;
}

@keyframes slideDown {
    from {
        transform: translateY(-20px);
        opacity: 0;
    }
    to {
        transform: translateY(0);
        opacity: 1;
    }
}

.subscription-warning-banner.subscription-warning-yellow {
    background-color: #fff8dc;
    border-color: #ffc107;
    color: #856404;
}

.subscription-warning-banner.subscription-warning-orange {
    background-color: #ffe8d6;
    border-color: #fd7e14;
    color: #7d4e2a;
}

.subscription-warning-banner.subscription-warning-red {
    background-color: #f8d7da;
    border-color: #dc3545;
    color: #721c24;
}

.banner-content {
    display: flex;
    align-items: center;
    gap: 15px;
    flex: 1;
}

.banner-icon {
    font-size: 24px;
    flex-shrink: 0;
}

.banner-text {
    flex: 1;
}

.banner-title {
    margin: 0;
    font-weight: 600;
    font-size: 14px;
}

.banner-message {
    margin: 5px 0 0;
    font-size: 13px;
}

.banner-actions {
    display: flex;
    gap: 8px;
    flex-shrink: 0;
}

.banner-actions .btn {
    font-size: 12px;
    padding: 6px 12px;
    white-space: nowrap;
}

.banner-countdown {
    text-align: right;
    font-size: 12px;
    font-weight: 600;
    margin-top: 5px;
}

@media (max-width: 768px) {
    .subscription-warning-banner {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .banner-content {
        width: 100%;
    }
    
    .banner-actions {
        width: 100%;
        margin-top: 10px;
    }
    
    .banner-actions .btn {
        flex: 1;
    }
}

/* Button colors */
.btn-yellow {
    background-color: #ffc107;
    color: #000;
    border-color: #ffc107;
}

.btn-yellow:hover {
    background-color: #ffb300;
    border-color: #ffb300;
}

.btn-orange {
    background-color: #fd7e14;
    color: #fff;
    border-color: #fd7e14;
}

.btn-orange:hover {
    background-color: #e5700f;
    border-color: #e5700f;
}

.btn-red {
    background-color: #dc3545;
    color: #fff;
    border-color: #dc3545;
}

.btn-red:hover {
    background-color: #c82333;
    border-color: #c82333;
}
</style>

<script>
// Countdown Timer Logic
function updateCountdown() {
    const countdownEl = document.getElementById('countdown-timer');
    if (!countdownEl) return;
    
    const expirationTime = new Date('{{ expiration_datetime|date:"c" }}').getTime();
    const now = new Date().getTime();
    const distance = expirationTime - now;
    
    if (distance < 0) {
        countdownEl.textContent = 'EXPIRED';
        return;
    }
    
    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
    
    document.getElementById('days').textContent = String(days).padStart(2, '0');
    document.getElementById('hours').textContent = String(hours).padStart(2, '0');
    document.getElementById('minutes').textContent = String(minutes).padStart(2, '0');
    document.getElementById('seconds').textContent = String(seconds).padStart(2, '0');
}

// Update countdown every second
setInterval(updateCountdown, 1000);
updateCountdown(); // Initial call

function dismissSubscriptionBanner() {
    const banner = document.querySelector('.subscription-warning-banner');
    if (banner) {
        banner.style.animation = 'slideUp 0.3s ease-in-out forwards';
        setTimeout(() => banner.remove(), 300);
    }
}

function handleSubscriptionAction(action) {
    switch(action) {
        case 'upgrade':
            window.location.href = '/admin/subscription/plans/';
            break;
        case 'renew':
            window.location.href = '/admin/subscription/renew/';
            break;
        case 'view_plans':
        case 'choose_plan':
        case 'explore_plans':
            window.location.href = '/admin/subscription/upgrade/';
            break;
    }
}
</script>

{% endif %}
"""


# ============================================================================
# HTML TEMPLATE: Countdown Modal (Popup when expiration imminent)
# ============================================================================

SUBSCRIPTION_COUNTDOWN_MODAL_HTML = """
<!-- Subscription Expiration Countdown Modal -->
<div class="modal fade" id="subscriptionCountdownModal" tabindex="-1" data-bs-keyboard="false" data-bs-backdrop="static">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content subscription-modal-content">
            <!-- Header -->
            <div class="modal-header subscription-modal-header subscription-header-{{ warning_level }}">
                <div class="modal-title-section">
                    <i class="fas fa-clock modal-icon"></i>
                    <h5 class="modal-title">Subscription Status</h5>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            
            <!-- Body -->
            <div class="modal-body subscription-modal-body">
                <!-- Company Info -->
                <div class="company-info">
                    <h6>{{ company.company_name }}</h6>
                    <span class="badge badge-{{ warning_level }}">{{ subscription_status|upper }}</span>
                </div>
                
                <!-- Status Message -->
                <div class="status-message status-{{ warning_level }}">
                    <p class="status-text">{{ status_message }}</p>
                </div>
                
                <!-- Countdown Display -->
                <div class="countdown-section">
                    <div class="countdown-label">
                        {% if is_trial %}
                            Trial Expires In:
                        {% else %}
                            Subscription Expires In:
                        {% endif %}
                    </div>
                    
                    <div class="countdown-display countdown-{{ warning_level }}">
                        <div class="countdown-unit">
                            <span class="countdown-number" id="modal-days">00</span>
                            <span class="countdown-label-small">Days</span>
                        </div>
                        <span class="countdown-separator">:</span>
                        <div class="countdown-unit">
                            <span class="countdown-number" id="modal-hours">00</span>
                            <span class="countdown-label-small">Hours</span>
                        </div>
                        <span class="countdown-separator">:</span>
                        <div class="countdown-unit">
                            <span class="countdown-number" id="modal-minutes">00</span>
                            <span class="countdown-label-small">Minutes</span>
                        </div>
                        <span class="countdown-separator">:</span>
                        <div class="countdown-unit">
                            <span class="countdown-number" id="modal-seconds">00</span>
                            <span class="countdown-label-small">Seconds</span>
                        </div>
                    </div>
                </div>
                
                <!-- Subscription Details -->
                <div class="subscription-details">
                    <div class="detail-row">
                        <span class="detail-label">Current Plan:</span>
                        <span class="detail-value">{{ plan_name }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Billing Cycle:</span>
                        <span class="detail-value">{{ billing_cycle|capfirst }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Amount:</span>
                        <span class="detail-value">₦{{ amount|default:"0" }}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Expires:</span>
                        <span class="detail-value">{{ expiration_datetime|date:"M d, Y H:i" }}</span>
                    </div>
                </div>
                
                <!-- Access Restrictions (if in grace period/expired) -->
                {% if restrictions.read_only_mode %}
                <div class="alert alert-warning mt-4">
                    <i class="fas fa-exclamation-triangle"></i>
                    <strong>Limited Access:</strong> {{ restrictions.message }}
                </div>
                {% endif %}
            </div>
            
            <!-- Footer -->
            <div class="modal-footer subscription-modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                    <i class="fas fa-times"></i> Close
                </button>
                
                {% if not is_expired %}
                    <button type="button" class="btn btn-primary" onclick="openUpgradeModal()">
                        <i class="fas fa-credit-card"></i> Upgrade/Renew
                    </button>
                {% else %}
                    <button type="button" class="btn btn-danger" onclick="openRenewalModal()">
                        <i class="fas fa-refresh"></i> Renew Now
                    </button>
                {% endif %}
            </div>
        </div>
    </div>
</div>

<style>
/* Subscription Modal Styles */
.subscription-modal-content {
    border: none;
    border-radius: 12px;
    box-shadow: 0 5px 20px rgba(0,0,0,0.15);
}

.subscription-modal-header {
    border: none;
    border-bottom: 3px solid;
    padding: 20px;
}

.subscription-modal-header.subscription-header-yellow {
    background: linear-gradient(135deg, #fff8dc 0%, #ffe8cc 100%);
    border-color: #ffc107;
    color: #856404;
}

.subscription-modal-header.subscription-header-orange {
    background: linear-gradient(135deg, #ffe8d6 0%, #ffd9b3 100%);
    border-color: #fd7e14;
    color: #7d4e2a;
}

.subscription-modal-header.subscription-header-red {
    background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
    border-color: #dc3545;
    color: #721c24;
}

.modal-title-section {
    display: flex;
    align-items: center;
    gap: 10px;
}

.modal-icon {
    font-size: 24px;
}

.modal-title {
    margin: 0;
    font-weight: 600;
    font-size: 18px;
}

.company-info {
    text-align: center;
    margin-bottom: 20px;
    padding: 15px;
    background-color: #f8f9fa;
    border-radius: 8px;
}

.company-info h6 {
    margin: 0 0 8px;
    font-weight: 600;
}

.badge-yellow {
    background-color: #ffc107;
    color: #000;
}

.badge-orange {
    background-color: #fd7e14;
    color: #fff;
}

.badge-red {
    background-color: #dc3545;
    color: #fff;
}

.status-message {
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 20px;
    text-align: center;
}

.status-message.status-yellow {
    background-color: #fffbea;
    color: #856404;
    border: 1px solid #ffc107;
}

.status-message.status-orange {
    background-color: #fffaf0;
    color: #7d4e2a;
    border: 1px solid #fd7e14;
}

.status-message.status-red {
    background-color: #fef5f5;
    color: #721c24;
    border: 1px solid #dc3545;
}

.status-text {
    margin: 0;
    font-size: 14px;
    font-weight: 500;
}

/* Countdown Display */
.countdown-section {
    margin: 25px 0;
}

.countdown-label {
    text-align: center;
    font-size: 14px;
    font-weight: 600;
    color: #666;
    margin-bottom: 15px;
}

.countdown-display {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 20px;
    border-radius: 10px;
    background-color: #f8f9fa;
}

.countdown-display.countdown-yellow {
    background: linear-gradient(135deg, #fff8dc 0%, #fffbea 100%);
    border: 2px solid #ffc107;
}

.countdown-display.countdown-orange {
    background: linear-gradient(135deg, #ffe8d6 0%, #fffaf0 100%);
    border: 2px solid #fd7e14;
}

.countdown-display.countdown-red {
    background: linear-gradient(135deg, #f8d7da 0%, #fef5f5 100%);
    border: 2px solid #dc3545;
}

.countdown-unit {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0 8px;
}

.countdown-number {
    font-size: 32px;
    font-weight: 700;
    line-height: 1;
    color: #333;
}

.countdown-label-small {
    font-size: 11px;
    color: #666;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.countdown-separator {
    font-size: 24px;
    font-weight: 300;
    color: #999;
}

/* Subscription Details */
.subscription-details {
    background-color: #f8f9fa;
    border-radius: 8px;
    padding: 15px;
    margin: 20px 0;
}

.detail-row {
    display: flex;
    justify-content: space-between;
    padding: 8px 0;
    border-bottom: 1px solid #e9ecef;
}

.detail-row:last-child {
    border-bottom: none;
}

.detail-label {
    font-weight: 500;
    color: #666;
    font-size: 13px;
}

.detail-value {
    font-weight: 600;
    color: #333;
    font-size: 13px;
}

.subscription-modal-footer {
    border: none;
    padding: 20px;
    gap: 10px;
}

/* Animations */
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

.countdown-display.countdown-red {
    animation: pulse 2s infinite;
}

@media (max-width: 576px) {
    .countdown-number {
        font-size: 24px;
    }
    
    .countdown-separator {
        font-size: 18px;
    }
    
    .subscription-details {
        font-size: 12px;
    }
}
</style>

<script>
// Modal Countdown Update
function updateModalCountdown() {
    const expirationTime = new Date('{{ expiration_datetime|date:"c" }}').getTime();
    const now = new Date().getTime();
    const distance = expirationTime - now;
    
    if (distance < 0) {
        document.getElementById('modal-days').textContent = '00';
        document.getElementById('modal-hours').textContent = '00';
        document.getElementById('modal-minutes').textContent = '00';
        document.getElementById('modal-seconds').textContent = '00';
        return;
    }
    
    const days = Math.floor(distance / (1000 * 60 * 60 * 24));
    const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((distance % (1000 * 60)) / 1000);
    
    document.getElementById('modal-days').textContent = String(days).padStart(2, '0');
    document.getElementById('modal-hours').textContent = String(hours).padStart(2, '0');
    document.getElementById('modal-minutes').textContent = String(minutes).padStart(2, '0');
    document.getElementById('modal-seconds').textContent = String(seconds).padStart(2, '0');
}

// Auto-show modal if needed
document.addEventListener('DOMContentLoaded', function() {
    {% if should_show_modal %}
    const modal = new bootstrap.Modal(document.getElementById('subscriptionCountdownModal'));
    modal.show();
    setInterval(updateModalCountdown, 1000);
    updateModalCountdown();
    {% endif %}
});

function openUpgradeModal() {
    window.location.href = '/admin/subscription/upgrade/';
}

function openRenewalModal() {
    window.location.href = '/admin/subscription/renew/';
}
</script>
"""


# ============================================================================
# TEMPLATE CONTEXT HELPER (Add to views)
# ============================================================================

def get_subscription_context(company):
    """
    Helper function to get all subscription context data for templates
    Call this in views to populate subscription-related template variables
    """
    from .subscription_billing_models import SubscriptionBillingModel
    
    try:
        billing = company.billing
    except SubscriptionBillingModel.DoesNotExist:
        return {}
    
    billing.refresh_status()
    
    warning_msg = billing.get_warning_message()
    expiration = billing.get_expiration_datetime()
    
    return {
        'subscription_billing': billing,
        'warning_message': warning_msg,
        'status_message': billing.get_access_restriction_message(),
        'is_trial': billing.is_trial(),
        'is_active': billing.is_active(),
        'is_grace_period': billing.is_grace_period(),
        'is_expired': billing.is_expired(),
        'subscription_status': billing.status,
        'warning_level': 'red' if billing.get_warning_level() >= 3 else ('orange' if billing.get_warning_level() == 2 else 'yellow'),
        'days_remaining': billing.get_days_remaining(),
        'hours_remaining': billing.get_hours_remaining(),
        'expiration_datetime': expiration,
        'should_show_modal': warning_msg is not None and billing.get_warning_level() >= 2,
        'countdown_enabled': True,
        'restrictions': billing.get_access_restrictions(),
        'plan_name': billing.current_plan.name if billing.current_plan else 'Trial',
        'billing_cycle': billing.billing_cycle,
        'amount': billing.get_current_amount(),
    }
