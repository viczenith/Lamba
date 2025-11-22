/**
 * Multi-Tenant Aware API Client
 * Handles all API requests with automatic tenant context
 */

const api = (() => {
  const BASE_URL = '/api/v1';
  let authToken = null;
  let currentTenant = null;
  let currentUser = null;

  // Initialize client with token and tenant context
  const init = (token, tenant = null, user = null) => {
    authToken = token;
    currentTenant = tenant;
    currentUser = user;
    if (token) localStorage.setItem('auth_token', token);
  };

  const setToken = (token) => {
    authToken = token;
    if (token) localStorage.setItem('auth_token', token);
  };

  const setTenant = (tenant) => {
    currentTenant = tenant;
    if (tenant) localStorage.setItem('current_tenant', JSON.stringify(tenant));
  };

  const setUser = (user) => {
    currentUser = user;
    if (user) localStorage.setItem('current_user', JSON.stringify(user));
  };

  // Build headers with authentication and tenant context
  const buildHeaders = (additionalHeaders = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...additionalHeaders
    };

    if (authToken) {
      headers['Authorization'] = `Bearer ${authToken}`;
    }

    // Pass tenant context if available
    if (currentTenant?.id) {
      headers['X-Tenant-ID'] = currentTenant.id;
    }

    return headers;
  };

  // Make HTTP request with error handling
  const request = async (method, endpoint, data = null, options = {}) => {
    const url = `${BASE_URL}${endpoint}`;
    const config = {
      method,
      headers: buildHeaders(options.headers),
      ...options
    };

    if (data && (method === 'POST' || method === 'PUT' || method === 'PATCH')) {
      config.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, config);

      if (response.status === 401) {
        // Handle unauthorized - clear token and redirect to login
        authToken = null;
        localStorage.removeItem('auth_token');
        window.location.href = '/login/';
        throw new Error('Unauthorized');
      }

      const contentType = response.headers.get('content-type');
      let responseData = null;

      if (contentType && contentType.includes('application/json')) {
        responseData = await response.json();
      } else {
        responseData = await response.text();
      }

      if (!response.ok) {
        throw new APIError(
          responseData?.detail || responseData?.error || 'API Error',
          response.status,
          responseData
        );
      }

      return responseData;
    } catch (error) {
      if (error instanceof APIError) throw error;
      throw new APIError(error.message, 0, error);
    }
  };

  // ===== AUTHENTICATION ENDPOINTS =====

  const login = (email, password) =>
    request('POST', '/auth/login/', { email, password });

  const logout = () =>
    request('POST', '/auth/logout/', {});

  const refresh_token = (refresh) =>
    request('POST', '/auth/refresh/', { refresh });

  const verify_token = (token) =>
    request('POST', '/auth/verify/', { token });

  // ===== COMPANY ENDPOINTS (Tenant Management) =====

  const company_list = (params = {}) =>
    request('GET', `/companies/?${new URLSearchParams(params)}`);

  const company_retrieve = (id) =>
    request('GET', `/companies/${id}/`);

  const company_create = (data) =>
    request('POST', '/companies/', data);

  const company_update = (id, data) =>
    request('PUT', `/companies/${id}/`, data);

  const company_partial_update = (id, data) =>
    request('PATCH', `/companies/${id}/`, data);

  const company_delete = (id) =>
    request('DELETE', `/companies/${id}/`);

  const company_stats = (id) =>
    request('GET', `/companies/${id}/stats/`);

  const company_users = (id, params = {}) =>
    request('GET', `/companies/${id}/users/?${new URLSearchParams(params)}`);

  const company_allocations = (id, params = {}) =>
    request('GET', `/companies/${id}/allocations/?${new URLSearchParams(params)}`);

  const company_subscriptions = (id, params = {}) =>
    request('GET', `/companies/${id}/subscriptions/?${new URLSearchParams(params)}`);

  // ===== USER ENDPOINTS (Multi-tenant filtered) =====

  const user_list = (params = {}) =>
    request('GET', `/users/?${new URLSearchParams(params)}`);

  const user_retrieve = (id) =>
    request('GET', `/users/${id}/`);

  const user_create = (data) =>
    request('POST', '/users/', data);

  const user_update = (id, data) =>
    request('PUT', `/users/${id}/`, data);

  const user_partial_update = (id, data) =>
    request('PATCH', `/users/${id}/`, data);

  const user_delete = (id) =>
    request('DELETE', `/users/${id}/`);

  const user_change_password = (id, oldPassword, newPassword) =>
    request('POST', `/users/${id}/change-password/`, { old_password: oldPassword, new_password: newPassword });

  const user_deactivate = (id) =>
    request('POST', `/users/${id}/deactivate/`, {});

  // ===== ESTATE ENDPOINTS =====

  const estate_list = (params = {}) =>
    request('GET', `/estates/?${new URLSearchParams(params)}`);

  const estate_retrieve = (id) =>
    request('GET', `/estates/${id}/`);

  const estate_create = (data) =>
    request('POST', '/estates/', data);

  const estate_update = (id, data) =>
    request('PUT', `/estates/${id}/`, data);

  const estate_partial_update = (id, data) =>
    request('PATCH', `/estates/${id}/`, data);

  const estate_delete = (id) =>
    request('DELETE', `/estates/${id}/`);

  const estate_stats = (id) =>
    request('GET', `/estates/${id}/stats/`);

  // ===== PROPERTY ENDPOINTS =====

  const property_list = (params = {}) =>
    request('GET', `/properties/?${new URLSearchParams(params)}`);

  const property_retrieve = (id) =>
    request('GET', `/properties/${id}/`);

  const property_create = (data) =>
    request('POST', '/properties/', data);

  const property_update = (id, data) =>
    request('PUT', `/properties/${id}/`, data);

  const property_partial_update = (id, data) =>
    request('PATCH', `/properties/${id}/`, data);

  const property_delete = (id) =>
    request('DELETE', `/properties/${id}/`);

  // ===== ALLOCATION ENDPOINTS =====

  const allocation_list = (params = {}) =>
    request('GET', `/allocations/?${new URLSearchParams(params)}`);

  const allocation_retrieve = (id) =>
    request('GET', `/allocations/${id}/`);

  const allocation_create = (data) =>
    request('POST', '/allocations/', data);

  const allocation_update = (id, data) =>
    request('PUT', `/allocations/${id}/`, data);

  const allocation_partial_update = (id, data) =>
    request('PATCH', `/allocations/${id}/`, data);

  const allocation_delete = (id) =>
    request('DELETE', `/allocations/${id}/`);

  const allocation_approve = (id) =>
    request('POST', `/allocations/${id}/approve/`, {});

  const allocation_reject = (id, reason) =>
    request('POST', `/allocations/${id}/reject/`, { reason });

  // ===== SUBSCRIPTION ENDPOINTS =====

  const subscription_list = (params = {}) =>
    request('GET', `/subscriptions/?${new URLSearchParams(params)}`);

  const subscription_retrieve = (id) =>
    request('GET', `/subscriptions/${id}/`);

  const subscription_create = (data) =>
    request('POST', '/subscriptions/', data);

  const subscription_update = (id, data) =>
    request('PUT', `/subscriptions/${id}/`, data);

  const subscription_partial_update = (id, data) =>
    request('PATCH', `/subscriptions/${id}/`, data);

  const subscription_cancel = (id) =>
    request('POST', `/subscriptions/${id}/cancel/`, {});

  const subscription_renew = (id) =>
    request('POST', `/subscriptions/${id}/renew/`, {});

  // ===== PAYMENT ENDPOINTS =====

  const payment_list = (params = {}) =>
    request('GET', `/payments/?${new URLSearchParams(params)}`);

  const payment_retrieve = (id) =>
    request('GET', `/payments/${id}/`);

  const payment_create = (data) =>
    request('POST', '/payments/', data);

  const payment_verify = (id, paymentRef) =>
    request('POST', `/payments/${id}/verify/`, { payment_reference: paymentRef });

  const payment_process_refund = (id) =>
    request('POST', `/payments/${id}/refund/`, {});

  // ===== TRANSACTION ENDPOINTS =====

  const transaction_list = (params = {}) =>
    request('GET', `/transactions/?${new URLSearchParams(params)}`);

  const transaction_retrieve = (id) =>
    request('GET', `/transactions/${id}/`);

  const transaction_create = (data) =>
    request('POST', '/transactions/', data);

  const transaction_update = (id, data) =>
    request('PUT', `/transactions/${id}/`, data);

  const transaction_partial_update = (id, data) =>
    request('PATCH', `/transactions/${id}/`, data);

  const transaction_export = (format = 'csv', params = {}) =>
    request('GET', `/transactions/export/?format=${format}&${new URLSearchParams(params)}`);

  // ===== BULK OPERATIONS =====

  const bulk_import = (file, type) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    return fetch(`${BASE_URL}/bulk/import/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${authToken}`,
        ...(currentTenant?.id && { 'X-Tenant-ID': currentTenant.id })
      },
      body: formData
    }).then(res => res.json());
  };

  const bulk_export = (type, params = {}) =>
    request('GET', `/bulk/export/?type=${type}&${new URLSearchParams(params)}`);

  return {
    init,
    setToken,
    setTenant,
    setUser,
    // Auth
    login,
    logout,
    refresh_token,
    verify_token,
    // Company
    company_list,
    company_retrieve,
    company_create,
    company_update,
    company_partial_update,
    company_delete,
    company_stats,
    company_users,
    company_allocations,
    company_subscriptions,
    // User
    user_list,
    user_retrieve,
    user_create,
    user_update,
    user_partial_update,
    user_delete,
    user_change_password,
    user_deactivate,
    // Estate
    estate_list,
    estate_retrieve,
    estate_create,
    estate_update,
    estate_partial_update,
    estate_delete,
    estate_stats,
    // Property
    property_list,
    property_retrieve,
    property_create,
    property_update,
    property_partial_update,
    property_delete,
    // Allocation
    allocation_list,
    allocation_retrieve,
    allocation_create,
    allocation_update,
    allocation_partial_update,
    allocation_delete,
    allocation_approve,
    allocation_reject,
    // Subscription
    subscription_list,
    subscription_retrieve,
    subscription_create,
    subscription_update,
    subscription_partial_update,
    subscription_cancel,
    subscription_renew,
    // Payment
    payment_list,
    payment_retrieve,
    payment_create,
    payment_verify,
    payment_process_refund,
    // Transaction
    transaction_list,
    transaction_retrieve,
    transaction_create,
    transaction_update,
    transaction_partial_update,
    transaction_export,
    // Bulk
    bulk_import,
    bulk_export
  };
})();

/**
 * Custom API Error class
 */
class APIError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}
