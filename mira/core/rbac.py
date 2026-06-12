"""Role-Based Access Control (RBAC) system for Mira platform."""
from enum import Enum
from typing import Dict, List, Optional, Set
from functools import wraps
from flask import request, jsonify
import logging


class Role(Enum):
    """User roles with hierarchical permissions."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"


class Permission(Enum):
    """Available permissions in the system."""
    LIST_OWN_KEYS = "list_own_keys"
    LIST_ALL_KEYS = "list_all_keys"
    GENERATE_KEYS = "generate_keys"
    REVOKE_KEYS = "revoke_keys"
    CRUD_KEYS = "crud_keys"
    READ_WEBHOOKS = "read_webhooks"
    EXECUTE_WEBHOOKS = "execute_webhooks"


class RBACManager:
    """Manage role-based access control and permissions."""
    
    # Define role hierarchy and their permissions
    ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
        Role.VIEWER: {
            Permission.LIST_OWN_KEYS,
            Permission.READ_WEBHOOKS,
        },
        Role.OPERATOR: {
            Permission.LIST_OWN_KEYS,
            Permission.LIST_ALL_KEYS,
            Permission.GENERATE_KEYS,
            Permission.READ_WEBHOOKS,
            Permission.EXECUTE_WEBHOOKS,
        },
        Role.ADMIN: {
            Permission.LIST_OWN_KEYS,
            Permission.LIST_ALL_KEYS,
            Permission.GENERATE_KEYS,
            Permission.REVOKE_KEYS,
            Permission.CRUD_KEYS,
            Permission.READ_WEBHOOKS,
            Permission.EXECUTE_WEBHOOKS,
        },
    }
    
    def __init__(self):
        """Initialize RBAC manager."""
        self.logger = logging.getLogger("mira.rbac")
    
    def has_permission(self, role: Role, permission: Permission) -> bool:
        """
        Check if a role has a specific permission.
        
        Args:
            role: User role
            permission: Permission to check
            
        Returns:
            True if role has permission, False otherwise
        """
        return permission in self.ROLE_PERMISSIONS.get(role, set())
    
    def get_role_permissions(self, role: Role) -> Set[Permission]:
        """
        Get all permissions for a role.
        
        Args:
            role: User role
            
        Returns:
            Set of permissions
        """
        return self.ROLE_PERMISSIONS.get(role, set())
    
    def validate_access(self, role: Role, required_permission: Permission) -> bool:
        """
        Validate if a role has access based on required permission.
        
        Args:
            role: User role
            required_permission: Required permission
            
        Returns:
            True if access is granted, False otherwise
        """
        has_access = self.has_permission(role, required_permission)
        if not has_access:
            self.logger.warning(
                f"Access denied: Role {role.value} does not have permission {required_permission.value}"
            )
        return has_access


# Global RBAC manager instance
_rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """
    Get the global RBAC manager instance.
    
    Returns:
        RBAC manager instance
    """
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission for an endpoint.
    
    Args:
        permission: Required permission
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get user role from request context (set by authentication middleware)
            user_role = getattr(request, 'user_role', None)
            
            if user_role is None:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Convert string to Role enum if needed
            if isinstance(user_role, str):
                try:
                    user_role = Role(user_role.lower())
                except ValueError:
                    return jsonify({'error': 'Invalid role'}), 403
            
            # Check permission
            rbac = get_rbac_manager()
            if not rbac.validate_access(user_role, permission):
                return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_role(required_role: Role):
    """
    Decorator to require a minimum role level for an endpoint.
    
    Args:
        required_role: Minimum required role
        
    Returns:
        Decorated function
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_role = getattr(request, 'user_role', None)
            
            if user_role is None:
                return jsonify({'error': 'Authentication required'}), 401
            
            # Convert string to Role enum if needed
            if isinstance(user_role, str):
                try:
                    user_role = Role(user_role.lower())
                except ValueError:
                    return jsonify({'error': 'Invalid role'}), 403
            
            # Role hierarchy check
            role_hierarchy = {Role.VIEWER: 1, Role.OPERATOR: 2, Role.ADMIN: 3}
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                return jsonify({'error': 'Insufficient role level'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
