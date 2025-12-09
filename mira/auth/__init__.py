"""
Authentication module for Mira platform.

Provides authenticated webhook handling with async support, Redis caching,
and structured logging.
"""
from mira.auth.authenticated_webhook_handler import AuthenticatedWebhookHandler

# Export main classes
__all__ = [
    'AuthenticatedWebhookHandler',
]

# Backwards compatibility - WebhookHandler alias
WebhookHandler = AuthenticatedWebhookHandler

__version__ = '1.0.0'
