# TURFMAPP Permission Management System - User Guide

## Overview
TURFMAPP now features a comprehensive permission management system with role-based access control. This guide explains how to use the Settings page and its features.

## Accessing Settings
1. Log in to your TURFMAPP account
2. Click on **Settings** in the main navigation menu
3. The Settings page will open with two tabs (if you have admin privileges)

## Settings Tab (Available to Everyone)

The Settings tab contains personal account settings that every user can access:

### Profile Settings
- **Name**: Update your display name
- **Email**: View your registered email (cannot be changed)
- **Role**: View your current role in the system

### Model Preferences
- **Default Model**: Choose your preferred AI model (gpt-4o, gpt-4o-mini, o1-preview, o1-mini)
- **System Prompt**: Set a custom system prompt that will be used for all your conversations

### Account Management
- **Delete Account**: Permanently delete your account and all associated data
  - ⚠️ **Warning**: This action cannot be undone
  - All your conversations, uploads, and settings will be permanently removed

## Admin Tab (Admins and Super Admins Only)

The Admin tab is only visible if you have admin or super_admin privileges:

### User Management
- **View All Users**: See a list of all registered users
- **User Roles**: Assign roles to users (user, admin, super_admin)
- **User Status**: Approve pending users or manage user status
- **User Actions**: Delete user accounts (except your own)

### Role Hierarchy
- **User**: Standard user with access to basic features
- **Admin**: Can manage users and create announcements
- **Super Admin**: Full administrative access, can assign admin roles

### System Statistics
View important system metrics:
- Total users, active users, pending users
- Total conversations and recent activity
- Message counts and upload statistics

### Announcements
- **Create Announcements**: Post system-wide announcements
- **Manage Announcements**: Edit or delete existing announcements
- **Set Expiration**: Configure when announcements should expire

## User Roles Explained

### User Role
- Access to personal settings and preferences
- Can use all AI chat features
- Can upload files and manage conversations
- Cannot see admin functions

### Admin Role
- All user permissions plus:
- View and manage other users
- Approve pending user registrations
- Create and manage system announcements
- View system statistics
- **Cannot assign super_admin role**

### Super Admin Role
- All admin permissions plus:
- Can assign admin roles to other users
- Can assign super_admin roles
- Full system access
- Cannot delete own account through admin panel

## Performance Features

### Admin Status Caching
- Your admin status is cached for 5 minutes to improve page load speed
- Cache automatically refreshes when you sign in with a different account
- This ensures the Admin tab appears instantly for admin users

### Instant UI Updates
- Settings changes are applied immediately
- Role changes take effect on next page refresh
- Admin UI elements show/hide based on your permissions

## Security Features

### Authentication
- All settings require valid login
- JWT tokens are verified for each request
- Automatic logout if session expires

### Authorization
- Role-based access control prevents unauthorized actions
- Users cannot access admin functions without proper privileges
- Database-level security ensures data isolation

### Data Protection
- Account deletion removes all personal data
- Admin actions are logged for audit purposes
- Sensitive operations require confirmation

## Common Tasks

### Changing Your Display Name
1. Go to Settings tab
2. Update the Name field
3. Click Save Changes

### Setting a Custom System Prompt
1. Go to Settings tab
2. Enter your custom prompt in the System Prompt field
3. Click Save Changes
4. This prompt will be used for all future conversations

### Choosing Your Preferred AI Model
1. Go to Settings tab  
2. Select from the Model dropdown
3. Your choice will be remembered for future chats

### Admin: Approving New Users
1. Go to Admin tab
2. Click on "Pending Users" 
3. Review user information
4. Click "Approve" to activate their account

### Admin: Assigning Roles
1. Go to Admin tab
2. Find the user in the users list
3. Select their new role from the dropdown
4. Click "Update User"
5. **Note**: Only super_admins can assign admin or super_admin roles

### Admin: Creating Announcements
1. Go to Admin tab
2. Scroll to Announcements section
3. Enter announcement content
4. Optionally set an expiration date
5. Click "Create Announcement"

## Troubleshooting

### Admin Tab Not Visible
- Ensure you have admin or super_admin privileges
- Try refreshing the page
- Check with a super_admin if you should have admin access

### Settings Not Saving
- Check your internet connection
- Ensure you're still logged in
- Try refreshing the page and attempting again

### Permission Denied Errors
- Verify you have the required role for the action
- Contact an admin if you believe you should have access
- Check if your session has expired

### Slow Admin Tab Loading
- Admin status is cached for 5 minutes for performance
- If you were recently promoted to admin, wait up to 5 minutes or clear browser cache

## Best Practices

### For Users
- Regularly update your profile information
- Choose a system prompt that matches your use case
- Be cautious with account deletion - it's permanent

### For Admins
- Regularly review pending users
- Keep announcements current and relevant
- Monitor system statistics for unusual activity
- Only assign admin roles to trusted users

### For Super Admins
- Carefully manage admin role assignments
- Regularly audit user roles and permissions
- Ensure at least one other super_admin exists before making changes

## Support

If you encounter issues with the permission management system:
1. Check this user guide for solutions
2. Try logging out and logging back in
3. Clear your browser cache and cookies
4. Contact a super_admin or system administrator

## Version History

- **v1.0**: Initial release with basic settings and admin functionality
- Current version includes role-based permissions, caching, and comprehensive user management