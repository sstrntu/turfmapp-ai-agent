#!/bin/bash
# Install pgvector extension for PostgreSQL 17

set -e

echo "🔧 Installing pgvector extension for PostgreSQL 17..."
echo ""

# Symlink extension files
echo "Creating symlinks for pgvector extension files..."
sudo ln -sf /opt/homebrew/Cellar/pgvector/0.8.1/share/postgresql@17/extension/* /Library/PostgreSQL/17/share/postgresql/extension/

# Symlink library files
echo "Creating symlinks for pgvector library files..."
sudo ln -sf /opt/homebrew/Cellar/pgvector/0.8.1/lib/postgresql@17/vector.dylib /Library/PostgreSQL/17/lib/postgresql/vector.dylib

echo ""
echo "✅ pgvector symlinks created"
echo ""

# Enable the extension in the database
echo "Enabling vector extension in turfmapp_dev database..."
PGPASSWORD='Z3c2et-2025' psql -U sirasasitorn -d turfmapp_dev -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo ""
echo "🎉 pgvector installation complete!"
echo ""
echo "Verify with:"
echo "  PGPASSWORD='Z3c2et-2025' psql -U sirasasitorn -d turfmapp_dev -c \"SELECT * FROM pg_extension WHERE extname = 'vector';\""
echo ""
