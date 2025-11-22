/**
 * Reusable UI Components
 * Generic components used across all dashboards
 */

// ===== SPINNER / LOADING =====

const Spinner = (() => {
  let spinner = null;

  const create = () => {
    if (spinner) return spinner;

    spinner = document.createElement('div');
    spinner.id = 'global-spinner';
    spinner.innerHTML = `
      <div style="
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
      ">
        <div style="
          background: white;
          padding: 30px;
          border-radius: 12px;
          text-align: center;
        ">
          <div class="spinner-border text-primary mb-3" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
          <p class="text-muted mb-0">Loading...</p>
        </div>
      </div>
    `;
    document.body.appendChild(spinner);
    return spinner;
  };

  const showOverlay = () => {
    const el = create();
    el.style.display = 'flex';
  };

  const hideOverlay = () => {
    if (spinner) spinner.style.display = 'none';
  };

  const show = (element) => {
    const spinner = document.createElement('div');
    spinner.className = 'spinner-border spinner-border-sm text-primary';
    spinner.role = 'status';
    element.innerHTML = '';
    element.appendChild(spinner);
  };

  return { showOverlay, hideOverlay, show, create };
})();

// ===== TOAST / NOTIFICATIONS =====

const Toast = (() => {
  const show = (message, type = 'info', duration = 3000) => {
    const container = document.getElementById('toast-container') || createContainer();

    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.role = 'alert';
    toast.style.cssText = `
      position: relative;
      margin-bottom: 10px;
      animation: slideIn 0.3s ease-out;
    `;
    toast.innerHTML = `
      <div style="display: flex; gap: 10px; align-items: center;">
        <i class="ri-${getIcon(type)}-line"></i>
        <span>${message}</span>
      </div>
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => toast.remove(), duration);
    }

    return toast;
  };

  const createContainer = () => {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: 9999;
      max-width: 400px;
      width: 100%;
    `;
    document.body.appendChild(container);
    return container;
  };

  const getIcon = (type) => {
    const icons = {
      success: 'check-circle',
      error: 'error-warning',
      warning: 'alert',
      info: 'information'
    };
    return icons[type] || 'information';
  };

  return {
    show,
    success: (msg, duration) => show(msg, 'success', duration),
    error: (msg, duration) => show(msg, 'danger', duration),
    warning: (msg, duration) => show(msg, 'warning', duration),
    info: (msg, duration) => show(msg, 'info', duration)
  };
})();

// ===== MODAL HELPER =====

const Modal = (() => {
  const show = (elementId) => {
    const modal = new bootstrap.Modal(document.querySelector(`#${elementId}`));
    modal.show();
    return modal;
  };

  const hide = (elementId) => {
    const modal = bootstrap.Modal.getInstance(document.querySelector(`#${elementId}`));
    if (modal) modal.hide();
  };

  const confirm = (title, message, confirmText = 'Confirm', cancelText = 'Cancel') => {
    return new Promise((resolve) => {
      const modalHtml = `
        <div class="modal fade" id="confirmModal" tabindex="-1">
          <div class="modal-dialog">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title">${title}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
              </div>
              <div class="modal-body">
                <p>${message}</p>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">${cancelText}</button>
                <button type="button" class="btn btn-primary" id="confirmBtn">${confirmText}</button>
              </div>
            </div>
          </div>
        </div>
      `;

      let existing = document.querySelector('#confirmModal');
      if (existing) existing.remove();

      document.body.insertAdjacentHTML('beforeend', modalHtml);

      const modal = new bootstrap.Modal(document.querySelector('#confirmModal'));
      modal.show();

      document.querySelector('#confirmBtn').addEventListener('click', () => {
        modal.hide();
        resolve(true);
      });

      document.querySelector('#confirmModal').addEventListener('hidden.bs.modal', () => {
        resolve(false);
      });
    });
  };

  return { show, hide, confirm };
})();

// ===== FORM VALIDATOR =====

class FormValidator {
  constructor(formId) {
    this.form = document.querySelector(`#${formId}`);
    this.errors = {};
  }

  validate() {
    this.errors = {};
    const formData = new FormData(this.form);

    for (let [name, value] of formData.entries()) {
      const field = this.form.querySelector(`[name="${name}"]`);
      if (!field) continue;

      // Required validation
      if (field.hasAttribute('required') && !value.trim()) {
        this.addError(name, `${field.placeholder || name} is required`);
      }

      // Email validation
      if (field.type === 'email' && value && !this.isValidEmail(value)) {
        this.addError(name, 'Invalid email address');
      }

      // Min length
      if (field.minLength && value.length < field.minLength) {
        this.addError(name, `Minimum ${field.minLength} characters required`);
      }

      // Custom validation
      if (field.dataset.validate) {
        const result = this.runCustomValidation(field.dataset.validate, value);
        if (!result) {
          this.addError(name, field.dataset.validateMessage || 'Invalid value');
        }
      }
    }

    return Object.keys(this.errors).length === 0;
  }

  isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  }

  addError(fieldName, message) {
    if (!this.errors[fieldName]) {
      this.errors[fieldName] = [];
    }
    this.errors[fieldName].push(message);
  }

  runCustomValidation(type, value) {
    const validations = {
      phone: (v) => /^[\d\s\-\+\(\)]+$/.test(v) && v.length >= 10,
      url: (v) => /^https?:\/\/.+/.test(v),
      number: (v) => !isNaN(v),
      positive: (v) => !isNaN(v) && parseFloat(v) > 0
    };
    return validations[type] ? validations[type](value) : true;
  }

  showErrors() {
    // Clear previous errors
    this.form.querySelectorAll('.is-invalid').forEach(el => {
      el.classList.remove('is-invalid');
      const feedback = el.nextElementSibling;
      if (feedback?.classList.contains('invalid-feedback')) {
        feedback.remove();
      }
    });

    // Show new errors
    for (let [fieldName, messages] of Object.entries(this.errors)) {
      const field = this.form.querySelector(`[name="${fieldName}"]`);
      if (field) {
        field.classList.add('is-invalid');
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback d-block';
        feedback.textContent = messages[0];
        field.parentElement.appendChild(feedback);
      }
    }
  }

  getData() {
    const formData = new FormData(this.form);
    const data = {};
    for (let [key, value] of formData.entries()) {
      data[key] = value;
    }
    return data;
  }

  reset() {
    this.form.reset();
    this.errors = {};
    this.form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
  }
}

// ===== UI HELPERS =====

const UIHelpers = (() => {
  const formatCurrency = (amount, currency = '$') => {
    if (!amount && amount !== 0) return '-';
    return `${currency}${parseFloat(amount).toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })}`;
  };

  const formatDate = (date, format = 'short') => {
    if (!date) return '-';
    const d = new Date(date);

    if (format === 'short') {
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    }
    if (format === 'long') {
      return d.toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
    }
    if (format === 'time') {
      return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
    return d.toISOString();
  };

  const formatDateTime = (date) => {
    if (!date) return '-';
    const d = new Date(date);
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatPhoneNumber = (phone) => {
    if (!phone) return '-';
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length === 10) {
      return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
    }
    return phone;
  };

  const truncateText = (text, length = 50) => {
    if (!text) return '-';
    if (text.length <= length) return text;
    return text.substring(0, length) + '...';
  };

  const getBadgeClass = (status) => {
    const badges = {
      active: 'bg-success',
      inactive: 'bg-secondary',
      pending: 'bg-warning',
      completed: 'bg-success',
      failed: 'bg-danger',
      approved: 'bg-success',
      rejected: 'bg-danger',
      cancelled: 'bg-secondary'
    };
    return badges[status?.toLowerCase()] || 'bg-secondary';
  };

  const getStatusIcon = (status) => {
    const icons = {
      active: 'check-circle',
      inactive: 'close-circle',
      pending: 'time',
      completed: 'check-double',
      failed: 'error-warning',
      approved: 'check-circle',
      rejected: 'close-circle',
      cancelled: 'close-line'
    };
    return icons[status?.toLowerCase()] || 'help';
  };

  const humanize = (text) => {
    return text
      .replace(/([A-Z])/g, ' $1')
      .replace(/^./, (str) => str.toUpperCase())
      .trim();
  };

  const debounce = (func, delay) => {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), delay);
    };
  };

  const throttle = (func, limit) => {
    let inThrottle;
    return (...args) => {
      if (!inThrottle) {
        func(...args);
        inThrottle = true;
        setTimeout(() => inThrottle = false, limit);
      }
    };
  };

  return {
    formatCurrency,
    formatDate,
    formatDateTime,
    formatPhoneNumber,
    truncateText,
    getBadgeClass,
    getStatusIcon,
    humanize,
    debounce,
    throttle
  };
})();

// ===== TABLE HELPER =====

const TableHelper = {
  sort: (tableId, columnIndex, ascending = true) => {
    const table = document.querySelector(`#${tableId}`);
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort((a, b) => {
      const aVal = a.cells[columnIndex].textContent.trim();
      const bVal = b.cells[columnIndex].textContent.trim();

      if (!isNaN(aVal) && !isNaN(bVal)) {
        return ascending ? parseFloat(aVal) - parseFloat(bVal) : parseFloat(bVal) - parseFloat(aVal);
      }

      return ascending ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
    });

    rows.forEach(row => tbody.appendChild(row));
  },

  paginate: (items, page = 1, pageSize = 10) => {
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    return items.slice(start, end);
  },

  filter: (items, query, fields) => {
    if (!query) return items;
    return items.filter(item =>
      fields.some(field => {
        const value = item[field];
        return value && value.toString().toLowerCase().includes(query.toLowerCase());
      })
    );
  }
};

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
  @keyframes slideIn {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .invalid-feedback {
    color: #dc3545;
    font-size: 0.875rem;
  }

  .form-control.is-invalid,
  .form-select.is-invalid {
    border-color: #dc3545;
  }
`;
document.head.appendChild(style);
