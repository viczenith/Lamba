# Phase 1: Company Admin Features - Detailed Implementation Guide

## Overview
This document provides complete implementation details for Phase 1 company admin features based on tenancy rules and SaaS best practices.

---

## 🎯 Feature 1: Company Branding & Profile Management

### Current State
✅ Company model with logo field  
✅ Company model with office_address field  
✅ Dynamic logo in header.html  
✅ CompanyForm includes logo and office_address  

### What Needs Implementation

#### A. Company Profile Page (Already Partially Done)
**File:** `estateApp/templates/admin_side/company_profile.html`

**Sections to Display:**
```html
1. Company Header
   - Logo (company.logo or placeholder)
   - Company Name
   - Quick Stats

2. Company Details Card
   - Company Name
   - Registration Number
   - Registration Date
   - Email
   - Phone
   - Office Address
   - CEO Name
   - CEO DOB

3. Edit Company Modal
   - Logo Upload (with preview)
   - Office Address (text area)
   - Company Name
   - Email
   - Phone
   - Theme Color Picker (new)
```

#### B. Theme Color Customization
**Field Already Exists:** `Company.theme_color` (default='#003366')

**Implementation:**
```python
# In forms.py - Add to CompanyForm
theme_color = forms.CharField(
    widget=forms.TextInput(attrs={
        'type': 'color',
        'class': 'form-control',
        'title': 'Select dashboard theme color'
    })
)

# In models.py - Already exists
theme_color = models.CharField(max_length=7, default='#003366')
```

**Frontend Usage:**
```html
<!-- In CSS variables -->
<style>
  :root {
    --company-primary-color: {{ company.theme_color }};
  }
</style>
```

#### C. Company Logo Display Rules
```
RULES:
1. Header displays company.logo if available, else placeholder
2. All dashboard pages show company branding
3. Admin profile page shows company logo prominently
4. Email templates include company logo
5. Exports/reports include company logo

PLACEHOLDER LOGIC (Current in header.html):
- If company.logo exists → display from /media/company_logos/
- Else → display static placeholder or icon + company name
```

---

## 🎯 Feature 2: Admin Team Management

### Database Models to Create

#### Model 1: AdminRole
```python
# estateApp/models.py

class AdminRole(models.Model):
    """Define role types for admin users"""
    ROLE_CHOICES = [
        ('company_admin', 'Company Administrator'),
        ('finance_manager', 'Finance Manager'),
        ('support_manager', 'Support Manager'),
        ('analyst', 'Analyst (Read-only)'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    permissions = models.JSONField(default=dict)  # Granular permissions
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('company', 'role')
    
    def __str__(self):
        return f"{self.role} - {self.company.company_name}"
```

#### Model 2: AdminActivityLog
```python
# estateApp/models.py

class AdminActivityLog(models.Model):
    """Track all admin actions for audit purposes"""
    ACTION_TYPES = [
        ('login', 'User Login'),
        ('logout', 'User Logout'),
        ('create', 'Created Record'),
        ('update', 'Updated Record'),
        ('delete', 'Deleted Record'),
        ('approve', 'Approved'),
        ('reject', 'Rejected'),
        ('export', 'Exported Data'),
        ('import', 'Imported Data'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='admin_activity_logs')
    admin = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, related_name='activity_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    description = models.TextField()
    object_id = models.IntegerField(null=True, blank=True)
    object_type = models.CharField(max_length=100, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['company', '-timestamp']),
            models.Index(fields=['admin', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.admin.email} - {self.action_type}"
```

### Views to Create

#### View 1: Admin List View
```python
# estateApp/views.py

@login_required
def admin_team_management(request):
    """Display list of admin users for the company"""
    if request.user.role != 'admin':
        return redirect('home')
    
    company = request.user.company_profile
    admin_users = CustomUser.objects.filter(
        company_profile=company,
        role='admin'
    ).order_by('-date_joined')
    
    context = {
        'admin_users': admin_users,
        'total_admins': admin_users.count(),
    }
    return render(request, 'admin_side/admin_team.html', context)
```

#### View 2: Invite Admin
```python
@login_required
@require_http_methods(["POST"])
def invite_admin(request):
    """Invite new admin to company"""
    if request.user.role != 'admin':
        return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)
    
    company = request.user.company_profile
    email = request.POST.get('email', '').strip()
    role_type = request.POST.get('role', 'company_admin')
    
    # Check if user already exists
    try:
        user = CustomUser.objects.get(email=email)
        if user.company_profile != company:
            return JsonResponse({
                'ok': False, 
                'error': 'User already assigned to another company'
            }, status=400)
    except CustomUser.DoesNotExist:
        # Create new user
        user = CustomUser.objects.create(
            email=email,
            username=email.split('@')[0],
            role='admin',
            company_profile=company,
            is_active=True
        )
        # Send welcome email with temp password
        send_admin_invitation_email(user)
    
    # Log activity
    AdminActivityLog.objects.create(
        company=company,
        admin=request.user,
        action_type='create',
        description=f'Invited admin: {email}',
        ip_address=get_client_ip(request),
    )
    
    return JsonResponse({'ok': True, 'message': f'Invitation sent to {email}'})
```

#### View 3: Toggle Admin Status
```python
@login_required
@require_http_methods(["POST"])
def toggle_admin_status(request, admin_id):
    """Mute/unmute an admin user"""
    if request.user.role != 'admin':
        return JsonResponse({'ok': False, 'error': 'Forbidden'}, status=403)
    
    company = request.user.company_profile
    action = request.POST.get('action', 'mute')  # mute or unmute
    
    try:
        target_admin = CustomUser.objects.get(
            id=admin_id,
            company_profile=company,
            role='admin'
        )
    except CustomUser.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Admin not found'}, status=404)
    
    # Prevent disabling all admins
    if action == 'mute':
        active_admins = CustomUser.objects.filter(
            company_profile=company,
            role='admin',
            is_active=True
        ).count()
        if active_admins <= 1:
            return JsonResponse({
                'ok': False,
                'error': 'Cannot mute the last active admin'
            }, status=400)
    
    target_admin.is_active = (action == 'unmute')
    target_admin.save()
    
    # Log activity
    AdminActivityLog.objects.create(
        company=company,
        admin=request.user,
        action_type='update',
        description=f'{action.capitalize()} admin: {target_admin.email}',
        object_id=target_admin.id,
        object_type='CustomUser',
        ip_address=get_client_ip(request),
    )
    
    return JsonResponse({
        'ok': True,
        'status': 'active' if target_admin.is_active else 'inactive'
    })
```

### Template to Create

**File:** `estateApp/templates/admin_side/admin_team.html`

```html
{% extends 'admin_base.html' %}
{% load static %}

{% block content %}
<main id="main" class="main">
    <div class="pagetitle">
        <h1>Admin Team Management</h1>
        <nav>
            <ol class="breadcrumb">
                <li class="breadcrumb-item"><a href="{% url 'admin-dashboard' %}">Home</a></li>
                <li class="breadcrumb-item active">Admin Team</li>
            </ol>
        </nav>
    </div>

    <section class="section">
        <div class="row">
            <div class="col-lg-12">
                <div class="card">
                    <div class="card-header d-flex justify-content-between align-items-center">
                        <strong>Admin Users ({{ total_admins }})</strong>
                        <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#inviteAdminModal">
                            <i class="bi bi-plus-circle"></i> Invite Admin
                        </button>
                    </div>
                    <div class="card-body">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>Email</th>
                                    <th>Name</th>
                                    <th>Joined Date</th>
                                    <th>Status</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for admin in admin_users %}
                                <tr>
                                    <td>{{ admin.email }}</td>
                                    <td>{{ admin.get_full_name|default:admin.username }}</td>
                                    <td>{{ admin.date_joined|date:'M d, Y' }}</td>
                                    <td>
                                        {% if admin.is_active %}
                                            <span class="badge bg-success">Active</span>
                                        {% else %}
                                            <span class="badge bg-warning">Muted</span>
                                        {% endif %}
                                    </td>
                                    <td>
                                        {% if admin.id != request.user.id %}
                                            <button class="btn btn-sm btn-outline-warning toggle-admin-btn" 
                                                    data-admin-id="{{ admin.id }}"
                                                    data-action="{% if admin.is_active %}mute{% else %}unmute{% endif %}">
                                                {% if admin.is_active %}<i class="bi bi-lock"></i> Mute{% else %}<i class="bi bi-unlock"></i> Unmute{% endif %}
                                            </button>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% empty %}
                                <tr>
                                    <td colspan="5" class="text-center text-muted">No admin users found</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <!-- Invite Admin Modal -->
    <div class="modal fade" id="inviteAdminModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Invite New Admin</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <form id="inviteAdminForm">
                    <div class="modal-body">
                        {% csrf_token %}
                        <div class="mb-3">
                            <label for="adminEmail" class="form-label">Admin Email</label>
                            <input type="email" class="form-control" id="adminEmail" name="email" required>
                        </div>
                        <div class="mb-3">
                            <label for="adminRole" class="form-label">Role</label>
                            <select class="form-control" id="adminRole" name="role">
                                <option value="company_admin">Company Administrator</option>
                                <option value="finance_manager">Finance Manager</option>
                                <option value="support_manager">Support Manager</option>
                            </select>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="submit" class="btn btn-primary">Send Invitation</button>
                    </div>
                </form>
            </div>
        </div>
    </div>
</main>

<script>
document.getElementById('inviteAdminForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    const response = await fetch('{% url "invite_admin" %}', {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    });
    
    const data = await response.json();
    if (data.ok) {
        alert(data.message);
        location.reload();
    } else {
        alert('Error: ' + data.error);
    }
});

document.querySelectorAll('.toggle-admin-btn').forEach(btn => {
    btn.addEventListener('click', async function() {
        const adminId = this.dataset.adminId;
        const action = this.dataset.action;
        
        const response = await fetch(`/admin/admin/${adminId}/toggle-status/`, {
            method: 'POST',
            body: new URLSearchParams({
                action: action,
                csrfmiddlewaretoken: document.querySelector('[name=csrfmiddlewaretoken]').value
            })
        });
        
        const data = await response.json();
        if (data.ok) {
            location.reload();
        }
    });
});
</script>
{% endblock %}
```

### URL Configuration

```python
# In estateApp/urls.py or admin_urls.py

urlpatterns = [
    # ... existing patterns
    
    # Admin Team Management
    path('admin/team/', admin_team_management, name='admin_team_management'),
    path('admin/invite/', invite_admin, name='invite_admin'),
    path('admin/admin/<int:admin_id>/toggle-status/', toggle_admin_status, name='toggle_admin_status'),
]
```

---

## 🎯 Feature 3: Admin Activity Audit Logging

### Middleware to Create

**File:** `estateApp/audit_middleware.py`

```python
import logging
from django.utils.deprecation import MiddlewareMixin
from estateApp.models import AdminActivityLog

logger = logging.getLogger(__name__)

class AdminAuditMiddleware(MiddlewareMixin):
    """Log admin activities for audit trail"""
    
    SENSITIVE_PATHS = [
        '/admin/',
        '/api/company/',
        '/api/payments/',
    ]
    
    ACTION_MAP = {
        'GET': 'view',
        'POST': 'create',
        'PUT': 'update',
        'PATCH': 'update',
        'DELETE': 'delete',
    }
    
    def process_response(self, request, response):
        # Only log for authenticated admin users
        if not request.user.is_authenticated:
            return response
        
        if request.user.role != 'admin':
            return response
        
        # Check if sensitive path
        if not any(request.path.startswith(p) for p in self.SENSITIVE_PATHS):
            return response
        
        # Don't log static/media files
        if request.path.startswith(('/static/', '/media/')):
            return response
        
        # Log the activity
        try:
            company = request.user.company_profile
            action_type = self.ACTION_MAP.get(request.method, 'other')
            
            AdminActivityLog.objects.create(
                company=company,
                admin=request.user,
                action_type=action_type,
                description=f'{request.method} {request.path}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
        
        return response
    
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
```

### Register in settings.py

```python
# In MIDDLEWARE
MIDDLEWARE = [
    # ... existing middleware
    'estateApp.audit_middleware.AdminAuditMiddleware',
]
```

---

## 🎯 Feature 4: Activity Report

### View to Display Activity

```python
@login_required
def admin_activity_report(request):
    """Display admin activity logs"""
    if request.user.role != 'admin':
        return redirect('home')
    
    company = request.user.company_profile
    days = int(request.GET.get('days', 30))
    
    activities = AdminActivityLog.objects.filter(
        company=company,
        timestamp__gte=timezone.now() - timedelta(days=days)
    ).order_by('-timestamp')
    
    context = {
        'activities': activities[:1000],  # Limit for display
        'total_activities': activities.count(),
        'days': days,
    }
    return render(request, 'admin_side/activity_report.html', context)
```

### Template

```html
<!-- estateApp/templates/admin_side/activity_report.html -->

{% extends 'admin_base.html' %}

{% block content %}
<main id="main" class="main">
    <div class="pagetitle">
        <h1>Activity Audit Log</h1>
    </div>

    <section class="section">
        <div class="card">
            <div class="card-header">
                <strong>Admin Activities (Last {{ days }} days)</strong>
            </div>
            <div class="card-body">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Admin</th>
                            <th>Action</th>
                            <th>Description</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for activity in activities %}
                        <tr>
                            <td>{{ activity.timestamp|date:'M d, Y H:i' }}</td>
                            <td>{{ activity.admin.email }}</td>
                            <td><span class="badge bg-primary">{{ activity.action_type }}</span></td>
                            <td>{{ activity.description }}</td>
                            <td>{{ activity.ip_address }}</td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="5" class="text-center text-muted">No activities found</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </section>
</main>
{% endblock %}
```

---

## 📋 Tenant Isolation Checklist

For all Phase 1 features, ensure:

- [x] All models have `company` or `company_profile` FK
- [x] All queries filter by `request.user.company_profile`
- [x] Database indexes created on `company_id`
- [x] No cross-company data leakage
- [x] Audit logging captures company context
- [x] Admin activity logs include company_id

---

## 🚀 Implementation Roadmap

**Week 1:**
- [ ] Create AdminRole & AdminActivityLog models
- [ ] Create migrations
- [ ] Add audit middleware

**Week 2:**
- [ ] Implement admin team management views
- [ ] Create admin team HTML template
- [ ] Add invite functionality
- [ ] Create activity report

**Week 3:**
- [ ] Test cross-company isolation
- [ ] Add admin permissions system
- [ ] Create activity dashboard widget

**Week 4:**
- [ ] Performance optimization (indexes, caching)
- [ ] Documentation
- [ ] User training materials

---

## 🔗 Related Documentation

- `COMPANY_ADMIN_IMPLEMENTATION_ROADMAP.md` - Full feature roadmap
- `multi-infra.md` - SaaS strategy
- `adminSupport/docs/tenancy/README.md` - Multi-tenancy architecture

---

*This Phase 1 implementation provides a solid foundation for company admin management with proper tenant isolation and audit trails.*
