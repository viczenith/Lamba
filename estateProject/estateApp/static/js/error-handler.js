/**
 * Global Error Handler
 * Centralized error handling for all dashboards
 */

const ErrorHandler = (() => {
  const errorLog = [];
  const maxLogs = 100;

  // Log error
  const log = (error, context = {}) => {
    const errorEntry = {
      timestamp: new Date().toISOString(),
      message: error?.message || String(error),
      type: error?.name || 'Error',
      stack: error?.stack,
      context,
      status: error?.status,
      data: error?.data
    };

    errorLog.push(errorEntry);

    // Keep only last 100 errors
    if (errorLog.length > maxLogs) {
      errorLog.shift();
    }

    // Log to console in development
    if (window.location.hostname === 'localhost') {
      console.error('ErrorHandler:', errorEntry);
    }

    return errorEntry;
  };

  // Handle API errors
  const handleAPIError = (error, defaultMessage = 'An error occurred') => {
    log(error, { type: 'API_ERROR' });

    if (error instanceof APIError) {
      if (error.status === 401) {
        Toast.error('Your session has expired. Please log in again.');
        setTimeout(() => {
          window.location.href = '/login/';
        }, 1500);
      } else if (error.status === 403) {
        Toast.error('You do not have permission to perform this action.');
      } else if (error.status === 404) {
        Toast.error('The requested resource was not found.');
      } else if (error.status === 409) {
        Toast.error('Conflict: ' + (error.data?.detail || 'This resource already exists.'));
      } else if (error.status === 422) {
        const messages = error.data?.errors || [error.message];
        Toast.error(Array.isArray(messages) ? messages.join(', ') : messages);
      } else if (error.status >= 500) {
        Toast.error('Server error. Please try again later.');
      } else {
        Toast.error(error.message || defaultMessage);
      }
    } else {
      Toast.error(error?.message || defaultMessage);
    }
  };

  // Handle validation errors
  const handleValidationError = (errors, formValidator = null) => {
    log(errors, { type: 'VALIDATION_ERROR' });

    if (formValidator) {
      formValidator.errors = errors;
      formValidator.showErrors();
    } else {
      const messages = Array.isArray(errors)
        ? errors.join(', ')
        : Object.entries(errors)
          .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(', ') : msgs}`)
          .join('; ');
      Toast.error(messages);
    }
  };

  // Handle network errors
  const handleNetworkError = (error) => {
    log(error, { type: 'NETWORK_ERROR' });

    if (navigator.onLine === false) {
      Toast.error('No internet connection. Please check your network.');
    } else {
      Toast.error('Network error. Please try again.');
    }
  };

  // Handle generic errors
  const handleError = (error, context = {}) => {
    if (error instanceof APIError) {
      handleAPIError(error);
    } else if (error instanceof TypeError && error.message.includes('fetch')) {
      handleNetworkError(error);
    } else {
      log(error, context);
      Toast.error(error?.message || 'An unexpected error occurred');
    }
  };

  // Get error history
  const getHistory = (limit = 10) => {
    return errorLog.slice(-limit).reverse();
  };

  // Clear error log
  const clear = () => {
    errorLog.length = 0;
  };

  // Export errors for debugging
  const export_logs = () => {
    const data = {
      timestamp: new Date().toISOString(),
      url: window.location.href,
      userAgent: navigator.userAgent,
      errors: errorLog
    };

    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `error-log-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return {
    log,
    handleAPIError,
    handleValidationError,
    handleNetworkError,
    handleError,
    getHistory,
    clear,
    export_logs
  };
})();

// Global error handler
window.addEventListener('error', (event) => {
  ErrorHandler.log(event.error, { type: 'UNCAUGHT_ERROR' });
});

window.addEventListener('unhandledrejection', (event) => {
  ErrorHandler.log(event.reason, { type: 'UNHANDLED_REJECTION' });
});
