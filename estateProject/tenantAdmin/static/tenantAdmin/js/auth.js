"""
Tenant Admin JavaScript - Authentication & API Client
"""

class TenantAdminAuth {
    constructor() {
        this.baseURL = '/api/tenant-admin';
        this.token = localStorage.getItem('tenant_admin_token');
    }

    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                ...options,
                headers,
            });

            if (response.status === 401) {
                this.logout();
                throw new Error('Unauthorized - Please login again');
            }

            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || `Request failed with status ${response.status}`);
            }

            return data;
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    async getDashboardStats() {
        return this.request('/dashboard-stats/');
    }

    async getRecentActivity() {
        return this.request('/recent-activity/');
    }

    async getSystemHealth() {
        return this.request('/system-health/');
    }

    logout() {
        localStorage.removeItem('tenant_admin_token');
        window.location.href = '/tenant-admin/login/';
    }

    isAuthenticated() {
        return !!this.token;
    }
}

// Export for use in other scripts
window.TenantAdminAuth = TenantAdminAuth;
