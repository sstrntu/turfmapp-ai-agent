#!/bin/bash
# Reset PostgreSQL password for sirasasitorn user
# This script requires sudo access

set -e

echo "🔐 Resetting PostgreSQL password for user 'sirasasitorn'..."
echo ""
echo "⚠️  This script will modify PostgreSQL configuration and requires sudo access."
echo ""

NEW_PASSWORD="Z3c2et-2025"
PG_DATA_DIR="/Library/PostgreSQL/17/data"
PG_BIN="/Library/PostgreSQL/17/bin"
PG_HBA_CONF="$PG_DATA_DIR/pg_hba.conf"

# Step 1: Backup current pg_hba.conf
echo "Step 1: Backing up pg_hba.conf..."
sudo cp "$PG_HBA_CONF" "$PG_HBA_CONF.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ Backup created"

# Step 2: Update pg_hba.conf to use trust authentication
echo ""
echo "Step 2: Enabling trust authentication temporarily..."
sudo tee "$PG_HBA_CONF" > /dev/null << 'EOF'
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
echo "✅ pg_hba.conf updated"

# Step 3: Reload PostgreSQL configuration
echo ""
echo "Step 3: Reloading PostgreSQL configuration..."
sudo -u postgres "$PG_BIN/pg_ctl" reload -D "$PG_DATA_DIR"
sleep 2
echo "✅ Configuration reloaded"

# Step 4: Create user and set password
echo ""
echo "Step 4: Creating/updating user 'sirasasitorn'..."
psql -U postgres postgres -c "CREATE USER sirasasitorn WITH PASSWORD '$NEW_PASSWORD' CREATEDB SUPERUSER;" 2>/dev/null || \
psql -U postgres postgres -c "ALTER USER sirasasitorn WITH PASSWORD '$NEW_PASSWORD' CREATEDB SUPERUSER;"
echo "✅ User created/updated successfully"

# Step 5: Create turfmapp_dev database if it doesn't exist
echo ""
echo "Step 5: Creating database 'turfmapp_dev'..."
psql -U postgres postgres -c "CREATE DATABASE turfmapp_dev OWNER sirasasitorn;" 2>/dev/null || echo "Database already exists (skipping)"
psql -U postgres postgres -c "GRANT ALL PRIVILEGES ON DATABASE turfmapp_dev TO sirasasitorn;" 2>/dev/null
echo "✅ Database ready"

# Step 6: Restore pg_hba.conf to use password authentication
echo ""
echo "Step 6: Restoring password authentication..."
sudo tee "$PG_HBA_CONF" > /dev/null << 'EOF'
# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     md5
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
# Allow replication connections from localhost
local   replication     all                                     md5
host    replication     all             127.0.0.1/32            md5
host    replication     all             ::1/128                 md5
EOF
echo "✅ pg_hba.conf restored"

# Step 7: Reload PostgreSQL configuration again
echo ""
echo "Step 7: Reloading PostgreSQL with password authentication..."
sudo -u postgres "$PG_BIN/pg_ctl" reload -D "$PG_DATA_DIR"
sleep 2
echo "✅ Configuration reloaded"

# Step 8: Test connection
echo ""
echo "Step 8: Testing connection..."
PGPASSWORD="$NEW_PASSWORD" psql -U sirasasitorn -d turfmapp_dev -c "SELECT version();" | head -3
echo "✅ Connection test successful"

echo ""
echo "🎉 Password reset complete!"
echo ""
echo "Database Details:"
echo "  User: sirasasitorn"
echo "  Password: $NEW_PASSWORD"
echo "  Database: turfmapp_dev"
echo "  Connection String: postgresql://sirasasitorn:$NEW_PASSWORD@localhost:5432/turfmapp_dev"
echo ""
echo "Test with:"
echo "  PGPASSWORD='$NEW_PASSWORD' psql -U sirasasitorn -d turfmapp_dev"
echo ""
