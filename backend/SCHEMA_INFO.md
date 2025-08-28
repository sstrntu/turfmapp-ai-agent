# TURFMAPP-AGENT Database Schema

## Schema Organization

This application uses the `turfmapp_agent` schema in your Supabase PostgreSQL database to ensure proper isolation when multiple applications share the same Supabase project.

## Schema Structure

```
Database: postgres
├── auth (Supabase managed)
│   └── users (Supabase auth users)
│
├── public (default schema)
│   └── (available for other apps)
│
└── turfmapp_agent (our application schema)
    ├── users (application user profiles)
    ├── user_preferences (system prompts, settings)
    ├── admin_permissions (admin privileges)
    ├── conversations (chat conversations)
    ├── messages (chat messages with ratings)
    ├── uploads (file uploads)
    ├── document_collections (RAG collections)
    ├── documents (RAG documents with vectors)
    └── announcements (system announcements)
```

## Benefits

1. **Multi-App Support**: You can deploy multiple applications to the same Supabase project
2. **Clean Separation**: Each app's data is isolated in its own schema
3. **Manageable Permissions**: Fine-grained access control per schema
4. **Easy Maintenance**: Clear organization for database administration

## Usage

All application tables are prefixed with the `turfmapp_agent` schema. When working with the database:

- **SQL Queries**: Use `turfmapp_agent.table_name`
- **SQLAlchemy Models**: Schema is defined in `__table_args__`
- **Supabase Dashboard**: Navigate to the `turfmapp_agent` schema to view tables

## Adding Other Apps

To add another app to the same Supabase project:

1. Create a new schema: `CREATE SCHEMA IF NOT EXISTS your_app_name;`
2. Deploy your app's tables to that schema
3. Set up appropriate RLS policies
4. Configure your app's search path

This keeps all applications organized and prevents conflicts.