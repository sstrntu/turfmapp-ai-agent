#!/bin/bash
# Restart PostgreSQL 17 to load pgvector extension

echo "🔄 Restarting PostgreSQL 17..."
sudo -u postgres /Library/PostgreSQL/17/bin/pg_ctl restart -D /Library/PostgreSQL/17/data

echo ""
echo "Waiting for PostgreSQL to start..."
sleep 3

echo ""
echo "✅ PostgreSQL restarted"
echo ""

# Now try to enable the extension
echo "Enabling vector extension..."
PGPASSWORD='Z3c2et-2025' psql -U sirasasitorn -d turfmapp_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "Verifying extension..."
PGPASSWORD='Z3c2et-2025' psql -U sirasasitorn -d turfmapp_dev -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

echo ""
echo "🎉 Done!"
