/**
 * Alert Management System
 * Handles display, dismissal, acknowledgement of subscription alerts
 */

(function() {
    'use strict';

    // Configuration
    const ALERTS_CONFIG = {
        API_BASE: '/api/alerts/',
        STORAGE_KEY: 'estate_dismissed_alerts',
        STORAGE_ACKNOWLEDGED: 'estate_acknowledged_alerts',
        AUTO_REFRESH_INTERVAL: 300000, // 5 minutes
        ANIMATION_DURATION: 300, // ms
    };

    // Track dismissed alerts in localStorage
    class AlertManager {
        constructor() {
            this.dismissedAlerts = this.loadDismissedAlerts();
            this.acknowledgedAlerts = this.loadAcknowledgedAlerts();
            this.activeAlerts = [];
            this.init();
        }

        /**
         * Initialize alert manager
         */
        init() {
            this.setupEventListeners();
            this.checkStorageExpiry();
            this.displayAlerts();
            this.setupAutoRefresh();
        }

        /**
         * Setup event listeners for alert buttons
         */
        setupEventListeners() {
            // Dismiss buttons
            document.querySelectorAll('[data-alert-dismiss]').forEach(btn => {
                btn.addEventListener('click', (e) => this.handleDismiss(e));
            });

            // Acknowledge buttons
            document.querySelectorAll('[data-alert-acknowledge]').forEach(btn => {
                btn.addEventListener('click', (e) => this.handleAcknowledge(e));
            });

            // Action buttons
            document.querySelectorAll('[data-alert-action]').forEach(btn => {
                btn.addEventListener('click', (e) => this.handleAction(e));
            });

            // Close buttons (for modals)
            document.querySelectorAll('.alert-modal-close, .alert-sticky-close').forEach(btn => {
                btn.addEventListener('click', (e) => this.handleModalClose(e));
            });
        }

        /**
         * Load dismissed alerts from localStorage
         */
        loadDismissedAlerts() {
            try {
                const stored = localStorage.getItem(ALERTS_CONFIG.STORAGE_KEY);
                return stored ? JSON.parse(stored) : {};
            } catch (e) {
                console.error('Error loading dismissed alerts:', e);
                return {};
            }
        }

        /**
         * Load acknowledged alerts from localStorage
         */
        loadAcknowledgedAlerts() {
            try {
                const stored = localStorage.getItem(ALERTS_CONFIG.STORAGE_ACKNOWLEDGED);
                return stored ? JSON.parse(stored) : {};
            } catch (e) {
                console.error('Error loading acknowledged alerts:', e);
                return {};
            }
        }

        /**
         * Save dismissed alerts to localStorage
         */
        saveDismissedAlerts() {
            try {
                localStorage.setItem(ALERTS_CONFIG.STORAGE_KEY, JSON.stringify(this.dismissedAlerts));
            } catch (e) {
                console.error('Error saving dismissed alerts:', e);
            }
        }

        /**
         * Save acknowledged alerts to localStorage
         */
        saveAcknowledgedAlerts() {
            try {
                localStorage.setItem(ALERTS_CONFIG.STORAGE_ACKNOWLEDGED, JSON.stringify(this.acknowledgedAlerts));
            } catch (e) {
                console.error('Error saving acknowledged alerts:', e);
            }
        }

        /**
         * Check if alert is dismissed and not expired
         */
        isDismissed(alertId) {
            const dismissedTime = this.dismissedAlerts[alertId];
            if (!dismissedTime) return false;

            // Check if dismissal has expired (24 hours)
            const dismissedDate = new Date(dismissedTime);
            const now = new Date();
            const hoursDiff = (now - dismissedDate) / (1000 * 60 * 60);

            if (hoursDiff > 24) {
                delete this.dismissedAlerts[alertId];
                this.saveDismissedAlerts();
                return false;
            }

            return true;
        }

        /**
         * Check if alert is acknowledged
         */
        isAcknowledged(alertId) {
            return !!this.acknowledgedAlerts[alertId];
        }

        /**
         * Check and clean up expired dismissals
         */
        checkStorageExpiry() {
            let hasChanges = false;

            // Check dismissed alerts expiry
            for (const [alertId, dismissedTime] of Object.entries(this.dismissedAlerts)) {
                const dismissedDate = new Date(dismissedTime);
                const now = new Date();
                const hoursDiff = (now - dismissedDate) / (1000 * 60 * 60);

                if (hoursDiff > 24) {
                    delete this.dismissedAlerts[alertId];
                    hasChanges = true;
                }
            }

            if (hasChanges) {
                this.saveDismissedAlerts();
            }
        }

        /**
         * Display visible alerts
         */
        displayAlerts() {
            const alerts = document.querySelectorAll('[data-alert-id][data-alert-type]');

            alerts.forEach(alertElement => {
                const alertId = alertElement.getAttribute('data-alert-id');
                const alertType = alertElement.getAttribute('data-alert-type');

                // Skip if dismissed (unless blocking)
                if (alertType !== 'blocking' && this.isDismissed(alertId)) {
                    alertElement.style.display = 'none';
                    return;
                }

                // Show alert with animation
                this.showAlert(alertElement, alertType);
                this.activeAlerts.push(alertId);
            });

            // Sort and show highest priority alerts only
            this.sortAndShowAlerts();
        }

        /**
         * Show alert with animation
         */
        showAlert(element, type) {
            // Banners should remain in normal document flow; overlays use flex.
            if (type === 'banner') {
                element.style.display = 'block';
            } else {
                element.style.display = 'flex';
            }

            // Add animation class
            switch (type) {
                case 'banner':
                    element.classList.add('alert-animate-slide-in');
                    break;
                case 'modal':
                    element.classList.add('alert-animate-fade-in');
                    break;
                case 'sticky':
                case 'blocking':
                    element.classList.add('alert-animate-bounce-in');
                    break;
            }

            // Trigger animation
            setTimeout(() => {
                element.style.opacity = '1';
            }, 10);
        }

        /**
         * Sort and show alerts by priority
         * Only show highest priority alert of each type
         */
        sortAndShowAlerts() {
            const alertsByType = {};
            const alerts = document.querySelectorAll('[data-alert-id][data-alert-type]');

            // Group by type
            alerts.forEach(alert => {
                const type = alert.getAttribute('data-alert-type');
                const priority = this.getPriority(type);

                if (!alertsByType[type] || priority > this.getPriority(alertsByType[type])) {
                    alertsByType[type] = alert;
                }
            });

            // Hide lower priority alerts of same type
            alerts.forEach(alert => {
                const type = alert.getAttribute('data-alert-type');
                if (alertsByType[type] !== alert && alert.style.display !== 'none') {
                    this.hideAlert(alert);
                }
            });
        }

        /**
         * Get priority value for alert type
         */
        getPriority(type) {
            const priorities = {
                'blocking': 4,
                'sticky': 3,
                'modal': 2,
                'banner': 1,
            };
            return priorities[type] || 0;
        }

        /**
         * Handle dismiss action
         */
        handleDismiss(event) {
            event.preventDefault();
            event.stopPropagation();

            const button = event.currentTarget;
            const alertId = button.getAttribute('data-alert-id');
            const alertElement = document.getElementById(`alert-banner-${alertId}`) ||
                                  document.getElementById(`alert-modal-${alertId}`);

            if (!alertElement) return;

            // Send dismiss request to server
            this.sendAlertAction('dismiss', alertId, () => {
                this.dismissedAlerts[alertId] = new Date().toISOString();
                this.saveDismissedAlerts();

                // Hide with animation
                this.hideAlert(alertElement);
            });
        }

        /**
         * Handle acknowledge action
         */
        handleAcknowledge(event) {
            event.preventDefault();
            event.stopPropagation();

            const button = event.currentTarget;
            const alertId = button.getAttribute('data-alert-id');
            const alertElement = document.getElementById(`alert-sticky-${alertId}`);

            if (!alertElement) return;

            // Send acknowledge request to server
            this.sendAlertAction('acknowledge', alertId, () => {
                this.acknowledgedAlerts[alertId] = true;
                this.saveAcknowledgedAlerts();

                // Show success message
                this.showToast('Alert acknowledged. Thank you!', 'success');

                // Optional: hide after short delay
                setTimeout(() => {
                    this.hideAlert(alertElement);
                }, 1000);
            });
        }

        /**
         * Handle action button clicks (upgrade, etc.)
         */
        handleAction(event) {
            const button = event.currentTarget;
            const actionUrl = button.getAttribute('data-alert-action');

            if (actionUrl) {
                window.location.href = actionUrl;
            }
        }

        /**
         * Handle modal close (X button)
         */
        handleModalClose(event) {
            event.preventDefault();
            event.stopPropagation();

            const button = event.currentTarget;
            const alertId = button.getAttribute('data-alert-id');
            const alertElement = button.closest('[data-alert-type]');

            if (alertElement && alertElement.getAttribute('data-alert-type') !== 'blocking') {
                this.dismissedAlerts[alertId] = new Date().toISOString();
                this.saveDismissedAlerts();
                this.hideAlert(alertElement);
            }
        }

        /**
         * Hide alert with animation
         */
        hideAlert(element) {
            element.style.opacity = '0';
            element.classList.add('alert-animate-fade-out');

            setTimeout(() => {
                element.style.display = 'none';
                element.classList.remove('alert-animate-fade-out', 'alert-animate-slide-in',
                                         'alert-animate-bounce-in', 'alert-animate-fade-in');
            }, ALERTS_CONFIG.ANIMATION_DURATION);
        }

        /**
         * Send alert action to server
         */
        sendAlertAction(action, alertId, callback) {
            const endpoint = `${ALERTS_CONFIG.API_BASE}${action}/`;
            const data = { alert_id: alertId };

            // Get CSRF token
            const csrfToken = this.getCsrfToken();

            fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                },
                body: JSON.stringify(data),
                credentials: 'include',
            })
            .then(response => {
                if (response.ok) {
                    if (callback) callback();
                } else {
                    console.error(`Failed to ${action} alert:`, response.statusText);
                    this.showToast(`Error ${action}ing alert`, 'error');
                }
            })
            .catch(error => {
                console.error(`Error ${action}ing alert:`, error);
                // Still perform local action even if server fails
                if (callback) callback();
            });
        }

        /**
         * Get CSRF token from cookie
         */
        getCsrfToken() {
            const name = 'csrftoken';
            let cookieValue = null;

            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }

        /**
         * Show toast notification
         */
        showToast(message, type = 'info') {
            const toast = document.createElement('div');
            toast.className = `alert-toast alert-toast-${type}`;
            toast.textContent = message;
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background-color: ${type === 'success' ? '#28a745' : '#dc3545'};
                color: white;
                padding: 16px 24px;
                border-radius: 8px;
                z-index: 10000;
                animation: slideInUp 0.3s ease-out;
                max-width: 300px;
            `;

            document.body.appendChild(toast);

            setTimeout(() => {
                toast.style.animation = 'slideOutDown 0.3s ease-out';
                setTimeout(() => {
                    toast.remove();
                }, 300);
            }, 3000);
        }

        /**
         * Setup auto-refresh of alerts
         */
        setupAutoRefresh() {
            setInterval(() => {
                this.refreshAlerts();
            }, ALERTS_CONFIG.AUTO_REFRESH_INTERVAL);
        }

        /**
         * Refresh alerts from server
         */
        refreshAlerts() {
            const endpoint = `${ALERTS_CONFIG.API_BASE}list/`;

            fetch(endpoint, {
                method: 'GET',
                credentials: 'include',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Check for new alerts and display them
                    console.log('Alerts refreshed:', data.alerts);
                }
            })
            .catch(error => {
                console.error('Error refreshing alerts:', error);
            });
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.alertManager = new AlertManager();
        });
    } else {
        window.alertManager = new AlertManager();
    }

    // Export for manual use
    window.dismissAlert = function(button) {
        if (window.alertManager) {
            window.alertManager.handleDismiss({ currentTarget: button, preventDefault: () => {}, stopPropagation: () => {} });
        }
    };

    window.acknowledgeAlert = function(button) {
        if (window.alertManager) {
            window.alertManager.handleAcknowledge({ currentTarget: button, preventDefault: () => {}, stopPropagation: () => {} });
        }
    };

})();

// CSS Animation styles (can be moved to separate CSS file)
const alertStyles = `
<style>
    @keyframes slideInUp {
        from {
            transform: translateY(100%);
            opacity: 0;
        }
        to {
            transform: translateY(0);
            opacity: 1;
        }
    }

    @keyframes slideOutDown {
        from {
            transform: translateY(0);
            opacity: 1;
        }
        to {
            transform: translateY(100%);
            opacity: 0;
        }
    }

    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
    }

    .alert-animate-slide-in {
        animation: slideInDown 0.3s ease-out !important;
    }

    .alert-animate-fade-in {
        animation: fadeIn 0.3s ease-out !important;
    }

    .alert-animate-bounce-in {
        animation: bounceIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
    }

    .alert-animate-fade-out {
        animation: fadeOut 0.3s ease-out !important;
    }
</style>
`;

// Inject styles if not already present
if (!document.querySelector('style[data-alerts-style]')) {
    const styleTag = document.createElement('style');
    styleTag.setAttribute('data-alerts-style', 'true');
    styleTag.textContent = alertStyles.replace(/<\/?style>/g, '');
    document.head.appendChild(styleTag);
}
