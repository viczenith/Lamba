# User Engagement Email System

## Overview

The User Engagement Email System automatically sends targeted emails to users based on their activity levels across all company-affiliated users. This includes direct company members, affiliated marketers, and affiliated clients.

## Features

### 1. **Re-engagement Emails**
- **Target Users**: Users who haven't logged in for 30+ days
- **Purpose**: Encourage inactive users to return to the platform
- **Template**: Professional reminder with highlights of new features
- **Email Type**: HTML + Plain Text

### 2. **Onboarding Emails**  
- **Target Users**: Users who have never logged in
- **Purpose**: Welcome new users and provide guidance to get started
- **Template**: Step-by-step onboarding guide with action items
- **Email Type**: HTML + Plain Text

## User Identification

The system identifies users from **all sources**:

1. **Direct Company Users**
   - Users with `company_profile = company`
   - Stored in `CustomUser` base model

2. **Affiliated Marketers**
   - Users added via `MarketerAffiliation` table
   - Added through "Add Existing User" modal
   - Can work with multiple companies

3. **Affiliated Clients**
   - Users tracked in `ClientMarketerAssignment` table
   - Company-specific assignments

## Implementation

### Backend Files

#### 1. **estateApp/engagement_emails.py** (New)
Main engagement email module with:
- `EngagementEmailConfig`: Email template configuration
- `send_reengagement_email()`: Send single re-engagement email
- `send_onboarding_email()`: Send single onboarding email
- `send_bulk_reengagement_emails()`: Send batch re-engagement emails
- `send_bulk_onboarding_emails()`: Send batch onboarding emails
- `get_email_engagement_summary()`: Get engagement stats for a company

#### 2. **estateApp/views.py** (Modified)
- Added `send_engagement_emails()` POST API endpoint
- Modified `company_profile_view()` to include:
  - `users_needing_reengagement`: List of users inactive 30+ days
  - `users_never_logged_in`: List of users never logged in
  - `engagement_email_stats`: Summary statistics

#### 3. **Email Templates** (New)
Located in `templates/emails/`:

- **reengagement_reminder.html**: Beautiful HTML template with company branding
- **reengagement_reminder.txt**: Plain text fallback
- **onboarding_reminder.html**: Detailed welcome guide with 3-step onboarding
- **onboarding_reminder.txt**: Plain text version

### Frontend Integration

#### Company Profile Dashboard
Added in `admin_side/company_profile.html`:

1. **Engagement Email Section**
   - Shows count of users needing re-engagement
   - Shows count of users needing onboarding
   - Total users to contact

2. **Action Buttons**
   - "Send Re-engagement Emails" button
   - "Send Onboarding Emails" button
   - JavaScript handling for async email sending

### URL Routes

Added to `estateApp/urls.py`:
```
path('company-profile/send-engagement-emails/', send_engagement_emails, name='send-engagement-emails')
```

## Usage

### For Company Admins

1. Navigate to Company Profile → Users Tab
2. View engagement statistics:
   - Users not active for 30+ days
   - Users who never logged in
3. Click "Send Re-engagement Emails" or "Send Onboarding Emails"
4. System sends emails to corresponding users
5. Receive confirmation with count of emails sent

### API Endpoint

**POST** `/company-profile/send-engagement-emails/`

**Parameters:**
```json
{
  "email_type": "reengagement"  // or "onboarding"
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Successfully sent 4 reengagement emails",
  "stats": {
    "total": 4,
    "sent": 4,
    "failed": 0,
    "errors": []
  }
}
```

## Email Templates Details

### Re-engagement Email
- **Subject**: "We miss you! Get back to {company_name}"
- **Highlights**:
  - Professional reminder tone
  - Highlights of new features
  - Easy call-to-action to log in
  - Support contact information

### Onboarding Email
- **Subject**: "Welcome to {company_name}! Let's get started"
- **Includes**:
  - 3-step getting started guide
  - Benefits of the platform
  - User role information
  - Help resources
  - Quick bookmark tip
  - Professional welcome

## Email Configuration

Emails are sent using Django's `EmailMultiAlternatives`:

```python
# Settings required in settings.py:
DEFAULT_FROM_EMAIL = 'noreply@yourdomain.com'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # or your email provider
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
SITE_URL = 'http://localhost:8000'  # or production URL
```

## Multi-tenancy

✅ **Fully Multi-Tenant Safe**

- Emails only sent to users of the requesting company
- Company admins can only see/send emails for their own company
- Affiliated users from different companies are NOT included
- Each company is completely isolated

## Logging

All email operations are logged to Django logger:

```
estateApp.engagement_emails
```

Log levels:
- **INFO**: Email sent successfully
- **INFO**: Batch completed with stats
- **ERROR**: Email send failures with details

## Features & Benefits

✅ **Automated Engagement**: Keep users active with timely reminders
✅ **New User Onboarding**: Guide first-time users through the platform
✅ **Multi-tenant Safe**: Each company has complete isolation
✅ **Batch Processing**: Send to multiple users efficiently
✅ **Error Handling**: Graceful failure handling with logging
✅ **Beautiful Templates**: Professional HTML emails with fallback
✅ **User Identification**: Includes all affiliated users
✅ **Real-time Stats**: Dashboard shows exact counts before sending
✅ **Audit Trail**: All sends logged for compliance

## Future Enhancements

Potential additions:
1. Schedule emails for specific times
2. A/B testing for subject lines
3. Email open tracking
4. Click-through tracking
5. Custom email templates per company
6. Frequency capping (prevent spam)
7. User preference management (opt-out)
8. Template variables for personalization

## Security

✅ Admin-only access
✅ Company-scoped isolation
✅ CSRF protection on POST
✅ Logging of all sends
✅ Error messages don't leak user data
✅ HTML email sanitization
