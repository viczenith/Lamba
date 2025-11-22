# Dashboard Implementation Templates

Quick reference templates for implementing each dashboard with proper multi-tenant filtering.

## 1. Company Admin Dashboard Template

**File**: `estateApp/templates/admin_side/index.html`

**Key Principle**: Filter ALL queries by `company_id = current_tenant.id`

```html
{% extends 'base.html' %}
{% load static %}

{% block head %}
<style>
  /* Dashboard-specific styles */
</style>
{% endblock %}

{% block content %}
<div class="page-header">
  <div class="container-fluid">
    <h1><i class="ri-admin-line"></i> Company Admin Dashboard</h1>
    <p>Manage {{ current_company.name }}</p>
  </div>
</div>

<div class="container-fluid">
  <!-- Company Statistics (Current Company Only) -->
  <div class="row mb-4">
    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Company Users</p>
          <div class="stat-value" data-stat="company_users">0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Total Allocations</p>
          <div class="stat-value" data-stat="company_allocations">0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Subscriptions</p>
          <div class="stat-value" data-stat="company_subscriptions">0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Revenue</p>
          <div class="stat-value" data-stat="company_revenue">$0</div>
        </div>
      </div>
    </div>
  </div>

  <!-- Users Management -->
  <div class="row">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <h5>Company Users</h5>
          <table class="table" id="usersTable">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="usersTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- Allocations Management -->
  <div class="row mt-4">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <h5>Allocations</h5>
          <table class="table" id="allocationsTable">
            <thead>
              <tr>
                <th>Property</th>
                <th>Client</th>
                <th>Status</th>
                <th>Amount</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="allocationsTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="{% static 'js/api-client.js' %}"></script>
<script src="{% static 'js/components.js' %}"></script>
<script src="{% static 'js/error-handler.js' %}"></script>
<script src="{% static 'js/websocket-service.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize API client with current tenant context
  {% if user.is_authenticated %}
    const token = '{{ request.user.token }}';
    const tenant = {
      id: {{ current_company.id }},
      name: '{{ current_company.name }}'
    };
    const user = {
      id: {{ request.user.id }},
      email: '{{ request.user.email }}',
      company_id: {{ request.user.company_id }}
    };

    api.init(token, tenant, user);
    WebSocketService.init(token, tenant);
  {% endif %}

  // Load company statistics
  async function loadCompanyStats() {
    try {
      Spinner.showOverlay();

      // Key: Always filter by company_id
      const [users, allocations, subscriptions, transactions] = await Promise.all([
        api.user_list({ 
          company_id: {{ current_company.id }},
          page_size: 1 
        }),
        api.allocation_list({ 
          company_id: {{ current_company.id }},
          page_size: 1 
        }),
        api.subscription_list({ 
          company_id: {{ current_company.id }},
          page_size: 1 
        }),
        api.transaction_list({ 
          company_id: {{ current_company.id }},
          page_size: 1 
        })
      ]);

      document.querySelector('[data-stat="company_users"]').textContent = users.count || 0;
      document.querySelector('[data-stat="company_allocations"]').textContent = allocations.count || 0;
      document.querySelector('[data-stat="company_subscriptions"]').textContent = subscriptions.count || 0;

      const revenue = (transactions.results || []).reduce((sum, t) => sum + (t.amount || 0), 0);
      document.querySelector('[data-stat="company_revenue"]').textContent = UIHelpers.formatCurrency(revenue);

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  // Load company users
  async function loadCompanyUsers() {
    try {
      Spinner.showOverlay();

      // Key: Filter by company_id ONLY
      const response = await api.user_list({ 
        company_id: {{ current_company.id }},
        page_size: 100 
      });

      const tableBody = document.querySelector('#usersTableBody');
      tableBody.innerHTML = (response.results || []).map(user => `
        <tr>
          <td>${user.name}</td>
          <td>${user.email}</td>
          <td><span class="badge">${user.role}</span></td>
          <td>
            <span class="badge ${user.is_active ? 'bg-success' : 'bg-danger'}">
              ${user.is_active ? 'Active' : 'Inactive'}
            </span>
          </td>
          <td>
            <button class="btn btn-sm btn-view" onclick="viewUser(${user.id})">View</button>
            <button class="btn btn-sm btn-edit" onclick="editUser(${user.id})">Edit</button>
            <button class="btn btn-sm btn-delete" onclick="deleteUser(${user.id})">Delete</button>
          </td>
        </tr>
      `).join('');

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  // Load company allocations
  async function loadCompanyAllocations() {
    try {
      Spinner.showOverlay();

      // Key: Filter by company_id ONLY
      const response = await api.allocation_list({ 
        company_id: {{ current_company.id }},
        page_size: 100,
        ordering: '-created_at'
      });

      const tableBody = document.querySelector('#allocationsTableBody');
      tableBody.innerHTML = (response.results || []).map(alloc => `
        <tr>
          <td>${alloc.property_name}</td>
          <td>${alloc.client_name}</td>
          <td><span class="badge ${UIHelpers.getBadgeClass(alloc.status)}">${alloc.status}</span></td>
          <td>${UIHelpers.formatCurrency(alloc.amount)}</td>
          <td>${UIHelpers.formatDate(alloc.created_at)}</td>
          <td>
            <button class="btn btn-sm btn-view" onclick="viewAllocation(${alloc.id})">View</button>
            <button class="btn btn-sm btn-edit" onclick="editAllocation(${alloc.id})">Edit</button>
          </td>
        </tr>
      `).join('');

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  // Global functions
  window.viewUser = (id) => { window.location.href = `/admin/users/${id}/`; };
  window.editUser = (id) => { window.location.href = `/admin/users/${id}/edit/`; };
  window.deleteUser = async (id) => {
    if (!await Modal.confirm('Delete User?', 'Are you sure?')) return;
    try {
      Spinner.showOverlay();
      await api.user_delete(id);
      Toast.success('User deleted');
      loadCompanyUsers();
      loadCompanyStats();
    } catch (error) {
      ErrorHandler.handleError(error);
    } finally {
      Spinner.hideOverlay();
    }
  };

  window.viewAllocation = (id) => { window.location.href = `/admin/allocations/${id}/`; };
  window.editAllocation = (id) => { window.location.href = `/admin/allocations/${id}/edit/`; };

  // Initial load
  loadCompanyStats();
  loadCompanyUsers();
  loadCompanyAllocations();

  // Listen for real-time updates
  WebSocketService.on('data_updated', (data) => {
    if (data.type === 'user' || data.type === 'allocation') {
      loadCompanyStats();
      loadCompanyUsers();
      loadCompanyAllocations();
    }
  });
});
</script>

{% endblock %}
```

---

## 2. Client Dashboard Template

**File**: `estateApp/templates/client_side/client_side.html`

**Key Principle**: Filter ALL queries by `user_id = current_user.id AND company_id = current_company.id`

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div class="page-header">
  <div class="container-fluid">
    <h1><i class="ri-user-line"></i> My Dashboard</h1>
    <p>Welcome, {{ request.user.name }}</p>
  </div>
</div>

<div class="container-fluid">
  <!-- Client Summary -->
  <div class="row mb-4">
    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Total Allocations</p>
          <div class="stat-value" data-stat="my_allocations">0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Paid Amount</p>
          <div class="stat-value" data-stat="paid_amount">$0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Outstanding</p>
          <div class="stat-value" data-stat="outstanding">$0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Subscription</p>
          <div class="stat-value" data-stat="subscription_status">-</div>
        </div>
      </div>
    </div>
  </div>

  <!-- My Allocations -->
  <div class="row">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <h5>My Allocations</h5>
          <table class="table" id="allocationsTable">
            <thead>
              <tr>
                <th>Property</th>
                <th>Amount</th>
                <th>Paid</th>
                <th>Outstanding</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="allocationsTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- Payment History -->
  <div class="row mt-4">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <h5>Payment History</h5>
          <table class="table" id="paymentsTable">
            <thead>
              <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Reference</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="paymentsTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="{% static 'js/api-client.js' %}"></script>
<script src="{% static 'js/components.js' %}"></script>
<script src="{% static 'js/error-handler.js' %}"></script>
<script src="{% static 'js/websocket-service.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize with user context
  {% if user.is_authenticated %}
    const token = '{{ request.user.token }}';
    const tenant = { id: {{ request.user.company_id }} };
    const user = { id: {{ request.user.id }} };

    api.init(token, tenant, user);
    WebSocketService.init(token, tenant);
  {% endif %}

  const currentUserId = {{ request.user.id }};
  const currentCompanyId = {{ request.user.company_id }};

  async function loadClientSummary() {
    try {
      Spinner.showOverlay();

      // Key: Filter by user_id AND company_id
      const allocations = await api.allocation_list({
        user_id: currentUserId,
        company_id: currentCompanyId
      });

      const payments = await api.payment_list({
        user_id: currentUserId,
        company_id: currentCompanyId
      });

      const totalAllocated = (allocations.results || []).reduce((sum, a) => sum + (a.amount || 0), 0);
      const totalPaid = (payments.results || []).reduce((sum, p) => sum + (p.amount || 0), 0);
      const outstanding = totalAllocated - totalPaid;

      document.querySelector('[data-stat="my_allocations"]').textContent = allocations.count || 0;
      document.querySelector('[data-stat="paid_amount"]').textContent = UIHelpers.formatCurrency(totalPaid);
      document.querySelector('[data-stat="outstanding"]').textContent = UIHelpers.formatCurrency(outstanding);

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  async function loadMyAllocations() {
    try {
      Spinner.showOverlay();

      // Key: Filter by user_id AND company_id ONLY
      const response = await api.allocation_list({
        user_id: currentUserId,
        company_id: currentCompanyId,
        page_size: 100,
        ordering: '-created_at'
      });

      const tableBody = document.querySelector('#allocationsTableBody');
      tableBody.innerHTML = (response.results || []).map(alloc => `
        <tr>
          <td>${alloc.property_name}</td>
          <td>${UIHelpers.formatCurrency(alloc.amount)}</td>
          <td>${UIHelpers.formatCurrency(alloc.paid_amount || 0)}</td>
          <td>${UIHelpers.formatCurrency((alloc.amount || 0) - (alloc.paid_amount || 0))}</td>
          <td><span class="badge ${UIHelpers.getBadgeClass(alloc.status)}">${alloc.status}</span></td>
          <td>
            <button class="btn btn-sm btn-view" onclick="viewAllocation(${alloc.id})">
              View Details
            </button>
          </td>
        </tr>
      `).join('');

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  async function loadPaymentHistory() {
    try {
      Spinner.showOverlay();

      // Key: Filter by user_id AND company_id ONLY
      const response = await api.payment_list({
        user_id: currentUserId,
        company_id: currentCompanyId,
        page_size: 100,
        ordering: '-created_at'
      });

      const tableBody = document.querySelector('#paymentsTableBody');
      tableBody.innerHTML = (response.results || []).map(payment => `
        <tr>
          <td>${UIHelpers.formatDate(payment.created_at)}</td>
          <td>${UIHelpers.formatCurrency(payment.amount)}</td>
          <td>${payment.payment_reference || 'N/A'}</td>
          <td><span class="badge ${UIHelpers.getBadgeClass(payment.status)}">${payment.status}</span></td>
          <td>
            <button class="btn btn-sm btn-view" onclick="downloadReceipt(${payment.id})">
              Receipt
            </button>
          </td>
        </tr>
      `).join('');

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  window.viewAllocation = (id) => {
    window.location.href = `/client/allocations/${id}/`;
  };

  window.downloadReceipt = (paymentId) => {
    window.location.href = `/client/payments/${paymentId}/receipt/`;
  };

  // Initial load
  loadClientSummary();
  loadMyAllocations();
  loadPaymentHistory();

  // Real-time updates
  WebSocketService.on('data_updated', () => {
    loadClientSummary();
    loadMyAllocations();
  });
});
</script>

{% endblock %}
```

---

## 3. Marketer Dashboard Template

**File**: `estateApp/templates/marketer_side/marketer_side.html`

**Key Principle**: Filter ALL queries by `marketer_id = current_user.id AND company_id = current_company.id`

```html
{% extends 'base.html' %}
{% load static %}

{% block content %}
<div class="page-header">
  <div class="container-fluid">
    <h1><i class="ri-line-chart-line"></i> Sales Dashboard</h1>
    <p>Your Performance & Commission Tracking</p>
  </div>
</div>

<div class="container-fluid">
  <!-- Sales Summary -->
  <div class="row mb-4">
    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Total Sales</p>
          <div class="stat-value" data-stat="total_sales">0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Total Value</p>
          <div class="stat-value" data-stat="total_value">$0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Commission Earned</p>
          <div class="stat-value" data-stat="commission_earned">$0</div>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card">
        <div class="card-body">
          <p class="stat-label">Commission Rate</p>
          <div class="stat-value" data-stat="commission_rate">-</div>
        </div>
      </div>
    </div>
  </div>

  <!-- My Sales -->
  <div class="row">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <h5>My Sales</h5>
          <table class="table" id="salesTable">
            <thead>
              <tr>
                <th>Client</th>
                <th>Property</th>
                <th>Amount</th>
                <th>Commission (5%)</th>
                <th>Status</th>
                <th>Date</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="salesTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>

  <!-- Commission History -->
  <div class="row mt-4">
    <div class="col-12">
      <div class="card">
        <div class="card-body">
          <h5>Commission Payments</h5>
          <table class="table" id="commissionsTable">
            <thead>
              <tr>
                <th>Period</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Payment Date</th>
              </tr>
            </thead>
            <tbody id="commissionsTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="{% static 'js/api-client.js' %}"></script>
<script src="{% static 'js/components.js' %}"></script>
<script src="{% static 'js/error-handler.js' %}"></script>
<script src="{% static 'js/websocket-service.js' %}"></script>

<script>
document.addEventListener('DOMContentLoaded', async () => {
  // Initialize with marketer context
  {% if user.is_authenticated %}
    const token = '{{ request.user.token }}';
    const tenant = { id: {{ request.user.company_id }} };
    const user = { id: {{ request.user.id }} };

    api.init(token, tenant, user);
    WebSocketService.init(token, tenant);
  {% endif %}

  const currentMarketerId = {{ request.user.id }};
  const currentCompanyId = {{ request.user.company_id }};
  const commissionRate = 0.05; // 5%

  async function loadSalesSummary() {
    try {
      Spinner.showOverlay();

      // Key: Filter by marketer_id AND company_id
      const allocations = await api.allocation_list({
        marketer_id: currentMarketerId,
        company_id: currentCompanyId
      });

      const approvedSales = (allocations.results || []).filter(a => a.status === 'approved');
      const totalValue = approvedSales.reduce((sum, a) => sum + (a.amount || 0), 0);
      const commission = totalValue * commissionRate;

      document.querySelector('[data-stat="total_sales"]').textContent = allocations.count || 0;
      document.querySelector('[data-stat="total_value"]').textContent = UIHelpers.formatCurrency(totalValue);
      document.querySelector('[data-stat="commission_earned"]').textContent = UIHelpers.formatCurrency(commission);
      document.querySelector('[data-stat="commission_rate"]').textContent = `${(commissionRate * 100).toFixed(1)}%`;

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  async function loadMySales() {
    try {
      Spinner.showOverlay();

      // Key: Filter by marketer_id AND company_id ONLY
      const response = await api.allocation_list({
        marketer_id: currentMarketerId,
        company_id: currentCompanyId,
        page_size: 100,
        ordering: '-created_at'
      });

      const tableBody = document.querySelector('#salesTableBody');
      tableBody.innerHTML = (response.results || []).map(sale => {
        const commission = (sale.amount || 0) * commissionRate;
        return `
          <tr>
            <td>${sale.client_name}</td>
            <td>${sale.property_name}</td>
            <td>${UIHelpers.formatCurrency(sale.amount)}</td>
            <td>${UIHelpers.formatCurrency(commission)}</td>
            <td><span class="badge ${UIHelpers.getBadgeClass(sale.status)}">${sale.status}</span></td>
            <td>${UIHelpers.formatDate(sale.created_at)}</td>
            <td>
              <button class="btn btn-sm btn-view" onclick="viewSale(${sale.id})">
                View
              </button>
            </td>
          </tr>
        `;
      }).join('');

      Spinner.hideOverlay();
    } catch (error) {
      Spinner.hideOverlay();
      ErrorHandler.handleError(error);
    }
  }

  window.viewSale = (id) => {
    window.location.href = `/marketer/sales/${id}/`;
  };

  // Initial load
  loadSalesSummary();
  loadMySales();

  // Real-time updates
  WebSocketService.on('data_updated', () => {
    loadSalesSummary();
    loadMySales();
  });
});
</script>

{% endblock %}
```

---

## Key Implementation Notes

### For All Dashboards:

1. **Always use `company_id` filter** (except Tenant Admin)
   ```javascript
   const data = await api.list({
     company_id: currentCompanyId,  // REQUIRED
     page_size: 100
   });
   ```

2. **For individual user dashboards, add user filter**
   ```javascript
   // Client dashboard
   await api.allocation_list({
     user_id: currentUserId,        // REQUIRED
     company_id: currentCompanyId,  // REQUIRED
     page_size: 100
   });

   // Marketer dashboard
   await api.allocation_list({
     marketer_id: currentMarketerId,  // REQUIRED
     company_id: currentCompanyId,    // REQUIRED
     page_size: 100
   });
   ```

3. **Initialize API and WebSocket**
   ```javascript
   api.init(token, tenant, user);
   WebSocketService.init(token, tenant);
   ```

4. **Listen for real-time updates**
   ```javascript
   WebSocketService.on('data_updated', () => {
     // Reload affected data
   });
   ```

5. **Always wrap operations in error handling**
   ```javascript
   try {
     Spinner.showOverlay();
     await api.operation();
     Spinner.hideOverlay();
     Toast.success('Done');
   } catch (error) {
     Spinner.hideOverlay();
     ErrorHandler.handleError(error);
   }
   ```

---

## Testing Multi-Tenant Isolation

**Verification Checklist**:

- [ ] Super Admin sees ALL companies
- [ ] Company Admin sees ONLY their company's users
- [ ] Client sees ONLY their allocations
- [ ] Marketer sees ONLY their sales
- [ ] Cross-tenant data access returns 403 Forbidden
- [ ] API respects company_id filter
- [ ] WebSocket only sends tenant-specific updates
