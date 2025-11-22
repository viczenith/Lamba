# LOGIN PAGE 404 ERRORS - TROUBLESHOOTING GUIDE

## Quick Summary

✅ **FIX APPLIED**: Changed `BASE_URL` in `api-client.js` from `/api/v1` to `/api`

## 🚨 If You Still See 404 Errors

### Step 1: Hard Refresh Browser Cache

```
Windows/Linux:  Ctrl + Shift + Delete
Mac:            Cmd + Shift + Delete
```

Then:
1. Select "All time"
2. Check "Cached images and files"
3. Click "Clear data"
4. Reload page: `Ctrl + F5`

### Step 2: Check Developer Tools

**Open DevTools**:
- Press `F12` or `Ctrl + Shift + I`
- Go to "Network" tab
- Reload page: `Ctrl + F5`

**Look for**:
- ❌ Any requests to `/api/v1/...` → Should be GONE now
- ✅ Requests to `/api/companies/` → Normal, should work
- ✅ Page Status → Should be 200 OK

### Step 3: Check Console for Errors

In DevTools:
1. Click "Console" tab
2. Look for red errors
3. If error mentions `api-client.js`, check that:
   - File exists at `estateApp/static/js/api-client.js`
   - File contains `const BASE_URL = '/api';` (not `/api/v1`)

### Step 4: Verify File Was Modified

Open: `estateApp/static/js/api-client.js`

Check line 7:
```javascript
const BASE_URL = '/api';  // ✅ Should be THIS
```

NOT:
```javascript
const BASE_URL = '/api/v1';  // ❌ If it's this, change it
```

### Step 5: Restart Django Server

```bash
# If server is running, stop it: Ctrl + C
# Then restart:
python manage.py runserver
# Or with host:
python manage.py runserver 0.0.0.0:8000
```

## 📋 What Could Cause 404 Errors

| Cause | Solution |
|-------|----------|
| Browser cache not cleared | Clear cache (Ctrl+Shift+Delete) |
| Django server not restarted | Restart: Stop (Ctrl+C) then `python manage.py runserver` |
| File not saved properly | Save again and verify change |
| Old version of code deployed | Pull latest and restart |
| Reverse proxy configuration | Check nginx/Apache configuration |

## 🔍 Understanding the 404s

### Why `/api/v1/companies/` Was Being Requested:

1. **Old Configuration**:
   - `api-client.js` had `BASE_URL = '/api/v1'`
   - This was WRONG - Django routes were at `/api/` not `/api/v1/`

2. **What We Fixed**:
   - Changed BASE_URL to `/api`
   - Now matches Django's actual URL configuration

3. **Result**:
   - All JavaScript API calls go to correct endpoint
   - No more 404 errors
   - Pages work properly

## ✅ How to Verify It's Fixed

### Method 1: Check Network Tab
1. Open DevTools (F12)
2. Go to Network tab
3. Refresh page (Ctrl+F5)
4. Search for `/api/v1` in the Network tab
   - Should find: **NOTHING** ✅
5. Search for `/api/` in the Network tab
   - Should find: Multiple requests all with 200/201 status ✅

### Method 2: Check API Works
1. Login successfully
2. Navigate to dashboard
3. Check that dashboard loads without errors
4. DevTools console should be clean

### Method 3: Test API Directly
Open browser console (F12 → Console) and run:
```javascript
// This should work now (not return 404)
fetch('/api/companies/')
  .then(r => r.json())
  .then(d => console.log('API Working:', d))
  .catch(e => console.error('API Error:', e))
```

## 🎯 Login Page Checklist

- [ ] Login page loads without JavaScript errors
- [ ] Login page shows centered form ✅
- [ ] Email/Password fields visible
- [ ] "Sign In" button clickable
- [ ] Signup modal opens when clicking "Create Account"
- [ ] No red error messages in DevTools console

## 📞 Debugging Commands

### Check Django URL Configuration:
```bash
python manage.py show_urls | grep api
```

### Check if API Endpoints Exist:
```bash
curl http://localhost:8000/api/companies/
```

Should return (not 404):
- `{"detail":"Authentication credentials were not provided."}` → **API exists** ✅
- `{"detail":"Not found."}` → **Endpoint doesn't exist** ❌
- `404 Not Found` → **API path doesn't exist** ❌

### Check api-client.js Syntax:
```bash
# On Windows/PowerShell
python -m json.tool estateApp\static\js\api-client.js
```

## 🚀 Final Verification

Run this script to verify everything:
```bash
python verify_api_config.py
```

Expected output should show:
```
✅ API Endpoints Found:
  ✅ api/...
  ✅ api/admin-support/...
  ✅ All endpoints at /api/
```

## 💡 Pro Tips

1. **Use Incognito Window**: Opens with completely fresh cache
   - Windows: `Ctrl + Shift + N`
   - Mac: `Cmd + Shift + N`

2. **Check Django Debug Toolbar** (if installed):
   - Bottom right corner while on page
   - Shows all API calls made
   - Shows timing and responses

3. **Monitor Logs**: Keep terminal open showing Django logs
   ```bash
   python manage.py runserver 2>&1 | grep -i "api\|404\|error"
   ```

## 🎓 What You Learned

- API client was pointing to wrong URL prefix
- Django was configured at `/api/` not `/api/v1/`
- Browser cache can hide code changes
- DevTools Network tab is your best debugging tool
- Clearing cache and restarting server fixes most issues

---

**Last Updated**: 2025-11-20
**Status**: ✅ All 404 errors should be resolved
