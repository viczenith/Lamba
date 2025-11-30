# Quick Reference: Company-Specific User IDs

## 🎯 What This System Does

Each marketer and client gets a **unique ID per company** they work with.

**Example:**
- Victor works for Lamba Property Limited → Gets ID: `LPLMKT001`
- Victor is added to Lamba Real Homes → Gets NEW ID: `LRHMKT001`
- Same person, different companies = different IDs

## 📊 ID Format

### Marketer IDs
```
{COMPANY_PREFIX}MKT{NUMBER:03d}
Example: LPLMKT001, LRHMKT003
```

### Client IDs
```
{COMPANY_PREFIX}CLT{NUMBER:03d}
Example: LPLCLT001, LRHMKT007
```

### Company Prefixes
- Lamba Property Limited → `LPL`
- Lamba Real Homes → `LRH`
- [Other Company] → First 3 letters uppercase

## 🚀 How to Use

### Look Up Marketer by Company ID

```python
# Get company
company = Company.objects.get(slug='lamba-property-limited')

# Method 1: By numeric ID
marketer = company.get_marketer_by_company_id(1)

# Method 2: By UID string
marketer = company.get_marketer_by_company_uid('LPLMKT001')

# Get full profile info
profile = company.get_marketer_profile(marketer)
print(profile.company_marketer_uid)  # LPLMKT001
print(profile.company_marketer_id)    # 1
```

### Look Up Client by Company ID

```python
company = Company.objects.get(slug='lamba-property-limited')

# Method 1: By numeric ID
client = company.get_client_by_company_id(5)

# Method 2: By UID string
client = company.get_client_by_company_uid('LPLCLT005')

# Get full profile info
profile = company.get_client_profile(client)
```

### Get All Marketers in a Company

```python
company = Company.objects.get(slug='lamba-property-limited')

# Get all marketer profiles
for profile in company.marketer_profiles.all():
    print(f"{profile.marketer.full_name}: {profile.company_marketer_uid}")

# Output:
# Victor marketer 3: LPLMKT001
# John Doe: LPLMKT002
# Jane Smith: LPLMKT003
```

### Get All Clients in a Company

```python
company = Company.objects.get(slug='lamba-property-limited')

# Get all client profiles
for profile in company.client_profiles.all():
    print(f"{profile.client.full_name}: {profile.company_client_uid}")

# Output:
# Victor client2: LPLCLT001
# Victor Client: LPLCLT002
# Victor Client 4: LPLCLT003
```

## 🔄 Automatic ID Generation

### When Creating a New Marketer

```python
# When you create a MarketerUser with company_profile
marketer = MarketerUser.objects.create(
    email='victor@example.com',
    full_name='Victor',
    company_profile=company,  # ← Triggers auto-creation
)
# CompanyMarketerProfile is automatically created!
# Profile: LPLMKT001 (if company is Lamba Property Limited)
```

### When Adding to New Company

```python
from estateApp.models import MarketerAffiliation

# Create affiliation
affiliation = MarketerAffiliation.objects.create(
    marketer=victor,
    company=lamba_real_homes,  # ← Triggers signal
)
# CompanyMarketerProfile automatically created for Lamba Real Homes!
# Profile: LRHMKT001 (new company = new ID)
```

## 📋 Database Tables

### CompanyMarketerProfile
Stores marketer IDs per company:
- `company_marketer_id`: Sequential (1, 2, 3, ...)
- `company_marketer_uid`: Human-readable (LPLMKT001, LPLMKT002, ...)

### CompanyClientProfile
Stores client IDs per company:
- `company_client_id`: Sequential (1, 2, 3, ...)
- `company_client_uid`: Human-readable (LPLCLT001, LPLCLT002, ...)

## 🔧 Management Commands

### Generate Profiles for Existing Users

```bash
# Preview what will be generated
python manage.py generate_company_user_profiles --dry-run

# Actually generate
python manage.py generate_company_user_profiles

# For specific company only
python manage.py generate_company_user_profiles --company 1
```

## ✅ Key Benefits

✅ **No Conflicts**: Same ID number can exist in different companies
✅ **Multi-Company**: One person can work for many companies with different IDs
✅ **Automatic**: IDs are generated automatically, no manual work
✅ **Unique**: Each (user, company) pair has exactly one ID
✅ **Readable**: UIDs are human-friendly with company prefix
✅ **Fast**: Indexed database fields for quick lookups
✅ **Safe**: Atomic operations prevent race conditions

## 🐛 Troubleshooting

### "No profile found for marketer in this company"
The marketer hasn't been affiliated with this company yet.
```python
# Solution: Create affiliation
MarketerAffiliation.objects.create(marketer=marketer, company=company)
# Profile will be created automatically
```

### "Marketer shows in dropdown but has wrong client count"
Client might be assigned to a different company context.
```python
# Check: Is the client in the same company?
client.company_profile  # Should match the company you're looking at
```

### "ID is not unique"
Shouldn't happen, but if it does, regenerate:
```bash
python manage.py generate_company_user_profiles
```

## 📚 Full Documentation

See `COMPANY_SPECIFIC_USER_IDS.md` for complete details including:
- Detailed architecture
- Database schema
- Signal handlers
- All method signatures
- Troubleshooting guide
- Future enhancements

## 🧪 Run Tests

```bash
python test_company_user_ids.py
```

All 3 tests should pass ✅

---

**Quick Summary**: Every marketer/client gets a unique ID in each company. IDs are auto-generated. Use company.get_marketer_by_company_id() or company.get_client_by_company_id() to look them up.
