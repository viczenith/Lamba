# Admin API README

## Structure

```
DRF/admin/
├── __init__.py
├── api_views/
│   ├── __init__.py
│   ├── auth_views.py          # Authentication, Company, User Management ViewSets
│   ├── property_views.py       # Estate, Property, Allocation ViewSets
│   └── subscription_views.py   # Subscription, Payment, Transaction ViewSets
└── serializers/
    └── __init__.py             # (optional for custom serializers)
```

## ViewSets Included

### Authentication (auth_views.py)
- **AuthenticationViewSet**: Register, Login, Logout endpoints
- **CompanyViewSet**: Company CRUD, subscription management
- **UserManagementViewSet**: User CRUD, permissions, password management

### Property Management (property_views.py)
- **EstateViewSet**: Estate CRUD, statistics, allocations
- **PropertyViewSet**: Property/plot management, bulk price updates
- **PropertyAllocationViewSet**: Allocation CRUD, payment tracking, bulk allocate

### Subscriptions & Payments (subscription_views.py)
- **SubscriptionViewSet**: Current, upgrade, downgrade, cancel, billing history
- **PaymentViewSet**: Process payment, Stripe webhooks
- **TransactionViewSet**: List, statistics, export

## Routing

All ViewSets are registered in `DRF/urls.py` using a DefaultRouter:

```python
router.register(r'auth', AuthenticationViewSet, basename='auth')
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'users', UserManagementViewSet, basename='user')
router.register(r'estates', EstateViewSet, basename='estate')
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'allocations', PropertyAllocationViewSet, basename='allocation')
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'transactions', TransactionViewSet, basename='transaction')
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register company
- `POST /api/auth/login/` - Login user
- `POST /api/auth/logout/` - Logout user

### Companies
- `GET /api/companies/` - List companies
- `GET /api/companies/{id}/` - Retrieve company
- `POST /api/companies/{id}/upgrade_subscription/` - Upgrade subscription
- `GET /api/companies/{id}/check_api_limit/` - Check API usage

### Users
- `GET /api/users/` - List users
- `POST /api/users/` - Create user
- `POST /api/users/{id}/change_password/` - Change password
- `POST /api/users/{id}/toggle_status/` - Activate/deactivate user

### Estates
- `GET /api/estates/` - List estates
- `POST /api/estates/` - Create estate
- `GET /api/estates/{id}/` - Retrieve estate
- `GET /api/estates/{id}/statistics/` - Get statistics
- `GET /api/estates/{id}/allocations/` - Get allocations

### Properties
- `GET /api/properties/` - List properties
- `POST /api/properties/` - Create property
- `POST /api/properties/{id}/bulk_price_update/` - Bulk update prices

### Allocations
- `GET /api/allocations/` - List allocations
- `POST /api/allocations/` - Create allocation
- `POST /api/allocations/{id}/record_payment/` - Record payment
- `GET /api/allocations/{id}/payment_history/` - Get payment history
- `POST /api/allocations/bulk_allocate/` - Bulk allocate

### Subscriptions
- `GET /api/subscriptions/current/` - Get current subscription
- `POST /api/subscriptions/upgrade/` - Upgrade tier
- `POST /api/subscriptions/downgrade/` - Downgrade tier
- `POST /api/subscriptions/cancel/` - Cancel subscription
- `GET /api/subscriptions/billing_history/` - Get billing history

### Payments
- `POST /api/payments/process/` - Process payment
- `POST /api/payments/webhook/` - Stripe webhook handler

### Transactions
- `GET /api/transactions/` - List transactions
- `GET /api/transactions/statistics/` - Get statistics
- `GET /api/transactions/export/` - Export as CSV

## Security Features

All ViewSets include:
- ✅ Authentication requirement
- ✅ Permission classes
- ✅ Rate limiting by subscription tier
- ✅ Audit logging
- ✅ Error tracking with Sentry
- ✅ Multi-tenant isolation
- ✅ Full CRUD with audit trails

## Integration

Import in `DRF/urls.py`:

```python
from DRF.admin.api_views.auth_views import (
    AuthenticationViewSet, CompanyViewSet, UserManagementViewSet
)
from DRF.admin.api_views.property_views import (
    EstateViewSet, PropertyViewSet, PropertyAllocationViewSet
)
from DRF.admin.api_views.subscription_views import (
    SubscriptionViewSet, PaymentViewSet, TransactionViewSet
)
```

## Similar Structure

This follows the same organization pattern as:
- `DRF/clients/api_views/` - Client-facing endpoints
- `DRF/marketers/api_views/` - Marketer-facing endpoints
