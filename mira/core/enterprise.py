"""Revenue-aligned enterprise features for Mira platform."""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import logging


class SubscriptionTier(Enum):
    """Subscription tiers aligned with revenue goals."""
    BASIC = "basic"              # $50k annual revenue
    PROFESSIONAL = "professional"  # $500k annual revenue
    ENTERPRISE = "enterprise"      # $5M annual revenue


class Feature(Enum):
    """Feature flags for different subscription tiers."""
    # Basic features (all tiers)
    BASIC_WORKFLOWS = "basic_workflows"
    BASIC_INTEGRATIONS = "basic_integrations"
    WEBHOOK_SUPPORT = "webhook_support"
    STANDARD_AGENTS = "standard_agents"
    
    # Professional features ($500k tier)
    ADVANCED_WORKFLOWS = "advanced_workflows"
    CUSTOM_INTEGRATIONS = "custom_integrations"
    N8N_INTEGRATION = "n8n_integration"
    PRIORITY_SUPPORT = "priority_support"
    ANALYTICS_DASHBOARD = "analytics_dashboard"
    
    # Enterprise features ($5M tier)
    MULTI_TENANT_RBAC = "multi_tenant_rbac"
    CUSTOM_AGENTS = "custom_agents"
    ENTERPRISE_INTEGRATIONS = "enterprise_integrations"
    DEDICATED_SUPPORT = "dedicated_support"
    ADVANCED_ANALYTICS = "advanced_analytics"
    AUDIT_LOGGING = "audit_logging"
    SLA_GUARANTEE = "sla_guarantee"
    WHITE_LABEL = "white_label"


# Feature availability by tier
TIER_FEATURES = {
    SubscriptionTier.BASIC: [
        Feature.BASIC_WORKFLOWS,
        Feature.BASIC_INTEGRATIONS,
        Feature.WEBHOOK_SUPPORT,
        Feature.STANDARD_AGENTS,
    ],
    SubscriptionTier.PROFESSIONAL: [
        # All basic features
        Feature.BASIC_WORKFLOWS,
        Feature.BASIC_INTEGRATIONS,
        Feature.WEBHOOK_SUPPORT,
        Feature.STANDARD_AGENTS,
        # Plus professional features
        Feature.ADVANCED_WORKFLOWS,
        Feature.CUSTOM_INTEGRATIONS,
        Feature.N8N_INTEGRATION,
        Feature.PRIORITY_SUPPORT,
        Feature.ANALYTICS_DASHBOARD,
    ],
    SubscriptionTier.ENTERPRISE: [
        # All features
        f for f in Feature
    ],
}


# Usage limits by tier
TIER_LIMITS = {
    SubscriptionTier.BASIC: {
        'max_users': 5,
        'max_projects': 10,
        'max_webhooks_per_day': 1000,
        'max_integrations': 3,
        'max_workflows_per_month': 100,
    },
    SubscriptionTier.PROFESSIONAL: {
        'max_users': 50,
        'max_projects': 100,
        'max_webhooks_per_day': 10000,
        'max_integrations': 10,
        'max_workflows_per_month': 1000,
    },
    SubscriptionTier.ENTERPRISE: {
        'max_users': -1,  # Unlimited
        'max_projects': -1,
        'max_webhooks_per_day': -1,
        'max_integrations': -1,
        'max_workflows_per_month': -1,
    },
}


class UsageMetrics:
    """Track usage metrics for a tenant."""
    
    def __init__(self, tenant_id: str):
        """
        Initialize usage metrics.
        
        Args:
            tenant_id: Tenant ID
        """
        self.tenant_id = tenant_id
        self.metrics: Dict[str, Any] = {
            'users_created': 0,
            'projects_created': 0,
            'webhooks_received': 0,
            'workflows_executed': 0,
            'integrations_active': 0,
            'api_calls': 0,
        }
        self.daily_metrics: Dict[str, Dict[str, int]] = {}
        self.monthly_metrics: Dict[str, Dict[str, int]] = {}
    
    def record_event(self, event_type: str, count: int = 1):
        """
        Record a usage event.
        
        Args:
            event_type: Type of event
            count: Number of events
        """
        if event_type in self.metrics:
            self.metrics[event_type] += count
        
        # Track daily metrics
        today = datetime.utcnow().date().isoformat()
        if today not in self.daily_metrics:
            self.daily_metrics[today] = {}
        if event_type not in self.daily_metrics[today]:
            self.daily_metrics[today][event_type] = 0
        self.daily_metrics[today][event_type] += count
    
    def get_daily_usage(self, date: str = None) -> Dict[str, int]:
        """
        Get usage for a specific day.
        
        Args:
            date: Date in ISO format (defaults to today)
            
        Returns:
            Usage metrics for the day
        """
        if date is None:
            date = datetime.utcnow().date().isoformat()
        return self.daily_metrics.get(date, {})
    
    def get_total_usage(self) -> Dict[str, Any]:
        """Get total usage metrics."""
        return self.metrics.copy()


class AuditLog:
    """Enterprise audit logging."""
    
    def __init__(self):
        """Initialize audit log."""
        self.logs: List[Dict[str, Any]] = []
    
    def log_event(self, tenant_id: str, user_id: str, action: str,
                  resource_type: str, resource_id: str, 
                  details: Dict[str, Any] = None):
        """
        Log an audit event.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'tenant_id': tenant_id,
            'user_id': user_id,
            'action': action,
            'resource_type': resource_type,
            'resource_id': resource_id,
            'details': details or {}
        }
        self.logs.append(event)
    
    def get_logs(self, tenant_id: str = None, user_id: str = None,
                 since: datetime = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get audit logs with optional filters.
        
        Args:
            tenant_id: Filter by tenant
            user_id: Filter by user
            since: Filter by timestamp
            limit: Maximum number of logs
            
        Returns:
            List of audit log entries
        """
        filtered = self.logs
        
        if tenant_id:
            filtered = [log for log in filtered if log['tenant_id'] == tenant_id]
        if user_id:
            filtered = [log for log in filtered if log['user_id'] == user_id]
        if since:
            since_iso = since.isoformat()
            filtered = [log for log in filtered if log['timestamp'] >= since_iso]
        
        return filtered[-limit:]


class EnterpriseFeatures:
    """Manage enterprise features and usage tracking."""
    
    def __init__(self):
        """Initialize enterprise features."""
        self.usage_by_tenant: Dict[str, UsageMetrics] = {}
        self.audit_log = AuditLog()
        self.logger = logging.getLogger("mira.enterprise")
    
    def get_tier(self, tier_name: str) -> Optional[SubscriptionTier]:
        """
        Get subscription tier enum from string.
        
        Args:
            tier_name: Tier name
            
        Returns:
            SubscriptionTier or None
        """
        try:
            return SubscriptionTier(tier_name)
        except ValueError:
            return None
    
    def has_feature(self, tier_name: str, feature: Feature) -> bool:
        """
        Check if a tier has a specific feature.
        
        Args:
            tier_name: Tier name
            feature: Feature to check
            
        Returns:
            True if tier has the feature
        """
        tier = self.get_tier(tier_name)
        if not tier:
            return False
        return feature in TIER_FEATURES.get(tier, [])
    
    def get_tier_features(self, tier_name: str) -> List[Feature]:
        """
        Get all features for a tier.
        
        Args:
            tier_name: Tier name
            
        Returns:
            List of features
        """
        tier = self.get_tier(tier_name)
        if not tier:
            return []
        return TIER_FEATURES.get(tier, [])
    
    def check_limit(self, tier_name: str, limit_type: str, 
                   current_value: int) -> bool:
        """
        Check if current usage is within tier limits.
        
        Args:
            tier_name: Tier name
            limit_type: Type of limit to check
            current_value: Current usage value
            
        Returns:
            True if within limits
        """
        tier = self.get_tier(tier_name)
        if not tier:
            return False
        
        limits = TIER_LIMITS.get(tier, {})
        max_value = limits.get(limit_type, 0)
        
        # -1 means unlimited
        if max_value == -1:
            return True
        
        return current_value < max_value
    
    def get_tier_limits(self, tier_name: str) -> Dict[str, int]:
        """
        Get all limits for a tier.
        
        Args:
            tier_name: Tier name
            
        Returns:
            Dictionary of limits
        """
        tier = self.get_tier(tier_name)
        if not tier:
            return {}
        return TIER_LIMITS.get(tier, {})
    
    def get_usage_metrics(self, tenant_id: str) -> UsageMetrics:
        """
        Get usage metrics for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            UsageMetrics instance
        """
        if tenant_id not in self.usage_by_tenant:
            self.usage_by_tenant[tenant_id] = UsageMetrics(tenant_id)
        return self.usage_by_tenant[tenant_id]
    
    def record_usage(self, tenant_id: str, event_type: str, count: int = 1):
        """
        Record usage event for a tenant.
        
        Args:
            tenant_id: Tenant ID
            event_type: Type of event
            count: Number of events
        """
        metrics = self.get_usage_metrics(tenant_id)
        metrics.record_event(event_type, count)
        self.logger.info(f"Recorded {count} {event_type} for tenant {tenant_id}")
    
    def log_audit_event(self, tenant_id: str, user_id: str, action: str,
                       resource_type: str, resource_id: str,
                       details: Dict[str, Any] = None):
        """
        Log an audit event.
        
        Args:
            tenant_id: Tenant ID
            user_id: User ID
            action: Action performed
            resource_type: Type of resource
            resource_id: Resource ID
            details: Additional details
        """
        self.audit_log.log_event(
            tenant_id, user_id, action, resource_type, 
            resource_id, details
        )
        self.logger.info(f"Audit: {action} on {resource_type} by user {user_id}")
    
    def get_analytics(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get analytics dashboard data for a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            Analytics data
        """
        metrics = self.get_usage_metrics(tenant_id)
        total_usage = metrics.get_total_usage()
        today_usage = metrics.get_daily_usage()
        
        return {
            'tenant_id': tenant_id,
            'total_usage': total_usage,
            'today_usage': today_usage,
            'recent_activity': len(today_usage) > 0
        }


# Global enterprise features instance
_enterprise_features = EnterpriseFeatures()


def get_enterprise_features() -> EnterpriseFeatures:
    """Get the global enterprise features instance."""
    return _enterprise_features
