# Smart Downgrade Validation System

## Problem Statement

**Before**: Companies could downgrade from unlimited Enterprise plan to limited Starter/Professional plans without checking if their current usage exceeded the new plan's limits. This would create data access issues and system inconsistencies.

**Example Bad Scenario**:
- Company on Enterprise (unlimited) has 600 clients
- Downgrades to Starter (100 clients max)
- Result: 500 clients become inaccessible, system breaks

## Solution Implemented

**Smart Two-Stage Validation System**:
1. **Backend validates** current usage against target plan limits
2. **Blocks downgrade** if usage exceeds ANY limit
3. **Shows detailed comparison** of what needs to be reduced
4. **Only allows downgrade** when ALL usage is within target limits

---

## How It Works

### Step 1: User Attempts Downgrade

User clicks on a lower-tier plan (e.g., Enterprise → Starter)

### Step 2: Frontend Triggers Validation

```javascript
function validateDowngradeWithBackend(newPlan) {
  // Show loading state
  fetch('/api/subscription/validate-downgrade/', {
    method: 'POST',
    body: JSON.stringify({ plan_id: newPlan.id })
  })
  .then(response => response.json())
  .then(data => {
    if (data.can_downgrade) {
      // Usage OK - show warning
      showDowngradeWarning(currentPlan, newPlan);
    } else {
      // Usage exceeds - BLOCK downgrade
      showDowngradeBlocked(currentPlan, newPlan, data.usage_comparison, data.exceeds);
    }
  });
}
```

### Step 3: Backend Calculates Current Usage

**API Endpoint**: `/api/subscription/validate-downgrade/`

**Calculations**:
```python
# Count estates
current_estates = Estate.objects.filter(company=company).count()

# Count allocations (transactions)
current_allocations = Transaction.objects.filter(
    company=company,
    transaction_type__in=['full_payment', 'part_payment']
).count()

# Count clients (primary + affiliated)
primary_clients = CustomUser.objects.filter(role='client', company_profile=company).count()
affiliated_clients = ClientMarketerAssignment.objects.filter(company=company).values('client_id').distinct().count()
current_clients = primary_clients + affiliated_clients

# Count marketers (primary + affiliated)
primary_marketers = CustomUser.objects.filter(role='marketer', company_profile=company).count()
affiliated_marketers = MarketerAffiliation.objects.filter(company=company).values('marketer_id').distinct().count()
current_marketers = primary_marketers + affiliated_marketers

# Count properties
current_properties = current_estates
```

### Step 4: Compare Against Target Plan Limits

**Plan Limits**:
```python
plan_limits = {
    'starter': {
        'max_estates': 25,
        'max_allocations': 50,
        'max_clients': 100,
        'max_marketers': 5,
        'max_properties': 50,
    },
    'professional': {
        'max_estates': 100,
        'max_allocations': 200,
        'max_clients': 500,
        'max_marketers': 25,
        'max_properties': 200,
    },
    'enterprise': {
        'max_estates': -1,  # Unlimited
        'max_allocations': -1,
        'max_clients': -1,
        'max_marketers': -1,
        'max_properties': -1,
    }
}
```

**Validation Logic**:
```python
exceeds = []

for resource in resources:
    if limit == -1:  # Unlimited
        status = 'within'
    elif current_count > limit:
        status = 'exceeds'
        overage = current_count - limit
        exceeds.append({
            'resource': display_name,
            'current': current_count,
            'limit': limit,
            'overage': overage
        })
    else:
        status = 'within'

can_downgrade = len(exceeds) == 0
```

### Step 5A: Block Downgrade (If Usage Exceeds)

**Response**:
```json
{
  "success": true,
  "can_downgrade": false,
  "exceeds": [
    {
      "resource": "Estate Properties",
      "current": 150,
      "limit": 25,
      "overage": 125
    },
    {
      "resource": "Clients",
      "current": 600,
      "limit": 100,
      "overage": 500
    }
  ],
  "usage_comparison": [...]
}
```

**Frontend Shows Blocked Modal**:
```
┌────────────────────────────────────────────────────┐
│  🚫 DOWNGRADE BLOCKED                              │
│                                                    │
│  Your current usage exceeds Starter Plan limits   │
│                                                    │
│  ┌─────────────┬──────────┬────────┬──────────┐  │
│  │ Resource    │ Usage    │ Max    │ Overage  │  │
│  ├─────────────┼──────────┼────────┼──────────┤  │
│  │ Estates     │   150    │   25   │  +125 ❌ │  │
│  │ Allocations │   300    │   50   │  +250 ❌ │  │
│  │ Clients     │   600    │  100   │  +500 ❌ │  │
│  │ Marketers   │    50    │    5   │   +45 ❌ │  │
│  └─────────────┴──────────┴────────┴──────────┘  │
│                                                    │
│  To downgrade to Starter:                         │
│  1. Delete/archive 125 estates (150 → 25)         │
│  2. Delete/archive 250 allocations (300 → 50)     │
│  3. Delete/archive 500 clients (600 → 100)        │
│  4. Delete/archive 45 marketers (50 → 5)          │
│                                                    │
│  OR stay on Enterprise to keep unlimited access   │
│                                                    │
│  [Close] [Stay on Enterprise]                     │
└────────────────────────────────────────────────────┘
```

**User Actions**:
- ❌ Cannot proceed with downgrade
- ✅ Must reduce usage first OR stay on current plan

### Step 5B: Allow Downgrade (If Usage Within Limits)

**Response**:
```json
{
  "success": true,
  "can_downgrade": true,
  "exceeds": [],
  "usage_comparison": [
    {
      "resource": "Estate Properties",
      "current": 10,
      "limit": 25,
      "status": "within",
      "overage": 0
    }
  ]
}
```

**Frontend Shows Warning Modal** (Orange, not red):
```
┌────────────────────────────────────────────────────┐
│  ⚠️ DOWNGRADE WARNING                              │
│                                                    │
│  You're about to downgrade your plan              │
│                                                    │
│  Current: Enterprise → New: Starter               │
│                                                    │
│  Important:                                        │
│  • You'll lose unlimited features                 │
│  • Future additions will be limited               │
│  • Max 25 estates, 100 clients, 5 marketers       │
│  • This change takes effect immediately           │
│                                                    │
│  [Cancel] [I Understand, Continue]                │
└────────────────────────────────────────────────────┘
```

**User Actions**:
- ✅ Can proceed with downgrade after confirmation
- ✅ Usage fits within target plan limits

---

## API Details

### Endpoint: `/api/subscription/validate-downgrade/`

**Method**: POST

**Authentication**: Required (login_required)

**Request Body**:
```json
{
  "plan_id": "starter"
}
```

**Success Response** (Can Downgrade):
```json
{
  "success": true,
  "can_downgrade": true,
  "usage_comparison": [
    {
      "resource": "Estate Properties",
      "current": 10,
      "limit": 25,
      "status": "within",
      "overage": 0
    },
    {
      "resource": "Allocations",
      "current": 20,
      "limit": 50,
      "status": "within",
      "overage": 0
    },
    {
      "resource": "Clients",
      "current": 50,
      "limit": 100,
      "status": "within",
      "overage": 0
    },
    {
      "resource": "Marketers/Affiliates",
      "current": 3,
      "limit": 5,
      "status": "within",
      "overage": 0
    },
    {
      "resource": "Properties",
      "current": 10,
      "limit": 50,
      "status": "within",
      "overage": 0
    }
  ],
  "exceeds": [],
  "message": "Downgrade validation complete"
}
```

**Success Response** (Cannot Downgrade):
```json
{
  "success": true,
  "can_downgrade": false,
  "usage_comparison": [...],
  "exceeds": [
    {
      "resource": "Estate Properties",
      "current": 150,
      "limit": 25,
      "overage": 125
    },
    {
      "resource": "Clients",
      "current": 600,
      "limit": 100,
      "overage": 500
    }
  ],
  "message": "Downgrade validation complete"
}
```

**Error Response**:
```json
{
  "success": false,
  "message": "Company not found"
}
```

---

## Testing Scenarios

### Scenario 1: Usage Exceeds All Limits
**Setup**:
- Current Plan: Enterprise (unlimited)
- Usage: 150 estates, 300 allocations, 600 clients, 50 marketers
- Target Plan: Starter (25/50/100/5)

**Expected Result**: ❌ BLOCKED
- Modal shows red "Downgrade Blocked"
- Table shows all 4 overages
- Suggests reducing each resource
- Cannot proceed with downgrade

### Scenario 2: Usage Exceeds One Limit
**Setup**:
- Current Plan: Enterprise
- Usage: 10 estates, 20 allocations, 150 clients, 3 marketers
- Target Plan: Starter (25/50/100/5)

**Expected Result**: ❌ BLOCKED
- Modal shows red "Downgrade Blocked"
- Table shows clients overage: +50
- Other resources show ✓ within limits
- Suggests reducing clients from 150 to 100
- Cannot proceed with downgrade

### Scenario 3: Usage Within All Limits
**Setup**:
- Current Plan: Enterprise
- Usage: 10 estates, 20 allocations, 50 clients, 3 marketers
- Target Plan: Starter (25/50/100/5)

**Expected Result**: ⚠️ WARNING (ALLOWED)
- Modal shows orange "Downgrade Warning"
- Explains feature loss
- User can cancel or continue
- Downgrade proceeds if confirmed

### Scenario 4: Usage at Exact Limit
**Setup**:
- Current Plan: Enterprise
- Usage: 25 estates (exact Starter limit)
- Target Plan: Starter (25 max)

**Expected Result**: ⚠️ WARNING (ALLOWED)
- 25 estates = 25 limit (not exceeding)
- Shows warning modal
- Downgrade allowed

### Scenario 5: Usage One Over Limit
**Setup**:
- Current Plan: Enterprise
- Usage: 26 estates
- Target Plan: Starter (25 max)

**Expected Result**: ❌ BLOCKED
- 26 estates > 25 limit
- Shows blocked modal with "+1" overage
- Must reduce by 1 estate

---

## User Experience Flow

```
┌─────────────────────────────────────────────────────┐
│  User selects lower-tier plan                       │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Frontend: "Validating..." spinner                  │
└─────────────────┬───────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────┐
│  Backend: Calculate usage vs target limits          │
└─────────────────┬───────────────────────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
    EXCEEDS           WITHIN LIMITS
         │                 │
         ▼                 ▼
┌─────────────┐   ┌─────────────────┐
│   BLOCKED   │   │     WARNING     │
│  (Red Modal)│   │  (Orange Modal) │
└──────┬──────┘   └────────┬────────┘
       │                   │
       ▼                   ▼
┌─────────────┐   ┌─────────────────┐
│ Cannot      │   │ Can proceed     │
│ downgrade   │   │ after           │
│             │   │ confirmation    │
└─────────────┘   └─────────────────┘
```

---

## Benefits

1. **Prevents System Breaks**: No more inaccessible data from exceeded limits
2. **Clear Communication**: Users see exactly what needs to be reduced
3. **Smart Protection**: Only blocks when necessary, allows valid downgrades
4. **Better UX**: Detailed comparison table shows exact overages
5. **Accurate Calculations**: Counts primary + affiliated users correctly
6. **Future-Proof**: Easy to add more resource types to validation

---

## Code Files Involved

1. **Backend**:
   - `estateApp/paystack_payment_views.py` - `validate_downgrade()` function
   - `estateApp/urls.py` - Route: `/api/subscription/validate-downgrade/`

2. **Frontend**:
   - `estateApp/templates/admin_side/company_profile_tabs/_billing.html`
   - `validateDowngradeWithBackend()` - API call
   - `showDowngradeBlocked()` - Blocked modal
   - `showDowngradeWarning()` - Warning modal (usage within limits)

3. **Models**:
   - `Company` - Subscription and limits
   - `Estate` - Property count
   - `Transaction` - Allocation count
   - `CustomUser` - Client/Marketer count
   - `ClientMarketerAssignment` - Affiliated clients
   - `MarketerAffiliation` - Affiliated marketers

---

## Future Enhancements

1. **Bulk Actions**: Add "Delete oldest estates" button in blocked modal
2. **Archive Feature**: Move excess data to archive instead of deletion
3. **Grace Period**: Allow temporary overage with warning
4. **Smart Suggestions**: Suggest which resources to remove based on activity
5. **Export Before Downgrade**: Auto-export excess data before downgrade
6. **Partial Downgrade**: Allow downgrade with data marked as "archived"
