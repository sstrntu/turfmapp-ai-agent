# API Documentation - Permission Management System

## Overview
This document describes the API endpoints for the permission management system in TURFMAPP. The system provides user settings management and administrative functions with role-based access control.

## Authentication
All endpoints require authentication via Bearer token in the Authorization header:
```
Authorization: Bearer <supabase_jwt_token>
```

## User Roles
- `user`: Standard user with access to basic settings
- `admin`: Administrative user with user management capabilities
- `super_admin`: Super administrator with full system access

## Settings Endpoints

### Get User Profile
**GET** `/api/v1/settings/profile`

Returns the current user's profile information.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "role": "user",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "last_login_at": "2024-01-01T00:00:00Z"
}
```

### Update User Profile
**PUT** `/api/v1/settings/profile`

Updates the current user's profile. Only `name` field can be updated.

**Request Body:**
```json
{
  "name": "New Name"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com", 
  "name": "New Name",
  "role": "user",
  "status": "active",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Get User Preferences
**GET** `/api/v1/settings/preferences`

Returns user preferences. Creates default preferences if none exist.

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "system_prompt": "You are a helpful assistant",
  "default_model": "gpt-4o",
  "settings": {"theme": "dark"},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Update User Preferences
**PUT** `/api/v1/settings/preferences`

Updates user preferences. Creates new preferences if none exist.

**Request Body:**
```json
{
  "system_prompt": "Custom system prompt",
  "default_model": "gpt-4o-mini",
  "settings": {"theme": "light"}
}
```

**Response:**
```json
{
  "id": "uuid",
  "user_id": "uuid", 
  "system_prompt": "Custom system prompt",
  "default_model": "gpt-4o-mini",
  "settings": {"theme": "light"},
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Delete Account
**DELETE** `/api/v1/settings/account`

Permanently deletes the current user's account and all associated data.

**Response:**
```json
{
  "message": "Account deleted successfully"
}
```

## Admin Endpoints

### Get Admin Statistics
**GET** `/api/v1/admin/stats`

Returns system statistics. Requires admin or super_admin role.

**Response:**
```json
{
  "users": {
    "total": 150,
    "active": 145,
    "pending": 5
  },
  "conversations": {
    "total": 500,
    "recent": 120
  },
  "messages": {
    "total": 2500,
    "recent": 800
  },
  "uploads": {
    "total": 75
  }
}
```

### Get All Users
**GET** `/api/v1/admin/users`

Returns list of all users. Requires admin or super_admin role.

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "user@example.com",
    "name": "User Name", 
    "role": "user",
    "status": "active",
    "created_at": "2024-01-01T00:00:00Z",
    "last_login_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get Pending Users
**GET** `/api/v1/admin/users/pending`

Returns list of users with pending status. Requires admin or super_admin role.

**Response:**
```json
[
  {
    "id": "uuid",
    "email": "pending@example.com",
    "name": "Pending User",
    "role": "user", 
    "status": "pending",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Update User
**PUT** `/api/v1/admin/users/{user_id}`

Updates a user's role or status. Requires admin or super_admin role.
Note: Only super_admin can assign super_admin role.

**Request Body:**
```json
{
  "role": "admin",
  "status": "active"
}
```

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "role": "admin",
  "status": "active",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Approve User
**POST** `/api/v1/admin/users/{user_id}/approve`

Approves a pending user, changing their status to active. Requires admin or super_admin role.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "name": "User Name",
  "role": "user",
  "status": "active",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Delete User
**DELETE** `/api/v1/admin/users/{user_id}`

Deletes a user account. Requires admin or super_admin role.
Note: Users cannot delete their own account through this endpoint.

**Response:**
```json
{
  "message": "User deleted successfully"
}
```

## Announcement Endpoints

### Get Active Announcements (Public)
**GET** `/api/v1/admin/announcements/active`

Returns all active announcements. No authentication required.

**Response:**
```json
[
  {
    "id": "uuid",
    "content": "Welcome to TURFMAPP!",
    "expires_at": "2024-12-31T23:59:59Z",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Get All Announcements
**GET** `/api/v1/admin/announcements`

Returns all announcements. Requires admin or super_admin role.

**Response:**
```json
[
  {
    "id": "uuid",
    "created_by": "uuid",
    "content": "System maintenance tonight",
    "expires_at": "2024-12-31T23:59:59Z",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Announcement
**POST** `/api/v1/admin/announcements`

Creates a new announcement. Requires admin or super_admin role.

**Request Body:**
```json
{
  "content": "System maintenance tonight",
  "expires_at": "2024-12-31T23:59:59Z"
}
```

**Response:**
```json
{
  "id": "uuid",
  "created_by": "uuid",
  "content": "System maintenance tonight",
  "expires_at": "2024-12-31T23:59:59Z",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Update Announcement
**PUT** `/api/v1/admin/announcements/{announcement_id}`

Updates an existing announcement. Requires admin or super_admin role.

**Request Body:**
```json
{
  "content": "Updated announcement content",
  "expires_at": "2024-12-31T23:59:59Z",
  "is_active": false
}
```

**Response:**
```json
{
  "id": "uuid",
  "created_by": "uuid",
  "content": "Updated announcement content",
  "expires_at": "2024-12-31T23:59:59Z", 
  "is_active": false,
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### Delete Announcement
**DELETE** `/api/v1/admin/announcements/{announcement_id}`

Deletes an announcement. Requires admin or super_admin role.

**Response:**
```json
{
  "message": "Announcement deleted successfully"
}
```

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 403 Forbidden
```json
{
  "detail": "Admin privileges required"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting
- Standard endpoints: 100 requests per minute
- Admin endpoints: 50 requests per minute
- Account deletion: 1 request per hour

## Security Notes
- All endpoints validate JWT tokens through Supabase
- Role-based access control is enforced at the API level
- Admin cache is implemented on the frontend for performance (5-minute TTL)
- User preferences are isolated per user through database-level security
- Account deletion is irreversible and removes all associated data