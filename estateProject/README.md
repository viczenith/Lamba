# 🏢 Multi-Tenant Real Estate SaaS Platform

## 📋 Project Overview

This is a **comprehensive, production-ready Multi-Tenant SaaS (Software as a Service) platform** designed to revolutionize the real estate industry in Nigeria. The platform enables multiple real estate companies to manage their operations independently within a unified infrastructure, while allowing clients and marketers to interact with multiple companies through a single, seamless interface.

---

## 🎯 Core Vision & Strategic Goals

### **The Big Picture**
The platform aims to **capture the entire real estate ecosystem in Nigeria** by providing:

1. **For Real Estate Companies**: A complete management system for clients, marketers, properties, plot allocations, transactions, and subscriptions
2. **For Clients**: A unified dashboard to view and manage properties purchased from different companies in one place
3. **For Marketers**: The ability to affiliate with multiple companies and earn commissions across all of them from a single app
4. **For the Future**: A powerful marketplace ecosystem connecting buyers, sellers, agents, and companies nationwide

### **Strategic Positioning**
This isn't just property management software - it's building the **infrastructure for Nigeria's digital real estate transformation**, positioning the platform to become the central hub for all real estate transactions in the country.

---

## 🏗️ System Architecture

### **Multi-Tenant Architecture**

The platform uses **true multi-tenancy** with complete data isolation:

- **Company Model**: Each real estate company is a separate tenant with its own slug (e.g., `lamba-property-limited`)
- **Data Isolation**: All company-specific data (properties, clients, marketers, transactions) is automatically scoped to the tenant
- **URL-Based Routing**: Companies can access the system via custom domains or tenant-specific URLs
- **Database Isolation**: Implements `CompanyAwareManager` that automatically filters all queries by the current company context
- **Middleware Stack**: Multiple security and isolation layers prevent cross-tenant data leakage

### **Technology Stack**

#### **Backend**
- **Framework**: Django 5.2.8 (Python)
- **API**: Django REST Framework 3.15.2
- **Real-Time**: Django Channels 4.3.1 + Redis (WebSockets for live chat/notifications)
- **Async Tasks**: Celery 5.4.0 with Redis broker
- **Database**: PostgreSQL (production) / SQLite (development)
- **Authentication**: Multi-factor with session-based + token-based auth

#### **Frontend**
- **Admin Dashboard**: Server-rendered Django templates with Tailwind CSS
- **Interactive UI**: Vanilla JavaScript with modern ES6+ features
- **Real-Time Updates**: WebSocket integration for live notifications
- **Mobile Support**: Responsive design + planned Flutter mobile app integration

#### **Infrastructure**
- **Payment Processing**: Paystack integration (card payments + dedicated virtual accounts)
- **File Storage**: Django media handling + cloud storage ready
- **Email Service**: Django email backend
- **Deployment**: Docker-ready, Render/Heroku/AWS compatible
- **Monitoring**: Built-in health checks and system alerts

---

## 🚀 Key Features & Capabilities

### 1. **Subscription & Billing Management**

#### **Three-Tier Subscription Plans**
- **Starter Plan** (₦70,000/month or ₦700,000/year)
  - 2 estate properties
  - 50 plot allocations
  - 5 agents/marketers
  - 30 clients
  - 20 affiliates
  
- **Professional Plan** (₦100,000/month or ₦1,000,000/year)
  - 5 estate properties
  - 200 plot allocations
  - 15 agents/marketers
  - 80 clients
  - 30 affiliates
  
- **Enterprise Plan** (₦150,000/month or ₦1,500,000/year)
  - Unlimited everything
  - Priority support
  - Dedicated account manager

#### **Advanced Billing Features**
- **Trial Period**: 14-day free trial for new companies
- **Grace Period**: 7-day grace period after subscription expiration
- **Promo Codes**: Percentage and fixed-amount discount codes
- **Upgrade/Downgrade Warnings**: Intelligent plan change validation
- **Usage Tracking**: Real-time monitoring of plan limits
- **Invoice Generation**: Automated invoice creation with unique numbers
- **Payment Methods**: 
  - Paystack card payments
  - Bank transfer with dedicated virtual accounts
  - Webhook-based automatic activation
- **Read-Only Mode**: Graceful feature degradation when subscription expires

### 2. **Company Management System**

#### **Admin Dashboard**
- Real-time metrics and analytics
- User management (admins, support staff)
- Company profile with CEO information
- Custom branding (logo, theme colors, custom domains)
- Receipt generation with digital signatures
- Email engagement campaigns

#### **Property & Estate Management**
- **Estates**: Create and manage multiple estate properties
- **Plot Management**: 
  - Multiple plot sizes and numbering systems
  - Plot allocation to clients
  - Status tracking (available, allocated, sold)
  - Payment plans (full payment, installment, special packages)
- **Property Details**:
  - Floor plans and prototypes
  - Amenities and facilities
  - Estate layouts and maps
  - Image galleries
  - GPS coordinates and location data
- **Price Regulation**: Dynamic pricing with promotional offers
- **Pre-sale Management**: Special pricing for early buyers

#### **Transaction Management**
- Plot allocation tracking
- Payment recording and verification
- Receipt generation
- Transaction history
- Payment plans with installment tracking
- Outstanding balance monitoring
- Automated payment reminders

### 3. **Client Management System**

#### **Unified Client Dashboard**
- **Cross-Company Portfolio View**: Clients see ALL their properties from different companies in ONE place
- **Investment Metrics**:
  - Total properties owned
  - Total amount invested
  - Current portfolio value
  - ROI percentage
  - Month-over-month growth
  - 1-year and 5-year projections
- **Client Rankings**: Automatic tier assignment based on investment
  - First-Time Investor
  - Smart Owner (₦20M+ or 2+ plots)
  - Prime Investor (₦50M+ or 3+ plots)
  - Estate Ambassador (₦100M+ or 4+ plots)
  - Royal Elite (₦150M+ and 5+ plots)

#### **Property Viewing & Discovery**
- Browse properties across all companies
- Save favorites
- Track viewing history
- Express interest in properties
- Personal notes on properties

#### **Communication**
- Direct messaging with company admins
- Real-time notifications
- Birthday and special day greetings
- Transaction updates

### 4. **Marketer Management & Affiliate System**

#### **Multi-Company Affiliation**
- **Unique Feature**: Marketers can affiliate with MULTIPLE companies
- **Commission Tracking**:
  - Bronze tier (2%)
  - Silver tier (3.5%)
  - Gold tier (5%)
  - Platinum tier (7%+)
- **Performance Metrics**:
  - Properties sold across all companies
  - Total commissions earned
  - Commissions paid vs pending
  - Sales leaderboards
- **Commission Management**:
  - Automatic commission calculation on plot sales
  - Approval workflow
  - Payment tracking with references
  - Dispute resolution system
- **Bank Details**: Store payout information for each company affiliation

#### **Marketer Dashboard**
- Performance analytics with charts
- Client portfolio tracking
- Commission statements
- Target setting and tracking
- Real-time commission notifications

#### **Client-Marketer Assignment**
- Assign clients to specific marketers
- Track marketer performance per client
- Commission attribution on sales

### 5. **Advanced Communication System**

#### **Multi-Channel Messaging**
- **Client ↔ Admin**: Direct messaging with file attachments
- **Marketer ↔ Admin**: Separate communication channels
- **Admin Support**: Dedicated support user role
- **Message Types**: Complaints, enquiries, compliments
- **Features**:
  - Read receipts
  - Message status tracking (sent, delivered, read)
  - Reply-to functionality
  - Delete for everyone
  - File attachments
  - End-to-end encryption ready

#### **Chat Management**
- **Chat Assignments**: Assign conversations to specific admins
- **Priority Levels**: Low, medium, high, urgent
- **SLA Tracking**: Response time targets and monitoring
- **Chat Queue**: Organized queue system for incoming messages
- **Performance Metrics**: Response times, resolution times, compliance rates

#### **Notifications System**
- **Real-Time WebSocket Notifications**: Instant updates
- **Email Notifications**: Transaction updates, payment reminders
- **Push Notifications**: Mobile app ready
- **Birthday Reminders**: Automatic birthday greetings for clients and marketers
- **Special Days**: Custom events and celebrations

### 6. **Security & Compliance**

#### **Multi-Layer Security**
- **Tenant Isolation**: Automatic company-scoped queries via middleware
- **Authentication**:
  - Email-based login (no username)
  - Password validation (minimum 12 characters)
  - Session security with secure cookies
  - Multi-device session tracking
  - IP address logging
- **Authorization**:
  - Role-based access control (admin, client, marketer, support)
  - Admin levels (system admin, company admin)
  - Full control permissions for trusted admins
- **Data Protection**:
  - CSRF protection
  - XSS prevention headers
  - Clickjacking protection
  - SQL injection prevention (Django ORM)
  - Message encryption support
- **Audit Logging**: Comprehensive activity tracking
- **Rate Limiting**: API request throttling
- **Security Middleware Stack**:
  - AdvancedSecurityMiddleware
  - SessionSecurityMiddleware
  - TenantValidationMiddleware
  - SubscriptionEnforcementMiddleware

### 7. **Super Admin Panel**

#### **Platform-Wide Management**
- **Company Management**:
  - View all companies
  - Activate/suspend companies
  - Extend trials
  - Change subscription plans
  - Delete companies (with safety checks)
- **User Management**:
  - View all users across all companies
  - Filter by role, company, status
  - Last login tracking
  - User activity monitoring
- **Subscription Management**:
  - Create and edit subscription plans
  - Set pricing and limits
  - Configure features per plan
  - Billing settings management
- **Promo Code Management**:
  - Create discount codes
  - Set validity periods
  - Usage limits (total and per-user)
  - Plan-specific restrictions
  - Minimum amount requirements
- **Analytics Dashboard**:
  - Total companies (active, trial, suspended)
  - Total users breakdown
  - Monthly Recurring Revenue (MRR)
  - Annual Recurring Revenue (ARR)
  - Revenue trends (12-month charts)
  - Company signup trends
  - Plan distribution
  - Failed payments tracking
- **System Health Monitoring**:
  - Database health
  - Cache/Redis status
  - API server status
  - Email service status
  - Payment gateway status
  - WebSocket status

### 8. **API Integration**

#### **RESTful API**
- **Authentication Options**:
  - Token-based authentication
  - Session-based authentication
  - API key authentication
- **Comprehensive Endpoints**:
  - Company management
  - User management
  - Property and estate operations
  - Client dashboard data
  - Marketer performance data
  - Transaction history
  - Billing and subscription operations
  - Notifications
  - Chat messaging
- **API Documentation**: Self-documenting with drf-spectacular
- **Mobile App Ready**: Full API coverage for Flutter integration

#### **Webhook Support**
- Paystack payment webhooks
- Subscription event webhooks
- Custom webhook endpoints

### 9. **Reporting & Analytics**

#### **Company Analytics**
- Sales performance
- Revenue tracking
- Plot allocation statistics
- Client acquisition metrics
- Marketer performance rankings
- Transaction trends
- Outstanding payments

#### **Client Analytics**
- Portfolio valuation
- Investment growth tracking
- Property distribution
- Payment history analysis

#### **Marketer Analytics**
- Commission earnings
- Sales conversion rates
- Client lifetime value
- Performance vs targets

---

## 📊 Database Schema Overview

### **Core Models**

1. **Company (Tenant)**
   - Basic info (name, slug, email, phone, location)
   - Subscription details (tier, status, dates)
   - Usage limits (plots, agents, API calls)
   - Billing information (Paystack/Stripe customer IDs)
   - Custom branding (logo, theme, domain)

2. **CustomUser (Multi-Role)**
   - Base user model for all user types
   - Roles: admin, client, marketer, support
   - Company association
   - Profile information
   - Security metadata (last login IP, location)

3. **Estate & Property Models**
   - Estate (main property container)
   - EstatePlot (individual plots)
   - PlotSize, PlotNumber
   - EstateFloorPlan, EstatePrototype
   - EstateAmenities, EstateLayout, EstateMap

4. **Transaction Models**
   - PlotAllocation (plot assignment to clients)
   - Transaction (financial records)
   - Payment (payment records)
   - Invoice (billing invoices)

5. **Subscription Models**
   - SubscriptionPlan (plan definitions)
   - SubscriptionBillingModel (company billing records)
   - BillingHistory (transaction history)
   - PromoCode (discount codes)

6. **Affiliation Models**
   - MarketerAffiliation (marketer-company relationships)
   - MarketerEarnedCommission (commission tracking)
   - CompanyMarketerProfile (company-specific marketer IDs)
   - CompanyClientProfile (company-specific client IDs)

7. **Communication Models**
   - Message (chat messages)
   - ChatAssignment (chat routing)
   - ChatQueue (incoming chat management)
   - ChatSLA (response time targets)
   - Notification, UserNotification

8. **Dashboard Models**
   - ClientDashboard (unified portfolio view)
   - ClientPropertyView (property viewing tracker)

---

## 🔄 Key Business Flows

### **Company Onboarding Flow**
1. Company registers with basic information
2. Automatic slug generation for tenant isolation
3. 14-day trial period activated
4. Trial end notifications sent (7 days, 3 days, 1 day before expiry)
5. Grace period after trial (7 days with read-only mode)
6. Subscription required to continue full operations

### **Client Property Purchase Flow**
1. Client browses available plots
2. Client selects plot and payment plan
3. Marketer (if assigned) gets notified
4. Admin creates plot allocation
5. Transaction record created
6. Payment recorded (full or installment)
7. Receipt generated and emailed
8. Commission calculated for marketer
9. Client dashboard updated
10. Notification sent to client

### **Marketer Commission Flow**
1. Marketer affiliates with company
2. Client purchase linked to marketer
3. Commission automatically calculated based on tier
4. Commission status: Pending → Approved → Paid
5. Commission added to marketer's earnings
6. Payout processed to bank account
7. Payment reference recorded

### **Subscription Renewal Flow**
1. Subscription expiry notification (7 days before)
2. Auto-renewal attempt via saved payment method
3. If payment fails:
   - Grace period activated (7 days)
   - Read-only mode enabled
   - Renewal reminders sent daily
4. If payment succeeds:
   - Subscription extended
   - Full access restored
   - Invoice generated

---

## 🎨 User Interfaces

### **Admin Dashboard**
- Modern, responsive design with Tailwind CSS
- Dark mode support
- Real-time charts and metrics
- Quick actions and shortcuts
- Notification center
- Profile management

### **Client Portal**
- Unified property dashboard
- Property search and filters
- Investment analytics
- Transaction history
- Document downloads
- Direct messaging

### **Marketer Portal**
- Performance dashboard with charts
- Commission statements
- Client portfolio view
- Target tracking
- Leaderboards
- Sales pipeline

### **Super Admin Panel**
- Comprehensive platform overview
- Company management tools
- User administration
- Subscription configuration
- Promo code management
- System health monitoring
- Revenue analytics

---

## 🌟 Unique Selling Points

1. **True Multi-Tenancy**: Complete data isolation with automatic tenant routing
2. **Unified Client Experience**: One dashboard for properties across multiple companies
3. **Marketer Flexibility**: Affiliate with multiple companies from one account
4. **Flexible Pricing**: Multiple subscription tiers with graceful degradation
5. **Advanced Billing**: Promo codes, upgrade warnings, virtual bank accounts
6. **Real-Time Communication**: WebSocket-based chat and notifications
7. **Commission Automation**: Automatic commission calculation and tracking
8. **Comprehensive API**: Full mobile app support
9. **Security First**: Multiple security layers, audit logging, encryption
10. **Scalable Architecture**: Built to handle thousands of companies and millions of users

---

## 🚀 Deployment & Infrastructure

### **Production Deployment**
- **Recommended**: Render, Heroku, AWS, DigitalOcean
- **Database**: PostgreSQL (required for production)
- **Cache**: Redis (required for Celery and Channels)
- **Media Storage**: S3-compatible storage or local
- **Email**: SendGrid, AWS SES, or SMTP
- **Payment**: Paystack (Nigeria) with fallback support

### **Environment Configuration**
```bash
# Core Settings
SECRET_KEY=<your-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,*.yourdomain.com
DATABASE_URL=postgresql://user:password@host:port/dbname

# Paystack
PAYSTACK_SECRET_KEY=sk_live_...
PAYSTACK_PUBLIC_KEY=pk_live_...

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@example.com
EMAIL_HOST_PASSWORD=your-password
```

### **Docker Support**
The project includes `docker-compose.production.yml` for containerized deployment with:
- Django app container
- PostgreSQL container
- Redis container
- Nginx reverse proxy

---

## 📈 Future Roadmap

### **Planned Features**
1. **Marketplace Integration**
   - Property listing marketplace
   - Co-buying opportunities (fractional ownership)
   - Rental management automation
   - Mortgage origination integration

2. **Advanced Analytics**
   - AI-powered property valuation
   - Market trend analysis
   - Investment recommendations
   - Predictive analytics for sales

3. **Mobile Applications**
   - Flutter mobile app (iOS and Android)
   - Offline capabilities
   - Push notifications
   - Mobile payment integration

4. **Blockchain Integration**
   - Smart contracts for property transactions
   - Blockchain deed registration
   - Fraud prevention
   - Transparent ownership records

5. **Enhanced Features**
   - Virtual property tours
   - Document management system
   - Legal document generation
   - Automated contract signing
   - Property management tools

---

## 👥 User Roles & Permissions

### **System Administrator**
- Full platform access
- Manage all companies
- Configure subscription plans
- System-wide settings
- Analytics and reporting

### **Company Administrator**
- Manage company profile
- User management (company-specific)
- Property and estate management
- Transaction management
- View company analytics
- Billing and subscription management

### **Support Staff**
- Access to messaging system
- View client and marketer information
- Limited transaction viewing
- Cannot modify critical data

### **Marketer**
- View assigned clients
- Track commissions
- Affiliate with multiple companies
- Access sales dashboard
- Communicate with clients and admins

### **Client**
- View owned properties (all companies)
- Track investment portfolio
- Make payments
- Communication with companies
- Document access
- Property discovery

---

## 📚 Documentation

The project includes extensive documentation:
- `_PROJECT_STATUS.txt` - Current implementation status
- `BILLING_SYSTEM_DOCUMENTATION.md` - Billing features guide
- `SUBSCRIPTION_MANAGEMENT_IMPLEMENTATION.md` - Subscription system details
- `SUPERADMIN_COMPREHENSIVE_GUIDE.md` - Super admin panel guide
- `PROMO_CODE_BILLING_INTEGRATION.md` - Promo code implementation
- `API_DOCUMENTATION.md` - Complete API reference
- `DEPLOYMENT_CHECKLIST.md` - Production deployment guide
- `QUICK_START_BILLING.md` - Quick billing setup guide

---

## 🛠️ Development

### **Prerequisites**
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- Node.js (for frontend build tools)

### **Setup Commands**
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create subscription plans
python manage.py shell < scripts/create_plans.py

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run Celery worker (separate terminal)
celery -A estateProject worker --loglevel=info

# Run Celery beat (separate terminal)
celery -A estateProject beat --loglevel=info
```

### **Management Commands**
- `python manage.py process_commissions` - Process pending commissions
- `python manage.py manage_subscriptions` - Handle subscription renewals
- `python manage.py generate_invoices` - Generate monthly invoices
- `python manage.py check_plans` - Verify subscription plans
- `python manage.py create_demo_transactions` - Create demo data

---

## 💰 Business Model

### **Revenue Streams**
1. **Subscription Fees**: Monthly/annual recurring revenue from real estate companies
2. **Commission on Marketplace**: Transaction fees on property sales through platform
3. **Premium Features**: Advanced analytics, API access, white-labeling
4. **Affiliate Programs**: Revenue share with successful marketers
5. **Advertising**: Promoted listings in property marketplace (future)

### **Target Market**
- **Primary**: Real estate companies in Nigeria (SMEs to large enterprises)
- **Secondary**: Property developers, estate agents, real estate marketers
- **Tertiary**: Individual property investors and buyers

### **Growth Strategy**
1. **Phase 1 (MVP)**: Onboard 50-100 real estate companies in Lagos and Abuja
2. **Phase 2 (Expansion)**: Scale to 500+ companies across major Nigerian cities
3. **Phase 3 (Marketplace)**: Launch property marketplace with co-buying features
4. **Phase 4 (Regional)**: Expand to other West African markets
5. **Phase 5 (Platform)**: Become the de facto infrastructure for African real estate

---

## 🔐 Security & Compliance

- **Data Protection**: GDPR-inspired data handling practices
- **Financial Compliance**: PCI-DSS ready for card data
- **Audit Trail**: Complete activity logging
- **Backup Strategy**: Automated database backups
- **Disaster Recovery**: Documented recovery procedures
- **Penetration Testing**: Security assessment checkpoints

---

## 📞 Support & Contact

- **Technical Documentation**: Available in `/docs` directory
- **API Documentation**: Available at `/api/docs/` endpoint
- **Admin Panel**: Accessible at `/admin/` (Django admin)
- **Super Admin Panel**: Accessible at `/super-admin/`

---

## 📝 License

Proprietary - All rights reserved. This is a commercial SaaS platform.

---

## 🎉 Conclusion

This platform represents a **complete digital transformation solution** for Nigeria's real estate industry. It's not just software - it's the foundation for building the largest real estate network in Africa, connecting companies, marketers, clients, and properties in one unified, scalable, secure ecosystem.

### **Current Status**: ✅ Production-Ready MVP
### **Companies Supported**: Unlimited
### **Scalability**: Designed for millions of users
### **Maintenance**: Active development and support

---

**Built with ❤️ for Nigeria's Real Estate Future**

*Transform your real estate business. Scale your operations. Join the digital revolution.*
