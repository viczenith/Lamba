# Chat Company Tenancy Implementation

## Overview

This document describes the comprehensive company tenancy and data isolation implementation for the chat system. The implementation ensures that users from Company A cannot see or interact with users from Company B.

## Data Model Analysis

### User-Company Relationships

The system uses multiple mechanisms to associate users with companies:

#### 1. Direct Assignment (`company_profile`)
```python
# CustomUser model (line 961)
company_profile = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL)
```
- PRIMARY relationship for all users
- All clients and marketers have this field set to their "home" company

#### 2. Marketer Affiliations (`MarketerAffiliation`)
```python
# models.py (line 525)
class MarketerAffiliation(models.Model):
    marketer = models.ForeignKey('CustomUser', on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    status = models.CharField(choices=['active', 'suspended', 'terminated', 'pending_approval'])
```
- Allows marketers to work with MULTIPLE companies
- Only `status='active'` affiliations are considered for chat visibility
- Created when admin uses "Add Existing User" for marketers

#### 3. Client-Marketer Assignments (`ClientMarketerAssignment`)
```python
# models.py (line 1296)
class ClientMarketerAssignment(models.Model):
    client = models.ForeignKey(ClientUser, on_delete=models.CASCADE)
    marketer = models.ForeignKey(MarketerUser, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
```
- Links clients to marketers per company
- Allows clients to exist in MULTIPLE companies
- Created when assigning marketers to clients

## Helper Functions Added

### `get_all_clients_for_company(company_obj)`
Returns a set of all client IDs for a company, including:
1. Clients with `company_profile` pointing to the company
2. Clients with `ClientMarketerAssignment` to the company

```python
def get_all_clients_for_company(company_obj):
    if not company_obj:
        return set()
    
    # Primary: direct company_profile
    primary_client_ids = set(
        CustomUser.objects.filter(
            role='client',
            company_profile=company_obj
        ).values_list('id', flat=True)
    )
    
    # Affiliated: via ClientMarketerAssignment
    affiliated_client_ids = set(
        ClientMarketerAssignment.objects.filter(
            company=company_obj
        ).values_list('client_id', flat=True).distinct()
    )
    
    return primary_client_ids | affiliated_client_ids
```

### `get_all_marketer_ids_for_company(company_obj)`
Returns a set of all marketer IDs for a company, including:
1. Marketers with `company_profile` pointing to the company
2. Marketers with ACTIVE `MarketerAffiliation` to the company

```python
def get_all_marketer_ids_for_company(company_obj):
    if not company_obj:
        return set()
    
    # Primary: direct company_profile
    primary_marketer_ids = set(
        CustomUser.objects.filter(
            role='marketer',
            company_profile=company_obj
        ).values_list('id', flat=True)
    )
    
    # Affiliated: via MarketerAffiliation (active only)
    affiliated_marketer_ids = set(
        MarketerAffiliation.objects.filter(
            company=company_obj,
            status='active'
        ).values_list('marketer_id', flat=True).distinct()
    )
    
    return primary_marketer_ids | affiliated_marketer_ids
```

### `is_user_in_company(user_id, company_obj, user_role=None)`
Checks if a user belongs to a company (via any method).

## Views Updated

### 1. `admin_chat_hub_view`
**Purpose**: Chat hub showing sidebar with clients/marketers

**Security Applied**:
- Gets all user IDs using helper functions
- Filters `CustomUser.objects.filter(id__in=all_client_ids, ...)` 
- Only shows users belonging to the company (including affiliations)

### 2. `chat_search_users_api`
**Purpose**: Search API for finding users to chat with

**Security Applied**:
- Gets all user IDs using helper functions
- Searches only within company's user IDs
- Returns only users belonging to the company

### 3. `chat_load_conversation_api`
**Purpose**: AJAX endpoint to load conversation without page reload

**Security Applied**:
- Validates user_id against company's user IDs
- Returns 404 if user not in company
- Filters messages to/from company support

### 4. `chat_unread_count`
**Purpose**: API for sidebar unread counts and new message detection

**Security Applied**:
- Gets all user IDs using helper functions
- Filters unread messages by company user IDs
- Only returns users with unread messages who belong to company

### 5. `admin_chat_view`
**Purpose**: Full page chat view for specific client

**Security Applied**:
- Validates client_id against `get_all_clients_for_company()`
- Redirects to hub if client not in company
- Marks only company-relevant messages as read

### 6. `admin_marketer_chat_view`
**Purpose**: Full page chat view for specific marketer

**Security Applied**:
- Validates marketer_id against `get_all_marketer_ids_for_company()`
- Redirects to hub if marketer not in company
- Marks only company-relevant messages as read

## Message Filtering Logic

All message queries now use company isolation:

```python
# For unread counts (admin receiving from client/marketer)
Message.objects.filter(
    sender_id__in=all_client_ids | all_marketer_ids,  # Only company users
    recipient__company_profile=company,               # To company support
    recipient__role__in=SUPPORT_ROLES,
    is_read=False
)

# For conversations
Message.objects.filter(
    Q(sender=user, recipient__role__in=SUPPORT_ROLES, recipient__company_profile=company) |
    Q(sender__role__in=SUPPORT_ROLES, sender__company_profile=company, recipient=user),
)
```

## Security Guarantees

1. **User Visibility**: Users from Company A cannot see users from Company B in:
   - Chat sidebar
   - Search results
   - Unread count notifications

2. **Conversation Access**: Users cannot load conversations with users outside their company

3. **Message Isolation**: Messages are filtered to only show those relevant to the current company context

4. **Affiliation Support**: Users affiliated with multiple companies appear correctly in each company's chat

## Testing Checklist

- [ ] Admin logs into Company A - sees only Company A clients/marketers
- [ ] Admin logs into Company B - sees only Company B clients/marketers
- [ ] Search in Company A returns only Company A users
- [ ] Search in Company B returns only Company B users
- [ ] Unread counts show only messages from company users
- [ ] Direct URL access to other company's user redirects to hub
- [ ] Marketers with multiple affiliations appear in each company's chat
- [ ] Clients with multiple assignments appear in each company's chat

## Files Modified

1. `estateApp/views.py`:
   - Added `get_all_clients_for_company()`
   - Added `get_all_marketer_ids_for_company()`
   - Added `is_user_in_company()`
   - Updated `admin_chat_hub_view`
   - Updated `chat_search_users_api`
   - Updated `chat_load_conversation_api`
   - Updated `chat_unread_count`
   - Updated `admin_chat_view`
   - Updated `admin_marketer_chat_view`
