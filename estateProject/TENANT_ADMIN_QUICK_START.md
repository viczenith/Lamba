# 🚀 TENANT ADMIN DASHBOARD - QUICK START GUIDE

## 📍 Access URLs

```
Login:     http://127.0.0.1:8000/tenant-admin/login/
Dashboard: http://127.0.0.1:8000/tenant-admin/dashboard/
Logout:    http://127.0.0.1:8000/tenant-admin/logout/
```

## 🔐 System Admin Credentials

Check your `create_admin.py` script or create a new system admin:

```python
python create_admin.py
```

Required fields:
- `is_system_admin = True`
- `admin_level = 'system'`
- `company_profile = None`

## 🎯 Dashboard Navigation

| Section | Icon | What You Can Do |
|---------|------|-----------------|
| **Overview** | 📊 | View system stats, charts, recent activity |
| **Companies** | 🏢 | Search, view, manage all companies |
| **Users** | 👥 | Browse clients, marketers, admins |
| **Properties** | 🏠 | View all estates across companies |
| **Financial** | 💰 | Monitor revenue, transactions, MRR |
| **System Health** | 🏥 | Check uptime, API speed, database size |
| **Audit Logs** | 📋 | Review security logs and actions |

## 📊 Key Features

### Statistics Cards (Overview)
- **Total Companies:** Current count + growth trend
- **Total Users:** All users + weekly growth
- **Total Revenue:** Aggregate income + monthly %
- **Total Allocations:** Plot assignments + additions

### Company Management
- ✅ Search by name/email
- ✅ Filter by status/subscription
- ✅ View company details
- ✅ Export to CSV

### User Management (4 Tabs)
1. **All Users** - Complete directory
2. **Clients** - Shows CLT-XXX-#### IDs
3. **Marketers** - Shows MKT-XXX-#### IDs
4. **Admins** - System/company levels

### Financial Analytics
- Revenue trends (6 months)
- Transaction volume
- MRR calculation
- Pending payments

### System Health
- Uptime: 99.9% target
- API Response: ~124ms
- Database Size: Real-time
- Active Sessions: Live count

## 🔌 API Endpoints

All endpoints require system admin JWT token:

```javascript
Authorization: Bearer YOUR_JWT_TOKEN
```

### Dashboard Stats
```
GET /api/tenant-admin/dashboard-stats/
```

**Returns:** Companies, users, revenue, allocations with growth trends

### Recent Activity
```
GET /api/tenant-admin/recent-activity/
```

**Returns:** Last 20 system events with timestamps

### System Health
```
GET /api/tenant-admin/system-health/
```

**Returns:** Uptime, API speed, database metrics, active sessions

## 🛠️ Common Tasks

### 1. Find a Company
1. Click "Companies" in sidebar
2. Type name/email in search box
3. Click view icon to see details

### 2. Check User Status
1. Click "Users" in sidebar
2. Select appropriate tab (All/Clients/Marketers/Admins)
3. Search for user
4. Check status badge (Active/Inactive)

### 3. Monitor Revenue
1. Click "Financial" in sidebar
2. Review "Total Revenue" card
3. Check growth percentage
4. View revenue chart for trends

### 4. Check System Health
1. Click "System Health" in sidebar
2. Review all 4 metric cards
3. Check metrics chart for performance
4. Verify uptime is above 99%

### 5. Review Security Logs
1. Click "Audit Logs" in sidebar
2. Use search to filter logs
3. Export for compliance
4. Review suspicious activity

## 🎨 UI Components

### Status Badges
- 🟢 **Green (Active)** - Company/user is active
- 🔴 **Red (Inactive)** - Company/user is inactive
- 🟠 **Orange (Trial)** - Trial subscription
- 🟣 **Purple (Enterprise)** - Enterprise tier

### Action Buttons
- 👁️ **Eye icon** - View details
- ✏️ **Pencil icon** - Edit record
- 🗑️ **Trash icon** - Delete record
- 📥 **Download icon** - Export data

## 📱 Responsive Design

| Device | Sidebar | Layout |
|--------|---------|--------|
| Desktop (1920px+) | Fixed left | Multi-column grids |
| Tablet (768-1919px) | Collapsible | 2-column grids |
| Mobile (<768px) | Hidden/Toggle | Single column |

## ⚠️ Important Notes

1. **Authentication Required**
   - Must be logged in as system admin
   - JWT token auto-refreshed
   - Session expires after inactivity

2. **Data Security**
   - All API calls authenticated
   - System-wide access only for system admins
   - Company admins cannot access this dashboard

3. **Auto-Refresh**
   - Statistics refresh every 2 minutes
   - Activity feed updates automatically
   - Manual refresh available

4. **Browser Support**
   - Chrome/Edge (recommended)
   - Firefox
   - Safari
   - Modern browsers only

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Dashboard won't load | Check if logged in as system admin |
| Stats show zero | Verify database has data |
| Charts not rendering | Check internet connection (CDN) |
| Search not working | Clear browser cache |
| Slow loading | Check network speed |

## 📊 Performance Tips

1. **Use Search** - Don't scroll through large tables
2. **Tab Between Sections** - Avoid reloading page
3. **Export Data** - For detailed analysis offline
4. **Monitor System Health** - Keep uptime above 99%

## 🔄 Refresh Options

### Auto-Refresh (Enabled)
- Statistics: Every 2 minutes
- Activity feed: Real-time
- Charts: On section load

### Manual Refresh
Click the "Refresh" button in top-right corner

## 📞 Quick Help

### Need More Data?
- Check if companies are registered
- Verify users are active
- Ensure transactions are recorded

### Dashboard Not Updating?
- Click refresh button
- Check API endpoint status
- Review browser console

### Security Concerns?
- Review audit logs
- Check failed login attempts
- Monitor suspicious activity

## ✅ Success Checklist

- [ ] Logged in as system admin
- [ ] Dashboard loads all sections
- [ ] Statistics cards show data
- [ ] Charts render properly
- [ ] Search works in tables
- [ ] Activity feed updates
- [ ] System health shows green

---

**Dashboard Version:** 2.0  
**Last Updated:** November 21, 2025  
**Status:** ✅ Fully Operational  
**Support:** See TENANT_ADMIN_DASHBOARD_DEPLOYMENT.md for details
