# Quick Start Guide - Multi-Tenant Features

## 🚀 For Developers

This guide will get you up and running with the new multi-tenant features in 5 minutes.

## 1. Public Signup (Already Working!)

### What Changed
- Users can now signup as **Client** or **Marketer** from the login page
- They are created with `company_profile = NULL` (independent users)
- Clients automatically get a `ClientDashboard` for portfolio tracking

### No Code Changes Needed
The existing signup flow has been enhanced. Just test it!

### Test It
```bash
# Visit login page
http://localhost:8000/login/

# Click "Sign Up" button
# Fill form and select role (Client or Marketer)
# Submit
```

---

## 2. Client Cross-Company Portfolio

### New API Endpoints

#### Get Portfolio Overview
```javascript
GET /api/client/portfolio/overview/

Response:
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
      "properties_count": 3,
      "total_invested": "9000000.00",
      "properties": [...]
    }
  ]
}
```

#### Get Companies List
```javascript
GET /api/client/companies/

Response:
{
  "companies": [
    {
      "id": 1,
      "name": "ABC Real Estate",
      "logo": "...",
      "properties_count": 3,
      "total_invested": "9000000.00"
    }
  ],
  "total_companies": 1
}
```

#### Get Properties by Company
```javascript
GET /api/client/companies/{company_id}/properties/

Response:
{
  "company": {...},
  "properties": [...],
  "total_properties": 3,
  "total_invested": "9000000.00"
}
```

#### Get All Properties (Flat List)
```javascript
GET /api/client/all-properties/

Response:
{
  "properties": [
    {
      "allocation_id": 1,
      "company": {...},
      "estate": {...},
      "plot_number": "A-101",
      ...
    }
  ],
  "total_properties": 5,
  "total_invested": "15000000.00"
}
```

### Frontend Integration
```javascript
// Fetch and display portfolio
async function loadClientPortfolio() {
  const response = await fetch('/api/client/portfolio/overview/', {
    headers: {
      'Authorization': `Token ${clientToken}`
    }
  });
  const data = await response.json();
  
  // Display overview
  console.log(`Total Properties: ${data.overview.total_properties}`);
  console.log(`Total Invested: ₦${data.overview.total_invested}`);
  
  // Loop through companies
  data.companies.forEach(company => {
    console.log(`\n${company.company_name}:`);
    console.log(`  - ${company.properties_count} properties`);
    console.log(`  - ₦${company.total_invested} invested`);
    
    company.properties.forEach(property => {
      console.log(`    • ${property.estate_name} - Plot ${property.plot_number}`);
    });
  });
}
```

---

## 3. Marketer Affiliation System

### New API Endpoints

#### For Marketers

##### Browse Available Companies
```javascript
GET /api/marketer/available-companies/

Response:
{
  "companies": [
    {
      "id": 1,
      "name": "ABC Real Estate",
      "logo": "...",
      "email": "info@abc.com",
      "phone": "+2348012345678",
      "location": "Lagos",
      "marketers_count": 15
    }
  ],
  "total_companies": 3
}
```

##### Request Affiliation
```javascript
POST /api/marketer/request-affiliation/
Body: {"company_id": 1}

Response:
{
  "success": true,
  "message": "Affiliation request sent to ABC Real Estate...",
  "affiliation": {
    "id": 1,
    "company_name": "ABC Real Estate",
    "status": "pending_approval",
    "date_requested": "2024-11-20T10:30:00Z"
  }
}
```

##### View All Affiliations
```javascript
GET /api/marketer/affiliations/

Response:
{
  "affiliations": [
    {
      "id": 1,
      "company": {...},
      "status": "active",
      "status_display": "Active",
      "commission_tier": "Silver - 3.5%",
      "commission_rate": "3.50",
      "properties_sold": 5,
      "total_commissions_earned": "525000.00",
      "pending_commissions": "225000.00",
      ...
    }
  ],
  "summary": {
    "total": 2,
    "active": 1,
    "pending": 1,
    "suspended": 0,
    "terminated": 0
  }
}
```

##### Cancel Pending Request
```javascript
DELETE /api/marketer/affiliations/{affiliation_id}/cancel/

Response:
{
  "success": true,
  "message": "Affiliation request with ABC Real Estate has been cancelled"
}
```

#### For Company Admins

##### View Pending Requests
```javascript
GET /api/admin/affiliation-requests/

Response:
{
  "requests": [
    {
      "id": 1,
      "marketer": {
        "id": 5,
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+2348012345678",
        "profile_image": "..."
      },
      "date_requested": "2024-11-20T10:30:00Z",
      "days_pending": 2
    }
  ],
  "total_pending": 1
}
```

##### Approve Request
```javascript
POST /api/admin/affiliation-requests/{affiliation_id}/approve/
Body: {"commission_tier": "silver"}  // optional

Response:
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

##### Reject Request
```javascript
POST /api/admin/affiliation-requests/{affiliation_id}/reject/

Response:
{
  "success": true,
  "message": "Affiliation request from John Doe has been rejected"
}
```

##### View Affiliated Marketers
```javascript
GET /api/admin/affiliated-marketers/

Response:
{
  "marketers": [
    {
      "id": 1,
      "marketer": {...},
      "commission_tier": "Silver - 3.5%",
      "commission_rate": "3.50",
      "properties_sold": 5,
      "total_sales_value": "15000000.00",
      "total_commissions_earned": "525000.00",
      "pending_commissions": "225000.00",
      ...
    }
  ],
  "total_marketers": 1,
  "total_sales": "15000000.00",
  "total_commissions": "525000.00"
}
```

---

## 🎨 Quick Frontend Examples

### Client Portfolio Component
```javascript
// React/Vue/Angular component
class ClientPortfolio {
  async mounted() {
    const data = await this.fetchPortfolio();
    this.displayPortfolio(data);
  }
  
  async fetchPortfolio() {
    const res = await fetch('/api/client/portfolio/overview/', {
      headers: { 'Authorization': `Token ${this.token}` }
    });
    return res.json();
  }
  
  displayPortfolio(data) {
    // Create company toggles
    data.companies.forEach(company => {
      const section = `
        <div class="company-section">
          <div class="company-header" onclick="toggle('${company.company_id}')">
            <img src="${company.company_logo}" alt="${company.company_name}">
            <h3>${company.company_name}</h3>
            <span class="badge">${company.properties_count} properties</span>
          </div>
          <div id="company-${company.company_id}" class="properties" style="display:none">
            ${this.renderProperties(company.properties)}
          </div>
        </div>
      `;
      document.getElementById('portfolio').innerHTML += section;
    });
  }
  
  renderProperties(properties) {
    return properties.map(p => `
      <div class="property-card">
        <img src="${p.plot_image}" alt="${p.estate_name}">
        <h4>${p.estate_name}</h4>
        <p>Plot: ${p.plot_number} | Size: ${p.plot_size}</p>
        <p class="amount">₦${p.amount_paid}</p>
      </div>
    `).join('');
  }
}
```

### Marketer Affiliation Component
```javascript
class MarketerAffiliations {
  async loadAvailableCompanies() {
    const res = await fetch('/api/marketer/available-companies/', {
      headers: { 'Authorization': `Token ${this.token}` }
    });
    const data = await res.json();
    
    data.companies.forEach(company => {
      // Render company card with "Request Affiliation" button
      const card = `
        <div class="company-card">
          <img src="${company.logo}">
          <h3>${company.name}</h3>
          <p>${company.location}</p>
          <button onclick="requestAffiliation(${company.id})">
            Request Affiliation
          </button>
        </div>
      `;
      document.getElementById('companies').innerHTML += card;
    });
  }
  
  async requestAffiliation(companyId) {
    const res = await fetch('/api/marketer/request-affiliation/', {
      method: 'POST',
      headers: {
        'Authorization': `Token ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ company_id: companyId })
    });
    
    const data = await res.json();
    if (data.success) {
      alert(data.message);
      this.loadMyAffiliations();
    }
  }
  
  async loadMyAffiliations() {
    const res = await fetch('/api/marketer/affiliations/', {
      headers: { 'Authorization': `Token ${this.token}` }
    });
    const data = await res.json();
    
    // Show active, pending, etc.
    this.displayAffiliations(data.grouped);
  }
}
```

### Admin Approval Component
```javascript
class AdminAffiliationRequests {
  async loadPendingRequests() {
    const res = await fetch('/api/admin/affiliation-requests/', {
      headers: { 'Authorization': `Token ${this.adminToken}` }
    });
    const data = await res.json();
    
    data.requests.forEach(request => {
      const item = `
        <div class="request-item">
          <img src="${request.marketer.profile_image}">
          <div class="info">
            <h4>${request.marketer.name}</h4>
            <p>${request.marketer.email}</p>
            <small>Requested ${request.days_pending} days ago</small>
          </div>
          <div class="actions">
            <button onclick="approve(${request.id})">✓ Approve</button>
            <button onclick="reject(${request.id})">✗ Reject</button>
          </div>
        </div>
      `;
      document.getElementById('requests').innerHTML += item;
    });
  }
  
  async approve(requestId) {
    const tier = prompt('Commission tier (bronze/silver/gold/platinum):');
    const res = await fetch(`/api/admin/affiliation-requests/${requestId}/approve/`, {
      method: 'POST',
      headers: {
        'Authorization': `Token ${this.adminToken}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ commission_tier: tier })
    });
    
    const data = await res.json();
    alert(data.message);
    this.loadPendingRequests();
  }
  
  async reject(requestId) {
    if (!confirm('Reject this affiliation request?')) return;
    
    const res = await fetch(`/api/admin/affiliation-requests/${requestId}/reject/`, {
      method: 'POST',
      headers: {
        'Authorization': `Token ${this.adminToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    const data = await res.json();
    alert(data.message);
    this.loadPendingRequests();
  }
}
```

---

## 📦 Files Modified/Created

### New Files
- `DRF/clients/api_views/client_portfolio_views.py` - Client portfolio APIs
- `DRF/marketers/api_views/marketer_affiliation_views.py` - Affiliation APIs
- `MULTI_TENANT_FEATURES_DOCUMENTATION.md` - Full documentation
- `IMPLEMENTATION_PLAN.md` - Implementation details
- `QUICK_START_GUIDE.md` - This file!

### Modified Files
- `estateApp/views.py` - Enhanced `individual_user_registration()`
- `DRF/urls.py` - Added new API routes

### No Database Changes Needed!
All features use existing models:
- `MarketerAffiliation` (already exists)
- `ClientDashboard` (already exists)
- `PlotAllocation` (already exists)

---

## ✅ Quick Test Checklist

### 1. Test Public Signup
- [ ] Visit `/login/`
- [ ] Click "Sign Up"
- [ ] Register as Client
- [ ] Register as Marketer
- [ ] Verify users created with `company_profile = NULL`

### 2. Test Client Portfolio
- [ ] Login as client
- [ ] Call `/api/client/portfolio/overview/`
- [ ] Verify properties grouped by company
- [ ] Check total investment calculations
- [ ] Test company filter

### 3. Test Marketer Affiliation
- [ ] Login as marketer
- [ ] Call `/api/marketer/available-companies/`
- [ ] Request affiliation
- [ ] Verify notification sent to admins
- [ ] View affiliation status

### 4. Test Admin Approval
- [ ] Login as company admin
- [ ] Call `/api/admin/affiliation-requests/`
- [ ] Approve a request
- [ ] Verify marketer notified
- [ ] Check active marketers list

---

## 🐛 Common Issues & Solutions

### Issue: 404 on new endpoints
**Solution:** Run migrations (even though no new models)
```bash
python manage.py makemigrations
python manage.py migrate
```

### Issue: Permission denied
**Solution:** Check token and user role
```javascript
// Client endpoints need client role
// Marketer endpoints need marketer role
// Admin endpoints need admin role with company_profile
```

### Issue: Company not showing
**Solution:** Ensure estates have company assigned
```python
# Each estate must have a company
estate.company = company
estate.save()
```

### Issue: Portfolio shows 0 properties
**Solution:** Check PlotAllocation records
```python
# Verify allocations linked to client
PlotAllocation.objects.filter(client=user)
```

---

## 🎯 Next Steps

1. **Test all endpoints** using Postman or curl
2. **Build frontend components** using examples above
3. **Add UI pages** for portfolio and affiliations
4. **Test notifications** system
5. **Add analytics** dashboards

---

## 📞 Support

For questions or issues:
1. Check `MULTI_TENANT_FEATURES_DOCUMENTATION.md` for detailed info
2. Review code in `DRF/clients/api_views/` and `DRF/marketers/api_views/`
3. Test with curl/Postman before frontend integration

Happy coding! 🚀
