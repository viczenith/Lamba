# Multi-Tenant Real Estate Platform - Implementation Plan

## Overview
This document outlines the implementation plan for adding public signup for clients/marketers and cross-company property tracking.

## Current Architecture Analysis

### User Model Structure
- **CustomUser**: Base user model with roles (admin, client, marketer, support)
- **ClientUser**: Proxy model for clients with `assigned_marketer` field
- **MarketerUser**: Proxy model for marketers
- **company_profile**: ForeignKey linking users to specific companies

### Existing Models
- **MarketerAffiliation**: Already exists! Allows marketers to affiliate with multiple companies
- **ClientDashboard**: Already exists! Aggregates properties across multiple companies
- **ClientPropertyView**: Tracks client interest in properties across companies
- **PlotAllocation**: Links clients to purchased properties

## Features to Implement

### 1. Public Signup for Clients and Marketers ✅ (Partially Exists)

**Current Status:**
- `individual_user_registration()` view already exists
- Route: `/register-user/`
- Form in login.html modal
- Creates users WITHOUT company_profile (independent users)

**What Needs Enhancement:**
- Ensure company_profile is NULL for public signups
- Add welcome dashboard for independent clients/marketers
- Guide them to browse companies and properties

### 2. Cross-Company Property Tracking for Clients

**Current Status:**
- `ClientDashboard` model already exists with `refresh_portfolio_data()` method
- Gets all allocations: `PlotAllocation.objects.filter(client=self.client)`
- Already aggregates across companies

**What Needs Enhancement:**
- Create a view to show properties grouped by company
- Add company toggles/sections in client profile
- Link allocations to show which company each property belongs to

### 3. Marketer Affiliation Request System

**Current Status:**
- `MarketerAffiliation` model already exists!
- Has `status` field with 'pending_approval' option
- Already tracks commission, performance, etc.

**What Needs Implementation:**
- API/View for marketers to request affiliation with companies
- Company admin interface to approve/reject requests
- Notification system for requests
- Dashboard showing affiliated companies for marketers

## Implementation Steps

### Phase 1: Enhance Public Signup ✅
1. Modify `individual_user_registration()` to ensure NULL company_profile
2. Add post-registration welcome page
3. Create "Browse Companies" view for independent users

### Phase 2: Client Cross-Company Portfolio View
1. Create API endpoint to fetch all client properties grouped by company
2. Build client profile page with company toggles
3. Show property details with company information
4. Add filters and search

### Phase 3: Marketer Affiliation System
1. Create `request_affiliation` API endpoint
2. Create company admin view to list pending affiliations
3. Create approve/reject actions
4. Add notifications for both parties
5. Show affiliated companies in marketer dashboard

### Phase 4: Testing and Documentation
1. Test all scenarios
2. Update API documentation
3. Create user guides

## Database Schema Impact

### No New Models Needed!
All required models already exist:
- MarketerAffiliation (for affiliation tracking)
- ClientDashboard (for cross-company portfolio)
- ClientPropertyView (for tracking interests)
- PlotAllocation (property ownership)

### Minor Modifications
- Ensure company_profile can be NULL for independent users
- Add indexes if needed for performance

## API Endpoints to Create

### Client APIs
- `GET /api/client/portfolio/` - Get all properties grouped by company
- `GET /api/client/companies/` - List all companies client has purchased from
- `GET /api/client/properties/<company_id>/` - Properties from specific company

### Marketer APIs
- `POST /api/marketer/request-affiliation/` - Request to join a company
- `GET /api/marketer/affiliations/` - List all affiliations (active, pending, etc.)
- `GET /api/marketer/available-companies/` - Companies marketer can request to join

### Company Admin APIs
- `GET /api/admin/affiliation-requests/` - List pending marketer requests
- `POST /api/admin/affiliation-requests/<id>/approve/` - Approve request
- `POST /api/admin/affiliation-requests/<id>/reject/` - Reject request

## UI Components to Create

### Client Side
1. **Portfolio Dashboard** - Show all properties with company grouping
2. **Company Toggle List** - Expandable sections per company
3. **Property Cards** - Display property details with company badge

### Marketer Side
1. **Affiliations Dashboard** - Show all affiliated companies
2. **Browse Companies** - List companies with "Request Affiliation" button
3. **Affiliation Status** - Track pending/approved/rejected requests

### Company Admin Side
1. **Affiliation Requests Panel** - List pending requests
2. **Approve/Reject Interface** - Quick actions for each request
3. **Affiliated Marketers List** - Show all active marketers

## Security Considerations
1. Validate that users can only access their own data
2. Company admins can only manage their own company's affiliations
3. Rate limiting on affiliation requests
4. Email verification for public signups

## Next Steps
1. Start with enhancing public signup (Phase 1)
2. Implement client portfolio view (Phase 2)
3. Build marketer affiliation system (Phase 3)
4. Test and document (Phase 4)
