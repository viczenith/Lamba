# Personalized URL System (Facebook-Style)

## Overview
The system now supports personalized URLs with user slugs in the address bar, similar to Facebook.

## Examples
- **Admin**: `http://127.0.0.1:8000/akorvikkyy/admin-dashboard/`
- **Marketer**: `http://127.0.0.1:8000/viczenithgodwin/marketer-dashboard/`
- **Client**: `http://127.0.0.1:8000/victorgodwinakor/client-dashboard/`

## How It Works

### 1. Automatic Slug Generation
- Every user gets a unique slug auto-generated from their email username
- Example: `victorgodwin@gmail.com` → `/victorgodwin/`
- Handles duplicates by appending numbers: `/victorgodwin-1/`, `/victorgodwin-2/`

### 2. Middleware Security
Two middleware layers provide complete protection:

#### SlugValidationMiddleware
- Validates that the slug in the URL belongs to the logged-in user
- Prevents users from accessing other users' personalized URLs
- Raises 404 for unauthorized access attempts
- Enforces tenant isolation (company-level security)

#### PersonalizedURLMiddleware  
- Auto-redirects generic URLs to personalized versions
- Example: `/admin-dashboard` → `/victor.godwin/admin-dashboard/`
- Maintains query parameters during redirection
- Skips public pages (login, static files, etc.)

### 3. Template Tags
Use the `personalized_url` template tag to generate correct URLs:

```django
{% load personalized_urls %}

<a href="{% personalized_url 'admin-dashboard' %}">Dashboard</a>
<!-- Outputs: /victor.godwin/admin-dashboard/ -->
```

## Security Features

### ✅ Protection Against:
1. **URL Manipulation** - Users cannot access `/another-user/dashboard/`
2. **Cross-Tenant Access** - Company isolation enforced
3. **Session Hijacking** - Slug ownership validated on every request
4. **Direct URL Bypass** - Middleware intercepts all requests

### 🔒 Validation Flow:
```
Request → Check Authentication → Validate Slug → Check Company → Allow/Deny
```

## URL Mappings

### Admin URLs
- `/user-slug/admin-dashboard/` - Dashboard
- `/user-slug/user-registration/` - Register Users
- `/user-slug/marketer-list/` - View Marketers
- `/user-slug/client-list/` - View Clients
- `/user-slug/plot-allocation/` - Allocate Plots
- `/user-slug/add-estate/` - Add Estate
- `/user-slug/view-estate/` - View Estates

### Marketer URLs
- `/user-slug/marketer-dashboard/` - Dashboard
- `/user-slug/marketer-profile/` - Profile
- `/user-slug/client-records/` - Client Records

### Client URLs
- `/user-slug/client-dashboard/` - Dashboard
- `/user-slug/my-client-profile/` - Profile
- `/user-slug/client-records/` - Records

## Configuration

### Settings (already configured)
```python
MIDDLEWARE = [
    ...
    'estateApp.middleware.SlugValidationMiddleware',
    'estateApp.middleware.PersonalizedURLMiddleware',
    ...
]
```

### Models
```python
class CustomUser(AbstractUser):
    slug = models.SlugField(max_length=100, unique=True, null=True, blank=True)
```

## Testing

### 1. Login as different users:
```
Admin: akorvikkyy@gmail.com / markgodwin001
Marketer: viczenithgodwin@gmail.com / markmarketer001  
Client: victorgodwinakor@gmail.com / victorclient001
```

### 2. Check URLs in browser:
- Notice the username appears in the address bar
- Try accessing another user's URL → Should get 404
- Navigate through sidebar → URLs update with your slug

### 3. Test Security:
```
# Login as admin (akorvikkyy)
# Try to access: /victorgodwinakor/client-dashboard/
# Result: 404 - Unauthorized access attempt detected
```

## Generate Slugs for Existing Users

Run this to generate slugs for all users:
```python
python manage.py shell
>>> from estateApp.models import CustomUser
>>> for user in CustomUser.objects.all():
...     user.save()  # Triggers auto-slug generation
```

## Benefits

1. **User Visibility** - Users see their identity in the URL
2. **Branded Experience** - Professional, personalized feel
3. **Security** - Multiple layers of validation
4. **SEO Friendly** - Clean, readable URLs
5. **Tenant Isolation** - Company data never leaks
6. **Shareable** - Each user has unique URL namespace

## Future Enhancements

- Public profile pages (optional): `/users/victor.godwin/`
- Custom slug editing (let users choose their slug)
- Analytics per user slug
- Slug history/aliases
