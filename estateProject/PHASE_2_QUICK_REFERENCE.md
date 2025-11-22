# Phase 2 Quick Reference Guide

## 🎯 Overview
**Status:** ✅ COMPLETE | **Tests:** 40/40 Passing | **Ready:** Production Deployment

---

## 📁 File Locations

### Alert Templates (Display Layer)
```
estateApp/templates/alerts/
├── banner_alert.html           # Level 1: Info (Blue) - Dismissible
├── closable_modal_alert.html   # Level 2: Warning (Orange) - 24hr Memory
├── sticky_modal_alert.html     # Level 3: Critical (Dark Red) - Requires Ack
└── blocking_modal_alert.html   # Level 4: Urgent (Red) - Full Block
```

### API Implementation (Backend)
```
estateApp/api_views/
└── alerts_views.py             # 5 REST endpoints (525+ lines)

estateApp/api_urls/
└── alerts_urls.py              # URL routing for alerts endpoints
```

### Frontend (Client-Side)
```
estateApp/static/js/
└── alerts.js                   # AlertManager class (600+ lines)
```

### Context & Configuration
```
estateApp/
├── context_processors.py       # subscription_alerts() injection
└── templates/admin_side/
    └── index.html              # Dashboard integration

estateProject/
└── settings.py                 # TEMPLATES context processor registration
```

---

## 🔌 API Endpoints

### 1. Acknowledge Alert
```
POST /api/alerts/acknowledge/
{
  "alert_id": 123
}
Response: {"success": true, "message": "Alert acknowledged"}
```

### 2. Dismiss Alert
```
POST /api/alerts/dismiss/
{
  "alert_id": 123,
  "dismiss_until": "2025-11-21T13:00:00Z"  # Optional, defaults to 24hrs
}
Response: {"success": true, "dismissed_until": "2025-11-21T13:00:00Z"}
```

### 3. Resolve Alert
```
POST /api/alerts/resolve/
{
  "alert_id": 123
}
Response: {"success": true, "message": "Alert resolved"}
```

### 4. List Alerts
```
GET /api/alerts/list/?status=active&severity=warning
Response: {
  "count": 5,
  "results": [
    {"id": 1, "severity": "warning", "title": "...", ...},
    ...
  ]
}
```

### 5. Clear Dismissed Alerts
```
POST /api/alerts/clear-dismissed/
{}
Response: {"success": true, "cleared": 3}
```

---

## 📊 Alert Severity Levels

| Level | Name | Color | Action | Dismissible | Example |
|-------|------|-------|--------|-------------|---------|
| 1 | **info** | Blue | Alert | ✅ Yes (immediate) | "Trial active" |
| 2 | **warning** | Orange | Warn | ✅ Yes (24hrs) | "Trial ending soon" |
| 3 | **critical** | Dark Red | Require Ack | ❌ No (requires action) | "Last day" |
| 4 | **urgent** | Red | Block | ❌ No (blocks UI) | "Trial expired" |

---

## 🔐 Security Features

✅ CSRF Token Protection
- Extracted from request or cookie
- Validated on all POST requests
- Included in all API responses

✅ Company Ownership Verification
- All endpoints verify company association
- Users can only access their company's alerts
- Cross-company access prevented

✅ Authentication Required
- Session-based auth on all endpoints
- Login required to access alerts
- Automatic logout on auth failure

✅ Error Handling
- Try-catch blocks on all endpoints
- Comprehensive logging
- User-friendly error messages
- No sensitive data in error responses

---

## 💾 Frontend Storage (localStorage)

**Key Format:** `alert_dismissal_{alert_id}`

**Data Structure:**
```javascript
{
  "alert_id": 123,
  "dismissed_at": "2025-11-20T13:00:00Z",
  "dismissed_until": "2025-11-21T13:00:00Z",
  "expires": "2025-11-22T13:00:00Z"  // Auto-cleanup reference
}
```

**Behavior:**
- Dismissed alerts hidden for 24 hours (default)
- Auto-cleanup of expired dismissals on page load
- Works offline (graceful degradation)
- No server required for dismissal memory

---

## 🧪 Testing

### Test Classes
- **AlertDisplayTests:** 4 tests for alert display
- **AlertInteractionTests:** 7 tests for interactions
- **SubscriptionAlertServiceTests:** Alert creation logic
- Plus 28 tests from Phase 1

### Running Tests
```bash
# All Phase 2 tests
python manage.py test estateApp.tests.test_subscription_lifecycle.AlertDisplayTests
python manage.py test estateApp.tests.test_subscription_lifecycle.AlertInteractionTests

# All subscription tests
python manage.py test estateApp.tests.test_subscription_lifecycle -v 1

# Specific test
python manage.py test estateApp.tests.test_subscription_lifecycle.AlertDisplayTests.test_banner_alert_display -v 2
```

### Test Results
```
✅ 40/40 tests passing (100%)
✅ 0 failures
✅ 0 regressions
✅ Execution time: 55.4 seconds
```

---

## 🚀 Usage Example

### Server-Side (Python/Django)
```python
from estateApp.models import SubscriptionAlert, Company
from estateApp.services.alerts import SubscriptionAlertService

# Create alert
company = Company.objects.get(id=1)
alert = SubscriptionAlert.objects.create(
    company=company,
    alert_type='trial_ending',
    severity='warning',
    title='Trial Ending Soon',
    message='Your trial ends in 3 days',
    action_label='Upgrade Now',
    action_url='/upgrade/',
)

# Trigger alert service
SubscriptionAlertService.generate_trial_alerts(company)

# Alert auto-injected in templates via context processor
```

### Template Usage (Django Template)
```html
<!-- Automatically available in all templates -->
{% if subscription_alerts %}
  <div class="alerts">
    {% for alert in subscription_alerts %}
      <div class="alert alert-{{ alert.severity }}">
        <h4>{{ alert.title }}</h4>
        <p>{{ alert.message }}</p>
        {% if alert.action_url %}
          <a href="{{ alert.action_url }}">{{ alert.action_label }}</a>
        {% endif %}
      </div>
    {% endfor %}
  </div>
{% endif %}
```

### Frontend JavaScript
```javascript
// Auto-initializes on page load
const alertManager = new AlertManager();

// Manual operations
alertManager.dismissAlert(123);
alertManager.acknowledgeAlert(123);
alertManager.resolveAlert(123);

// Global convenience functions
dismissAlert(123);
acknowledgeAlert(123);

// Refresh alerts
alertManager.refreshAlerts();
```

---

## 📋 Deployment Checklist

### Pre-Deployment
- [x] All 40 tests passing
- [x] No regressions from Phase 1
- [x] Code security review complete
- [x] Documentation complete

### Deployment
- [ ] Database backup created
- [ ] Deploy to staging
- [ ] Run smoke tests
- [ ] Monitor for 24 hours
- [ ] Deploy to production

### Post-Deployment
- [ ] Monitor alerts system
- [ ] Check error logs
- [ ] Gather user feedback
- [ ] Document any issues

---

## 🔄 User Flow

```
User Logs In
    ↓
Dashboard Loads
    ↓
Context Processor Injects Alerts
    ↓
Template Displays Alert Containers
    ↓
alerts.js Loads and Initializes
    ↓
AlertManager:
  1. Checks localStorage for dismissed alerts
  2. Filters out dismissed alerts
  3. Sorts by severity (highest first)
  4. Renders remaining alerts to DOM
  5. Sets up event listeners
  6. Starts 5-min auto-refresh polling
    ↓
User Sees Alert
    ↓
User Action:
  - Dismiss (24hr, stored in localStorage)
  - Acknowledge (API call to server)
  - Resolve (API call to server)
  - Click Action (redirects to action_url)
    ↓
Alert Hidden/Updated
    ↓
Server Syncs State (if API called)
    ↓
Next Refresh Shows Updated Status
```

---

## 🐛 Troubleshooting

### Alerts Not Showing
1. Check context processor is registered in settings.py
2. Verify alerts exist in database
3. Check browser console for JavaScript errors
4. Clear localStorage and refresh

### Dismissal Not Working
1. Verify localStorage is enabled in browser
2. Check browser console for API errors
3. Verify CSRF token in request
4. Check company ownership verification

### Tests Failing
1. Run migration: `python manage.py migrate`
2. Clear test database: `python manage.py flush`
3. Verify SubscriptionAlert model exists
4. Check test database permissions

---

## 📞 Support & Next Steps

### For Production Deployment
1. Review PHASE_2_COMPLETION_REPORT.md
2. Follow deployment checklist
3. Monitor production alerts
4. Document any issues

### For Phase 3
- Dashboard configuration panel
- Alert analytics & history
- Advanced targeting options
- Email/SMS notifications

---

**Last Updated:** November 20, 2025  
**Version:** 1.0 - Phase 2 Release  
**Status:** ✅ Production Ready
