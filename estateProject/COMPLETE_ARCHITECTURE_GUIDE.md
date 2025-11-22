# 🏗️ LAMBA REAL ESTATE - COMPLETE ARCHITECTURE GUIDE

## 📊 System Overview

This is a **Multi-Role, Multi-Tenant Real Estate Management System** with Django Backend and Flutter Mobile App.

### Core Roles
- **System Admin** (admin_level='system') → `/tenant-admin/dashboard/`
- **Company Admin** (admin_level='company') → `/admin_dashboard/`
- **Clients** (role='client') → `/client-dashboard/`
- **Marketers** (role='marketer') → `/marketer-dashboard/`
- **Support Staff** (role='support') → `/adminsupport/dashboard/`

### Single Tenant Configuration
**Company**: Lamba Real Estate (LAMBA-REALESTATE-001)
- **Status**: Active, Enterprise tier, Unlimited
- **Users**: 19 total (3 admins, 11 clients, 5 marketers)

---

## 🔐 Authentication Architecture

### 1. Login Flow (HTTP)

```
User visits /login/
    ↓
Django renders login.html with login form
    ↓
User enters email + password
    ↓
Form POSTs to /login/ endpoint
    ↓
CustomLoginView processes request
    ↓
CustomAuthenticationForm validates:
    - Field "username" (email format)
    - Field "password"
    ↓
Django authenticate() checks credentials
    ↓
SUCCESS → UserModel authenticated
    ↓
CustomLoginView.form_valid():
    - Create session
    - Save last_login_ip & location
    - Call get_success_url()
    ↓
get_success_url() checks user attributes:
    - if user.role='admin' & user.admin_level='system' → /tenant-admin/dashboard/
    - if user.role='admin' & user.admin_level='company' → /admin_dashboard/
    - if user.role='client' → /client-dashboard/
    - if user.role='marketer' → /marketer-dashboard/
    ↓
Redirect user to appropriate dashboard ✅
```

### 2. Custom User Model

**File**: `estateApp/models.py`

```python
class CustomUser(AbstractUser):
    # Standard fields: username, email, password, first_name, last_name, etc.
    
    # Custom fields:
    role = models.CharField(
        max_length=20,
        choices=[
            ('admin', 'Administrator'),
            ('client', 'Client'),
            ('marketer', 'Marketer'),
            ('support', 'Support Staff')
        ]
    )
    
    admin_level = models.CharField(
        max_length=20,
        choices=[
            ('system', 'System Admin'),
            ('company', 'Company Admin'),
            ('none', 'Regular User')
        ],
        default='none'
    )
    
    company_profile = models.ForeignKey(
        'Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_location = models.JSONField(null=True, blank=True)
```

### 3. Company Model

**File**: `estateApp/models.py`

```python
class Company(models.Model):
    company_name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, unique=True)
    registration_date = models.DateField()
    location = models.CharField(max_length=255)
    ceo_name = models.CharField(max_length=255)
    ceo_dob = models.DateField()
    
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    billing_email = models.EmailField(null=True, blank=True)
    
    logo = models.ImageField(upload_to='company_logos/', null=True)
    
    subscription_tier = models.CharField(
        max_length=20,
        choices=[
            ('starter', 'Starter'),
            ('professional', 'Professional'),
            ('enterprise', 'Enterprise')
        ]
    )
    
    status = models.CharField(
        max_length=20,
        choices=[('active', 'Active'), ('inactive', 'Inactive')],
        default='active'
    )
    
    custom_domain = models.CharField(max_length=255, null=True, blank=True)
    theme_color = models.CharField(max_length=7, default='#667eea')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

---

## 📁 Project Structure

```
estateProject/
├── estateApp/                      # Main application
│   ├── models.py                   # CustomUser, Company, Estate, etc.
│   ├── views.py                    # CustomLoginView, admin_dashboard, etc.
│   ├── forms.py                    # CustomAuthenticationForm
│   ├── urls.py                     # URL routing
│   ├── middleware.py               # TenantMiddleware
│   │
│   ├── templates/
│   │   ├── login.html              # Login page (FIXED)
│   │   ├── admin_side/
│   │   │   └── admin_dashboard.html
│   │   ├── client_side/
│   │   │   └── client_dashboard.html
│   │   └── marketer_side/
│   │       └── marketer_dashboard.html
│   │
│   ├── api_views/                  # REST API views
│   ├── api_urls/                   # API URL patterns
│   ├── serializers/                # DRF serializers
│   ├── services/                   # Business logic services
│   ├── migrations/                 # Database migrations
│   └── static/
│       ├── css/
│       └── js/
│           ├── api-client.js       # API client (BASE_URL fixed to /api)
│           ├── components.js
│           └── error-handler.js
│
├── DRF/                            # Django REST Framework app
│   ├── urls.py
│   ├── api_views/
│   │   ├── auth_views.py           # Tenant admin JWT auth
│   │   └── ...
│   └── admin/
│
├── adminSupport/                   # Admin support app
│   ├── views.py
│   ├── models.py
│   └── urls.py
│
├── estateProject/                  # Project configuration
│   ├── settings.py                 # Django settings
│   ├── urls.py                     # Main URL config
│   ├── wsgi.py                     # WSGI server
│   ├── asgi.py                     # ASGI server (WebSocket)
│   └── celery_app.py              # Celery task queue
│
├── real_estate_app/               # Flutter mobile app
│   ├── lib/
│   │   ├── shared/
│   │   │   └── login.dart         # Mobile login screen
│   │   ├── admin/
│   │   ├── client/
│   │   └── marketer/
│   └── pubspec.yaml
│
├── db.sqlite3                      # SQLite database
├── manage.py                       # Django CLI
└── requirements.txt               # Python dependencies
```

---

## 🔄 Request Flow Architecture

### HTTP Request Path (Traditional Login)

```
Browser
    ↓
HTTP POST /login/
    ↓
Django URL Router (estateProject/urls.py)
    → Matches: path('', include('estateApp.urls'))
    ↓
estateApp/urls.py
    → path('login/', CustomLoginView.as_view(), name='login')
    ↓
CustomLoginView (estateApp/views.py)
    → Inherits from Django's LoginView
    → form_class = CustomAuthenticationForm
    → template_name = 'login.html'
    ↓
CustomAuthenticationForm (estateApp/forms.py)
    → Inherits from Django's AuthenticationForm
    → Expects fields: username, password
    → Validates credentials
    ↓
Django's authenticate() function
    → Queries CustomUser model
    → Checks password hash
    ↓
Success → Session created
    ↓
CustomLoginView.form_valid()
    → Records last login IP/location
    → Calls get_success_url()
    ↓
get_success_url() checks:
    → user.role
    → user.admin_level
    → Returns appropriate dashboard URL
    ↓
HTTP Redirect (302) to dashboard
    ↓
Browser follows redirect
    ↓
User sees dashboard ✅
```

### API Request Path (REST)

```
JavaScript (api-client.js)
    ↓
fetch('/api/companies/')
    ↓
Django URL Router
    → Matches: path('api/', include('estateApp.api_urls.api_urls'))
    ↓
DRF Router (DefaultRouter)
    → Registered ViewSet
    ↓
ViewSet method (list, create, update, etc.)
    ↓
Serializer (validates/transforms data)
    ↓
Database query
    ↓
JSON Response
    ↓
JavaScript receives data ✅
```

---

## 🔐 Authentication Methods

### 1. Session-Based (Traditional, for web browsers)
- Used by login.html form
- Creates Django session cookie
- User stays logged in across page reloads
- Suitable for web dashboards

### 2. Token-Based (for APIs and mobile)
- Used by REST API endpoints
- Token stored in localStorage (JavaScript) or secure storage (Flutter)
- Header: `Authorization: Bearer <token>`
- Suitable for mobile apps and SPA

### 3. JWT-Based (for Tenant Admin)
- Specialized endpoint: `/api/admin/login/`
- Issues JWT token with claims
- Claims include: user_id, admin_level, company_id, etc.
- Used by Tenant Admin Dashboard

---

## 📊 Database Models (Key Entities)

### 1. CustomUser (Authentication)
```
id, email, password_hash, first_name, last_name,
role, admin_level, company_profile_id,
last_login_ip, last_login_location,
is_active, is_staff, is_superuser,
date_joined, last_login
```

### 2. Company (Tenant)
```
id, company_name, registration_number, registration_date,
location, ceo_name, ceo_dob,
email, phone, billing_email,
logo, subscription_tier, status,
custom_domain, theme_color,
created_at, updated_at
```

### 3. Estate (Property)
```
id, company_id, name, location,
estate_size, title_deed, status,
created_at, updated_at
```

### 4. PlotAllocation (Property Assignment)
```
id, estate_id, client_id, plot_size_id, plot_number_id,
status, allocated_date, payment_status,
created_at, updated_at
```

### 5. Notification (System Messages)
```
id, user_id, title, message, type,
is_read, created_at
```

---

## 🌐 URL Mapping Overview

### Public URLs
```
GET  /                          → Home (redirects to login if not authenticated)
GET  /login/                    → Login page
POST /login/                    → Login form submission
GET  /logout/                   → Logout
GET  /register/                 → Company registration page
POST /register/                 → Company registration submission
GET  /register-user/            → Individual user registration page
POST /register-user/            → Individual user registration submission
```

### Protected URLs (require login)
```
GET  /admin_dashboard/          → Company admin dashboard
GET  /client-dashboard/         → Client dashboard
GET  /marketer-dashboard/       → Marketer dashboard
GET  /tenant-admin/dashboard/   → System admin dashboard
```

### API URLs (all under /api/)
```
GET    /api/companies/                          → List companies
GET    /api/companies/{id}/                     → Get company
POST   /api/companies/                          → Create company
PATCH  /api/companies/{id}/                     → Partial update
DELETE /api/companies/{id}/                     → Delete company

GET    /api/users/                              → List users
GET    /api/estates/                            → List estates
GET    /api/plotallocations/                    → List allocations
POST   /api/plotallocations/                    → Create allocation

GET    /api/clients/                            → List clients
GET    /api/marketers/                          → List marketers

POST   /api-token-auth/                         → Get token (token auth)
POST   /api/admin/login/                        → System admin JWT login
```

---

## 🔗 Middleware Pipeline

**File**: `estateApp/middleware.py`

### TenantMiddleware
Runs on every request:

```
1. Check if path is public (/login/, /logout/, /register/, /register-user/)
   → If yes, skip tenant checking
   ↓
2. Get authenticated user
   → If anonymous and not public path, allow but may show warning
   ↓
3. Get user's company (company_profile)
   → If user has company_profile, set it in request context
   ↓
4. Pass request to view
   ↓
5. View can access request.company (the tenant)
```

---

## 🔄 Data Flow: Login → Dashboard

### Step-by-Step

1. **User Access** → http://localhost:8000/login/
2. **Page Load** → Django renders login.html with form fields
3. **User Input** → Enters email & password
4. **Form Submit** → POST to /login/ with data
5. **Validation** → CustomAuthenticationForm checks fields exist and format is correct
6. **Authentication** → Django checks email + password against database
7. **Session** → If correct, Django creates session cookie
8. **Record** → CustomLoginView saves last_login_ip & location
9. **Redirect** → get_success_url() determines dashboard based on role
10. **Navigate** → Browser redirects to appropriate dashboard
11. **Dashboard** → Django renders dashboard HTML with user's data
12. **API Calls** → JavaScript loads dashboard data via API
13. **Display** → Dashboard shows company/client/marketer specific content

---

## 🛡️ Security Features

### Authentication Security
- ✅ Passwords hashed with PBKDF2
- ✅ Session tokens generated for web
- ✅ JWT tokens with expiration for APIs
- ✅ CSRF token validation on all POST requests
- ✅ IP address and location tracking

### Authorization Security
- ✅ Role-based access control (RBAC)
- ✅ Admin level separation (system vs company)
- ✅ Company isolation (single company visible to each user)
- ✅ Login required decorators on all protected views
- ✅ Staff member checks for admin features

### Data Security
- ✅ Input validation on all forms
- ✅ SQL injection protection (ORM)
- ✅ XSS protection (template escaping)
- ✅ HTTPS recommended for production
- ✅ Secure cookie settings

---

## 🧪 Testing Architecture

### Login Test Cases
1. ✅ Valid admin login → redirects to admin_dashboard
2. ✅ Valid client login → redirects to client-dashboard
3. ✅ Valid marketer login → redirects to marketer-dashboard
4. ✅ Invalid credentials → shows error message
5. ✅ Missing fields → shows validation error
6. ✅ User not found → shows error message

### Database Test Cases
1. ✅ Company exists with 19 users
2. ✅ 3 admins have role='admin', admin_level='company'
3. ✅ 11 clients have role='client'
4. ✅ 5 marketers have role='marketer'
5. ✅ All users linked to Lamba Real Estate

---

## 📋 Configuration Overview

### Settings (estateProject/settings.py)
- Django version: 4.x
- Database: SQLite (development) / PostgreSQL (production)
- Auth backend: CustomUserManager
- Middleware: TenantMiddleware, AuthenticationMiddleware, etc.
- REST Framework: DRF with Spectacular (API docs)
- WebSocket: Daphne ASGI server
- Celery: Background tasks

### Installed Apps
```
- django.contrib.admin
- django.contrib.auth
- django.contrib.contenttypes
- django.contrib.sessions
- django.contrib.messages
- django.contrib.staticfiles
- rest_framework
- drf_spectacular
- corsheaders
- estateApp
- DRF
- adminSupport
- Marketers
```

---

## 🚀 Deployment Architecture

### Development
```
python manage.py runserver 0.0.0.0:8000
```

### Production (Options)

**Option 1: Daphne (WebSocket support)**
```
python -m daphne -b 0.0.0.0 -p 8000 estateProject.asgi:application
```

**Option 2: Gunicorn (HTTP)**
```
gunicorn estateProject.wsgi:application --bind 0.0.0.0:8000
```

**Option 3: Nginx + Gunicorn**
```
Nginx (reverse proxy, static files) → Gunicorn (Python application)
```

---

## 📱 Flutter Mobile Integration

### Mobile Login Flow
1. User opens Flutter app
2. App shows login screen
3. User enters email + password
4. App calls: `POST /api-token-auth/` with email/password
5. Backend returns auth token
6. App stores token in secure storage
7. App makes all API requests with: `Authorization: Bearer <token>`
8. Backend validates token and returns data
9. App displays user's specific dashboard

### Token Persistence
- Stored securely in device storage
- Refreshed on app startup
- Cleared on logout
- Automatic re-authentication if expired

---

## 🔗 Key Configuration Files

| File | Purpose | Key Content |
|------|---------|-------------|
| `settings.py` | Django configuration | DEBUG, DATABASES, INSTALLED_APPS, MIDDLEWARE |
| `urls.py` | URL routing | path patterns for all endpoints |
| `models.py` | Database schema | CustomUser, Company, Estate, etc. |
| `views.py` | Business logic | View classes and functions (6481 lines!) |
| `forms.py` | Form validation | CustomAuthenticationForm |
| `middleware.py` | Request processing | TenantMiddleware for company isolation |
| `serializers/` | API validation | DRF serializers for REST endpoints |
| `api_urls/` | API routing | REST Framework router configuration |
| `templates/login.html` | UI | Login page (HTML template) |

---

## 🎓 Learning Path

1. **Start**: Read this document (overview)
2. **Deep Dive**: 
   - Read `estateApp/models.py` (understand data structure)
   - Read `estateApp/views.py` (understand business logic)
   - Read `estateApp/forms.py` (understand validation)
3. **Integration**:
   - Read `estateApp/middleware.py` (understand request pipeline)
   - Read `estateApp/api_urls/api_urls.py` (understand API)
4. **Advanced**:
   - Read `DRF/admin/api_views/auth_views.py` (JWT authentication)
   - Explore celery_app.py (background tasks)
   - Explore `static/js/` (frontend integration)

---

## ✅ What's Been Fixed Today

1. **API Configuration**: Changed `/api/v1` → `/api` in api-client.js
2. **Login Form**: Changed `email` field → `username` field
3. **Error Display**: Added form error messages to login template
4. **UX**: Added autofocus to email field
5. **Documentation**: Created comprehensive guides

---

**Version**: 1.0
**Last Updated**: 2025-11-20
**Status**: ✅ System Operational

