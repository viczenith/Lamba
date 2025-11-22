/**
 * Tenant Admin Authentication & Authorization Module
 * Ensures only system administrators can access the Tenant Admin dashboard
 * Validates JWT tokens, checks user roles, and manages session security
 */

const TenantAdminAuth = {
    /**
     * Current authenticated user (after verification)
     */
    currentUser: null,
    
    /**
     * Decoded JWT token claims
     */
    tokenClaims: null,
    
    /**
     * Check if user is authorized to access Tenant Admin dashboard
     * Should be called on page load before showing any content
     */
    checkAccess: function() {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        const user = JSON.parse(localStorage.getItem('user') || '{}');

        // Check if token exists
        if (!token || !user.id) {
            console.warn('No authentication token found. Redirecting to login...');
            this.redirectToLogin('Authentication required');
            return false;
        }

        // Decode and verify JWT
        try {
            const decoded = this.decodeJWT(token);
            this.tokenClaims = decoded;

            // Verify system admin status
            if (!decoded.is_system_admin) {
                console.error('Access Denied: User is not a system administrator');
                this.redirectToDenied('Not a system administrator');
                return false;
            }

            // Verify admin level
            if (decoded.admin_level !== 'system') {
                console.error('Access Denied: Invalid admin level:', decoded.admin_level);
                this.redirectToDenied('Invalid admin level');
                return false;
            }

            // Verify scope (should be 'tenant_admin')
            if (decoded.scope !== 'tenant_admin') {
                console.error('Access Denied: Invalid scope for Tenant Admin:', decoded.scope);
                this.redirectToDenied('Invalid scope for Tenant Admin');
                return false;
            }

            // Check token expiration
            const now = Math.floor(Date.now() / 1000);
            if (decoded.exp && decoded.exp < now) {
                console.error('Token has expired');
                this.redirectToDenied('Session expired. Please login again.');
                return false;
            }

            // Calculate time until expiration
            const expiresIn = decoded.exp ? (decoded.exp - now) * 1000 : null;
            const expiresAt = decoded.exp ? new Date(decoded.exp * 1000) : null;

            // Check if token is expiring soon (less than 5 minutes)
            if (expiresIn && expiresIn < 300000) {
                console.warn('Token expiring soon:', Math.round(expiresIn / 1000), 'seconds');
                Toast.warning(`Session expiring in ${Math.round(expiresIn / 1000)} seconds`);
            }

            // Store verified user claims
            this.currentUser = {
                id: decoded.user_id,
                email: decoded.email,
                fullName: decoded.full_name || 'System Admin',
                role: decoded.role,
                isSystemAdmin: decoded.is_system_admin,
                adminLevel: decoded.admin_level,
                companyId: decoded.company_id,
                scope: decoded.scope,
                expiresAt: expiresAt,
                expiresIn: expiresIn
            };

            console.log('✅ Tenant Admin Authentication Successful');
            console.log('User:', this.currentUser.email, '| Expires:', expiresAt?.toLocaleString());

            return true;

        } catch (error) {
            console.error('JWT verification failed:', error.message);
            this.redirectToDenied('Invalid authentication token');
            return false;
        }
    },

    /**
     * Decode JWT token (without verification - for client-side use only)
     * Never trust claims from a decoded token for security - always verify server-side
     */
    decodeJWT: function(token) {
        try {
            // Validate token format
            if (typeof token !== 'string' || token.split('.').length !== 3) {
                throw new Error('Invalid JWT format');
            }

            // Get payload
            const base64Url = token.split('.')[1];
            if (!base64Url) {
                throw new Error('Missing JWT payload');
            }

            // Decode base64
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(
                atob(base64).split('').map(c =>
                    '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
                ).join('')
            );

            const decoded = JSON.parse(jsonPayload);

            // Validate required fields
            if (!decoded.user_id || !decoded.email) {
                throw new Error('Missing required JWT claims');
            }

            return decoded;

        } catch (error) {
            throw new Error(`Failed to decode JWT token: ${error.message}`);
        }
    },

    /**
     * Check if current user is a tenant admin
     */
    isTenantAdmin: function() {
        if (!this.currentUser) return false;

        return (
            this.currentUser.isSystemAdmin === true &&
            this.currentUser.adminLevel === 'system' &&
            this.currentUser.scope === 'tenant_admin'
        );
    },

    /**
     * Check if current user is a company admin
     */
    isCompanyAdmin: function() {
        if (!this.currentUser) return false;

        return this.currentUser.adminLevel === 'company';
    },

    /**
     * Check if JWT has admin-level access (system or company)
     */
    isAnyAdmin: function() {
        if (!this.currentUser) return false;

        return this.currentUser.adminLevel in ['system', 'company'];
    },

    /**
     * Get time remaining until session expires
     */
    getSessionTimeRemaining: function() {
        if (!this.currentUser || !this.currentUser.expiresAt) {
            return null;
        }

        const now = new Date();
        const msRemaining = this.currentUser.expiresAt - now;

        if (msRemaining <= 0) {
            return null; // Expired
        }

        return {
            ms: msRemaining,
            seconds: Math.floor(msRemaining / 1000),
            minutes: Math.floor(msRemaining / 60000),
            hours: Math.floor(msRemaining / 3600000),
            formatted: this.formatTimeRemaining(msRemaining)
        };
    },

    /**
     * Format time remaining as human-readable string
     */
    formatTimeRemaining: function(ms) {
        const seconds = Math.floor(ms / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    },

    /**
     * Redirect to login page
     */
    redirectToLogin: function(reason = 'Authentication required') {
        // Clear stored data
        localStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');

        // Add reason to URL for display
        const url = `/tenant-admin/login/?reason=${encodeURIComponent(reason)}`;
        window.location.href = url;
    },

    /**
     * Redirect to access denied page
     */
    redirectToDenied: function(reason = 'Access denied') {
        // Clear stored data
        localStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');

        // Redirect to access denied page
        const url = `/tenant-admin/access-denied/?reason=${encodeURIComponent(reason)}`;
        window.location.href = url;
    },

    /**
     * Logout user
     */
    logout: function() {
        console.log('Logging out user:', this.currentUser?.email);

        // Clear stored authentication
        localStorage.removeItem('auth_token');
        sessionStorage.removeItem('auth_token');
        localStorage.removeItem('user');
        localStorage.removeItem('tenant');

        // Optionally call backend logout endpoint
        try {
            fetch('/api/admin/logout/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`,
                    'Content-Type': 'application/json'
                }
            }).catch(e => console.warn('Logout API call failed:', e));
        } catch (e) {
            console.warn('Could not call logout endpoint:', e);
        }

        // Redirect to login
        this.redirectToLogin('You have been logged out');
    },

    /**
     * Refresh token before expiration
     * Should be called periodically or when token is about to expire
     */
    refreshToken: async function() {
        try {
            const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');

            if (!token) {
                throw new Error('No token to refresh');
            }

            const response = await fetch('/api/admin/token-refresh/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();

            // Store new token
            localStorage.setItem('auth_token', data.token);

            // Re-verify access
            if (!this.checkAccess()) {
                throw new Error('Re-verification failed after token refresh');
            }

            console.log('✅ Token refreshed successfully');
            return true;

        } catch (error) {
            console.error('Token refresh failed:', error);
            this.redirectToLogin('Session expired');
            return false;
        }
    },

    /**
     * Start automatic token refresh
     * Refresh token when it has 10 minutes or less remaining
     */
    startAutoRefresh: function() {
        // Check token every minute
        setInterval(() => {
            const remaining = this.getSessionTimeRemaining();

            if (!remaining) {
                console.warn('Session expired');
                this.logout();
                return;
            }

            // Refresh if less than 10 minutes remaining
            if (remaining.minutes < 10) {
                console.log('Token expiring soon, attempting refresh...');
                this.refreshToken();
            }

            // Show warning if less than 5 minutes
            if (remaining.minutes < 5) {
                const isNotificationVisible = document.getElementById('expiration-warning');
                if (!isNotificationVisible) {
                    Toast.warning(`Your session will expire in ${remaining.formatted}`);
                }
            }

        }, 60000); // Check every minute
    },

    /**
     * Display current user info
     */
    displayUserInfo: function() {
        if (!this.currentUser) return;

        const element = document.getElementById('admin-user-info');
        if (!element) return;

        const remaining = this.getSessionTimeRemaining();
        const timeStr = remaining ? remaining.formatted : 'Session expired';

        element.innerHTML = `
            <div class="admin-user-badge">
                <i class="ri-shield-key-line"></i>
                <span>${this.currentUser.email}</span>
                <small title="${this.currentUser.expiresAt?.toLocaleString()}">
                    Expires in ${timeStr}
                </small>
                <a href="javascript:TenantAdminAuth.logout()" class="logout-btn">
                    <i class="ri-logout-box-line"></i> Logout
                </a>
            </div>
        `;
    },

    /**
     * Log admin action to audit trail (server-side logging)
     */
    logAction: async function(action, resource, details = {}) {
        try {
            const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');

            await fetch('/api/admin/audit-log/', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    action,
                    resource,
                    details,
                    timestamp: new Date().toISOString()
                })
            });
        } catch (error) {
            console.warn('Could not log action:', error);
        }
    },

    /**
     * Initialize authentication on page load
     */
    init: function() {
        console.log('Initializing Tenant Admin Authentication...');

        // Check access on page load
        if (!this.checkAccess()) {
            return false;
        }

        // Display user info
        this.displayUserInfo();

        // Start auto-refresh
        this.startAutoRefresh();

        // Setup logout on window close
        window.addEventListener('beforeunload', () => {
            // Optionally notify backend
            console.log('Window closing - session ending');
        });

        return true;
    }
};

/**
 * Initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if we're on a protected page
    const isProtectedPage = document.body.classList.contains('tenant-admin-page');

    if (isProtectedPage) {
        TenantAdminAuth.init();
    }
});

// Expose globally for manual use if needed
window.TenantAdminAuth = TenantAdminAuth;
