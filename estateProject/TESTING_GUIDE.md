# 🧪 Unified Login - Quick Testing Guide

## Quick Test Commands

### 1. Validate Django Configuration
```powershell
cd "c:\Users\HP\Documents\VictorGodwin\RE\Multi-Tenant Architecture\RealEstateMSApp\estateProject"
python manage.py check
```
**Expected Output**: `System check identified no issues (0 silenced).`

### 2. Run Development Server
```powershell
python manage.py runserver
```
**Then visit**: http://127.0.0.1:8000/login/

---

## 🎯 Feature Testing Checklist

### Login Form
- [ ] Email field displays
- [ ] Password field displays
- [ ] Password visibility toggle (👁️) appears on password field
- [ ] Clicking toggle shows password as text
- [ ] Clicking toggle again hides password
- [ ] "Remember me" checkbox works
- [ ] "Forgot password?" link works
- [ ] "Sign in" button has purple gradient color

### Client/Affiliate Sign Up Link
- [ ] Text appears BELOW "Sign in" button
- [ ] Text reads: "Create Client or Affiliate Account? Sign up"
- [ ] "Sign up" is underlined
- [ ] "Sign up" link is clickable
- [ ] Clicking opens account type selector modal

### Register Company Button
- [ ] Button has GREEN gradient color (#11998e → #38ef7d)
- [ ] Button is located below signup link
- [ ] Button has 🏢 icon
- [ ] Clicking opens company registration modal
- [ ] Button has shadow effect on hover

### Company Registration Modal
- [ ] Modal opens when "Register Company" clicked
- [ ] Contains company fields (Name, Reg #, Date, Location, CEO details)
- [ ] **NEW: Contains Secondary Admin section** with:
  - [ ] Secondary Admin Email field
  - [ ] Secondary Admin Phone field
  - [ ] Secondary Admin Full Name field
  - [ ] Purple info box explaining secondary admin role
- [ ] Password fields have visibility toggle (👁️)
- [ ] Close button (X) works
- [ ] ESC key closes modal
- [ ] Clicking outside closes modal
- [ ] Password validation works (8 char min, match check)
- [ ] "Create Company Account" button works

### Account Type Selector Modal
- [ ] Modal opens when "Sign up" link clicked
- [ ] Shows two radio options:
  - [ ] 👤 Client
  - [ ] 🤝 Affiliate/Marketer
- [ ] Radio buttons are styled beautifully with borders
- [ ] Selected radio has purple gradient background
- [ ] "Next" button works
- [ ] Closes and opens appropriate registration modal

### Client Registration Modal
- [ ] Modal opens when "Client" selected
- [ ] Contains: First name, Last name, Email, Phone fields
- [ ] Password field has visibility toggle (👁️)
- [ ] Confirm password field has visibility toggle (👁️)
- [ ] Form validation works
- [ ] "Create Client Account" button works

### Marketer Registration Modal
- [ ] Modal opens when "Affiliate/Marketer" selected
- [ ] Contains: First name, Last name, Email, Phone, Experience dropdown
- [ ] Password field has visibility toggle (👁️)
- [ ] Confirm password field has visibility toggle (👁️)
- [ ] Form validation works
- [ ] "Create Marketer Account" button works

### Responsive Design
- [ ] **Desktop (>576px)**: All 2-column forms look good
- [ ] **Tablet (768px)**: Modals scale appropriately
- [ ] **Mobile (<576px)**: 
  - [ ] Forms are single-column
  - [ ] Radio buttons stack vertically
  - [ ] Password eye icon is positioned correctly
  - [ ] Modal is readable and usable
  - [ ] Buttons are finger-friendly

### Remember Me Feature
1. [ ] On login page, check "Remember me"
2. [ ] Enter email: `test@example.com`
3. [ ] Close browser/refresh page
4. [ ] Return to login page
5. [ ] **Verify**: Email field is auto-filled with `test@example.com`
6. [ ] **Verify**: "Remember me" checkbox is checked
7. [ ] Now uncheck "Remember me" and submit
8. [ ] Refresh page
9. [ ] **Verify**: Email field is now EMPTY

### Forgot Password Feature
- [ ] "Forgot password?" link appears in login form
- [ ] Clicking link redirects to password reset page
- [ ] Password reset form accepts email
- [ ] System sends reset email
- [ ] Reset link in email works
- [ ] New password can be set
- [ ] Can login with new password

### Security Features
- [ ] Honeypot field exists (hidden, not visible)
- [ ] CSRF token present in all forms
- [ ] Login throttle: 6 attempts → 2-min lockout
- [ ] Client IP field present (hidden)
- [ ] SSL badge displays on login page

### Visual Polish
- [ ] Animations are smooth (fadeIn, slideUp, float)
- [ ] Colors are consistent (purple #667eea, green #11998e)
- [ ] Buttons have hover effects
- [ ] Icons display correctly
- [ ] Spacing/padding is consistent
- [ ] No layout broken on any screen size

---

## 📊 Password Visibility Toggle Test

### Login Page
1. Go to login page
2. Click password field
3. Type a password (should be hidden with dots)
4. Click the 👁️ icon on right of password field
5. **Verify**: Password now displays as plain text
6. Click eye icon again
7. **Verify**: Password is hidden again

### Company Registration
1. Click "Register Company"
2. Scroll to Password section
3. Click password field
4. Type password
5. Click 👁️ icon
6. **Verify**: Shows as text
7. Test "Confirm Password" field same way

### Client Registration
1. Click "Sign up" → Select "Client" → Company modal opens
2. Scroll to password fields
3. Test both password and confirm password fields
4. **Verify**: Both have working eye toggle

### Marketer Registration
1. Click "Sign up" → Select "Affiliate/Marketer"
2. Scroll to password fields
3. Test both password and confirm password fields
4. **Verify**: Both have working eye toggle

---

## 🐛 Troubleshooting

### Modal not opening?
- Check browser console for JavaScript errors
- Verify modal IDs match function names
- Check if buttons have correct `onclick` handlers

### Password toggle not working?
- Verify button has `type="button"` (not submit)
- Check that input ID matches the onclick parameter
- Ensure FontAwesome is loaded for eye icons

### Remember me not working?
- Check browser allows localStorage
- Open DevTools → Application → Local Storage
- Should see key: `lamba_remember_email`

### Forgot password link broken?
- Verify URL route is added to urls.py
- Check password_reset.html template exists
- Verify email backend is configured

### Secondary admin fields not appearing?
- Refresh browser (clear cache)
- Check HTML for secondary admin section markup
- Verify backend view processes secondary admin fields

### Responsive design broken?
- Check media query in style tag
- Verify breakpoint at 576px
- Test on actual mobile device (not just browser DevTools)

---

## 📞 Support Notes

**All Features Working?** ✅ Ready for production!

**Deployment Checklist**:
- [ ] Email backend configured (for password reset)
- [ ] Allowed hosts updated with domain
- [ ] Password reset templates created
- [ ] SSL certificate installed
- [ ] DATABASE configured for secondary_admin fields
- [ ] Static files collected
- [ ] DEBUG = False set

---

**Last Updated**: November 22, 2025
**Status**: Ready for Testing ✅
