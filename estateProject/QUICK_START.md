# Frontend Quick Start Guide

## 📋 What Was Built in Phase 4

### ✅ Completed

1. **Tenant Admin Dashboard** (`estateApp/templates/tenant_admin/dashboard.html`)
   - Super-admin view managing ALL companies
   - System-wide statistics
   - Company CRUD operations
   - Ready to use

2. **4 JavaScript Libraries**
   - `api-client.js` - REST API with tenant context
   - `components.js` - Reusable UI components
   - `error-handler.js` - Global error handling
   - `websocket-service.js` - Real-time updates

### ⏳ Need to Implement (Phase 5)

1. **Company Admin Dashboard** (`admin_side/index.html`)
2. **Client Dashboard** (`client_side/client_side.html`)
3. **Marketer Dashboard** (`marketer_side/marketer_side.html`)

---

## 🚀 Quick Integration Steps

### Step 1: Include JavaScript Files in Your Base Template

```html
<!-- estateApp/templates/base.html -->
{% load static %}

<head>
  <!-- Existing head content -->
  <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdnjs.cloudflare.com/ajax/libs/remixicon/3.5.0/remixicon.min.css" rel="stylesheet">
</head>

<body>
  <!-- Your content -->
  {% block content %}{% endblock %}

  <!-- Scripts - include these AFTER Bootstrap -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
  
  <!-- Frontend libraries -->
  <script src="{% static 'js/api-client.js' %}"></script>
  <script src="{% static 'js/components.js' %}"></script>
  <script src="{% static 'js/error-handler.js' %}"></script>
  <script src="{% static 'js/websocket-service.js' %}"></script>
</body>
```

### Step 2: Create Context in Your Django View

```python
# estateApp/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Company
import json

@login_required
def company_admin_dashboard(request):
    company = request.user.company
    
    context = {
        'current_company': company,
        'current_company_json': json.dumps({
            'id': company.id,
            'name': company.name
        }),
        'current_user_json': json.dumps({
            'id': request.user.id,
            'email': request.user.email,
            'company_id': company.id
        })
    }
    return render(request, 'admin_side/index.html', context)

@login_required
def client_dashboard(request):
    context = {
        'current_company_json': json.dumps({
            'id': request.user.company_id,
            'name': request.user.company.name
        }),
        'current_user_json': json.dumps({
            'id': request.user.id,
            'email': request.user.email
        })
    }
    return render(request, 'client_side/client_side.html', context)
```

### Step 3: Add to Django URLs

```python
# estateApp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ... existing patterns
    path('tenant-admin/', views.tenant_admin_dashboard, name='tenant_admin'),
    path('admin/', views.company_admin_dashboard, name='company_admin'),
    path('client/', views.client_dashboard, name='client'),
    path('marketer/', views.marketer_dashboard, name='marketer'),
]
```

---

## 📁 File Locations

```
✅ CREATED - estateApp/static/js/
  ├── api-client.js              (560 lines)
  ├── components.js              (420 lines)
  ├── error-handler.js           (150 lines)
  └── websocket-service.js       (260 lines)

✅ CREATED - estateApp/templates/tenant_admin/
  └── dashboard.html             (Ready to use)

📖 DOCUMENTATION - Root Project/
  ├── FRONTEND_ARCHITECTURE.md    (Comprehensive guide)
  ├── PHASE_4_SUMMARY.md          (What was done)
  ├── DASHBOARD_TEMPLATES.md      (Implementation templates)
  └── QUICK_START.md              (This file)

⏳ TO DO - estateApp/templates/
  ├── admin_side/index.html       (Company Admin - See DASHBOARD_TEMPLATES.md)
  ├── client_side/client_side.html (Client - See DASHBOARD_TEMPLATES.md)
  └── marketer_side/marketer_side.html (Marketer - See DASHBOARD_TEMPLATES.md)
```

---

## 💡 Key Concepts

### Multi-Tenant Filtering

**Every dashboard filters by company/tenant:**

```javascript
// ✅ CORRECT - Includes company filter
const users = await api.user_list({ 
  company_id: currentTenant.id,
  page_size: 100 
});

// ❌ WRONG - Missing company filter
const users = await api.user_list({ page_size: 100 });
```

### API Client Usage

```javascript
// Initialize once per dashboard load
api.init(token, tenant, user);

// All API calls automatically include X-Tenant-ID header
const data = await api.company_list();  // Auto-filtered

// Optional parameters
const data = await api.user_list({
  company_id: 123,
  status: 'active',
  page_size: 50,
  ordering: '-created_at'
});
```

### UI Components

```javascript
// Loading
Spinner.showOverlay();
// ... do work ...
Spinner.hideOverlay();

// Notifications
Toast.success('Operation completed');
Toast.error('Something went wrong');

// Forms
const validator = new FormValidator('myForm');
if (validator.validate()) {
  const data = validator.getData();
}

// Formatting
UIHelpers.formatCurrency(1000);        // $1,000.00
UIHelpers.formatDate(new Date());       // Jan 01, 2024
UIHelpers.truncateText(text, 50);       // Truncate to 50 chars
```

### Real-Time Updates

```javascript
// Initialize WebSocket
WebSocketService.init(token, tenant);

// Listen for updates
WebSocketService.on('data_updated', (data) => {
  console.log('Something was updated:', data);
  // Reload affected data
  loadData();
});

// Subscribe to specific channels
WebSocketService.subscribeToCompany(companyId);
WebSocketService.subscribeToUser(userId);
```

---

## 🔍 Implementation Priority

### Phase 5 Order:

1. **Company Admin Dashboard** (Most complex)
   - User management
   - Allocation management
   - Subscription controls
   - ~3 hours

2. **Client Dashboard** (Medium complexity)
   - Allocation viewing
   - Payment history
   - Simple UI
   - ~2 hours

3. **Marketer Dashboard** (Medium complexity)
   - Sales listing
   - Commission calculation
   - Simple UI
   - ~2 hours

---

## ✔️ Implementation Checklist

### Before Starting Each Dashboard:

- [ ] Read the corresponding template in `DASHBOARD_TEMPLATES.md`
- [ ] Identify the unique `company_id`/`user_id` filter
- [ ] Create the HTML file with proper structure
- [ ] Initialize API client in JavaScript
- [ ] Implement data loading functions
- [ ] Add error handling
- [ ] Test with real data

### After Completing:

- [ ] Test multi-tenant isolation (verify cross-tenant access fails)
- [ ] Verify real-time updates work
- [ ] Check mobile responsiveness
- [ ] Test error scenarios
- [ ] Load test with large datasets

---

## 🧪 Testing Multi-Tenant Safety

### Quick Test Script

```javascript
// Run in browser console to test isolation
async function testTenantIsolation() {
  try {
    // Should work
    console.log('Testing own company data...');
    const myData = await api.company_list({ company_id: 1 });
    console.log('✅ Own company data loaded:', myData.count, 'items');

    // Should fail (403 Forbidden)
    console.log('Testing cross-tenant access...');
    const otherData = await api.company_list({ company_id: 999 });
    console.log('❌ SECURITY ISSUE: Should have been blocked!');
  } catch (error) {
    if (error.status === 403) {
      console.log('✅ Cross-tenant access blocked correctly');
    } else {
      console.log('❌ Unexpected error:', error);
    }
  }
}

testTenantIsolation();
```

---

## 🐛 Debugging Tips

### Check Current State

```javascript
// Check API client state
console.log('API State:', {
  token: !!api.token,
  tenant: api.currentTenant,
  user: api.currentUser
});

// Check WebSocket state
console.log('WebSocket Status:', WebSocketService.getStatus());

// Check error history
console.log('Recent Errors:', ErrorHandler.getHistory(5));
```

### Common Issues

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Token expired, re-login or refresh token |
| 403 Forbidden | Missing/wrong company_id filter |
| Data not loading | Check browser console for errors |
| WebSocket not connecting | Verify Django Channels is running |
| CORS error | Add headers to Django CORS settings |

---

## 📞 Support References

### Backend Files to Check

- **Models**: `estateApp/models.py` - Data structure
- **API Views**: `DRF/admin/api_views/` - 65+ endpoints
- **Serializers**: `DRF/admin/serializers/` - Data serialization
- **Auth**: `estateApp/backends.py` - Authentication logic

### Frontend Files to Use

- **API Client**: `estateApp/static/js/api-client.js`
- **Components**: `estateApp/static/js/components.js`
- **Errors**: `estateApp/static/js/error-handler.js`
- **Real-time**: `estateApp/static/js/websocket-service.js`

### Documentation Files

- **Full Guide**: `FRONTEND_ARCHITECTURE.md`
- **Templates**: `DASHBOARD_TEMPLATES.md`
- **Summary**: `PHASE_4_SUMMARY.md`
- **Quick Start**: This file

---

## 🎯 Success Criteria for Phase 5

- [x] Understand multi-tenant architecture
- [x] Know which data each dashboard should access
- [x] Have templates to copy/modify
- [ ] Implement Company Admin Dashboard
- [ ] Implement Client Dashboard
- [ ] Implement Marketer Dashboard
- [ ] Verify data isolation works
- [ ] Test error scenarios
- [ ] Deploy to production

---

## 💾 Next Steps

1. **Review Templates**
   - Read `DASHBOARD_TEMPLATES.md` for each dashboard
   - Understand the filtering pattern

2. **Create Dashboards**
   - Start with Company Admin (most complex)
   - Then Client and Marketer

3. **Test Thoroughly**
   - Use the isolation test script
   - Verify cross-tenant data is blocked
   - Test with multiple users

4. **Deploy**
   - Update Django views and URLs
   - Include JavaScript files in base template
   - Test in production environment

---

## 📊 Project Status

```
Phase 1-3: Backend ✅ (65+ endpoints)
Phase 4: Frontend Infrastructure ✅ (Complete)
  ├── Tenant Admin Dashboard ✅
  ├── API Client ✅
  ├── Components ✅
  ├── Error Handler ✅
  └── WebSocket Service ✅

Phase 5: Remaining Dashboards ⏳
  ├── Company Admin Dashboard
  ├── Client Dashboard
  └── Marketer Dashboard

Phase 6: Testing & Deployment ⏳
  ├── Unit tests
  ├── Integration tests
  ├── E2E tests
  └── Production deployment
```

---

## Questions?

If stuck on any dashboard implementation:
1. Check `DASHBOARD_TEMPLATES.md` for that specific dashboard
2. Review `FRONTEND_ARCHITECTURE.md` for detailed explanations
3. Check `api-client.js` for available API methods
4. Look at browser console for error messages
5. Use `ErrorHandler.export_logs()` to export error logs

Good luck with Phase 5! 🚀
