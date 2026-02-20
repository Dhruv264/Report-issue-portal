# Rejection Reason Feature Implementation

## Summary
The rejection reason feature has been successfully added to the Report Issue Portal. This allows admins to provide a reason when rejecting issues, and users can see the rejection reason when viewing their rejected issues.

## Changes Made

### 1. **Backend - Routes (routes/admin_routes.py)**
- Updated `/admin/reject-issue/<issue_id>` endpoint to accept `rejection_reason` from POST request
- Stores rejection reason in the database when an issue is rejected

### 2. **Frontend - Admin Dashboard (templates/admin_dashboard.html)**
- Added a rejection modal with a text area for entering rejection reason
- Replaced direct reject button with a modal-opening button
- Added JavaScript functions:
  - `openRejectModal()` - Opens rejection modal
  - `closeRejectModal()` - Closes rejection modal
  - `submitReject()` - Submits rejection reason
- Modal includes:
  - Issue title display
  - Text area for rejection reason
  - Cancel and Confirm buttons
  - Keyboard support (Escape to close)

### 3. **Frontend - User Issues Page (templates/my_issues.html)**
- Added styling for rejected status (red color)
- Added rejection banner that displays:
  - "Rejection Reason:" label
  - Admin's rejection reason text
  - Only shows when issue status is "Rejected" and reason exists

### 4. **Backend - App Route (app.py)**
- Updated `my_issues()` route to fetch `rejection_reason` field from database

### 5. **Database Migration**
- Created `add_rejection_reason.py` script to add `rejection_reason` column to issues table
- Column is TEXT type, nullable

## How to Use

### Run Migration (First Time Only)
```bash
python add_rejection_reason.py
```
This script will:
- Check if the `rejection_reason` column exists
- Add it if it doesn't exist
- Display success/error message

### Admin Workflow
1. Go to Admin Dashboard
2. View pending issues
3. Click "Reject" button on any pending issue
4. Modal appears asking for rejection reason
5. Type the reason in the text area
6. Click "Reject Issue" button
7. Issue status changes to "Rejected" with reason stored

### User Experience
1. User views "My Issues" page (dashboard)
2. If an issue is rejected, they see:
   - Status badge showing "Rejected" in red
   - A rejection banner showing the admin's reason
3. User understands why their issue was rejected

## Database Schema
```sql
ALTER TABLE issues
ADD COLUMN rejection_reason TEXT DEFAULT NULL;
```

## Features
✅ Non-intrusive rejection modal
✅ User-friendly reason display to users
✅ Preserves all issue data
✅ Keyboard support (Escape to close modal)
✅ Click outside modal to close
✅ Clear visual indicators for rejected issues
✅ Optional: Admin can provide detailed rejection reasons

## Future Enhancements
- Allow re-submission of rejected issues
- Email notification to users about rejection
- Rejection reason editing by admin
- Bulk rejection with multiple reason templates
