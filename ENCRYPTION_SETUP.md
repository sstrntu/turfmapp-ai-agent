# Encryption Setup for Google OAuth Tokens

## Overview

Google OAuth tokens (access_token and refresh_token) are now encrypted before being stored in the database for enhanced security.

## Security Benefits

- **Data at Rest Protection**: Tokens are encrypted in the database
- **Key Separation**: Encryption keys are stored separately from data
- **Zero-Knowledge Architecture**: Even database admins cannot read tokens without encryption keys

## Setup Instructions

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Generate Encryption Key

**For Production:**
```bash
cd backend
python -c "from app.services.encryption import generate_encryption_key; print(f'ENCRYPTION_KEY={generate_encryption_key()}')"
```

**For Development:**
The system will auto-generate a temporary key if none is provided (not recommended for production).

### 3. Set Environment Variable

**Production (.env or environment):**
```bash
# Add to your .env file or environment variables
ENCRYPTION_KEY=your_generated_key_here
```

**Development (.env.local):**
```bash
# The system will auto-generate for development
# ENCRYPTION_KEY=auto-generated-temporary-key
```

### 4. Run Database Migration

```sql
-- Apply the migration to add encrypted columns
-- Run: /database/migrations/create_google_accounts_tables.sql
```

## Database Schema

### Encrypted Columns:
- `google_tokens.access_token_encrypted` (TEXT) - Encrypted access token
- `google_tokens.refresh_token_encrypted` (TEXT) - Encrypted refresh token

### Legacy Columns (for migration):
- `google_tokens.access_token` (TEXT) - Plaintext (can be removed after migration)
- `google_tokens.refresh_token` (TEXT) - Plaintext (can be removed after migration)

## Migration Strategy

The system supports both encrypted and plaintext tokens during migration:

1. **New tokens**: Automatically encrypted and stored in `*_encrypted` columns
2. **Existing tokens**: Read from plaintext columns with a warning
3. **Re-authentication**: Users can re-authenticate to convert to encrypted storage

## Security Best Practices

### Production Environment:
1. **Unique Keys**: Generate unique encryption keys for each environment
2. **Key Rotation**: Regularly rotate encryption keys (requires data migration)
3. **Key Storage**: Store keys in secure key management services (AWS KMS, Azure Key Vault)
4. **Access Control**: Limit access to encryption keys
5. **Monitoring**: Monitor encryption/decryption failures

### Key Management:
```bash
# Environment-specific keys
ENCRYPTION_KEY_DEV=dev_key_here
ENCRYPTION_KEY_STAGING=staging_key_here  
ENCRYPTION_KEY_PROD=prod_key_here
```

## Troubleshooting

### Common Issues:

1. **"Failed to decrypt access token"**
   - Check if ENCRYPTION_KEY is set correctly
   - Ensure key hasn't changed since tokens were encrypted
   - User may need to re-authenticate

2. **"Encryption initialization failed"**
   - Verify cryptography package is installed
   - Check ENCRYPTION_KEY format (should be 44 characters ending with '=')

3. **"No valid access token found"**
   - Account may have invalid tokens
   - User should disconnect and reconnect Google account

### Recovery:

If encryption keys are lost:
1. **Data Loss**: Encrypted tokens cannot be recovered
2. **User Action**: Users must re-authenticate their Google accounts
3. **Clean Slate**: Clear all encrypted tokens and start fresh

```sql
-- Emergency: Clear all encrypted tokens (users must re-authenticate)
UPDATE google_tokens SET access_token_encrypted = NULL, refresh_token_encrypted = NULL;
```

## Monitoring & Maintenance

### Log Monitoring:
- Watch for decryption failures
- Monitor encryption service initialization
- Track token refresh patterns

### Regular Maintenance:
- Clean up expired tokens
- Rotate encryption keys annually
- Audit encryption key access

## Implementation Details

### Encryption Algorithm:
- **Algorithm**: AES-256 (via Fernet)
- **Key Derivation**: PBKDF2 with SHA-256
- **Encoding**: Base64 for database storage
- **Salt**: Environment-specific (change in production)

### Code Structure:
- `services/encryption.py` - Encryption service
- `services/google_db.py` - Database operations with encryption
- `database/migrations/create_google_accounts_tables.sql` - Schema with encrypted columns

## Security Considerations

### What's Protected:
✅ **Google OAuth tokens** (access_token, refresh_token)  
✅ **Database storage** (encrypted at rest)  
✅ **Memory** (tokens decrypted only when needed)  

### What's NOT Protected:
❌ **Application memory** (tokens briefly in plaintext during use)  
❌ **Network traffic** (use HTTPS/TLS)  
❌ **Client-side storage** (frontend should not store tokens)  

### Risk Mitigation:
- **Short token lifespans** - Access tokens expire quickly
- **Token refresh** - Automatic refresh reduces exposure time
- **Secure transport** - Always use HTTPS
- **Minimal exposure** - Tokens only decrypted when needed

## Production Checklist

- [ ] Generated unique encryption key for production
- [ ] Set ENCRYPTION_KEY environment variable
- [ ] Tested encryption/decryption functionality  
- [ ] Applied database migration
- [ ] Verified existing tokens work with fallback
- [ ] Documented key backup/recovery process
- [ ] Set up monitoring for encryption failures
- [ ] Planned key rotation schedule