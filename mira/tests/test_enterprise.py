"""Unit tests for enterprise features."""
import unittest
from datetime import datetime, timedelta
from mira.core.enterprise import (
    EnterpriseFeatures, SubscriptionTier, Feature, UsageMetrics,
    AuditLog, get_enterprise_features, TIER_FEATURES, TIER_LIMITS
)


class TestSubscriptionTiers(unittest.TestCase):
    """Test subscription tier definitions."""
    
    def test_tier_enum(self):
        """Test subscription tier enum."""
        self.assertEqual(SubscriptionTier.BASIC.value, "basic")
        self.assertEqual(SubscriptionTier.PROFESSIONAL.value, "professional")
        self.assertEqual(SubscriptionTier.ENTERPRISE.value, "enterprise")
    
    def test_tier_features_coverage(self):
        """Test that all tiers have feature definitions."""
        for tier in SubscriptionTier:
            self.assertIn(tier, TIER_FEATURES)
            self.assertGreater(len(TIER_FEATURES[tier]), 0)
    
    def test_tier_limits_coverage(self):
        """Test that all tiers have limit definitions."""
        for tier in SubscriptionTier:
            self.assertIn(tier, TIER_LIMITS)
            self.assertGreater(len(TIER_LIMITS[tier]), 0)
    
    def test_basic_tier_features(self):
        """Test basic tier has core features."""
        basic_features = TIER_FEATURES[SubscriptionTier.BASIC]
        self.assertIn(Feature.BASIC_WORKFLOWS, basic_features)
        self.assertIn(Feature.WEBHOOK_SUPPORT, basic_features)
    
    def test_professional_tier_includes_basic(self):
        """Test professional tier includes basic features."""
        pro_features = TIER_FEATURES[SubscriptionTier.PROFESSIONAL]
        self.assertIn(Feature.BASIC_WORKFLOWS, pro_features)
        self.assertIn(Feature.N8N_INTEGRATION, pro_features)
    
    def test_enterprise_tier_has_all_features(self):
        """Test enterprise tier has all features."""
        ent_features = TIER_FEATURES[SubscriptionTier.ENTERPRISE]
        all_features = list(Feature)
        self.assertEqual(len(ent_features), len(all_features))


class TestUsageMetrics(unittest.TestCase):
    """Test usage metrics tracking."""
    
    def test_metrics_initialization(self):
        """Test metrics initialization."""
        metrics = UsageMetrics("tenant_123")
        self.assertEqual(metrics.tenant_id, "tenant_123")
        self.assertEqual(metrics.metrics['webhooks_received'], 0)
    
    def test_record_event(self):
        """Test recording events."""
        metrics = UsageMetrics("tenant_123")
        metrics.record_event('webhooks_received', 5)
        self.assertEqual(metrics.metrics['webhooks_received'], 5)
        
        metrics.record_event('webhooks_received', 3)
        self.assertEqual(metrics.metrics['webhooks_received'], 8)
    
    def test_daily_metrics(self):
        """Test daily metrics tracking."""
        metrics = UsageMetrics("tenant_123")
        metrics.record_event('api_calls', 10)
        
        today = datetime.utcnow().date().isoformat()
        daily = metrics.get_daily_usage(today)
        self.assertEqual(daily['api_calls'], 10)
    
    def test_total_usage(self):
        """Test total usage retrieval."""
        metrics = UsageMetrics("tenant_123")
        metrics.record_event('projects_created', 5)
        metrics.record_event('users_created', 3)
        
        total = metrics.get_total_usage()
        self.assertEqual(total['projects_created'], 5)
        self.assertEqual(total['users_created'], 3)


class TestAuditLog(unittest.TestCase):
    """Test audit logging."""
    
    def test_log_event(self):
        """Test logging an event."""
        audit = AuditLog()
        audit.log_event(
            'tenant_123', 'user_456', 'create',
            'project', 'proj_789',
            {'name': 'Test Project'}
        )
        
        logs = audit.get_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]['action'], 'create')
        self.assertEqual(logs[0]['tenant_id'], 'tenant_123')
    
    def test_filter_by_tenant(self):
        """Test filtering logs by tenant."""
        audit = AuditLog()
        audit.log_event('tenant_1', 'user_1', 'create', 'project', 'p1')
        audit.log_event('tenant_2', 'user_2', 'delete', 'project', 'p2')
        audit.log_event('tenant_1', 'user_3', 'update', 'project', 'p3')
        
        tenant1_logs = audit.get_logs(tenant_id='tenant_1')
        self.assertEqual(len(tenant1_logs), 2)
    
    def test_filter_by_user(self):
        """Test filtering logs by user."""
        audit = AuditLog()
        audit.log_event('tenant_1', 'user_1', 'create', 'project', 'p1')
        audit.log_event('tenant_1', 'user_2', 'delete', 'project', 'p2')
        audit.log_event('tenant_1', 'user_1', 'update', 'project', 'p3')
        
        user1_logs = audit.get_logs(user_id='user_1')
        self.assertEqual(len(user1_logs), 2)
    
    def test_limit_logs(self):
        """Test limiting number of logs returned."""
        audit = AuditLog()
        for i in range(20):
            audit.log_event(f'tenant_{i}', f'user_{i}', 'create', 'project', f'p{i}')
        
        limited_logs = audit.get_logs(limit=10)
        self.assertEqual(len(limited_logs), 10)


class TestEnterpriseFeatures(unittest.TestCase):
    """Test enterprise features management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.features = EnterpriseFeatures()
    
    def test_get_tier(self):
        """Test getting tier from string."""
        tier = self.features.get_tier("basic")
        self.assertEqual(tier, SubscriptionTier.BASIC)
        
        tier = self.features.get_tier("invalid")
        self.assertIsNone(tier)
    
    def test_has_feature(self):
        """Test checking feature availability."""
        # Basic tier has basic workflows
        self.assertTrue(self.features.has_feature(
            "basic", Feature.BASIC_WORKFLOWS
        ))
        
        # Basic tier doesn't have n8n integration
        self.assertFalse(self.features.has_feature(
            "basic", Feature.N8N_INTEGRATION
        ))
        
        # Enterprise tier has all features
        self.assertTrue(self.features.has_feature(
            "enterprise", Feature.AUDIT_LOGGING
        ))
    
    def test_get_tier_features(self):
        """Test getting all features for a tier."""
        features = self.features.get_tier_features("professional")
        self.assertIn(Feature.N8N_INTEGRATION, features)
        self.assertIn(Feature.ANALYTICS_DASHBOARD, features)
    
    def test_check_limit_within_bounds(self):
        """Test checking limits within bounds."""
        # Basic tier: max 5 users
        self.assertTrue(self.features.check_limit("basic", "max_users", 3))
    
    def test_check_limit_exceeds(self):
        """Test checking limits that exceed."""
        # Basic tier: max 5 users
        self.assertFalse(self.features.check_limit("basic", "max_users", 10))
    
    def test_check_limit_unlimited(self):
        """Test unlimited tier limits."""
        # Enterprise has unlimited users (-1)
        self.assertTrue(self.features.check_limit("enterprise", "max_users", 1000))
    
    def test_get_tier_limits(self):
        """Test getting tier limits."""
        limits = self.features.get_tier_limits("basic")
        self.assertEqual(limits['max_users'], 5)
        self.assertEqual(limits['max_projects'], 10)
        self.assertEqual(limits['max_webhooks_per_day'], 1000)
    
    def test_record_usage(self):
        """Test recording usage."""
        self.features.record_usage('tenant_123', 'webhooks_received', 5)
        
        metrics = self.features.get_usage_metrics('tenant_123')
        self.assertEqual(metrics.metrics['webhooks_received'], 5)
    
    def test_log_audit_event(self):
        """Test logging audit event."""
        self.features.log_audit_event(
            'tenant_123', 'user_456', 'create',
            'project', 'proj_789'
        )
        
        logs = self.features.audit_log.get_logs(tenant_id='tenant_123')
        self.assertEqual(len(logs), 1)
    
    def test_get_analytics(self):
        """Test getting analytics."""
        self.features.record_usage('tenant_123', 'projects_created', 3)
        self.features.record_usage('tenant_123', 'users_created', 5)
        
        analytics = self.features.get_analytics('tenant_123')
        self.assertEqual(analytics['tenant_id'], 'tenant_123')
        self.assertIn('total_usage', analytics)
        self.assertEqual(analytics['total_usage']['projects_created'], 3)


class TestRevenueTierScenarios(unittest.TestCase):
    """Test scenarios aligned with revenue tiers."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.features = EnterpriseFeatures()
    
    def test_50k_basic_tier_limits(self):
        """Test $50k basic tier has appropriate limits."""
        limits = self.features.get_tier_limits("basic")
        
        # Basic tier: small team limits
        self.assertEqual(limits['max_users'], 5)
        self.assertEqual(limits['max_projects'], 10)
        self.assertEqual(limits['max_webhooks_per_day'], 1000)
    
    def test_500k_professional_tier_limits(self):
        """Test $500k professional tier has appropriate limits."""
        limits = self.features.get_tier_limits("professional")
        
        # Professional tier: medium team limits
        self.assertEqual(limits['max_users'], 50)
        self.assertEqual(limits['max_projects'], 100)
        self.assertEqual(limits['max_webhooks_per_day'], 10000)
    
    def test_5m_enterprise_tier_unlimited(self):
        """Test $5M enterprise tier has unlimited resources."""
        limits = self.features.get_tier_limits("enterprise")
        
        # Enterprise tier: unlimited
        self.assertEqual(limits['max_users'], -1)
        self.assertEqual(limits['max_projects'], -1)
        self.assertEqual(limits['max_webhooks_per_day'], -1)
    
    def test_n8n_webhook_professional_feature(self):
        """Test n8n webhooks available in professional tier."""
        # n8n integration for professional and enterprise
        self.assertFalse(self.features.has_feature(
            "basic", Feature.N8N_INTEGRATION
        ))
        self.assertTrue(self.features.has_feature(
            "professional", Feature.N8N_INTEGRATION
        ))
        self.assertTrue(self.features.has_feature(
            "enterprise", Feature.N8N_INTEGRATION
        ))
    
    def test_10k_daily_webhooks_professional(self):
        """Test professional tier supports 10k daily webhooks."""
        limits = self.features.get_tier_limits("professional")
        self.assertEqual(limits['max_webhooks_per_day'], 10000)
        
        # Simulate 9999 webhooks - should be within limit
        self.assertTrue(self.features.check_limit(
            "professional", "max_webhooks_per_day", 9999
        ))
    
    def test_enterprise_audit_logging(self):
        """Test enterprise tier has audit logging."""
        self.assertFalse(self.features.has_feature(
            "basic", Feature.AUDIT_LOGGING
        ))
        self.assertFalse(self.features.has_feature(
            "professional", Feature.AUDIT_LOGGING
        ))
        self.assertTrue(self.features.has_feature(
            "enterprise", Feature.AUDIT_LOGGING
        ))
    
    def test_usage_tracking_all_tiers(self):
        """Test usage tracking works for all tiers."""
        # Simulate usage for different tiers
        for tier_name in ["basic", "professional", "enterprise"]:
            tenant_id = f"tenant_{tier_name}"
            self.features.record_usage(tenant_id, 'webhooks_received', 100)
            
            metrics = self.features.get_usage_metrics(tenant_id)
            self.assertEqual(metrics.metrics['webhooks_received'], 100)


if __name__ == '__main__':
    unittest.main()
