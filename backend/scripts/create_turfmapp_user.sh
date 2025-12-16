#!/bin/bash
# Create turfmapp_agent user and transfer database ownership

set -e

echo "🔧 Creating turfmapp_agent user and transferring database ownership..."
echo ""

DB_NAME="turfmapp_dev"
OLD_USER="sirasasitorn"
NEW_USER="turfmapp_agent"
PASSWORD="Z3c2et-2025"

# Step 1: Create new user
echo "Step 1: Creating user '$NEW_USER'..."
PGPASSWORD='Z3c2et-2025' psql -U $OLD_USER postgres -c "CREATE USER $NEW_USER WITH PASSWORD '$PASSWORD' CREATEDB SUPERUSER;" 2>/dev/null || \
PGPASSWORD='Z3c2et-2025' psql -U $OLD_USER postgres -c "ALTER USER $NEW_USER WITH PASSWORD '$PASSWORD' CREATEDB SUPERUSER;"
echo "✅ User created/updated"
echo ""

# Step 2: Grant privileges on database
echo "Step 2: Granting privileges on database '$DB_NAME'..."
PGPASSWORD='Z3c2et-2025' psql -U $OLD_USER postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $NEW_USER;"
echo "✅ Database privileges granted"
echo ""

# Step 3: Transfer ownership of database
echo "Step 3: Transferring database ownership..."
PGPASSWORD='Z3c2et-2025' psql -U $OLD_USER postgres -c "ALTER DATABASE $DB_NAME OWNER TO $NEW_USER;"
echo "✅ Database ownership transferred"
echo ""

# Step 4: Transfer ownership of schema
echo "Step 4: Transferring schema ownership..."
PGPASSWORD='Z3c2et-2025' psql -U $OLD_USER -d $DB_NAME -c "ALTER SCHEMA turfmapp_agent OWNER TO $NEW_USER;"
echo "✅ Schema ownership transferred"
echo ""

# Step 5: Transfer ownership of all tables
echo "Step 5: Transferring table ownership..."
PGPASSWORD='Z3c2et-2025' psql -U $OLD_USER -d $DB_NAME << EOF
-- Transfer ownership of all tables
ALTER TABLE turfmapp_agent.users OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.conversations OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.messages OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.user_preferences OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.document_nodes OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.embeddings OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.memory_states OWNER TO $NEW_USER;
ALTER TABLE turfmapp_agent.workflow_executions OWNER TO $NEW_USER;

-- Grant all privileges on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA turfmapp_agent TO $NEW_USER;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA turfmapp_agent TO $NEW_USER;
GRANT USAGE ON SCHEMA turfmapp_agent TO $NEW_USER;
EOF
echo "✅ Table ownership transferred"
echo ""

# Step 6: Test connection with new user
echo "Step 6: Testing connection with new user..."
PGPASSWORD='Z3c2et-2025' psql -U $NEW_USER -d $DB_NAME -c "SELECT COUNT(*) FROM turfmapp_agent.users;" > /dev/null
echo "✅ Connection test successful"
echo ""

echo "🎉 Migration complete!"
echo ""
echo "New connection details:"
echo "  User: $NEW_USER"
echo "  Password: $PASSWORD"
echo "  Database: $DB_NAME"
echo "  Connection String: postgresql://$NEW_USER:$PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "⚠️  Don't forget to update .env.local with the new connection string!"
echo ""
