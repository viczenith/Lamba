# Company Admin Dashboard Implementation Roadmap

## Overview
Based on your multi-tenant SaaS architecture, here's a comprehensive roadmap for company admin features that will ensure neat handling, scalability, and proper tenant isolation.

---

## 📊 Phase 1: Company Profile & Branding (CURRENT)

### ✅ Already Implemented
- Company registration with core details
- Admin authentication and role-based access
- Company subscription tier management
- Logo upload (being added)
- Office address (being added)

### Features to Add to Company Admin Dashboard
```
1. Dashboard Logo Display
   - Dynamic company logo in header
   - Fallback to placeholder if no logo
   - Logo used across all admin pages

2. Company Details Management
   - Edit company name, registration number
   - Update CEO information
   - Manage billing email
   - Update office address with geocoding
   - Theme color customization
```

---

## 📋 Phase 2: Team Management (HIGH PRIORITY)

### A. Admin User Management
```
Features:
✓ Add/invite new admin users
✓ Remove admin users (soft delete)
✓ Mute/unmute admin accounts (prevent login)
✓ View admin activity logs
✓ Set admin permissions/roles (system admin vs company admin)
✓ Admin user listing with status
✓ Bulk actions on admins

Models to Create/Update:
- AdminRole (system_admin, company_admin, department_admin)
- AdminActivityLog (tracks who did what and when)

API Endpoints Needed:
POST   /api/v1/company/admins/invite/
GET    /api/v1/company/admins/
PUT    /api/v1/company/admins/{id}/
DELETE /api/v1/company/admins/{id}/
POST   /api/v1/company/admins/{id}/toggle-mute/
GET    /api/v1/company/admins/{id}/activity/
```

### B. Support/Staff User Management
```
Features:
✓ Add support staff members
✓ Assign staff to departments/teams
✓ Set support staff permissions
✓ Track support staff activity
✓ Performance metrics (tickets handled, response time)
✓ Soft delete/archive staff

Tables to Manage:
- StaffMember (email, role, status)
- StaffRoster (assignment tracking)
- StaffActivityLog (action tracking)
```

---

## 💼 Phase 3: Client Management

### A. Client Lifecycle
```
Features:
✓ View all company clients
✓ Search/filter clients by status
✓ Block/unblock clients
✓ Delete/archive clients
✓ View client KYC status
✓ Track client subscription usage
✓ Export client list

Columns in Admin View:
- Client Name
- Email
- Phone
- Registration Date
- Last Login
- Status (Active/Inactive/Blocked)
- Allocated Properties
- Payment Status
- Documents Status

Filters Needed:
- Status (Active/Inactive/Blocked)
- Registration Date Range
- Payment Status
- Property Allocation Status
```

### B. KYC (Know Your Customer) Management
```
Features:
✓ View client KYC documents
✓ Approve/reject KYC
✓ Request additional documents
✓ Track KYC completion percentage
✓ Automated reminders for incomplete KYC
✓ Batch KYC verification

Models to Create:
- KYCDocument (document_type, file_url, status, uploaded_at)
- KYCVerification (verified_by, verified_at, notes)
- KYCTask (auto-generated reminders)

API Endpoints:
GET    /api/v1/company/clients/
GET    /api/v1/company/clients/{id}/kyc/
POST   /api/v1/company/clients/{id}/kyc/approve/
POST   /api/v1/company/clients/{id}/kyc/reject/
```

---

## 🏘️ Phase 4: Property & Allocation Management

### A. Estate Management
```
Features:
✓ Create/edit estates (properties)
✓ Upload estate images and floor plans
✓ Set estate pricing and availability
✓ Track estate occupancy
✓ Bulk import estates (CSV/Excel)
✓ Estate analytics (views, inquiries, conversions)

Data Points to Track:
- Estate Name & Location
- Total Plots/Units
- Available Plots
- Sold Plots
- Reserved Plots
- Images & Documents
- Pricing
```

### B. Plot/Unit Allocation
```
Features:
✓ View all allocations
✓ Filter by status (pending, allocated, paid, completed)
✓ Search allocations by client/estate
✓ Manual allocation creation
✓ Bulk allocation from CSV
✓ Allocation history & timeline
✓ Generate allocation certificates

Dashboard Metrics:
- Total Allocations
- Pending Allocations
- Fully Paid
- Partially Paid
- Completion Rate
```

---

## 💰 Phase 5: Financial Management

### A. Subscription & Billing
```
Features:
✓ View current subscription tier
✓ Upgrade/downgrade tier
✓ View billing history
✓ Manage payment methods
✓ Invoice generation & download
✓ Automatic invoice emails
✓ Subscription status tracking
✓ Usage metrics vs limits

Subscription Metrics:
- Active Subscriptions
- Recurring Revenue (MRR)
- Churn Rate
- Expansion Revenue

Models to Update:
- Company (add subscription_started_at, subscription_renewed_at)
- BillingRecord (track all charges)
- Invoice (generate invoices)

Stripe Integration Needed:
- Webhook handling (charge succeeded, failed, refunded)
- Customer portal link
- Automated renewal
```

### B. Payment Tracking
```
Features:
✓ View client payment history
✓ Track payment by allocation
✓ Generate payment reports
✓ Send payment reminders (automated)
✓ Process refunds
✓ Track outstanding payments
✓ Payment reconciliation

Reports to Generate:
- Monthly Payment Summary
- Outstanding Payments Report
- Payment by Client Report
- Revenue Recognition Report

Models Needed:
- PaymentRecord (tracks all transactions)
- PaymentReminder (automated/manual)
- Refund (refund tracking)
```

### C. Commission & Marketer Payouts
```
Features:
✓ Calculate commissions earned by marketers
✓ View marketer sales history
✓ Track commissions per allocation
✓ Automated payout scheduling
✓ Payout approval workflow
✓ Commission rate management
✓ Dispute resolution

Commission Tracking:
- Commission Rate (per tier)
- Total Commission Owed
- Commission Paid
- Pending Payouts
- Payout Status

Models Needed:
- CommissionRecord (tracks earnings)
- CommissionPayout (tracks disbursements)
- CommissionRate (config by allocation type)

API Endpoints:
GET    /api/v1/company/marketer-commissions/
GET    /api/v1/company/marketer-commissions/{marketer_id}/
POST   /api/v1/company/payouts/process/
GET    /api/v1/company/payouts/
```

---

## 👥 Phase 6: Marketer Management

### A. Marketer Affiliations
```
Features:
✓ View all affiliated marketers
✓ Accept/reject affiliation requests
✓ View marketer performance
✓ Deactivate marketer account
✓ Track marketer sales
✓ Commission settlements
✓ Marketer documents (ID, tax info)

Marketer Metrics:
- Total Sales
- Commission Owed
- Commission Paid
- Conversion Rate
- Active Clients
- Status (Active/Inactive/Suspended)

Models to Create:
- MarketerAffiliation (company <-> marketer relationship)
- MarketerPerformance (metrics tracking)
```

### B. Marketer Performance Analytics
```
Features:
✓ Sales by marketer (monthly/quarterly/yearly)
✓ Client acquisition cost
✓ Conversion funnel
✓ Top performers ranking
✓ Performance comparison
✓ Trend analysis

Dashboards Needed:
- Marketer Leaderboard
- Sales Pipeline by Marketer
- Commission Settlement Overview
```

---

## 📊 Phase 7: Analytics & Reporting

### A. Company Dashboard Widgets
```
Key Metrics Display:
- Total Revenue (MRR)
- Total Clients
- Total Properties
- Average Property Price
- Occupancy Rate
- Payment Collection Rate
- Commission Paid Out
- Pending Transactions

Widgets to Create:
✓ Revenue Trend (line chart)
✓ Client Growth (bar chart)
✓ Property Distribution (pie chart)
✓ Payment Status (donut chart)
✓ Top Properties (table)
✓ Recent Transactions (timeline)
```

### B. Advanced Reports
```
Report Types to Generate:
1. Financial Reports
   - Profit & Loss Statement
   - Revenue Recognition Report
   - Cash Flow Statement
   - Tax Summary

2. Operational Reports
   - Client Activity Report
   - Property Performance Report
   - Allocation Summary
   - Marketer Performance Report

3. Compliance Reports
   - KYC Completion Report
   - Document Audit Trail
   - User Access Logs
   - Data Export Logs

Export Formats:
- PDF (formatted)
- Excel (data-rich)
- CSV (data only)
```

### C. Real-time Dashboards
```
Features:
✓ Real-time transaction updates
✓ Live client activity feed
✓ System health status
✓ WebSocket notifications for key events
```

---

## 🔐 Phase 8: Security & Compliance

### A. Access Control
```
Features:
✓ Role-based access (RBAC)
✓ Permission management
✓ IP whitelisting (optional)
✓ Session management
✓ Forced re-authentication for sensitive actions
✓ Two-factor authentication (2FA) for admins

Roles to Define:
- Company Admin (full access)
- Finance Manager (billing, payments, reports)
- Support Manager (client management, support)
- Analyst (reports only, read-only)

Model to Create:
- Permission (granular permission system)
- RolePermission (mapping)
```

### B. Audit & Compliance
```
Features:
✓ Audit logs for all admin actions
✓ Data access logs
✓ Change tracking (who changed what, when)
✓ Compliance report generation
✓ Data retention policies
✓ GDPR compliance (right to delete)

Audit Logging:
- Admin Login/Logout
- Data Modifications (create, update, delete)
- Access to Sensitive Data
- Report Generation
- Payment Processing
- Bulk Operations

Models Needed:
- AuditLog (comprehensive activity tracking)
- DataAccessLog (who accessed what)
```

---

## 📱 Phase 9: Notifications & Communications

### A. Admin Notifications
```
Features:
✓ In-app notifications
✓ Email notifications
✓ SMS alerts (critical events)
✓ Push notifications (mobile)
✓ Notification preferences

Alert Types:
- New KYC Submission
- Payment Received
- Payment Failed
- Client Signup
- Allocation Completed
- System Alerts (quota exceeded, etc.)

Models to Create:
- AdminNotification (in-app)
- NotificationPreference (admin settings)
```

### B. Client Communications
```
Features:
✓ Send bulk emails to clients
✓ SMS notifications
✓ In-app messaging
✓ Email templates (editable)
✓ Scheduled communications
✓ Communication history

---

## 🔄 Phase 10: Integration & Automation

### A. Webhook Management
```
Features:
✓ View registered webhooks
✓ Configure event subscriptions
✓ Test webhooks
✓ Retry failed webhooks
✓ Webhook logs

Events to Track:
- allocation.created
- payment.received
- client.signup
- kyc.approved
- payout.processed
```

### B. Automated Workflows
```
Features:
✓ Payment reminder automation
✓ KYC expiry reminders
✓ Report scheduling
✓ Commission auto-payout
✓ Bulk import/export jobs

---

## 🛠️ Phase 11: System Configuration

### A. Company Settings
```
Features:
✓ Business Hours Configuration
✓ Currency & Localization
✓ Pricing Configuration (markups, markdowns)
✓ Commission Rules
✓ Payment Terms
✓ Custom Branding (colors, fonts)

Models to Create:
- CompanySettings (key-value store or model)
- PricingConfig (pricing rules per property type)
- CommissionConfig (commission structure)
```

### B. Data Management
```
Features:
✓ Data Backup & Recovery
✓ Data Export (bulk export all company data)
✓ Data Cleanup (archive old records)
✓ Import Tools (import from CSV/Excel)
✓ Database Health Check

---

## 📞 Phase 12: Support & Help

### A. Help Center
```
Features:
✓ FAQ section
✓ Knowledge base
✓ Video tutorials
✓ Contextual help (inline help bubbles)
✓ Chat support widget

```

### B. Ticket Management
```
Features:
✓ Admin can create support tickets
✓ View support ticket history
✓ Priority levels
✓ SLA tracking
✓ Ticket assignment

---

## 🗂️ Database Model Summary

### New Models to Create
```python
# Admin Management
AdminRole
AdminActivityLog
Permission
RolePermission

# Client Management
KYCDocument
KYCVerification
KYCTask

# Financial
BillingRecord
Invoice
CommissionRecord
CommissionPayout
CommissionRate
PaymentReminder
Refund

# Marketer
MarketerAffiliation
MarketerPerformance

# Security
AuditLog
DataAccessLog

# Notifications
AdminNotification
NotificationPreference
Webhook
WebhookLog

# Configuration
CompanySettings
PricingConfig
CommissionConfig
EmailTemplate
```

---

## 📈 Implementation Priority Matrix

### CRITICAL (Implement First - Week 1-2)
1. Team Management (Admins, Support Staff)
2. Client Management Dashboard
3. Financial Overview & Subscription Management
4. Audit Logging

### HIGH (Weeks 3-4)
5. Property/Allocation Management
6. Payment Tracking & Commission Calculations
7. Basic Reporting
8. Marketer Performance Tracking

### MEDIUM (Weeks 5-6)
9. KYC Management System
10. Advanced Analytics
11. Automated Workflows
12. Email Communications

### NICE-TO-HAVE (Later Phases)
13. Webhook Management
14. Advanced Permission System
15. Data Backup/Recovery
16. Help Center

---

## 🎯 Success Metrics

For each feature, track:
- User adoption rate
- Time saved per operation
- Error reduction
- Customer satisfaction score
- Feature usage frequency

---

## 📚 Technical Stack

### Backend
- Django ORM with proper tenant filtering
- Redis for caching & real-time updates
- Celery for async tasks
- Stripe API for payments
- WebSockets for real-time updates

### Frontend
- React components for admin UI
- Charts.js for analytics
- DataTables for data management
- Form builders for configurations

### Database Indices
- company_id (all tables)
- created_at, updated_at (timestamps)
- status fields (filters)
- user_id (activity logs)

---

## 🔗 Tenant Isolation Considerations

For each feature:
1. Always filter by `company_profile` or `request.company`
2. Add `company_id` to all multi-tenant models
3. Create indexes on `company_id` for performance
4. Add row-level security in queries
5. Validate company ownership before allowing access

---

## 💡 Next Steps

1. **Design Database Schema** - Create all models with proper relationships
2. **Build Admin Dashboard UI** - Create main dashboard layout
3. **Implement Team Management** - Start with admin user management
4. **Add Financial Tracking** - Subscription & payment management
5. **Create Reporting System** - Basic analytics first, advanced later
6. **Security Hardening** - Audit logs, permissions, access control

---

*This roadmap provides a comprehensive view of what a mature company admin dashboard should include for effective multi-tenant SaaS management.*
