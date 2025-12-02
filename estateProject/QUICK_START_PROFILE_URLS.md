# 🔐 SECURITY FIX: QUICK START GUIDE

## The Problem
Data was leaking between companies via profile URLs:
- `http://127.0.0.1:8000/client_profile/90/` - Anyone could access any client's data
- `http://127.0.0.1:8000/admin-marketer/15/` - Anyone could access any marketer's data

## The Solution
Now all profile URLs REQUIRE company context:

### ✅ CORRECT URLs (SECURE)
```
http://127.0.0.1:8000/victor-godwin.client-profile?company=lamba-real-homes
http://127.0.0.1:8000/victor-godwin.marketer-profile?company=lamba-real-homes
```

### ❌ WRONG URLs (BLOCKED)
```
http://127.0.0.1:8000/client_profile/90/          - Will return Http404
http://127.0.0.1:8000/admin-marketer/15/          - Will return Http404
```

---

## Implementation in Templates

### Step 1: Load the template tags
```django
{% load profile_tags %}
```

### Step 2: Use the profile filters or tags

#### Option 1: Using Filters (Simple)
```django
<!-- Generate URL only -->
<a href="{{ client|client_profile_url:company }}">{{ client.full_name }}</a>

<!-- Generates: /victor-godwin.client-profile?company=lamba-real-homes -->
```

#### Option 2: Using Tags (Full HTML)
```django
<!-- Generate complete link -->
{% client_profile_link client company "btn btn-primary" %}

<!-- Generates: <a href="/victor-godwin.client-profile?company=lamba-real-homes" class="btn btn-primary">Victor Godwin</a> -->
```

#### Option 3: Manual URL Construction
```django
<!-- If you prefer full control -->
<a href="/{{ client.full_name|name_slug }}.client-profile?company={{ company.slug }}">
  {{ client.full_name }}
</a>
```

---

## Available Template Filters & Tags

### Filters (Use with |)
```django
{{ user.full_name|name_slug }}
→ victor-godwin

{{ client|client_profile_url:company }}
→ /victor-godwin.client-profile?company=lamba-real-homes

{{ marketer|marketer_profile_url:company }}
→ /victor-godwin.marketer-profile?company=lamba-real-homes
```

### Tags (Use with {% %})
```django
{% client_profile_link client company "css-class" %}
→ <a href="/victor-godwin.client-profile?company=lamba-real-homes" class="css-class">Victor Godwin</a>

{% marketer_profile_link marketer company "css-class" %}
→ <a href="/victor-godwin.marketer-profile?company=lamba-real-homes" class="css-class">Victor Godwin</a>
```

---

## Real-World Examples

### Example 1: Client List
```django
{% load profile_tags %}

<table>
  <tbody>
    {% for client in clients %}
    <tr>
      <td>{{ client.full_name }}</td>
      <td>{{ client.email }}</td>
      <td>
        <a href="{{ client|client_profile_url:company }}" class="btn btn-sm btn-info">
          View Profile
        </a>
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
```

### Example 2: Marketer Card
```django
{% load profile_tags %}

<div class="marketer-card">
  <h3>{{ marketer.full_name }}</h3>
  <p>Email: {{ marketer.email }}</p>
  <p>Clients: {{ marketer.client_count }}</p>
  {% marketer_profile_link marketer company "btn btn-primary" %}
</div>
```

### Example 3: Admin Dashboard
```django
{% load profile_tags %}

<div class="dashboard">
  <!-- Client Section -->
  <section>
    <h2>Top Client</h2>
    {% if top_client %}
      {% client_profile_link top_client company "link-primary" %}
    {% endif %}
  </section>

  <!-- Marketer Section -->
  <section>
    <h2>Top Marketer</h2>
    {% if top_marketer %}
      {% marketer_profile_link top_marketer company "link-success" %}
    {% endif %}
  </section>
</div>
```

---

## Python/Views Usage

### In Views
```python
from estateApp.views import generate_name_slug

# Generate slug for a user
slug = generate_name_slug(user.full_name)
# "Victor Godwin" → "victor-godwin"

# Build profile URL
profile_url = f"/{slug}.client-profile?company={company.slug}"
# "/victor-godwin.client-profile?company=lamba-real-homes"
```

### In Context Passing
```python
def client_list(request):
    company = request.user.company_profile
    clients = ClientUser.objects.filter(company_profile=company)
    
    context = {
        'clients': clients,
        'company': company,  # Pass to template
    }
    
    return render(request, 'client_list.html', context)
```

---

## URL Formats Reference

### Legacy Format (Deprecated)
```
/client_profile/<pk>/?company=<slug>
/admin-marketer/<pk>/?company=<slug>
```
✅ Still works but not recommended

### Modern Format (RECOMMENDED)
```
/<name>.client-profile?company=<slug>
/<name>.marketer-profile?company=<slug>
```
✅ Uses human-readable names
✅ More SEO-friendly
✅ Better security

### Company-Namespaced Format
```
/<company-slug>/client/<name>/
/<company-slug>/marketer/<name>/
```
✅ Shows company context in URL

---

## Troubleshooting

### Problem: Links appear empty or as "#"
**Solution:** Check that company object is passed to template:
```django
<!-- ❌ Wrong -->
{{ client|client_profile_url }}

<!-- ✅ Right -->
{{ client|client_profile_url:company }}
```

### Problem: Links are showing wrong company
**Solution:** Verify company passed to template is correct:
```python
# In view
context = {
    'client': client,
    'company': request.user.company_profile,  # Make sure this is set
}
```

### Problem: Http404 when accessing profile
**Solution:** URL must include company parameter:
```
✅ /victor-godwin.client-profile?company=lamba-real-homes
❌ /victor-godwin.client-profile
```

### Problem: Special characters in names break URL
**Solution:** The `name_slug` filter handles this:
```
"O'Brien" → "obrien"
"José García" → "josé-garcía" → "jos-garcía" (special chars removed)
```

---

## Testing Your Changes

### Test in Browser
1. Get a client's slug: `Victor Godwin` → `victor-godwin`
2. Get company slug: `Lamba Real Homes` → `lamba-real-homes`
3. Navigate to: `/victor-godwin.client-profile?company=lamba-real-homes`
4. Should see profile ✅

### Test Access Control
```
# Try accessing without company param
/victor-godwin.client-profile
→ Http404 (expected)

# Try accessing from wrong company
/victor-godwin.client-profile?company=wrong-company
→ Http403 (access denied, expected)
```

---

## 🎯 Key Takeaways

1. **Always include company parameter** in profile URLs
2. **Use template tags/filters** for secure URL generation
3. **Never expose user IDs** directly in URLs (use name slugs)
4. **Company context is REQUIRED** - no implicit defaults
5. **Test access control** - verify cross-company access is blocked

---

## Need Help?

See full documentation: `DATA_LEAKAGE_FIX_DOCUMENTATION.md`
Run security tests: `python manage.py shell < test_data_leakage.py`
