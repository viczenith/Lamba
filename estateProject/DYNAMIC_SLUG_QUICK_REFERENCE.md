# Quick Reference: Dynamic Slug Routing & Security

## 🎯 URL Pattern Examples

```
Static Route (Old):
  /admin-dashboard

Dynamic Route (New):
  /victor-godwin-ventures/dashboard
  /green-estate-homes/dashboard
  /blue-sky-properties/dashboard

URL Pattern:
  path('<slug:company_slug>/dashboard/', secure_company_slug(admin_dashboard), name='company-dashboard')
```

---

## 🔐 Three Security Decorators

### 1. `@company_slug_required` - Standard
```python
@company_slug_required
def my_view(request, company_slug):
    # 4 security layers:
    # - Slug format validation
    # - Company existence check
    # - User authentication
    # - Company access verification
    company = request.company  # Safe to use
```

### 2. `@company_slug_context` - Minimal (for registration)
```python
@company_slug_context
def my_view(request, company_slug=None):
    # Only injects company context
    # No access verification
    if request.company:
        # Company-branded view
```

### 3. `@secure_company_slug` - Maximum (Recommended)
```python
@secure_company_slug
def my_view(request, company_slug):
    # 6 security layers:
    # - Slug format validation
    # - Company existence check
    # - User authentication
    # - Company access verification
    # - Subscription status check
    # - Rate limiting
    company = request.company  # Maximum security
```

---

## ✅ Checklist: Using Slug Routing

### In URL Patterns
- [ ] Add `<slug:company_slug>` to path
- [ ] Wrap view with decorator (`@secure_company_slug` recommended)
- [ ] Provide name (e.g., `'company-dashboard'`)

### In Views
- [ ] Add `company_slug` parameter to function signature
- [ ] Use `request.company` instead of querying
- [ ] ALWAYS verify object belongs to company: `Model.objects.get(id=pk, company=request.company)`
- [ ] Never trust user-provided company reference

### In Templates
- [ ] Use `{% url %}` tag with company_slug parameter
- [ ] Or use helper filter: `{{ request.company|company_url:'path' }}`
- [ ] Never hardcode slugs in templates

### In Queries
```python
# ❌ WRONG - Could access other company's data
client = Client.objects.get(id=client_id)

# ✅ CORRECT - Restricted to current company
client = Client.objects.get(id=client_id, company=request.company)
```

---

## 🛡️ Security Layers (6 Total)

```
┌─────────────────────────────────────┐
│ Layer 1: Slug Format Validation     │ (3-50 chars, lowercase, hyphens only)
├─────────────────────────────────────┤
│ Layer 2: Company Existence          │ (Company must exist in DB)
├─────────────────────────────────────┤
│ Layer 3: User Authentication        │ (User must be logged in)
├─────────────────────────────────────┤
│ Layer 4: Company Access Verification│ (User must belong to company)
├─────────────────────────────────────┤
│ Layer 5: Subscription Status        │ (Company subscription must be active)
├─────────────────────────────────────┤
│ Layer 6: Rate Limiting              │ (User not exceeding request limits)
└─────────────────────────────────────┘
        ↓
    FULL ACCESS GRANTED
```

---

## 📝 Common View Pattern

```python
from django.shortcuts import render, get_object_or_404
from .dynamic_slug_routing import secure_company_slug
from .models import Client

@secure_company_slug
def client_detail(request, company_slug, client_id):
    """View details for a specific client"""
    
    # request.company is already verified and safe
    company = request.company
    
    # Always verify object belongs to company
    client = get_object_or_404(
        Client,
        id=client_id,
        company=company  # ← Critical security check
    )
    
    context = {
        'company': company,
        'client': client,
    }
    return render(request, 'client/detail.html', context)
```

---

## 🔗 Template URL Pattern

### Old Way (Without Slug)
```html
<a href="{% url 'client-detail' pk=client.id %}">
  View Client
</a>
```

### New Way (With Slug)
```html
<a href="{% url 'company-client-detail' company_slug=request.company_slug client_id=client.id %}">
  View Client
</a>
```

### Using Helper Filter (Recommended)
```html
{% load slug_tags %}
<a href="{{ request.company|company_url:'clients' }}">
  Clients
</a>
<a href="{{ request.company|company_url }}/clients/{{ client.id }}/">
  View Client
</a>
```

---

## 🧪 Testing Slug Routes

```python
from django.test import TestCase, Client as TestClient
from estateApp.models import Company, CustomUser

class SlugRoutingTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(
            company_name="Test Company",
            slug="test-company",
        )
        self.user = CustomUser.objects.create_user(
            username="admin",
            email="admin@test.com",
            company=self.company,
            is_staff=True,
        )
        self.client = TestClient()
    
    def test_valid_slug_access(self):
        """User can access their company dashboard"""
        self.client.force_login(self.user)
        response = self.client.get('/test-company/dashboard/')
        self.assertEqual(response.status_code, 200)
    
    def test_invalid_slug_returns_404(self):
        """Invalid slug returns 404"""
        response = self.client.get('/nonexistent-slug/dashboard/')
        self.assertEqual(response.status_code, 404)
    
    def test_cross_company_denied(self):
        """User cannot access another company"""
        company2 = Company.objects.create(
            company_name="Other Company",
            slug="other-company",
        )
        self.client.force_login(self.user)
        response = self.client.get('/other-company/dashboard/')
        self.assertEqual(response.status_code, 403)
    
    def test_unauthenticated_redirected(self):
        """Unauthenticated user redirected to login"""
        response = self.client.get('/test-company/dashboard/')
        self.assertRedirects(response, '/test-company/login/')
```

---

## 🚀 Slug Utilities

### Generate Slug from Company Name
```python
from estateApp.dynamic_slug_routing import SlugManager

slug = SlugManager.generate_unique_slug("Victor Godwin Ventures")
# Result: "victor-godwin-ventures"
```

### Build Company URL
```python
from estateApp.dynamic_slug_routing import get_company_url, get_company_absolute_url

# Relative URL
url = get_company_url(company, 'dashboard')
# Result: "/victor-godwin-ventures/dashboard"

# Absolute URL (with domain)
url = get_company_absolute_url(request, company, 'dashboard')
# Result: "https://realestateapp.com/victor-godwin-ventures/dashboard"
```

### Validate Slug Format
```python
from estateApp.dynamic_slug_routing import SlugValidator

is_valid = SlugValidator.is_valid('victor-godwin-ventures')  # True
is_valid = SlugValidator.is_valid('INVALID')                 # False
is_valid = SlugValidator.is_valid('admin')                   # False (reserved)
```

---

## 🎯 Common Errors & Fixes

### Error 1: "Slug must be included in URL pattern"
**Fix:** Add `<slug:company_slug>` to path
```python
# ❌ Wrong
path('dashboard/', my_view)

# ✅ Correct
path('<slug:company_slug>/dashboard/', my_view)
```

### Error 2: "View doesn't accept company_slug parameter"
**Fix:** Add parameter to view function
```python
# ❌ Wrong
def my_view(request):

# ✅ Correct
def my_view(request, company_slug):
```

### Error 3: "Company not found" (404 instead of rendering)
**Fix:** Decorator validates company before view is called
```python
# ✅ Decorator does the validation
@secure_company_slug
def my_view(request, company_slug):
    # If company doesn't exist, decorator returns 404
    # You don't need to validate again
```

### Error 4: "Can access other company's data"
**Fix:** Always filter by company in queries
```python
# ❌ Wrong
client = Client.objects.get(id=client_id)

# ✅ Correct
client = Client.objects.get(id=client_id, company=request.company)
```

---

## 🔍 Debugging

### Check if Middleware is Added
```python
# In Django shell:
from django.conf import settings
print('CompanySlugContextMiddleware' in settings.MIDDLEWARE)
```

### Verify Company Context in View
```python
@secure_company_slug
def debug_view(request, company_slug):
    print(f"URL Slug: {company_slug}")
    print(f"Request Company: {request.company}")
    print(f"Request Company Slug: {request.company_slug}")
    print(f"User: {request.user}")
    print(f"User Company: {request.user.company}")
    print(f"Match: {request.company == request.user.company}")
```

### Check Slug Validation
```python
from estateApp.dynamic_slug_routing import SlugValidator

test_slugs = [
    'victor-godwin-ventures',  # Valid
    'green-estate-homes',       # Valid
    'admin',                    # Invalid (reserved)
    'UPPERCASE',                # Invalid (not lowercase)
    'with--double',             # Invalid (consecutive hyphens)
]

for slug in test_slugs:
    print(f"{slug}: {SlugValidator.is_valid(slug)}")
```

---

## 📊 Performance Tips

### 1. Use select_related for Company
```python
# Single query
company = Company.objects.select_related('subscription_billing').get(slug=slug)

# vs Multiple queries
company = Company.objects.get(slug=slug)
subscription = company.subscription_billing  # Extra query!
```

### 2. Cache Company Lookups
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
@secure_company_slug
def expensive_view(request, company_slug):
    # Only computed once every 5 minutes
```

### 3. Use Database Indexing
```python
# Already indexed in model:
slug = models.SlugField(db_index=True)
```

---

## 🔗 Related Documentation

- **Implementation Guide:** `DYNAMIC_SLUG_IMPLEMENTATION_GUIDE.md`
- **URL Patterns:** `DYNAMIC_SLUG_URL_PATTERNS.py`
- **Routing Module:** `estateApp/dynamic_slug_routing.py`
- **Tests:** `estateApp/tests/test_slug_routing.py`

---

## 🚀 Quick Start (5 minutes)

1. **Add Middleware:**
   ```python
   # settings.py
   'estateApp.dynamic_slug_routing.CompanySlugContextMiddleware',
   ```

2. **Generate Slugs:**
   ```bash
   python manage.py shell
   from estateApp.dynamic_slug_routing import SlugMigration
   SlugMigration.bulk_generate_slugs()
   ```

3. **Update URL:**
   ```python
   path('<slug:company_slug>/dashboard/', secure_company_slug(admin_dashboard), name='company-dashboard')
   ```

4. **Update View:**
   ```python
   @secure_company_slug
   def admin_dashboard(request, company_slug):
       company = request.company
   ```

5. **Update Template:**
   ```html
   <a href="{% url 'company-dashboard' company_slug=request.company_slug %}">
   ```

**Done! Your first dynamic slug route is ready.** 🎉

---

## ✅ Status

✓ Production Ready
✓ Maximum Security (6 layers)
✓ Easy to Implement (decorators)
✓ Well Documented (this guide)
✓ Fully Tested (see test suite)
✓ Performance Optimized

Ready to implement! 🚀
