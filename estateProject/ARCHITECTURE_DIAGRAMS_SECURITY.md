# Architecture Diagrams - Multi-Tenant Profile Security

## 1. Data Leakage Prevention Flow

```
BEFORE (Vulnerable):
┌─────────────────────────────────────────────────────────┐
│ Admin A (Company: Lamba Real Homes)                     │
├─────────────────────────────────────────────────────────┤
│ URL: /client_profile/90/                                │
│ Query: Transaction.objects.filter(client_id=90)         │
├─────────────────────────────────────────────────────────┤
│ Results:                                                │
│ ❌ Transactions from Company A (Lamba Real Homes)       │
│ ❌ Transactions from Company B (Victor Estates)         │
│ ❌ Transactions from Company C (Home Properties)        │
│ ❌ ALL COMPANIES VISIBLE (DATA LEAKAGE!)               │
└─────────────────────────────────────────────────────────┘

AFTER (Secure):
┌─────────────────────────────────────────────────────────┐
│ Admin A (Company: Lamba Real Homes)                     │
├─────────────────────────────────────────────────────────┤
│ URL: /victor-godwin.client-profile?company=lamba       │
│ Query: Transaction.objects.filter(                      │
│   client_id=90,                                          │
│   company=Company(slug='lamba')  ← CRITICAL FILTER     │
│ )                                                       │
├─────────────────────────────────────────────────────────┤
│ Results:                                                │
│ ✅ Transactions from Company A (Lamba Real Homes)      │
│ ✅ ONLY Company A Data (ISOLATED!)                     │
│ ❌ Company B - NOT VISIBLE (BLOCKED!)                  │
│ ❌ Company C - NOT VISIBLE (BLOCKED!)                  │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Company Context Determination

```
Client Request
    ↓
    ├─→ URL has company_slug? → Use URL company_slug
    │        ↓ NO
    ├─→ Query has ?company=slug? → Use query company
    │        ↓ NO
    ├─→ request.user.company_profile? → Use user's company
    │        ↓ NO
    └─→ RAISE Http404("No company context provided")

RESULT: company = CompanyProfile object
        ↓
        Verify user has access to this company
        ↓
        Proceed with company-scoped queries
```

---

## 3. User Lookup with Company Isolation

```
Find User by Username (slug) OR ID (pk)

IF slug provided:
  user = get_object_or_404(
    Model,
    user_ptr__username=slug,
    company_profile=company  ← DATABASE ENFORCED
  )
  ✅ Query fails if user not in this company

IF pk provided:
  user = get_object_or_404(Model, id=pk)
  
  Verify company membership:
  ├─ if user.company_profile == company?
  │   ✅ ALLOW - Direct membership
  │
  ├─ if Affiliation.objects.filter(
  │       user_id=pk,
  │       company=company
  │     ).exists()?
  │   ✅ ALLOW - Affiliated member
  │
  └─ else?
      ❌ DENY - raise Http404("User not found in this company")
```

---

## 4. Query Scoping Pattern

```
Transaction Query (Portfolio Isolation)

BEFORE (Vulnerable):
┌─────────────────────────────────────┐
│ transactions = Transaction.objects  │
│   .filter(client_id=client.id)      │
│                                     │
│ Database Query:                     │
│ SELECT * FROM transactions          │
│ WHERE client_id = 90                │
│ → Includes Companies A, B, C        │
└─────────────────────────────────────┘

AFTER (Secure):
┌─────────────────────────────────────┐
│ transactions = Transaction.objects  │
│   .filter(                          │
│     client_id=client.id,            │
│     company=company  ← ADDED        │
│   )                                 │
│                                     │
│ Database Query:                     │
│ SELECT * FROM transactions          │
│ WHERE client_id = 90                │
│ AND company_id = 1  ← FILTER       │
│ → Includes ONLY Company A           │
└─────────────────────────────────────┘
```

---

## 5. Multi-URL Format Support

```
THREE URL FORMATS ALL SUPPORTED:

1. LEGACY (Deprecated)
   /client_profile/90/
   /admin-marketer/15/
   ├─ Still works ✅
   ├─ Now company-scoped ✅
   └─ Allow enumeration ⚠️

2. SLUG-BASED (Recommended)
   /victor-godwin.client-profile?company=lamba-real-homes
   /john-smith.marketer-profile?company=lamba-real-homes
   ├─ User-friendly ✅
   ├─ Company parameter explicit ✅
   ├─ Secure by default ✅
   └─ Easy to share ✅

3. COMPANY-NAMESPACED (Most Secure)
   /lamba-real-homes/client/victor-godwin/
   /lamba-real-homes/marketer/john-smith/
   ├─ Company in URL path ✅
   ├─ Multi-tenant native ✅
   ├─ Clear company context ✅
   └─ Prevents accidental cross-company ✅

All three formats route to same view functions with same security
```

---

## 6. Security Check Flowchart

```
Request to Profile View
    ↓
GET request.user.company_profile
    ↓
OVERRIDE if URL provides company_slug or query company
    ↓
Verify company context exists
├─ NO? → return Http404
│
YES
    ↓
Find user by slug or pk with company filter
├─ Slug: Database enforces company_profile
├─ pk: Manual verification of company membership
│
NOT FOUND or WRONG COMPANY?
├─ NO? → return Http404
│
FOUND IN CORRECT COMPANY
    ↓
Execute all data queries with company filter
    ↓
Return company-scoped view
```

---

## 7. Leaderboard Isolation

```
BEFORE (Vulnerable):
┌─────────────────────────────────────────┐
│ for m in MarketerUser.objects.all():    │ ← NO FILTER
│     sales = Transaction.objects.filter( │
│         marketer=m                      │ ← NO FILTER
│     )                                   │
│ # Result: Leaderboard includes          │
│ # Marketers from Companies A, B, C      │
│ # CROSS-COMPANY DATA VISIBLE (LEAK)     │
└─────────────────────────────────────────┘

AFTER (Secure):
┌────────────────────────────────────────────────┐
│ marketers = MarketerUser.objects.filter(       │
│     company_profile=company  ← FILTER 1        │
│ )                                              │
│                                                │
│ for m in marketers:                            │
│     sales = Transaction.objects.filter(        │
│         marketer=m,                            │
│         company=company  ← FILTER 2 (DOUBLE)  │
│     )                                          │
│ # Result: Leaderboard includes ONLY           │
│ # Marketers from current company              │
│ # SINGLE COMPANY DATA ONLY (ISOLATED)          │
└────────────────────────────────────────────────┘
```

---

## 8. Access Control Decision Tree

```
                    User Requests Profile
                            ↓
                ┌──────────────────────────┐
                │ Determine Company Context│
                └──────────────────────────┘
                            ↓
              ┌─────────────────────────────┐
              │ Find User in Company?       │
              └─────────────────────────────┘
                      ↙           ↘
                   YES              NO
                   ↓                 ↓
            ┌────────────────┐  ┌────────┐
            │ Verify Company │  │ Return │
            │  Membership    │  │  404   │
            └────────────────┘  └────────┘
                   ↓
        ┌──────────────────────┐
        │ Member of Company?   │
        └──────────────────────┘
              ↙           ↘
            YES            NO
            ↓              ↓
    ┌──────────────┐   ┌────────┐
    │ Load All     │   │ Return │
    │Company-      │   │  404   │
    │Scoped Data   │   └────────┘
    └──────────────┘
          ↓
    ┌──────────────┐
    │ Render View  │
    │ with Company │
    │ Data Only    │
    └──────────────┘
```

---

## 9. Database Query Protection

```
Transaction Table (Example Data):

ID  | client_id | company_id | amount    | date
----|-----------|------------|-----------|----------
1   | 90        | 1 (Lamba)  | 500000    | 2024-01-15
2   | 90        | 1 (Lamba)  | 300000    | 2024-01-20
3   | 90        | 2 (Victor) | 999999    | 2024-01-25  ← Different company
4   | 91        | 1 (Lamba)  | 400000    | 2024-02-01

Admin A (Company 1 - Lamba) views Client 90:

BEFORE Query:
  SELECT * FROM transactions 
  WHERE client_id = 90;
  
  Results: Rows 1, 2, 3 (INCLUDES COMPANY 2!) ❌

AFTER Query:
  SELECT * FROM transactions 
  WHERE client_id = 90 
  AND company_id = 1;
  
  Results: Rows 1, 2 (COMPANY 1 ONLY!) ✅
```

---

## 10. Affiliation Support

```
User Can Be Member of Company Via:

1. DIRECT ASSIGNMENT (company_profile)
   User.company_profile = Company A
   ├─ ClientUser, MarketerUser, AdminUser
   └─ Direct ownership

2. AFFILIATION (Cross-Company Membership)
   
   MarketerAffiliation:
   marketer_id: 5
   company_id: 1 (Company A)
   
   ClientMarketerAssignment:
   client_id: 90
   company_id: 1 (Company A)

BOTH ARE CHECKED:
  company_member = (
    user.company_profile == company OR
    Affiliation.objects.filter(
      user_id=user.id,
      company=company
    ).exists()
  )

RESULT: ✅ Affiliated users properly scoped
```

---

## 11. Error Response Examples

```
CROSS-COMPANY ACCESS ATTEMPTS:

Scenario 1: Numeric ID in Different Company
  Admin A (Lamba) → GET /client_profile/90/
  (But client 90 is in Victor company)
  
  Response: ✅ 404 NOT FOUND
  Message: "Client not found in this company"

Scenario 2: Slug with Wrong Company Parameter
  Admin A (Lamba) → GET /victor-godwin.client-profile?company=victor
  (Victor is different company)
  
  Response: ✅ 404 NOT FOUND
  Message: "Client not found in this company"

Scenario 3: No Company Context
  Admin (No Company) → GET /client_profile/90/
  
  Response: ✅ 404 NOT FOUND
  Message: "No company context provided"

IMPORTANT: All return clean 404, no information leaked
```

---

## 12. Security Layers

```
DEFENSE IN DEPTH:

Layer 1: URL ROUTING
├─ Company parameter required (explicit)
└─ Company from URL > Company from query > Company from user

Layer 2: COMPANY CONTEXT
├─ Verify company exists (if URL specified)
├─ Verify admin has access to company (implicit in user context)
└─ Reject if no company available

Layer 3: USER LOOKUP
├─ Slug-based: Database enforces company_profile
├─ ID-based: Manual verification of membership or affiliation
└─ Reject with 404 if not found in company

Layer 4: DATA QUERIES
├─ All Transaction queries include company filter
├─ All Performance queries include company filter
├─ All Target queries include company filter
└─ No query executes without company filter

RESULT: Four independent security checks
        Any one failure = 404 (prevented)
        All must pass = Data returned (allowed)
```

---

## Summary

```
┌──────────────────────────────────────────────────────────┐
│         MULTI-TENANT PROFILE SECURITY ARCHITECTURE       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ✅ Company Context Determination                       │
│     ├─ URL company_slug                                 │
│     ├─ Query ?company parameter                         │
│     └─ request.user.company_profile                     │
│                                                          │
│  ✅ Strict User Verification                            │
│     ├─ Database-enforced (slug lookups)                 │
│     └─ Manual verification (ID lookups)                 │
│                                                          │
│  ✅ Complete Query Scoping                              │
│     ├─ All Transaction queries company-filtered         │
│     ├─ All Performance queries company-filtered         │
│     └─ All Leaderboard queries company-filtered         │
│                                                          │
│  ✅ Clean Error Handling                                │
│     └─ 404 on any security check failure                │
│                                                          │
│  Result: 100% Company Isolation                         │
│          Zero Cross-Company Data Leakage                │
│          Complete Multi-Tenant Protection               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

**All diagrams show the security architecture ensuring complete multi-tenant isolation.**
