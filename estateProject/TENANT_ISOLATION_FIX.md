# TENANT ISOLATION FIX - CRITICAL

## PROBLEM IDENTIFIED

New companies are seeing data from other companies because queries are NOT filtering by company. This is a **CRITICAL SECURITY ISSUE** in a multi-tenant system.

## ROOT CAUSE

The following models are missing `company` ForeignKey fields:
1. ❌ `Estate` - No company field
2. ❌ `PlotNumber` - No company field  
3. ❌ `PlotSize` - No company field
4. ❌ `PlotSizeUnits` - No company field
5. ❌ `PlotAllocation` - Links through client but not direct company field
6. ✅ `CustomUser` - Has `company_profile` field (GOOD)
7. ✅ `Message` - Links through sender/recipient (can filter)

## WHAT WAS FIXED (Partial - Views Only)

### ✅ Fixed in views.py:

1. **admin_dashboard():**
   - `total_clients` - Now filters by `company_profile=company`
   - `total_marketers` - Now filters by `company_profile=company`  
   - `estates` - Returns empty for new companies (Estate has no company field)
   - `total_allocations` - Filters by `client__company_profile=company`
   - `pending_allocations` - Filters by `client__company_profile=company`
   - `global_message_count` - Filters by `sender__company_profile=company`
   - `unread_messages` - Filters by `sender__company_profile=company`

2. **client():**
   - Now filters `ClientUser` by `company_profile=company`

3. **Marketer views:**
   - Client counts now filter by company

## WHAT STILL NEEDS FIXING (Database Schema Changes Required)

### 🔴 URGENT: Add company field to core models

These models MUST have a `company` ForeignKey added:

```python
# estateApp/models.py

class Estate(models.Model):
    # ADD THIS:
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='estates',
        help_text="Company that owns this estate"
    )
    # ... existing fields

class PlotNumber(models.Model):
    # ADD THIS:
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='plot_numbers',
        help_text="Company that owns this plot number"
    )
    # ... existing fields
    
    class Meta:
        # CHANGE unique=True to unique_together:
        unique_together = ('company', 'number')

class PlotSize(models.Model):
    # ADD THIS:
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='plot_sizes',
        help_text="Company that owns this plot size"
    )
    # ... existing fields

class PlotSizeUnits(models.Model):
    # ADD THIS:
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='plot_size_units',
        help_text="Company that owns these plot size units"
    )
    # ... existing fields

class PlotAllocation(models.Model):
    # ADD THIS:
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='plot_allocations',
        help_text="Company that made this allocation"
    )
    # ... existing fields
```

### 🔴 URGENT: Create migration

```bash
python manage.py makemigrations estateApp
# This will create a migration to add company field to all models
# You'll need to provide a default company ID for existing records
python manage.py migrate
```

### 🔴 URGENT: Update ALL queries

After adding company fields, update EVERY query in the codebase:

```python
# BEFORE (WRONG - NO TENANT ISOLATION):
estates = Estate.objects.all()
plot_numbers = PlotNumber.objects.all()
allocations = PlotAllocation.objects.all()

# AFTER (CORRECT - WITH TENANT ISOLATION):
company = request.company  # Set by middleware
estates = Estate.objects.filter(company=company)
plot_numbers = PlotNumber.objects.filter(company=company)
allocations = PlotAllocation.objects.filter(company=company)
```

## IMMEDIATE WORKAROUND (Until Migration Done)

For views that query models without company field:

```python
@login_required
def some_view(request):
    # Get company from middleware
    company = getattr(request, 'company', None)
    if not company and hasattr(request.user, 'company_profile'):
        company = request.user.company_profile
    
    if not company:
        # No company = no data (security)
        return render(request, 'template.html', {
            'estates': [],
            'clients': [],
            'allocations': []
        })
    
    # Filter everything by company
    clients = CustomUser.objects.filter(
        role='client',
        company_profile=company
    )
    
    # For models without company field, return empty until migration
    estates = Estate.objects.none()  # TEMPORARY
    
    return render(request, 'template.html', {
        'estates': estates,
        'clients': clients
    })
```

## HOW TO TEST TENANT ISOLATION

1. **Create two test companies:**
   ```python
   python manage.py shell
   from estateApp.models import Company, CustomUser
   
   # Company A
   company_a = Company.objects.create(
       company_name="Company A",
       email="companya@test.com",
       ...
   )
   
   # Company B  
   company_b = Company.objects.create(
       company_name="Company B", 
       email="companyb@test.com",
       ...
   )
   ```

2. **Create test data for each:**
   - Add clients to Company A
   - Add clients to Company B
   - Add estates to Company A (after migration)

3. **Login as Company A admin:**
   - Dashboard should show ONLY Company A data
   - Client count should be only Company A clients
   - NO Company B data should appear

4. **Login as Company B admin:**
   - Dashboard should show ONLY Company B data
   - NO Company A data should appear

## SECURITY IMPLICATIONS

**BEFORE FIX:**
- ❌ Company A admin can see Company B's clients
- ❌ Company A admin can see Company B's plot allocations
- ❌ Company A admin can see Company B's estates
- ❌ **DATA BREACH VULNERABILITY**

**AFTER FIX:**
- ✅ Company A admin sees ONLY Company A data
- ✅ Company B admin sees ONLY Company B data
- ✅ Complete tenant isolation
- ✅ Zero cross-tenant data leakage

## MIGRATION PRIORITY

🔴 **CRITICAL - DO IMMEDIATELY:**
1. Add `company` field to Estate, PlotNumber, PlotSize, PlotSizeUnits, PlotAllocation
2. Create and run migration
3. Update all queries to filter by company

⚠️ **HIGH PRIORITY:**
4. Add company filter to all list views
5. Add company filter to all detail views
6. Add company filter to all API endpoints

## FILES CHANGED (This Session)

✅ `estateApp/views.py`:
- `admin_dashboard()` - Added company filtering
- `client()` - Added company filtering
- Marketer views - Added company filtering

## NEXT STEPS

1. Review this document
2. Add company fields to models (models.py)
3. Create migration: `python manage.py makemigrations`
4. Apply migration: `python manage.py migrate`
5. Search codebase for ALL queries and add company filter
6. Test thoroughly with multiple companies
7. Deploy with confidence

## GREP SEARCH COMMANDS FOR AUDIT

Find all places that need company filtering:

```bash
# Find all .objects.all() calls (need company filter)
grep -r "\.objects\.all()" estateApp/

# Find all .objects.filter() calls (verify company filter)
grep -r "\.objects\.filter(" estateApp/

# Find all Estate queries
grep -r "Estate\.objects" estateApp/

# Find all PlotAllocation queries  
grep -r "PlotAllocation\.objects" estateApp/

# Find all ClientUser queries
grep -r "ClientUser\.objects" estateApp/
```

## STATUS

- [x] Problem identified
- [x] View-level fixes applied (partial)
- [ ] Database schema changes (PENDING)
- [ ] Migration created (PENDING)
- [ ] Migration applied (PENDING)
- [ ] All queries updated (PENDING)
- [ ] Testing completed (PENDING)

**CURRENT STATE:** Views are partially protected but NEW COMPANIES will see EMPTY data until database schema is fixed.
