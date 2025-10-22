#!/bin/bash
# Create PostgreSQL user and database for TurfMapp
# This script assumes you have sudo access and PostgreSQL is installed via Homebrew

set -e

echo "🔧 Setting up PostgreSQL user and database..."

# Configuration
DB_NAME="turfmapp_dev"
DB_USER="turfmapp_admin"
DB_PASSWORD="Z3c2et-2025"

# Stop PostgreSQL to modify configuration
echo "Stopping PostgreSQL..."
brew services stop postgresql@14

# Backup current pg_hba.conf
echo "Backing up pg_hba.conf..."
cp /opt/homebrew/var/postgresql@14/pg_hba.conf /opt/homebrew/var/postgresql@14/pg_hba.conf.backup

# Update pg_hba.conf to allow local trust authentication temporarily
echo "Updating pg_hba.conf for local trust..."
cat > /opt/homebrew/var/postgresql@14/pg_hba.conf << 'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
# Allow replication connections from localhost
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
EOF

# Start PostgreSQL
echo "Starting PostgreSQL..."
brew services start postgresql@14

# Wait for PostgreSQL to start
sleep 3

# Create PostgreSQL user
echo "Creating PostgreSQL user: $DB_USER..."
psql postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD' CREATEDB;" 2>/dev/null || \
psql postgres -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD' CREATEDB;"

# Create database
echo "Creating database: $DB_NAME..."
psql postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || \
echo "Database $DB_NAME already exists"

# Grant privileges
echo "Granting privileges..."
psql postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# Now update pg_hba.conf to use md5 authentication for the new user
echo "Updating pg_hba.conf for password authentication..."
cat > /opt/homebrew/var/postgresql@14/pg_hba.conf << 'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# Allow turfmapp_admin with password
local   all             turfmapp_admin                          md5
host    all             turfmapp_admin  127.0.0.1/32            md5
host    all             turfmapp_admin  ::1/128                 md5

# "local" is for Unix domain socket connections only (trust for other users)
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            trust
# IPv6 local connections:
host    all             all             ::1/128                 trust
# Allow replication connections from localhost
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
EOF

# Reload PostgreSQL configuration
echo "Reloading PostgreSQL configuration..."
psql postgres -c "SELECT pg_reload_conf();"

echo ""
echo "✅ PostgreSQL setup complete!"
echo ""
echo "Database Details:"
echo "  User: $DB_USER"
echo "  Password: $DB_PASSWORD"
echo "  Database: $DB_NAME"
echo "  Connection String: postgresql://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME"
echo ""
echo "Test connection with:"
echo "  PGPASSWORD='$DB_PASSWORD' psql -U $DB_USER -d $DB_NAME -c 'SELECT version();'"
echo ""
