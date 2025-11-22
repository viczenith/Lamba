# 🔌 COMPLETE API DOCUMENTATION - Multi-Tenant SaaS Platform

## Authentication & Headers

### Required Headers for All Requests

```bash
# Option 1: Token Authentication (Recommended for mobile/apps)
Authorization: Token YOUR_AUTH_TOKEN

# Option 2: API Key Authentication (For programmatic access)
X-API-Key: company_api_key

# Option 3: Session Authentication (Web browsers)
Cookie: sessionid=YOUR_SESSION_ID
```

### Response Headers (Multi-Tenancy)

```
X-Tenant-ID: 1              # Company ID
X-Tenant-Name: Lekki Homes  # Company name
```

---

## 🎯 CLIENT DASHBOARD ENDPOINTS

### 1. Get My Dashboard (Portfolio Overview)

**Endpoint:** `GET /api/dashboards/my-dashboard/`

**Authentication:** Required (Client role)

**Description:** Unified portfolio view aggregating properties from all companies

**Response:**
```json
{
  "id": 1,
  "client": 5,
  "total_properties_owned": 5,
  "total_invested": "15000000.00",
  "portfolio_value": "16500000.00",
  "roi_percentage": 10.0,
  "month_over_month_growth": 2.5,
  "projected_value_1yr": "18150000.00",
  "projected_value_5yr": "24105000.00",
  "preferred_currency": "NGN",
  "notification_preferences": {
    "price_alerts": true,
    "new_properties": true,
    "commission_updates": false
  },
  "properties_by_company": [
    {
      "company_id": 1,
      "company_name": "Lekki Homes",
      "property_count": 3,
      "total_value": "9000000.00"
    },
    {
      "company_id": 2,
      "company_name": "VI Properties",
      "property_count": 2,
      "total_value": "7500000.00"
    }
  ]
}
```

**Example Request:**
```bash
curl -X GET http://localhost:8000/api/dashboards/my-dashboard/ \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### 2. Get My Properties

**Endpoint:** `GET /api/dashboards/my-properties/`

**Query Parameters:**
- `company_id` (optional) - Filter by specific company
- `search` - Search by estate name or plot number
- `ordering` - Order by: `date_allocated`, `value`, `-value`

**Description:** List all properties owned by the client across all companies

**Response:**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 1,
      "plot": {
        "id": 42,
        "plot_number": "A-101",
        "plot_size": "500 sqm",
        "status": "allocated",
        "current_price": "3000000.00",
        "estate": {
          "id": 1,
          "estate_name": "Lekki Phase 1",
          "location": "Lekki, Lagos",
          "company": {
            "id": 1,
            "company_name": "Lekki Homes"
          }
        }
      },
      "date_allocated": "2024-01-15",
      "payment_status": "completed",
      "total_paid": "3000000.00"
    }
  ]
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/dashboards/my-properties/?company_id=1" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### 3. Get Portfolio Summary

**Endpoint:** `GET /api/dashboards/portfolio-summary/`

**Description:** Quick statistics without detailed property list

**Response:**
```json
{
  "total_properties": 5,
  "total_invested": "15000000.00",
  "portfolio_value": "16500000.00",
  "roi_percentage": 10.0,
  "top_company": {
    "id": 1,
    "company_name": "Lekki Homes",
    "property_count": 3
  }
}
```

---

## 🏘️ PROPERTY VIEW & INTEREST TRACKING

### 4. Get All Available Properties (Cross-Company Search)

**Endpoint:** `GET /api/property-views/all-available-properties/`

**Query Parameters:**
- `location` - Filter by location
- `price_min` - Minimum price
- `price_max` - Maximum price
- `search` - Search estate name or plot number
- `page` - Pagination (default 1)

**Description:** Search properties across all companies

**Response:**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/property-views/all-available-properties/?page=2",
  "results": [
    {
      "id": 1,
      "plot": {
        "id": 42,
        "plot_number": "A-101",
        "plot_size": "500 sqm",
        "current_price": "3000000.00",
        "status": "available",
        "estate": {
          "id": 1,
          "estate_name": "Lekki Phase 1",
          "location": "Lekki, Lagos",
          "company": {
            "id": 1,
            "company_name": "Lekki Homes",
            "theme_color": "#003366"
          }
        }
      },
      "view_count": 0,
      "is_interested": false,
      "is_favorited": false,
      "client_notes": ""
    }
  ]
}
```

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/property-views/all-available-properties/?location=Lekki&price_min=2000000&price_max=5000000" \
  -H "Authorization: Token YOUR_TOKEN"
```

---

### 5. Track Property View

**Endpoint:** `POST /api/property-views/track-view/`

**Request Body:**
```json
{
  "plot_id": 42
}
```

**Description:** Record that client viewed a property (for analytics)

**Response:**
```json
{
  "id": 1,
  "plot_id": 42,
  "view_count": 1,
  "first_viewed_at": "2025-01-15T10:30:00Z",
  "last_viewed_at": "2025-01-15T10:30:00Z",
  "message": "View tracked successfully"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/property-views/track-view/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"plot_id": 42}'
```

---

### 6. Toggle Favorite

**Endpoint:** `POST /api/property-views/toggle-favorite/`

**Request Body:**
```json
{
  "plot_id": 42
}
```

**Response:**
```json
{
  "id": 1,
  "plot_id": 42,
  "is_favorited": true,
  "message": "Added to favorites"
}
```

---

### 7. Toggle Interested

**Endpoint:** `POST /api/property-views/toggle-interested/`

**Request Body:**
```json
{
  "plot_id": 42
}
```

**Response:**
```json
{
  "id": 1,
  "plot_id": 42,
  "is_interested": true,
  "message": "Marked as interested"
}
```

---

### 8. Get My Favorites

**Endpoint:** `GET /api/property-views/my-favorites/`

**Description:** List all properties marked as favorites

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "plot": {...},
      "is_favorited": true,
      "view_count": 5
    }
  ]
}
```

---

### 9. Get My Interested Properties

**Endpoint:** `GET /api/property-views/my-interested/`

**Description:** List all properties marked as interested

**Response:**
```json
{
  "count": 7,
  "results": [...]
}
```

---

### 10. Add Property Note

**Endpoint:** `POST /api/property-views/add-note/`

**Request Body:**
```json
{
  "plot_id": 42,
  "client_notes": "Good location, close to school. Need to negotiate price."
}
```

**Response:**
```json
{
  "id": 1,
  "plot_id": 42,
  "client_notes": "Good location, close to school. Need to negotiate price.",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

---

## 🤝 MARKETER AFFILIATION MANAGEMENT

### 11. Request Company Affiliation

**Endpoint:** `POST /api/affiliations/`

**Request Body:**
```json
{
  "company": 1,
  "commission_tier": "bronze"
}
```

**Description:** Marketer requests to affiliate with a company

**Response:**
```json
{
  "id": 1,
  "marketer": 10,
  "company": 1,
  "commission_tier": "bronze",
  "commission_rate": 2.0,
  "status": "pending_approval",
  "created_at": "2025-01-15T10:30:00Z",
  "message": "Affiliation request submitted. Awaiting company approval."
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/affiliations/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": 1,
    "commission_tier": "bronze"
  }'
```

---

### 12. Get My Affiliations

**Endpoint:** `GET /api/affiliations/my-affiliations/`

**Description:** Marketer views all their affiliations with different companies

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "company": {
        "id": 1,
        "company_name": "Lekki Homes"
      },
      "commission_tier": "bronze",
      "commission_rate": 2.0,
      "status": "active",
      "properties_sold": 5,
      "total_commissions_earned": "300000.00",
      "total_commissions_paid": "280000.00",
      "pending_commissions": "20000.00"
    }
  ]
}
```

---

### 13. Get Active Affiliations

**Endpoint:** `GET /api/affiliations/active-affiliations/`

**Description:** Marketer views only approved, active affiliations

**Response:** Same as "Get My Affiliations" but filtered to active only

---

### 14. Get Performance Metrics

**Endpoint:** `GET /api/affiliations/performance-metrics/`

**Description:** Aggregated performance across all affiliations

**Response:**
```json
{
  "total_affiliations": 3,
  "total_properties_sold": 12,
  "total_commissions_earned": "540000.00",
  "total_commissions_paid": "500000.00",
  "pending_commissions": "40000.00",
  "average_commission_rate": 3.17,
  "by_company": [
    {
      "company_id": 1,
      "company_name": "Lekki Homes",
      "status": "active",
      "properties_sold": 5,
      "commissions_earned": "300000.00",
      "commission_rate": 2.0
    },
    {
      "company_id": 2,
      "company_name": "VI Properties",
      "status": "active",
      "properties_sold": 7,
      "commissions_earned": "240000.00",
      "commission_rate": 3.5
    }
  ]
}
```

---

## 💰 COMMISSION MANAGEMENT (Admin/Company Endpoints)

### 15. Get Pending Commissions (Admin)

**Endpoint:** `GET /api/commissions/pending/`

**Permission:** Company Admin only

**Query Parameters:**
- `affiliation_id` (optional) - Filter by marketer affiliation
- `company_id` (optional) - Filter by company (auto-filled for non-superusers)

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "affiliation": {
        "id": 1,
        "marketer": {
          "id": 10,
          "user": {
            "first_name": "John",
            "last_name": "Doe"
          }
        },
        "company": {
          "id": 1,
          "company_name": "Lekki Homes"
        }
      },
      "plot_allocation": 42,
      "sale_amount": "3000000.00",
      "commission_rate": 2.0,
      "commission_amount": "60000.00",
      "status": "pending",
      "created_at": "2025-01-14T10:30:00Z"
    }
  ]
}
```

---

### 16. Approve Single Commission

**Endpoint:** `POST /api/commissions/{id}/approve/`

**Permission:** Company Admin

**Response:**
```json
{
  "id": 1,
  "status": "approved",
  "message": "Commission approved",
  "commission_amount": "60000.00"
}
```

---

### 17. Bulk Approve Commissions

**Endpoint:** `POST /api/commissions/approve-bulk/`

**Permission:** Company Admin

**Request Body:**
```json
{
  "commission_ids": [1, 2, 3, 4, 5]
}
```

**Response:**
```json
{
  "approved_count": 5,
  "total_amount": "300000.00",
  "message": "5 commissions approved",
  "commissions": [
    {
      "id": 1,
      "status": "approved",
      "commission_amount": "60000.00"
    }
  ]
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/commissions/approve-bulk/ \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "commission_ids": [1, 2, 3, 4, 5]
  }'
```

---

### 18. Mark Commission as Paid

**Endpoint:** `POST /api/commissions/{id}/mark-paid/`

**Permission:** Company Admin

**Request Body:**
```json
{
  "payment_reference": "TRANSFER-001-2025-01-15"
}
```

**Response:**
```json
{
  "id": 1,
  "status": "paid",
  "payment_reference": "TRANSFER-001-2025-01-15",
  "message": "Commission marked as paid"
}
```

---

### 19. Dispute Commission

**Endpoint:** `POST /api/commissions/{id}/dispute/`

**Permission:** Company Admin or Marketer

**Request Body:**
```json
{
  "dispute_reason": "Plot not actually allocated to marketer"
}
```

**Response:**
```json
{
  "id": 1,
  "status": "disputed",
  "dispute_reason": "Plot not actually allocated to marketer",
  "disputed_at": "2025-01-15T10:30:00Z",
  "message": "Commission disputed"
}
```

---

### 20. Get Commission Summary

**Endpoint:** `GET /api/commissions/summary/`

**Permission:** Company Admin or Marketer (for their own)

**Response:**
```json
{
  "pending": {
    "count": 3,
    "total_amount": "180000.00"
  },
  "approved": {
    "count": 2,
    "total_amount": "120000.00"
  },
  "paid": {
    "count": 10,
    "total_amount": "600000.00"
  },
  "disputed": {
    "count": 1,
    "total_amount": "60000.00"
  },
  "total_commissions": "960000.00",
  "status_breakdown": {
    "pending": 15,
    "approved": 10,
    "paid": 75,
    "disputed": 1
  }
}
```

---

## 🏢 COMPANY ADMIN ENDPOINTS (Pending Approvals)

### 21. Get Pending Marketer Approvals

**Endpoint:** `GET /api/affiliations/pending-approvals/`

**Permission:** Company Admin only

**Response:**
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "marketer": {
        "id": 10,
        "user": {
          "id": 5,
          "first_name": "John",
          "last_name": "Doe",
          "email": "john@example.com"
        }
      },
      "company": 1,
      "commission_tier": "bronze",
      "commission_rate": 2.0,
      "status": "pending_approval",
      "requested_at": "2025-01-15T08:00:00Z"
    }
  ]
}
```

---

### 22. Approve Marketer Affiliation

**Endpoint:** `POST /api/affiliations/{id}/approve/`

**Permission:** Company Admin

**Response:**
```json
{
  "id": 1,
  "status": "active",
  "message": "Affiliation approved. Marketer is now active.",
  "marketer_name": "John Doe",
  "commission_rate": 2.0
}
```

---

### 23. Reject Marketer Affiliation

**Endpoint:** `POST /api/affiliations/{id}/reject/`

**Permission:** Company Admin

**Request Body:**
```json
{
  "reason": "Marketer not verified"
}
```

**Response:**
```json
{
  "id": 1,
  "status": "rejected",
  "message": "Affiliation rejected"
}
```

---

### 24. Suspend Marketer Affiliation

**Endpoint:** `POST /api/affiliations/{id}/suspend/`

**Permission:** Company Admin

**Request Body:**
```json
{
  "reason": "Inactive for 30 days"
}
```

**Response:**
```json
{
  "id": 1,
  "status": "suspended",
  "message": "Affiliation suspended"
}
```

---

### 25. Reactivate Marketer Affiliation

**Endpoint:** `POST /api/affiliations/{id}/activate/`

**Permission:** Company Admin

**Response:**
```json
{
  "id": 1,
  "status": "active",
  "message": "Affiliation reactivated"
}
```

---

## 🧪 TESTING ENDPOINTS

### Quick Test Commands

**1. Get Dashboard:**
```bash
curl -X GET http://localhost:8000/api/dashboards/my-dashboard/ \
  -H "Authorization: Token YOUR_CLIENT_TOKEN"
```

**2. Search Properties:**
```bash
curl -X GET "http://localhost:8000/api/property-views/all-available-properties/?location=Lekki" \
  -H "Authorization: Token YOUR_CLIENT_TOKEN"
```

**3. Request Affiliation:**
```bash
curl -X POST http://localhost:8000/api/affiliations/ \
  -H "Authorization: Token YOUR_MARKETER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company": 1,
    "commission_tier": "bronze"
  }'
```

**4. View Pending Commissions (Admin):**
```bash
curl -X GET http://localhost:8000/api/commissions/pending/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN"
```

**5. Approve Multiple Commissions:**
```bash
curl -X POST http://localhost:8000/api/commissions/approve-bulk/ \
  -H "Authorization: Token YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "commission_ids": [1, 2, 3, 4, 5]
  }'
```

---

## 📊 POSTMAN COLLECTION

Import this into Postman for easier API testing:

```json
{
  "info": {
    "name": "Real Estate SaaS API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Client Dashboard",
      "item": [
        {
          "name": "Get My Dashboard",
          "request": {
            "method": "GET",
            "url": "{{base_url}}/api/dashboards/my-dashboard/"
          }
        },
        {
          "name": "Get My Properties",
          "request": {
            "method": "GET",
            "url": "{{base_url}}/api/dashboards/my-properties/"
          }
        }
      ]
    }
  ]
}
```

---

## ⚠️ ERROR RESPONSES

### Authentication Error (401)
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Permission Denied (403)
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### Not Found (404)
```json
{
  "detail": "Not found."
}
```

### Validation Error (400)
```json
{
  "field_name": ["This field is required."]
}
```

---

## 🔐 MULTI-TENANCY SECURITY

All endpoints respect multi-tenancy through:

1. **Automatic Tenant Isolation** - Middleware extracts company from:
   - API key in header
   - Custom domain
   - Authenticated user's company

2. **Row-Level Security** - QuerySets filtered by company context

3. **Cross-Tenant Validation** - Clients/Marketers can search cross-company

4. **Admin Isolation** - Admins see only their company's data

---

## ✅ PRODUCTION CHECKLIST

- [ ] Enable HTTPS on all endpoints
- [ ] Rate limiting per API key
- [ ] Request logging for audit trail
- [ ] Cache frequently accessed endpoints
- [ ] Monitor API response times
- [ ] Set up error tracking (Sentry)
- [ ] Configure CORS properly
- [ ] Use environment variables for sensitive config
- [ ] Implement request signing for webhooks
- [ ] Set up API documentation auto-generation

