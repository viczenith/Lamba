# Multi-Tenant Frontend Architecture Documentation

## Overview

This document describes the frontend architecture for a multi-tenant real estate management system. The system consists of 4 distinct dashboard roles, each with tenant-specific data isolation:

1. **Tenant Admin Dashboard** - Super-admin managing ALL companies
2. **Company Admin Dashboard** - Company-specific management (admin_side)
3. **Client Dashboard** - Client-specific allocations/transactions (client_side)
4. **Marketer Dashboard** - Marketer-specific sales/commissions (marketer_side)

## Architecture Principles

### 1. Multi-Tenant Isolation

Every dashboard operates within a tenant context. Data is isolated at multiple levels:

- **Backend**: API endpoints auto-filter by current user's company/tenant
- **Frontend**: Dashboards only query data for their assigned tenant
- **Authentication**: JWT token includes tenant context
- **URLs**: Can optionally include tenant identifier (e.g., `/tenant/acme/dashboard/`)

### 2. Role-Based Access Control

Each role has specific permissions and dashboard views:

| Role | Tenant Context | Data Visibility | Dashboard |
|------|---|---|---|
| Super Admin | System-wide | ALL companies | Tenant Admin |
| Company Admin | Single company | Only their company | Company Admin |
| Client | Single user | Own allocations only | Client |
| Marketer | Single user | Own sales only | Marketer |

### 3. API Client with Tenant Awareness

The API client (`api-client.js`) automatically includes tenant context in all requests:

```javascript
// Automatically includes tenant context
const companies = await api.company_list();

// Or pass explicit tenant filter
const companies = await api.company_list({ 
  company_id: currentTenant.id 
});
```

## File Structure

```
estateApp/
├── static/
│   └── js/
│       ├── api-client.js          # Multi-tenant API client
│       ├── components.js           # Reusable UI components
│       ├── error-handler.js        # Global error handling
│       └── websocket-service.js    # Real-time updates
│
└── templates/
    ├── tenant_admin/
    │   └── dashboard.html          # NEW: Super-admin dashboard
    │
    ├── admin_side/
    │   └── index.html              # Company admin dashboard (tenant-specific)
    │
    ├── client_side/
    │   └── client_side.html        # Client dashboard (user-specific)
    │
    └── marketer_side/
        └── marketer_side.html      # Marketer dashboard (user-specific)
```

## JavaScript Modules

### 1. API Client (`api-client.js`)

**Purpose**: Handles all API communication with automatic tenant context

**Key Methods**:

```javascript
// Initialization
api.init(token, tenant, user);
api.setToken(token);
api.setTenant(tenant);
api.setUser(user);

// Authentication
api.login(email, password);
api.logout();
api.refresh_token(refresh);

// Company Management
api.company_list(params);
api.company_create(data);
api.company_update(id, data);
api.company_delete(id);
api.company_stats(id);
api.company_users(id);

// Users
api.user_list(params);
api.user_create(data);
api.user_update(id, data);

// Estates & Properties
api.estate_list(params);
api.estate_create(data);
api.property_list(params);
api.property_create(data);

// Allocations
api.allocation_list(params);
api.allocation_create(data);
api.allocation_approve(id);
api.allocation_reject(id, reason);

// Payments & Transactions
api.payment_list(params);
api.payment_verify(id, ref);
api.transaction_list(params);
api.transaction_export(format, params);

// Bulk Operations
api.bulk_import(file, type);
api.bulk_export(type, params);
```

**Tenant Context Handling**:

```javascript
// Tenant context is automatically included in all requests
// via the X-Tenant-ID header
const headers = {
  'Authorization': `Bearer ${token}`,
  'X-Tenant-ID': currentTenant.id  // Auto-included
};
```

### 2. Components (`components.js`)

**Reusable UI Components**:

#### Spinner
```javascript
Spinner.showOverlay();    // Show loading overlay
Spinner.hideOverlay();    // Hide loading overlay
Spinner.show(element);    // Show spinner in element
```

#### Toast Notifications
```javascript
Toast.success('Action completed');
Toast.error('Something went wrong');
Toast.warning('Warning message');
Toast.info('Information');
```

#### Modal Helper
```javascript
Modal.show('modalId');
Modal.hide('modalId');
Modal.confirm('Title', 'Message', 'Confirm', 'Cancel');
```

#### Form Validator
```javascript
const validator = new FormValidator('formId');
if (validator.validate()) {
  const data = validator.getData();
  await api.create(data);
} else {
  validator.showErrors();
}
```

#### UI Helpers
```javascript
UIHelpers.formatCurrency(1000);        // $1,000.00
UIHelpers.formatDate(date);             // Jan 01, 2024
UIHelpers.formatDateTime(date);         // Jan 01, 2024 03:45 PM
UIHelpers.formatPhoneNumber(phone);     // (XXX) XXX-XXXX
UIHelpers.truncateText(text, 50);       // Truncate to 50 chars
UIHelpers.getBadgeClass(status);        // Get badge color
UIHelpers.getStatusIcon(status);        // Get icon name
UIHelpers.debounce(func, 300);          // Debounce function
UIHelpers.throttle(func, 1000);         // Throttle function
```

### 3. Error Handler (`error-handler.js`)

**Purpose**: Centralized error management

```javascript
// Handle different error types
ErrorHandler.handleAPIError(error);
ErrorHandler.handleValidationError(errors, formValidator);
ErrorHandler.handleNetworkError(error);
ErrorHandler.handleError(error, context);

// Error history
ErrorHandler.getHistory(10);
ErrorHandler.clear();
ErrorHandler.export_logs();
```

### 4. WebSocket Service (`websocket-service.js`)

**Purpose**: Real-time updates within tenant context

```javascript
// Initialize
WebSocketService.init(token, tenant);

// Event Listeners
WebSocketService.on('connected', callback);
WebSocketService.on('authenticated', callback);
WebSocketService.on('disconnected', callback);
WebSocketService.on('data_updated', callback);
WebSocketService.on('data_created', callback);
WebSocketService.on('data_deleted', callback);

// Subscribe to specific channels
WebSocketService.subscribeToCompany(companyId);
WebSocketService.subscribeToUser(userId);
WebSocketService.subscribeToAllocation(allocationId);
WebSocketService.subscribeToPayment(paymentId);

// Status
const status = WebSocketService.getStatus();
// { connected: true, authenticated: true, reconnectAttempts: 0 }
```

## Dashboard Implementation Guide

### Tenant Admin Dashboard

**Location**: `estateApp/templates/tenant_admin/dashboard.html`

**Purpose**: Super-admin view managing all companies and system-wide activities

**Key Features**:
- View all companies
- System-wide statistics
- User management across all tenants
- Transaction monitoring
- Add/Edit/Delete companies

**Data Access**: NO tenant filter - sees all data

**Example Implementation**:

```javascript
// Load ALL companies (no tenant filter)
async function loadCompanies() {
  const companies = await api.company_list({ page_size: 100 });
  // Renders all companies
}

// Load system-wide statistics
async function loadSystemStats() {
  const [companies, users, allocations, transactions] = await Promise.all([
    api.company_list({ page_size: 1 }),
    api.user_list({ page_size: 1 }),
    api.allocation_list({ page_size: 1 }),
    api.transaction_list({ page_size: 1 })
  ]);
  // Shows global statistics
}
```

### Company Admin Dashboard

**Location**: `estateApp/templates/admin_side/index.html`

**Purpose**: Company-specific management dashboard

**Key Features**:
- View company-specific users
- Manage allocations within company
- View company transactions
- Subscription management
- Company settings

**Data Access**: FILTERED by `company_id = current_user.company_id`

**Example Implementation**:

```javascript
// Load company-specific users
async function loadUsers() {
  const users = await api.user_list({ 
    company_id: currentTenant.id,  // Filter by current company
    page_size: 100 
  });
  // Renders only this company's users
}

// Load company allocations
async function loadAllocations() {
  const allocations = await api.allocation_list({ 
    company_id: currentTenant.id,  // Filter by current company
    page_size: 100 
  });
  // Renders only this company's allocations
}
```

### Client Dashboard

**Location**: `estateApp/templates/client_side/client_side.html`

**Purpose**: Client's personal dashboard

**Key Features**:
- View personal allocations
- Payment history
- Subscription details
- Download receipts
- Update profile

**Data Access**: FILTERED by `user_id = current_user.id AND company_id = current_user.company_id`

**Example Implementation**:

```javascript
// Load client's allocations only
async function loadMyAllocations() {
  const allocations = await api.allocation_list({ 
    user_id: currentUser.id,           // Filter by current user
    company_id: currentTenant.id,      // Filter by company
    page_size: 100 
  });
  // Renders only this client's allocations
}

// Load client's transactions
async function loadMyTransactions() {
  const transactions = await api.transaction_list({ 
    user_id: currentUser.id,
    company_id: currentTenant.id,
    page_size: 50 
  });
  // Renders only this client's transactions
}
```

### Marketer Dashboard

**Location**: `estateApp/templates/marketer_side/marketer_side.html`

**Purpose**: Marketer's sales and performance dashboard

**Key Features**:
- Sales statistics
- Commission tracking
- Client list within company
- Performance metrics
- Report generation

**Data Access**: FILTERED by `marketer_id = current_user.id AND company_id = current_user.company_id`

**Example Implementation**:

```javascript
// Load marketer's sales
async function loadMySales() {
  const allocations = await api.allocation_list({ 
    marketer_id: currentUser.id,       // Filter by current marketer
    company_id: currentTenant.id,      // Filter by company
    page_size: 100 
  });
  // Renders only this marketer's sales
}

// Load marketer's commission summary
async function loadCommissionSummary() {
  const payments = await api.payment_list({ 
    marketer_id: currentUser.id,
    company_id: currentTenant.id
  });
  // Calculates commission from sales
}
```

## Implementation Checklist

### Frontend Files Created ✅

- [x] `api-client.js` - Multi-tenant API client (560 lines)
- [x] `components.js` - Reusable UI components (420 lines)
- [x] `error-handler.js` - Global error handling (150 lines)
- [x] `websocket-service.js` - Real-time updates (260 lines)
- [x] `tenant_admin/dashboard.html` - Super-admin dashboard

### Dashboards To Implement

- [ ] `admin_side/index.html` - Company admin dashboard
- [ ] `client_side/client_side.html` - Client dashboard
- [ ] `marketer_side/marketer_side.html` - Marketer dashboard

### Backend API Verification Needed

The following need to be verified in backend:

1. **Tenant Filtering**: All endpoints auto-filter by current user's tenant
2. **Auth Middleware**: JWT includes tenant context
3. **Query Parameters**: Accept `company_id`, `user_id`, `marketer_id` filters
4. **WebSocket Authentication**: Supports tenant context in WS headers

## Usage Example

### Initialize Dashboard

```html
<!-- In your template base.html -->
<script src="{% static 'js/api-client.js' %}"></script>
<script src="{% static 'js/components.js' %}"></script>
<script src="{% static 'js/error-handler.js' %}"></script>
<script src="{% static 'js/websocket-service.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', async () => {
  // Get token from storage or context
  const token = localStorage.getItem('auth_token') || '{{ request.user.token }}';
  
  // Get current tenant and user from context
  const tenant = {{ current_tenant_json|safe }};
  const user = {{ current_user_json|safe }};

  // Initialize API client
  api.init(token, tenant, user);

  // Initialize WebSocket for real-time updates
  WebSocketService.init(token, tenant);

  // Listen for data updates
  WebSocketService.on('data_updated', (data) => {
    console.log('Data updated:', data);
    // Reload affected data
  });

  // Load dashboard data
  try {
    Spinner.showOverlay();
    
    // Your dashboard initialization code here
    await loadDashboardData();
    
    Spinner.hideOverlay();
  } catch (error) {
    Spinner.hideOverlay();
    ErrorHandler.handleError(error);
  }
});
</script>
```

## Security Considerations

1. **Token Management**
   - Store JWT securely (localStorage or sessionStorage)
   - Clear token on logout
   - Refresh token before expiry

2. **Tenant Context**
   - Verify tenant_id on backend for every request
   - Don't trust client-side tenant context alone
   - Use server-side session to enforce tenant isolation

3. **Data Validation**
   - Validate all form input on frontend
   - Always validate on backend
   - Use CSRF tokens for state-changing requests

4. **Error Handling**
   - Never expose sensitive data in error messages
   - Log errors for debugging (export available)
   - Show user-friendly error messages

## Performance Optimization

### Caching Strategy

```javascript
// Cache company data for 5 minutes
const cache = {
  companies: { data: null, timestamp: null },
  users: { data: null, timestamp: null }
};

const getCachedCompanies = async (force = false) => {
  const now = Date.now();
  const cacheAge = now - (cache.companies.timestamp || 0);

  if (!force && cache.companies.data && cacheAge < 5 * 60 * 1000) {
    return cache.companies.data;
  }

  const data = await api.company_list();
  cache.companies = { data, timestamp: now };
  return data;
};
```

### Lazy Loading

```javascript
// Load only visible table rows
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      loadRow(entry.target);
    }
  });
});

document.querySelectorAll('[data-lazy]').forEach(el => {
  observer.observe(el);
});
```

## Next Steps

1. **Implement Company Admin Dashboard**
   - Create user management interface
   - Implement allocation management
   - Add subscription controls

2. **Implement Client Dashboard**
   - Create allocation view
   - Add payment tracking
   - Implement receipt download

3. **Implement Marketer Dashboard**
   - Create sales dashboard
   - Add commission calculator
   - Implement performance charts

4. **Testing**
   - Unit tests for API client
   - Integration tests for dashboards
   - E2E tests for multi-tenant isolation

5. **Monitoring**
   - Error tracking (Sentry)
   - Performance monitoring
   - User analytics
