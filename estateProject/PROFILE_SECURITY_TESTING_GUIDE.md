# Multi-Tenant Profile Security - Testing Guide

**Quick Reference for Testing Company Isolation**

## Test Scenarios

### 1️⃣ Accessing Client Profile

#### ✅ Same Company (Should Work)
```bash
# User: admin@lamba-real-homes.com
GET /victor-godwin.client-profile?company=lamba-real-homes
# Expected: 200 OK - Shows Victor Godwin's profile with only lamba-real-homes transactions
```

#### ❌ Different Company (Should Fail with 404)
```bash
# User: admin@lamba-real-homes.com
GET /victor-godwin.client-profile?company=another-company
# Expected: 404 NOT FOUND - Client not in this company
```

#### ✅ Legacy ID Format (Company-Scoped)
```bash
# User: admin@lamba-real-homes.com
GET /client_profile/90/
# Expected: 200 OK if client 90 is in lamba-real-homes
# Expected: 404 NOT FOUND if client 90 is in different company
```

---

### 2️⃣ Accessing Marketer Profile

#### ✅ Same Company (Should Work)
```bash
# User: admin@lamba-real-homes.com
GET /john-smith.marketer-profile?company=lamba-real-homes
# Expected: 200 OK - Shows John's performance metrics for lamba-real-homes only
```

#### ❌ Different Company (Should Fail with 404)
```bash
# User: admin@lamba-real-homes.com
GET /john-smith.marketer-profile?company=different-company
# Expected: 404 NOT FOUND - Marketer not in this company
```

#### ✅ Legacy ID Format (Company-Scoped)
```bash
# User: admin@lamba-real-homes.com
GET /admin-marketer/15/
# Expected: 200 OK if marketer 15 is in lamba-real-homes
# Expected: 404 NOT FOUND if marketer 15 is in different company
```

---

### 3️⃣ Portfolio Isolation Test

**Key Assertion**: Client portfolio should ONLY show transactions from accessing company

```python
# Test Case
user = User.objects.get(username='admin')
user.company_profile = Company.objects.get(slug='lamba-real-homes')

client = ClientUser.objects.get(id=90)
client.company_profile = Company.objects.get(slug='lamba-real-homes')

# Add test transaction
Transaction.objects.create(
    client=client,
    company=Company.objects.get(slug='lamba-real-homes'),
    total_amount=100000,
    ...
)

# Add decoy transaction from different company
Transaction.objects.create(
    client=client,
    company=Company.objects.get(slug='different-company'),
    total_amount=999999,
    ...
)

# Access client profile
response = client.get('/victor-godwin.client-profile?company=lamba-real-homes/')

# Assert: Should only see 1 transaction (from lamba-real-homes)
assert len(response.context['transactions']) == 1
assert response.context['transactions'][0].total_amount == 100000
```

---

### 4️⃣ Leaderboard Isolation Test

**Key Assertion**: Marketer leaderboard should ONLY include marketers from accessing company

```python
# Setup
marketer = MarketerUser.objects.get(id=15)
marketer.company_profile = Company.objects.get(slug='lamba-real-homes')
marketer.save()

# Add different company marketer
other_marketer = MarketerUser.objects.create(
    username='other-marketer',
    company_profile=Company.objects.get(slug='different-company'),
    ...
)

# Access marketer profile
response = client.get('/john-smith.marketer-profile?company=lamba-real-homes/')

# Assert: Leaderboard should NOT include other_marketer
leaderboard_ids = [entry['marketer'].id for entry in response.context['top3']]
assert other_marketer.id not in leaderboard_ids
assert marketer.id in leaderboard_ids or len(leaderboard_ids) < 3
```

---

## Manual Testing Checklist

### Setup
- [ ] Have test accounts in different companies
- [ ] Have test clients/marketers in each company
- [ ] Have test transactions for each company

### Tests to Run

#### Client Profile
- [ ] View own company's client: **Should work ✅**
- [ ] View different company's client: **Should fail 404 ❌**
- [ ] Check portfolio shows correct company only: **Should be isolated ✅**
- [ ] Try legacy ID URL in own company: **Should work ✅**
- [ ] Try legacy ID URL in different company: **Should fail 404 ❌**

#### Marketer Profile
- [ ] View own company's marketer: **Should work ✅**
- [ ] View different company's marketer: **Should fail 404 ❌**
- [ ] Check leaderboard includes own company only: **Should be isolated ✅**
- [ ] Check performance metrics for own company only: **Should be isolated ✅**
- [ ] Try legacy ID URL in own company: **Should work ✅**
- [ ] Try legacy ID URL in different company: **Should fail 404 ❌**

#### Edge Cases
- [ ] Affiliated user in multiple companies: **Should see own company only ✅**
- [ ] Admin with multiple company affiliations: **Should respect company parameter ✅**
- [ ] Missing company parameter: **Should use request.user's company ✅**
- [ ] Invalid company slug: **Should 404 ❌**
- [ ] Suspended user accessing profile: **Should work (if user not suspended) ✅**

---

## Browser Testing URLs

### Client Profiles

**Company A - Should Work**
```
http://127.0.0.1:8000/victor-godwin.client-profile?company=lamba-real-homes
http://127.0.0.1:8000/client_profile/90/
```

**Company B - Should Fail**
```
http://127.0.0.1:8000/victor-godwin.client-profile?company=different-company
```

**Company-Namespaced (Most Secure)**
```
http://127.0.0.1:8000/lamba-real-homes/client/victor-godwin/
```

### Marketer Profiles

**Company A - Should Work**
```
http://127.0.0.1:8000/john-smith.marketer-profile?company=lamba-real-homes
http://127.0.0.1:8000/admin-marketer/15/
```

**Company B - Should Fail**
```
http://127.0.0.1:8000/john-smith.marketer-profile?company=different-company
```

**Company-Namespaced (Most Secure)**
```
http://127.0.0.1:8000/lamba-real-homes/marketer/john-smith/
```

---

## Expected Test Results

### ✅ PASS - Company Isolation Working
- Accessing profile with correct company: **200 OK**
- Accessing profile with wrong company: **404 NOT FOUND**
- Portfolio shows only correct company transactions: **Verified**
- Leaderboard shows only correct company members: **Verified**
- Performance metrics scoped to company: **Verified**

### ❌ FAIL - Security Issue Detected
- Cross-company profile accessible: **CRITICAL BUG**
- Transactions from other companies visible: **CRITICAL BUG**
- Leaderboard includes other companies: **CRITICAL BUG**
- Direct ID access bypasses company check: **CRITICAL BUG**

---

## Log Inspection

### Watch for 404s (Expected)
```
Dec 01 10:32:45 django ERROR Marketer not found in this company [referrer: http://127.0.0.1:8000/]
Dec 01 10:32:50 django ERROR Client not found in this company [referrer: http://127.0.0.1:8000/]
```

### Watch for 500s (Bugs)
```
Dec 01 10:32:45 django ERROR Internal Server Error at /john-smith.marketer-profile/
Traceback: ...
```

---

## Performance Impact

### Expected Results
- Slug lookups: **~1-2ms** (indexed on username)
- Company filter: **~0.5-1ms** (indexed on company_id)
- Leaderboard query: **~10-20ms** (depends on marketer count)

### If Slower Than Expected
- Check database indexes on `username`, `company_id`, `company_profile_id`
- Check for N+1 queries with `.select_related()` and `.prefetch_related()`

---

## Security Test Results Template

```markdown
# Security Test Results - [Date]

## Test Environment
- Django Version: [X.X.X]
- Python Version: [X.X.X]
- Database: [SQLite/PostgreSQL]

## Client Profile Tests
- Same Company Access: [ ] PASS [ ] FAIL
- Cross Company Access: [ ] PASS [ ] FAIL
- Portfolio Isolation: [ ] PASS [ ] FAIL
- Legacy ID Format: [ ] PASS [ ] FAIL

## Marketer Profile Tests
- Same Company Access: [ ] PASS [ ] FAIL
- Cross Company Access: [ ] PASS [ ] FAIL
- Leaderboard Isolation: [ ] PASS [ ] FAIL
- Performance Isolation: [ ] PASS [ ] FAIL
- Legacy ID Format: [ ] PASS [ ] FAIL

## Overall Result
[ ] ✅ ALL TESTS PASSED - SECURE
[ ] ❌ TESTS FAILED - INVESTIGATE

## Issues Found
1. [Issue Description]
2. [Issue Description]

## Sign-Off
Tested By: _______________
Date: _______________
Approved: _______________
```

---

**All tests should confirm that multi-tenant isolation is enforced and data cannot leak between companies.**
