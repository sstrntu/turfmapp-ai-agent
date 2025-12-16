"""
Rate Limiting Configuration

This module configures the rate limiter using slowapi.
It provides a central Limiter instance that can be used to decorate endpoints.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter with remote address as the key
# In production, you might want to use user ID if available, but remote address is a good default
limiter = Limiter(key_func=get_remote_address)
