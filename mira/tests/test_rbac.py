"""Unit tests for multi-tenant RBAC system."""
import unittest
from mira.core.rbac import (
    RBACManager, Role, Permission, Tenant, User, get_rbac_manager
)


class TestTenant(unittest.TestCase):
    """Test tenant functionality."""
    
    def test_tenant_creation(self):
        """Test creating a tenant."""
        tenant = Tenant("Acme Corp", "enterprise")
        self.assertEqual(tenant.name, "Acme Corp")
        self.assertEqual(tenant.tier, "enterprise")
        self.assertTrue(tenant.active)
        self.assertEqual(len(tenant.users), 0)
    
    def test_tenant_to_dict(self):
        """Test tenant serialization."""
        tenant = Tenant("Test Corp", "professional")
        data = tenant.to_dict()
        self.assertEqual(data['name'], "Test Corp")
        self.assertEqual(data['tier'], "professional")
        self.assertIn('id', data)
        self.assertIn('created_at', data)


class TestUser(unittest.TestCase):
    """Test user functionality."""
    
    def test_user_creation(self):
        """Test creating a user."""
        user = User("john", "john@example.com", "tenant_123", Role.USER)
        self.assertEqual(user.username, "john")
        self.assertEqual(user.email, "john@example.com")
        self.assertEqual(user.tenant_id, "tenant_123")
        self.assertEqual(user.role, Role.USER)
        self.assertIsNotNone(user.api_key)
    
    def test_password_operations(self):
        """Test password setting and verification."""
        user = User("jane", "jane@example.com", "tenant_123")
        user.set_password("secret123")
        
        self.assertTrue(user.verify_password("secret123"))
        self.assertFalse(user.verify_password("wrong"))
    
    def test_permission_check(self):
        """Test permission checking."""
        admin = User("admin", "admin@example.com", "t1", Role.ADMIN)
        manager = User("manager", "manager@example.com", "t1", Role.MANAGER)
        user = User("user", "user@example.com", "t1", Role.USER)
        viewer = User("viewer", "viewer@example.com", "t1", Role.VIEWER)
        
        # Admin has all permissions
        self.assertTrue(admin.has_permission(Permission.TENANT_DELETE))
        
        # Manager has project permissions
        self.assertTrue(manager.has_permission(Permission.PROJECT_CREATE))
        self.assertTrue(manager.has_permission(Permission.PROJECT_DELETE))
        
        # User has limited permissions
        self.assertTrue(user.has_permission(Permission.PROJECT_READ))
        self.assertFalse(user.has_permission(Permission.PROJECT_DELETE))
        
        # Viewer is read-only
        self.assertTrue(viewer.has_permission(Permission.PROJECT_READ))
        self.assertFalse(viewer.has_permission(Permission.PROJECT_UPDATE))


class TestRBACManager(unittest.TestCase):
    """Test RBAC manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rbac = RBACManager()
    
    def test_create_tenant(self):
        """Test creating a tenant."""
        tenant = self.rbac.create_tenant("Test Corp", "professional")
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.name, "Test Corp")
        self.assertEqual(tenant.tier, "professional")
        
        # Verify it's stored
        retrieved = self.rbac.get_tenant(tenant.id)
        self.assertEqual(retrieved.id, tenant.id)
    
    def test_list_tenants(self):
        """Test listing tenants."""
        self.rbac.create_tenant("Tenant 1", "basic")
        self.rbac.create_tenant("Tenant 2", "enterprise")
        
        tenants = self.rbac.list_tenants()
        self.assertEqual(len(tenants), 2)
    
    def test_delete_tenant(self):
        """Test deleting a tenant."""
        tenant = self.rbac.create_tenant("Temp Corp", "basic")
        tenant_id = tenant.id
        
        # Create user in tenant
        self.rbac.create_user("user1", "user1@example.com", tenant_id)
        
        # Delete tenant
        self.assertTrue(self.rbac.delete_tenant(tenant_id))
        self.assertIsNone(self.rbac.get_tenant(tenant_id))
        
        # Users should also be deleted
        self.assertIsNone(self.rbac.get_user_by_username("user1"))
    
    def test_create_user(self):
        """Test creating a user."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user = self.rbac.create_user(
            "john", "john@example.com", tenant.id, 
            Role.USER, "password123"
        )
        
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "john")
        self.assertTrue(user.verify_password("password123"))
        
        # User should be in tenant
        self.assertIn(user.id, tenant.users)
    
    def test_create_user_invalid_tenant(self):
        """Test creating user with invalid tenant."""
        user = self.rbac.create_user(
            "invalid", "invalid@example.com", "nonexistent_tenant"
        )
        self.assertIsNone(user)
    
    def test_create_duplicate_username(self):
        """Test creating user with duplicate username."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user1 = self.rbac.create_user("john", "john1@example.com", tenant.id)
        user2 = self.rbac.create_user("john", "john2@example.com", tenant.id)
        
        self.assertIsNotNone(user1)
        self.assertIsNone(user2)
    
    def test_get_user_by_username(self):
        """Test retrieving user by username."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user = self.rbac.create_user("jane", "jane@example.com", tenant.id)
        
        retrieved = self.rbac.get_user_by_username("jane")
        self.assertEqual(retrieved.id, user.id)
    
    def test_get_user_by_api_key(self):
        """Test retrieving user by API key."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user = self.rbac.create_user("bob", "bob@example.com", tenant.id)
        
        retrieved = self.rbac.get_user_by_api_key(user.api_key)
        self.assertEqual(retrieved.id, user.id)
    
    def test_authenticate_user(self):
        """Test user authentication with password."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user = self.rbac.create_user(
            "alice", "alice@example.com", tenant.id,
            password="secure123"
        )
        
        # Valid credentials
        authenticated = self.rbac.authenticate_user("alice", "secure123")
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.id, user.id)
        
        # Invalid credentials
        self.assertIsNone(self.rbac.authenticate_user("alice", "wrong"))
        self.assertIsNone(self.rbac.authenticate_user("nonexistent", "password"))
    
    def test_authenticate_api_key(self):
        """Test user authentication with API key."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user = self.rbac.create_user("charlie", "charlie@example.com", tenant.id)
        
        # Valid API key
        authenticated = self.rbac.authenticate_api_key(user.api_key)
        self.assertIsNotNone(authenticated)
        self.assertEqual(authenticated.id, user.id)
        
        # Invalid API key
        self.assertIsNone(self.rbac.authenticate_api_key("invalid_key"))
    
    def test_check_permission_same_tenant(self):
        """Test permission checking within same tenant."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        admin = self.rbac.create_user(
            "admin", "admin@example.com", tenant.id, Role.ADMIN
        )
        user = self.rbac.create_user(
            "user", "user@example.com", tenant.id, Role.USER
        )
        
        # Admin has delete permission
        self.assertTrue(self.rbac.check_permission(
            admin.id, Permission.PROJECT_DELETE, tenant.id
        ))
        
        # User doesn't have delete permission
        self.assertFalse(self.rbac.check_permission(
            user.id, Permission.PROJECT_DELETE, tenant.id
        ))
    
    def test_check_permission_cross_tenant(self):
        """Test tenant isolation."""
        tenant1 = self.rbac.create_tenant("Tenant 1", "basic")
        tenant2 = self.rbac.create_tenant("Tenant 2", "basic")
        
        admin = self.rbac.create_user(
            "admin", "admin@example.com", tenant1.id, Role.ADMIN
        )
        manager = self.rbac.create_user(
            "manager", "manager@example.com", tenant1.id, Role.MANAGER
        )
        
        # Admin can access cross-tenant
        self.assertTrue(self.rbac.check_permission(
            admin.id, Permission.PROJECT_READ, tenant2.id
        ))
        
        # Manager cannot access cross-tenant
        self.assertFalse(self.rbac.check_permission(
            manager.id, Permission.PROJECT_READ, tenant2.id
        ))
    
    def test_delete_user(self):
        """Test deleting a user."""
        tenant = self.rbac.create_tenant("Test Corp", "basic")
        user = self.rbac.create_user("temp", "temp@example.com", tenant.id)
        user_id = user.id
        
        self.assertTrue(self.rbac.delete_user(user_id))
        self.assertIsNone(self.rbac.get_user(user_id))
        self.assertIsNone(self.rbac.get_user_by_username("temp"))
        
        # User should be removed from tenant
        self.assertNotIn(user_id, tenant.users)


class TestRolePermissions(unittest.TestCase):
    """Test role permission mappings."""
    
    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions."""
        from mira.core.rbac import ROLE_PERMISSIONS
        
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        all_perms = list(Permission)
        
        self.assertEqual(len(admin_perms), len(all_perms))
    
    def test_viewer_is_read_only(self):
        """Test that viewer role is read-only."""
        from mira.core.rbac import ROLE_PERMISSIONS
        
        viewer_perms = ROLE_PERMISSIONS[Role.VIEWER]
        
        # Should have read permissions
        self.assertIn(Permission.PROJECT_READ, viewer_perms)
        self.assertIn(Permission.TENANT_READ, viewer_perms)
        
        # Should not have write permissions
        self.assertNotIn(Permission.PROJECT_CREATE, viewer_perms)
        self.assertNotIn(Permission.PROJECT_DELETE, viewer_perms)


class TestMultiTenantScenarios(unittest.TestCase):
    """Test real-world multi-tenant scenarios."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rbac = RBACManager()
    
    def test_revenue_tier_scenario(self):
        """Test scenario aligned with $50k-$5M revenue tiers."""
        # Create tenants at different tiers
        basic_tenant = self.rbac.create_tenant("Startup Inc", "basic")  # $50k
        pro_tenant = self.rbac.create_tenant("Growth Co", "professional")  # $500k
        ent_tenant = self.rbac.create_tenant("Enterprise Corp", "enterprise")  # $5M
        
        # Create users with different roles
        basic_admin = self.rbac.create_user(
            "basic_admin", "admin@startup.com", basic_tenant.id, Role.MANAGER
        )
        pro_admin = self.rbac.create_user(
            "pro_admin", "admin@growth.com", pro_tenant.id, Role.MANAGER
        )
        ent_admin = self.rbac.create_user(
            "ent_admin", "admin@enterprise.com", ent_tenant.id, Role.ADMIN
        )
        
        # Verify tier information is stored
        self.assertEqual(basic_tenant.tier, "basic")
        self.assertEqual(pro_tenant.tier, "professional")
        self.assertEqual(ent_tenant.tier, "enterprise")
        
        # Enterprise admin can do more
        self.assertTrue(ent_admin.has_permission(Permission.TENANT_CREATE))
        self.assertFalse(pro_admin.has_permission(Permission.TENANT_CREATE))
    
    def test_n8n_webhook_with_rbac(self):
        """Test n8n webhook integration respects RBAC."""
        tenant = self.rbac.create_tenant("Webhook Corp", "professional")
        
        # User with webhook permission
        webhook_user = self.rbac.create_user(
            "webhook_user", "webhook@corp.com", tenant.id, Role.USER
        )
        
        # Viewer without webhook permission
        viewer = self.rbac.create_user(
            "viewer", "viewer@corp.com", tenant.id, Role.VIEWER
        )
        
        # Webhook user can receive webhooks
        self.assertTrue(webhook_user.has_permission(Permission.WEBHOOK_RECEIVE))
        
        # Viewer cannot configure webhooks
        self.assertFalse(viewer.has_permission(Permission.WEBHOOK_CONFIGURE))


if __name__ == '__main__':
    unittest.main()
