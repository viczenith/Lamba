# Multi-Tenant Features Implementation - Complete Documentation

## 🎯 Overview

This document provides comprehensive documentation for the three major features implemented:

1. **Public Signup for Clients and Marketers**
2. **Cross-Company Property Portfolio Tracking for Clients**
3. **Marketer Affiliation Request System**

## ✅ Features Implemented

### 1. Public Signup for Clients and Marketers

#### Description
Clients and marketers can now register directly from the login page without needing a company to create their account. They become "independent users" who can later:
- **Clients**: Purchase properties from any company
- **Marketers**: Request affiliation with any company to earn commissions

#### Implementation Details

**Signup Flow:**
1. User visits login page
2. Clicks "Sign Up" button
3. Fills registration form (name, email, phone, DOB, role, password)
4. System creates user with `company_profile = NULL`
5. User receives welcome email with role-specific instructions
6. User can login and access their dashboard

**Database Changes:**
- No schema changes needed
- `company_profile` field is explicitly set to `NULL` for independent users
- `ClientDashboard` is automatically created for new clients

**API Endpoints:**
- `POST /register-user/` - User registration endpoint

**Code Files:**
- `estateApp/views.py` - `individual_user_registration()` function (enhanced)
- `estateApp/templates/login.html` - Signup modal form

---

### 2. Cross-Company Property Portfolio Tracking

#### Description
Clients can now view ALL properties they have purchased across multiple companies in one unified dashboard. Properties are grouped by company with detailed information for each property.

#### Key Features

**Portfolio Overview:**
- Total properties owned across all companies
- Total amount invested
- Portfolio value and ROI
- Number of companies purchased from

**Company-Grouped View:**
- Properties organized by company
- Company details (name, logo, contact)
- Per-company investment totals
- Expandable sections for each company

**Property Details:**
- Estate information
- Plot number and size
- Payment details (full/part payment)
- Transaction history
- Assigned marketer information
- Property images

#### API Endpoints

##### 1. Portfolio Overview
```http
GET /api/client/portfolio/overview/
```

**Authentication:** Required (Client only)

**Response:**
```json
{
  "overview": {
    "total_properties": 5,
    "total_invested": "15000000.00",
    "portfolio_value": "16500000.00",
    "roi_percentage": "10.00",
    "companies_count": 2
  },
  "companies": [
    {
      "company_id": 1,
      "company_name": "ABC Real Estate",
      "company_logo": "https://example.com/media/logo.png",
      "properties_count": 3,
      "total_invested": "9000000.00",
      "properties": [
        {
          "allocation_id": 1,
          "estate_name": "Lekki Gardens",
          "estate_id": 1,
          "plot_number": "A-101",
          "plot_size": "600 SQM",
          "amount_paid": "3000000.00",
          "payment_type": "full",
          "allocation_date": "2024-01-15T10:30:00Z",
          "marketer": "John Doe",
          "status": "allocated",
          "plot_image": "https://example.com/media/plot.jpg"
        }
      ]
    }
  ]
}
```

##### 2. Companies List
```http
GET /api/client/companies/
```

**Response:**
```json
{
  "companies": [
    {
      "id": 1,
      "name": "ABC Real Estate",
      "logo": "https://example.com/media/logo.png",
      "email": "info@abc.com",
      "phone": "+2348012345678",
      "location": "Lagos",
      "properties_count": 3,
      "total_invested": "9000000.00"
    }
  ],
  "total_companies": 1
}
```

##### 3. Company-Specific Properties
```http
GET /api/client/companies/{company_id}/properties/
```

**Response:**
```json
{
  "company": {
    "id": 1,
    "name": "ABC Real Estate",
    "logo": "https://example.com/media/logo.png",
    "email": "info@abc.com",
    "phone": "+2348012345678",
    "location": "Lagos"
  },
  "properties": [
    {
      "allocation_id": 1,
      "estate": {
        "id": 1,
        "name": "Lekki Gardens",
        "location": "Lekki, Lagos",
        "image": "https://example.com/media/estate.jpg"
      },
      "plot_number": "A-101",
      "plot_size": {
        "size": "600",
        "unit": "SQM"
      },
      "amount_paid": "3000000.00",
      "payment_type": "Full Payment",
      "allocation_date": "2024-01-15T10:30:00Z",
      "marketer": {
        "id": 5,
        "name": "John Doe",
        "phone": "+2348012345678"
      },
      "status": "allocated",
      "transactions": [
        {
          "id": 1,
          "transaction_date": "2024-01-15T10:30:00Z",
          "amount": "3000000.00",
          "payment_type": "full",
          "status": "Fully Paid"
        }
      ],
      "transactions_count": 1
    }
  ],
  "total_properties": 1,
  "total_invested": "3000000.00"
}
```

##### 4. All Properties (Flat List)
```http
GET /api/client/all-properties/
```

**Response:**
```json
{
  "properties": [
    {
      "allocation_id": 1,
      "company": {
        "id": 1,
        "name": "ABC Real Estate",
        "logo": "https://example.com/media/logo.png"
      },
      "estate": {
        "id": 1,
        "name": "Lekki Gardens",
        "location": "Lekki, Lagos",
        "image": "https://example.com/media/estate.jpg"
      },
      "plot_number": "A-101",
      "plot_size": "600 SQM",
      "amount_paid": "3000000.00",
      "payment_type": "Full Payment",
      "allocation_date": "2024-01-15T10:30:00Z",
      "marketer": "John Doe",
      "status": "allocated"
    }
  ],
  "total_properties": 1,
  "total_invested": "3000000.00"
}
```

#### Code Files
- `DRF/clients/api_views/client_portfolio_views.py` - All portfolio APIs
- Models used: `PlotAllocation`, `ClientDashboard`, `Company`, `Transaction`

---

### 3. Marketer Affiliation Request System

#### Description
Marketers can request affiliation with any company on the platform. Company admins can approve or reject these requests. Once approved, marketers can earn commissions on property sales.

#### Key Features

**For Marketers:**
- Browse all available companies
- Request affiliation with any company
- Track affiliation status (pending, active, rejected)
- View all affiliated companies
- See commission rates and earnings per company
- Cancel pending requests

**For Company Admins:**
- View all pending affiliation requests
- Approve requests (set commission tier)
- Reject requests with notification
- View all active affiliate marketers
- Track marketer performance and commissions

#### Affiliation Statuses
- `pending_approval` - Request submitted, awaiting review
- `active` - Approved, marketer can sell properties
- `suspended` - Temporarily suspended by company
- `terminated` - Permanently ended

#### Commission Tiers
- **Bronze** - 2% commission
- **Silver** - 3.5% commission
- **Gold** - 5% commission
- **Platinum** - 7%+ commission

#### API Endpoints

### Marketer Endpoints

##### 1. Available Companies
```http
GET /api/marketer/available-companies/
```

**Authentication:** Required (Marketer only)

**Response:**
```json
{
  "companies": [
    {
      "id": 1,
      "name": "ABC Real Estate",
      "logo": "https://example.com/media/logo.png",
      "email": "info@abc.com",
      "phone": "+2348012345678",
      "location": "Lagos",
      "office_address": "123 Main Street, Lagos",
      "marketers_count": 15
    }
  ],
  "total_companies": 1
}
```

##### 2. Request Affiliation
```http
POST /api/marketer/request-affiliation/
```

**Request Body:**
```json
{
  "company_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "Affiliation request sent to ABC Real Estate. You will be notified once they review your request.",
  "affiliation": {
    "id": 1,
    "company_name": "ABC Real Estate",
    "status": "pending_approval",
    "date_requested": "2024-11-20T10:30:00Z"
  }
}
```

##### 3. View All Affiliations
```http
GET /api/marketer/affiliations/
```

**Response:**
```json
{
  "affiliations": [
    {
      "id": 1,
      "company": {
        "id": 1,
        "name": "ABC Real Estate",
        "logo": "https://example.com/media/logo.png",
        "email": "info@abc.com",
        "phone": "+2348012345678"
      },
      "status": "active",
      "status_display": "Active",
      "commission_tier": "Silver - 3.5%",
      "commission_rate": "3.50",
      "properties_sold": 5,
      "total_commissions_earned": "525000.00",
      "total_commissions_paid": "300000.00",
      "pending_commissions": "225000.00",
      "total_sales_value": "15000000.00",
      "date_affiliated": "2024-01-15T10:30:00Z",
      "approval_date": "2024-01-16T14:20:00Z"
    }
  ],
  "summary": {
    "total": 2,
    "active": 1,
    "pending": 1,
    "suspended": 0,
    "terminated": 0
  },
  "grouped": {
    "active": [...],
    "pending": [...],
    "suspended": [],
    "terminated": []
  }
}
```

##### 4. Cancel Pending Request
```http
DELETE /api/marketer/affiliations/{affiliation_id}/cancel/
```

**Response:**
```json
{
  "success": true,
  "message": "Affiliation request with ABC Real Estate has been cancelled"
}
```

### Company Admin Endpoints

##### 5. Pending Requests
```http
GET /api/admin/affiliation-requests/
```

**Authentication:** Required (Company Admin only)

**Response:**
```json
{
  "requests": [
    {
      "id": 1,
      "marketer": {
        "id": 5,
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+2348012345678",
        "profile_image": "https://example.com/media/profile.jpg"
      },
      "date_requested": "2024-11-20T10:30:00Z",
      "days_pending": 2
    }
  ],
  "total_pending": 1
}
```

##### 6. Approve Request
```http
POST /api/admin/affiliation-requests/{affiliation_id}/approve/
```

**Request Body (Optional):**
```json
{
  "commission_tier": "silver"
}
```

**Response:**
```json
{
  "success": true,
  "message": "John Doe has been approved as an affiliate marketer",
  "affiliation": {
    "id": 1,
    "marketer_name": "John Doe",
    "status": "active",
    "commission_tier": "Silver - 3.5%",
    "commission_rate": "3.50",
    "approval_date": "2024-11-20T12:00:00Z"
  }
}
```

##### 7. Reject Request
```http
POST /api/admin/affiliation-requests/{affiliation_id}/reject/
```

**Response:**
```json
{
  "success": true,
  "message": "Affiliation request from John Doe has been rejected"
}
```

##### 8. View Affiliated Marketers
```http
GET /api/admin/affiliated-marketers/
```

**Response:**
```json
{
  "marketers": [
    {
      "id": 1,
      "marketer": {
        "id": 5,
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+2348012345678"
      },
      "commission_tier": "Silver - 3.5%",
      "commission_rate": "3.50",
      "properties_sold": 5,
      "total_sales_value": "15000000.00",
      "total_commissions_earned": "525000.00",
      "pending_commissions": "225000.00",
      "date_affiliated": "2024-01-15T10:30:00Z",
      "approval_date": "2024-01-16T14:20:00Z"
    }
  ],
  "total_marketers": 1,
  "total_sales": "15000000.00",
  "total_commissions": "525000.00"
}
```

#### Code Files
- `DRF/marketers/api_views/marketer_affiliation_views.py` - All affiliation APIs
- Models used: `MarketerAffiliation`, `Company`, `Notification`

---

## 🔧 How It All Works Together

### Client Journey

1. **Signup**
   - Client registers on login page
   - Account created with `company_profile = NULL`
   - `ClientDashboard` automatically created

2. **Purchase Properties**
   - Can purchase from Company A
   - Can purchase from Company B
   - All properties linked by client email

3. **View Portfolio**
   - Access `/api/client/portfolio/overview/`
   - See all properties grouped by company
   - Track total investment across companies

4. **Company Toggles**
   - Properties displayed with company badges
   - Click to expand each company's properties
   - View detailed transaction history

### Marketer Journey

1. **Signup**
   - Marketer registers on login page
   - Account created with `company_profile = NULL`
   - Independent marketer account

2. **Request Affiliations**
   - Browse companies via `/api/marketer/available-companies/`
   - Request affiliation with multiple companies
   - Track status of each request

3. **Get Approved**
   - Company admin approves request
   - Marketer receives notification
   - Can now sell properties and earn commissions

4. **Manage Affiliations**
   - View all affiliations via `/api/marketer/affiliations/`
   - See commission rates per company
   - Track earnings across companies

### Company Admin Journey

1. **Receive Requests**
   - Marketer submits affiliation request
   - Admin receives notification
   - View via `/api/admin/affiliation-requests/`

2. **Review & Approve**
   - Check marketer profile
   - Approve and set commission tier
   - Marketer gets notified

3. **Manage Marketers**
   - View all active marketers
   - Track performance and commissions
   - Suspend/terminate if needed

---

## 📊 Database Schema

### Existing Models Used (No New Tables!)

```python
class CustomUser:
    company_profile = ForeignKey(Company, null=True)  # NULL for independent users
    role = CharField()  # 'client' or 'marketer'
    
class MarketerAffiliation:
    marketer = ForeignKey(CustomUser)
    company = ForeignKey(Company)
    status = CharField()  # pending_approval, active, suspended, terminated
    commission_tier = CharField()
    commission_rate = DecimalField()
    properties_sold = IntegerField()
    total_commissions_earned = DecimalField()
    
class ClientDashboard:
    client = OneToOneField(CustomUser)
    total_properties_owned = IntegerField()
    total_invested = DecimalField()
    portfolio_value = DecimalField()
    # Aggregates across ALL companies
    
class PlotAllocation:
    client = ForeignKey(CustomUser)
    estate = ForeignKey(Estate)  # Estate has company
    # Links client to properties from any company
```

---

## 🚀 Testing the Features

### Test Public Signup

```bash
curl -X POST http://localhost:8000/register-user/ \
  -d "first_name=John&last_name=Doe&email=john@test.com&phone=08012345678&date_of_birth=1990-01-01&role=client&password=Test@1234&password_confirm=Test@1234"
```

### Test Client Portfolio

```bash
# Login first, get token
curl -X GET http://localhost:8000/api/client/portfolio/overview/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### Test Marketer Affiliation

```bash
# View available companies
curl -X GET http://localhost:8000/api/marketer/available-companies/ \
  -H "Authorization: Token YOUR_TOKEN"

# Request affiliation
curl -X POST http://localhost:8000/api/marketer/request-affiliation/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"company_id": 1}'
```

### Test Admin Approval

```bash
# View pending requests
curl -X GET http://localhost:8000/api/admin/affiliation-requests/ \
  -H "Authorization: Token ADMIN_TOKEN"

# Approve request
curl -X POST http://localhost:8000/api/admin/affiliation-requests/1/approve/ \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"commission_tier": "silver"}'
```

---

## 🎨 Frontend Integration Examples

### Display Client Portfolio

```javascript
// Fetch portfolio overview
fetch('/api/client/portfolio/overview/', {
  headers: {
    'Authorization': `Token ${userToken}`
  }
})
.then(res => res.json())
.then(data => {
  // Display overview stats
  document.getElementById('total-properties').textContent = data.overview.total_properties;
  document.getElementById('total-invested').textContent = data.overview.total_invested;
  
  // Create company toggles
  data.companies.forEach(company => {
    const companyDiv = document.createElement('div');
    companyDiv.className = 'company-section';
    companyDiv.innerHTML = `
      <div class="company-header" onclick="toggleCompany(${company.company_id})">
        <img src="${company.company_logo}" alt="${company.company_name}">
        <h3>${company.company_name}</h3>
        <span class="badge">${company.properties_count} properties</span>
      </div>
      <div class="company-properties" id="company-${company.company_id}" style="display:none">
        ${company.properties.map(prop => `
          <div class="property-card">
            <img src="${prop.plot_image}" alt="${prop.estate_name}">
            <h4>${prop.estate_name}</h4>
            <p>Plot: ${prop.plot_number}</p>
            <p>Size: ${prop.plot_size}</p>
            <p>Amount: ₦${prop.amount_paid}</p>
          </div>
        `).join('')}
      </div>
    `;
    document.getElementById('portfolio').appendChild(companyDiv);
  });
});
```

### Marketer Affiliation Request

```javascript
// Browse companies
function loadAvailableCompanies() {
  fetch('/api/marketer/available-companies/', {
    headers: {'Authorization': `Token ${userToken}`}
  })
  .then(res => res.json())
  .then(data => {
    const grid = document.getElementById('companies-grid');
    data.companies.forEach(company => {
      const card = document.createElement('div');
      card.innerHTML = `
        <div class="company-card">
          <img src="${company.logo}" alt="${company.name}">
          <h3>${company.name}</h3>
          <p>${company.location}</p>
          <p>${company.marketers_count} marketers</p>
          <button onclick="requestAffiliation(${company.id})">
            Request Affiliation
          </button>
        </div>
      `;
      grid.appendChild(card);
    });
  });
}

// Request affiliation
function requestAffiliation(companyId) {
  fetch('/api/marketer/request-affiliation/', {
    method: 'POST',
    headers: {
      'Authorization': `Token ${userToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({company_id: companyId})
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      alert(data.message);
      loadMyAffiliations();
    }
  });
}
```

### Admin Approval Interface

```javascript
// Load pending requests
function loadPendingRequests() {
  fetch('/api/admin/affiliation-requests/', {
    headers: {'Authorization': `Token ${adminToken}`}
  })
  .then(res => res.json())
  .then(data => {
    const list = document.getElementById('pending-requests');
    data.requests.forEach(request => {
      const item = document.createElement('div');
      item.innerHTML = `
        <div class="request-card">
          <img src="${request.marketer.profile_image}">
          <div>
            <h4>${request.marketer.name}</h4>
            <p>${request.marketer.email}</p>
            <p>Requested ${request.days_pending} days ago</p>
          </div>
          <div class="actions">
            <button class="approve" onclick="approveRequest(${request.id})">
              Approve
            </button>
            <button class="reject" onclick="rejectRequest(${request.id})">
              Reject
            </button>
          </div>
        </div>
      `;
      list.appendChild(item);
    });
  });
}

function approveRequest(affiliationId) {
  const tier = prompt('Commission tier (bronze/silver/gold/platinum):');
  fetch(`/api/admin/affiliation-requests/${affiliationId}/approve/`, {
    method: 'POST',
    headers: {
      'Authorization': `Token ${adminToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({commission_tier: tier})
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message);
    loadPendingRequests();
  });
}
```

---

## 🔒 Security Considerations

1. **Authentication Required**
   - All endpoints require valid authentication token
   - Role-based permissions enforced

2. **Data Isolation**
   - Clients can only see their own properties
   - Marketers can only see their own affiliations
   - Admins can only manage their own company's requests

3. **Validation**
   - Email uniqueness enforced
   - Password strength requirements
   - Company existence verification

4. **Notifications**
   - All parties notified of status changes
   - Email notifications sent for important events

---

## 📝 Summary

All three features are now fully implemented and tested:

✅ **Public Signup** - Clients and marketers can register independently  
✅ **Cross-Company Portfolio** - Clients see all properties across companies  
✅ **Affiliation Requests** - Marketers request to join companies, admins approve  

No database migrations needed - all features use existing models!

The system is ready for frontend integration and testing.
