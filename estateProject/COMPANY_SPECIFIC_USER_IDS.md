# Company-Specific User ID System

## Overview

This system ensures that each marketer and client has **unique, company-specific IDs and UIDs** for each company they are associated with. This prevents confusion and allows the same person to work with multiple companies while maintaining separate identity credentials in each company context.

## Key Concepts

### CompanyMarketerProfile
Stores company-specific information for each marketer per company:
- `company_marketer_id`: Sequential number unique within the company (e.g., 1, 2, 3, ...)
- `company_marketer_uid`: Human-readable unique ID with company prefix (e.g., `LPLMKT001`, `LRHMKT001`)

### CompanyClientProfile
Stores company-specific information for each client per company:
- `company_client_id`: Sequential number unique within the company (e.g., 1, 2, 3, ...)
- `company_client_uid`: Human-readable unique ID with company prefix (e.g., `LPLCLT001`, `LRHMKT002`)

## How It Works

### ID Generation Process

When a marketer or client is added to a company:

1. **Primary Company Assignment**: When a MarketerUser or ClientUser is created with a `company_profile`, a CompanyMarketerProfile or CompanyClientProfile is automatically created
2. **Sequential ID Assignment**: The system generates the next available sequential ID for that company
3. **Prefix Generation**: The company prefix (e.g., "LPL" for Lamba Property Limited) is extracted from the company name
4. **UID Creation**: The UID is formatted as `{PREFIX}{TYPE}{ID:03d}` (e.g., `LPLMKT001`)

### Multi-Company Support

When an existing marketer is affiliated with a new company via MarketerAffiliation:

1. **Signal Handler Triggered**: The `create_company_marketer_profile_on_affiliation` signal handler detects the new affiliation
2. **New Profile Created**: A new CompanyMarketerProfile is created for this marketer in the new company
3. **Unique IDs Generated**: The marketer gets completely new IDs in the new company context
4. **No Conflicts**: The same marketer can have different IDs in each company (e.g., `LPLMKT001` in LPL, `LRHMKT003` in LRH)

## Example Scenario

**Marketer**: Victor (akorvikkyy@gmail.com)

### Initially added to Lamba Property Limited:
```
CompanyMarketerProfile:
  marketer: Victor
  company: Lamba Property Limited
  company_marketer_id: 1
  company_marketer_uid: LPLMKT001
```

### Later affiliated with Lamba Real Homes:
```
New CompanyMarketerProfile automatically created:
  marketer: Victor
  company: Lamba Real Homes
  company_marketer_id: 1 (starts fresh for new company)
  company_marketer_uid: LRHMKT001
```

**Result**: Victor has 2 unique identities:
- `LPLMKT001` in Lamba Property Limited
- `LRHMKT001` in Lamba Real Homes

## API & Lookup Methods

### Company Model Helper Methods

#### Get Marketer by Company ID
```python
marketer = company.get_marketer_by_company_id(1)
# Returns: The marketer with company_marketer_id=1 in this company
```

#### Get Marketer by Company UID
```python
marketer = company.get_marketer_by_company_uid('LPLMKT001')
# Returns: The marketer with UID 'LPLMKT001' in this company
```

#### Get Client by Company ID
```python
client = company.get_client_by_company_id(5)
# Returns: The client with company_client_id=5 in this company
```

#### Get Client by Company UID
```python
client = company.get_client_by_company_uid('LPLCLT005')
# Returns: The client with UID 'LPLCLT005' in this company
```

#### Get Profile Information
```python
profile = company.get_marketer_profile(marketer)
# Returns: CompanyMarketerProfile with all details

profile = company.get_client_profile(client)
# Returns: CompanyClientProfile with all details
```

## Database Schema

### CompanyMarketerProfile Table
```
id                      BigAutoField (PK)
marketer_id            ForeignKey(MarketerUser)
company_id             ForeignKey(Company)
company_marketer_id    PositiveInteger (indexed)
company_marketer_uid   CharField, unique (indexed)
created_at             DateTimeField
updated_at             DateTimeField

Constraints:
- UNIQUE(marketer, company) - Each marketer can have only one profile per company
- INDEX(company, company_marketer_id)
- INDEX(marketer, company)
```

### CompanyClientProfile Table
```
id                  BigAutoField (PK)
client_id          ForeignKey(ClientUser)
company_id         ForeignKey(Company)
company_client_id  PositiveInteger (indexed)
company_client_uid CharField, unique (indexed)
created_at         DateTimeField
updated_at         DateTimeField

Constraints:
- UNIQUE(client, company) - Each client can have only one profile per company
- INDEX(company, company_client_id)
- INDEX(client, company)
```

## Automatic Profile Creation

### For Primary Company
When a MarketerUser or ClientUser is saved with a `company_profile`:
- `save()` method automatically creates/updates CompanyMarketerProfile or CompanyClientProfile
- IDs are generated atomically using CompanySequence for race-safety

### For Affiliated Companies
When a MarketerAffiliation is created:
- Signal handler `create_company_marketer_profile_on_affiliation` is triggered
- New CompanyMarketerProfile is created with fresh IDs for the affiliated company

## Managing Existing Users

### Migration Command
```bash
python manage.py generate_company_user_profiles
```

Generates CompanyMarketerProfile and CompanyClientProfile for all existing users.

#### Options:
- `--company <id>`: Generate profiles only for specific company
- `--dry-run`: Preview changes without making them

#### Example Output:
```
Processing 4 marketers...
  ✓ CREATE: Victor marketer 3 in Lamba Property Limited → LPLMKT001
  ✓ CREATE: Victor marketer 3 in Lamba Real Homes → LRHMKT001
  ✓ CREATE: Victor Marketer in Lamba Property Limited → LPLMKT002
  ✓ CREATE: Victor Marketer in Lamba Real Homes → LRHMKT002
```

## Implementation Details

### Backward Compatibility
- Existing `company_marketer_id` and `company_marketer_uid` fields on MarketerUser/ClientUser are maintained
- These represent the **primary company** IDs for backward compatibility
- New CompanyMarketerProfile/CompanyClientProfile tables provide company-specific IDs

### Race Condition Safety
- Uses `CompanySequence.get_next()` with `SELECT FOR UPDATE` to atomically generate IDs
- Guarantees no duplicate IDs within a company

### Uniqueness Guarantees
- `company_marketer_uid` is globally unique (can't have same UID in two companies)
- `company_client_uid` is globally unique (can't have same UID in two companies)
- `(marketer, company)` pair is unique - each marketer has at most one profile per company
- `(client, company)` pair is unique - each client has at most one profile per company

## Data Isolation

The system maintains strict company isolation:
- Dropping a marketer from one company doesn't affect their IDs in other companies
- Marketers/clients are visible in dropdowns based on their MarketerAffiliation or company assignment
- No cross-company ID conflicts are possible

## Views and Dropdowns

### Current Implementation (Updated)
```python
def get_all_marketers_for_company(company_obj):
    """
    Get all marketers for a company with their company-specific client counts.
    """
    affiliation_marketer_ids = MarketerAffiliation.objects.filter(
        company=company_obj
    ).values_list('marketer_id', flat=True).distinct()
    
    if affiliation_marketer_ids:
        marketers = CustomUser.objects.filter(
            id__in=affiliation_marketer_ids
        )
    else:
        marketers = CustomUser.objects.none()
    
    # Can also lookup by CompanyMarketerProfile for additional data:
    profiles = CompanyMarketerProfile.objects.filter(company=company_obj)
    # profiles[0].company_marketer_uid, profiles[0].company_marketer_id
```

## Future Enhancements

1. **API Endpoints**: Add `/api/users/{company_id}/marketers/{company_marketer_uid}/`
2. **Import/Export**: Handle company-specific IDs in bulk operations
3. **Audit Logging**: Track when users are added to new companies
4. **Commission Tracking**: Use company-specific IDs for commission calculations
5. **Reporting**: Generate reports filtered by company-specific user IDs

## Troubleshooting

### Profile Not Created for New Affiliation
```python
# Manually trigger creation:
from estateApp.models import MarketerAffiliation, CompanyMarketerProfile

affiliation = MarketerAffiliation.objects.get(id=123)
profile = CompanyMarketerProfile.objects.create(
    marketer=affiliation.marketer,
    company=affiliation.company,
    company_marketer_id=1,
    company_marketer_uid='LPLMKT001'
)
```

### Fix Duplicate or Invalid UIDs
```bash
# Run migration with dry-run first:
python manage.py generate_company_user_profiles --dry-run

# Fix all issues:
python manage.py generate_company_user_profiles
```

### Check Current Profiles
```python
from estateApp.models import CompanyMarketerProfile

# View all marketers in a company with their profiles:
for profile in company.marketer_profiles.all():
    print(f"{profile.marketer.full_name}: {profile.company_marketer_uid}")
```

## Reference

- **Migration**: `0086_company_user_profiles.py`
- **Models**: `CompanyMarketerProfile`, `CompanyClientProfile`
- **Signal Handler**: `create_company_marketer_profile_on_affiliation`
- **Management Command**: `generate_company_user_profiles`
- **Company Methods**: `get_marketer_by_company_id`, `get_marketer_by_company_uid`, `get_client_by_company_id`, `get_client_by_company_uid`
