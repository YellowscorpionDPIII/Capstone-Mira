"""Multi-tenant RBAC (Role-Based Access Control) system."""
from typing import Dict, Any, List, Optional, Set
from enum import Enum
import uuid
import hashlib
import secrets
import logging
from datetime import datetime


class Role(Enum):
    """User roles in the system."""
    ADMIN = "admin"          # Full system access
    MANAGER = "manager"      # Tenant-level management
    USER = "user"           # Standard user access
    VIEWER = "viewer"       # Read-only access


class Permission(Enum):
    """System permissions."""
    # Tenant management
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    
    # Project management
    PROJECT_CREATE = "project:create"
    PROJECT_READ = "project:read"
    PROJECT_UPDATE = "project:update"
    PROJECT_DELETE = "project:delete"
    
    # Agent operations
    AGENT_EXECUTE = "agent:execute"
    AGENT_CONFIGURE = "agent:configure"
    
    # Integration management
    INTEGRATION_CREATE = "integration:create"
    INTEGRATION_READ = "integration:read"
    INTEGRATION_UPDATE = "integration:update"
    INTEGRATION_DELETE = "integration:delete"
    
    # Webhook management
    WEBHOOK_RECEIVE = "webhook:receive"
    WEBHOOK_CONFIGURE = "webhook:configure"
    
    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"


# Role-Permission mappings
ROLE_PERMISSIONS = {
    Role.ADMIN: [p for p in Permission],  # All permissions
    Role.MANAGER: [
        Permission.TENANT_READ,
        Permission.PROJECT_CREATE, Permission.PROJECT_READ, 
        Permission.PROJECT_UPDATE, Permission.PROJECT_DELETE,
        Permission.AGENT_EXECUTE, Permission.AGENT_CONFIGURE,
        Permission.INTEGRATION_READ, Permission.INTEGRATION_UPDATE,
        Permission.WEBHOOK_RECEIVE, Permission.WEBHOOK_CONFIGURE,
        Permission.USER_CREATE, Permission.USER_READ, 
        Permission.USER_UPDATE, Permission.USER_DELETE,
    ],
    Role.USER: [
        Permission.TENANT_READ,
        Permission.PROJECT_READ, Permission.PROJECT_UPDATE,
        Permission.AGENT_EXECUTE,
        Permission.INTEGRATION_READ,
        Permission.WEBHOOK_RECEIVE,
        Permission.USER_READ,
    ],
    Role.VIEWER: [
        Permission.TENANT_READ,
        Permission.PROJECT_READ,
        Permission.INTEGRATION_READ,
        Permission.USER_READ,
    ],
}


class Tenant:
    """Represents a tenant in the multi-tenant system."""
    
    def __init__(self, name: str, tier: str = "basic", tenant_id: str = None):
        """
        Initialize a tenant.
        
        Args:
            name: Tenant name
            tier: Subscription tier (basic, professional, enterprise)
            tenant_id: Optional tenant ID
        """
        self.id = tenant_id or str(uuid.uuid4())
        self.name = name
        self.tier = tier
        self.created_at = datetime.utcnow()
        self.active = True
        self.users: List[str] = []  # User IDs
        self.resources: Dict[str, List[str]] = {
            'projects': [],
            'integrations': [],
            'webhooks': []
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tenant to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'tier': self.tier,
            'created_at': self.created_at.isoformat(),
            'active': self.active,
            'user_count': len(self.users),
            'resource_count': {k: len(v) for k, v in self.resources.items()}
        }


class User:
    """Represents a user in the system."""
    
    def __init__(self, username: str, email: str, tenant_id: str, 
                 role: Role = Role.USER, user_id: str = None):
        """
        Initialize a user.
        
        Args:
            username: Username
            email: User email
            tenant_id: Tenant ID
            role: User role
            user_id: Optional user ID
        """
        self.id = user_id or str(uuid.uuid4())
        self.username = username
        self.email = email
        self.tenant_id = tenant_id
        self.role = role
        self.password_hash = None
        self.api_key = secrets.token_urlsafe(32)
        self.created_at = datetime.utcnow()
        self.active = True
    
    def set_password(self, password: str):
        """
        Set user password with secure hashing.
        
        Args:
            password: Plain text password
        
        Note: In production, use bcrypt, scrypt, or argon2 instead of SHA-256.
        SHA-256 is used here for simplicity and no external dependencies.
        For production deployment, replace with:
        import bcrypt
        self.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        """
        # Add salt for basic protection against rainbow tables
        import secrets
        salt = secrets.token_hex(16)
        salted_password = salt + password
        self.password_hash = salt + ':' + hashlib.sha256(salted_password.encode()).hexdigest()
    
    def verify_password(self, password: str) -> bool:
        """
        Verify password.
        
        Args:
            password: Plain text password
            
        Returns:
            True if password is correct
        """
        if not self.password_hash:
            return False
        
        # Parse salt and hash
        parts = self.password_hash.split(':')
        if len(parts) != 2:
            # Legacy format without salt (for backward compatibility)
            return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
        
        salt, stored_hash = parts
        salted_password = salt + password
        computed_hash = hashlib.sha256(salted_password.encode()).hexdigest()
        return computed_hash == stored_hash
    
    def has_permission(self, permission: Permission) -> bool:
        """
        Check if user has a permission.
        
        Args:
            permission: Permission to check
            
        Returns:
            True if user has permission
        """
        return permission in ROLE_PERMISSIONS.get(self.role, [])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'tenant_id': self.tenant_id,
            'role': self.role.value,
            'active': self.active,
            'created_at': self.created_at.isoformat()
        }


class RBACManager:
    """Manages multi-tenant RBAC system."""
    
    def __init__(self):
        """Initialize RBAC manager."""
        self.tenants: Dict[str, Tenant] = {}
        self.users: Dict[str, User] = {}
        self.user_by_username: Dict[str, str] = {}  # username -> user_id
        self.user_by_api_key: Dict[str, str] = {}  # api_key -> user_id
        self.logger = logging.getLogger("mira.rbac")
    
    # Tenant management
    def create_tenant(self, name: str, tier: str = "basic") -> Tenant:
        """
        Create a new tenant.
        
        Args:
            name: Tenant name
            tier: Subscription tier
            
        Returns:
            Created tenant
        """
        tenant = Tenant(name, tier)
        self.tenants[tenant.id] = tenant
        self.logger.info(f"Created tenant: {name} (ID: {tenant.id})")
        return tenant
    
    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        return self.tenants.get(tenant_id)
    
    def list_tenants(self) -> List[Tenant]:
        """List all tenants."""
        return list(self.tenants.values())
    
    def delete_tenant(self, tenant_id: str) -> bool:
        """
        Delete a tenant.
        
        Args:
            tenant_id: Tenant ID
            
        Returns:
            True if deleted
        """
        if tenant_id in self.tenants:
            # Delete all users in tenant
            users_to_delete = [uid for uid, u in self.users.items() 
                             if u.tenant_id == tenant_id]
            for uid in users_to_delete:
                self.delete_user(uid)
            
            del self.tenants[tenant_id]
            self.logger.info(f"Deleted tenant: {tenant_id}")
            return True
        return False
    
    # User management
    def create_user(self, username: str, email: str, tenant_id: str,
                   role: Role = Role.USER, password: str = None) -> Optional[User]:
        """
        Create a new user.
        
        Args:
            username: Username
            email: User email
            tenant_id: Tenant ID
            role: User role
            password: Optional password
            
        Returns:
            Created user or None if tenant doesn't exist
        """
        if tenant_id not in self.tenants:
            self.logger.error(f"Tenant not found: {tenant_id}")
            return None
        
        if username in self.user_by_username:
            self.logger.error(f"Username already exists: {username}")
            return None
        
        user = User(username, email, tenant_id, role)
        if password:
            user.set_password(password)
        
        self.users[user.id] = user
        self.user_by_username[username] = user.id
        self.user_by_api_key[user.api_key] = user.id
        self.tenants[tenant_id].users.append(user.id)
        
        self.logger.info(f"Created user: {username} (ID: {user.id})")
        return user
    
    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        user_id = self.user_by_username.get(username)
        return self.users.get(user_id) if user_id else None
    
    def get_user_by_api_key(self, api_key: str) -> Optional[User]:
        """Get user by API key."""
        user_id = self.user_by_api_key.get(api_key)
        return self.users.get(user_id) if user_id else None
    
    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted
        """
        if user_id in self.users:
            user = self.users[user_id]
            
            # Remove from tenant
            if user.tenant_id in self.tenants:
                self.tenants[user.tenant_id].users.remove(user_id)
            
            # Remove from indexes
            del self.user_by_username[user.username]
            del self.user_by_api_key[user.api_key]
            del self.users[user_id]
            
            self.logger.info(f"Deleted user: {user_id}")
            return True
        return False
    
    # Authorization
    def check_permission(self, user_id: str, permission: Permission,
                        resource_tenant_id: str = None) -> bool:
        """
        Check if user has permission.
        
        Args:
            user_id: User ID
            permission: Permission to check
            resource_tenant_id: Tenant ID of the resource (for isolation)
            
        Returns:
            True if user has permission
        """
        user = self.get_user(user_id)
        if not user or not user.active:
            return False
        
        # Check tenant isolation
        if resource_tenant_id and user.tenant_id != resource_tenant_id:
            # Only admins can cross tenant boundaries
            if user.role != Role.ADMIN:
                return False
        
        return user.has_permission(permission)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate user with username and password.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            User if authenticated, None otherwise
        """
        user = self.get_user_by_username(username)
        if user and user.active and user.verify_password(password):
            return user
        return None
    
    def authenticate_api_key(self, api_key: str) -> Optional[User]:
        """
        Authenticate user with API key.
        
        Args:
            api_key: API key
            
        Returns:
            User if authenticated, None otherwise
        """
        user = self.get_user_by_api_key(api_key)
        if user and user.active:
            return user
        return None


# Global RBAC manager instance
_rbac_manager = RBACManager()


def get_rbac_manager() -> RBACManager:
    """Get the global RBAC manager instance."""
    return _rbac_manager
