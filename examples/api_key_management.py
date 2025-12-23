"""Example: API key management and authenticated webhook usage."""
import json
from mira.auth import ApiKeyManager
from mira.integrations.airtable_integration import AirtableIntegration


def example_generate_api_keys():
    """Example: Generate API keys for different roles."""
    print("=" * 60)
    print("Example 1: Generating API Keys")
    print("=" * 60)
    
    # Initialize API key manager
    # In production, connect to Airtable for persistent storage
    airtable = AirtableIntegration({'api_key': 'your-key', 'base_id': 'your-base'})
    airtable.connect()
    
    manager = ApiKeyManager(storage_backend=airtable, default_expiry_days=90)
    
    # Generate a viewer key
    viewer_key, viewer_metadata = manager.generate_key(
        role='viewer',
        name='n8n Workflow Monitor',
        expiry_days=90
    )
    
    print(f"\n✓ Generated Viewer Key:")
    print(f"  Key ID: {viewer_metadata.key_id}")
    print(f"  API Key: {viewer_key}")
    print(f"  Role: {viewer_metadata.role}")
    print(f"  Expires: {viewer_metadata.expires_at}")
    print(f"  Permissions: {', '.join(ApiKeyManager.ROLE_PERMISSIONS['viewer'])}")
    
    # Generate an operator key
    operator_key, operator_metadata = manager.generate_key(
        role='operator',
        name='n8n Automation Bot',
        expiry_days=180
    )
    
    print(f"\n✓ Generated Operator Key:")
    print(f"  Key ID: {operator_metadata.key_id}")
    print(f"  API Key: {operator_key}")
    print(f"  Role: {operator_metadata.role}")
    print(f"  Expires: {operator_metadata.expires_at}")
    print(f"  Permissions: {', '.join(ApiKeyManager.ROLE_PERMISSIONS['operator'])}")
    
    # Generate an admin key
    admin_key, admin_metadata = manager.generate_key(
        role='admin',
        name='System Administrator',
        expiry_days=365
    )
    
    print(f"\n✓ Generated Admin Key:")
    print(f"  Key ID: {admin_metadata.key_id}")
    print(f"  API Key: {admin_key}")
    print(f"  Role: {admin_metadata.role}")
    print(f"  Expires: {admin_metadata.expires_at}")
    print(f"  Permissions: {', '.join(ApiKeyManager.ROLE_PERMISSIONS['admin'])}")
    
    print("\n⚠️  Important: Save these keys securely. They won't be shown again!")
    
    return manager, {
        'viewer': viewer_key,
        'operator': operator_key,
        'admin': admin_key
    }


def example_validate_and_use_key():
    """Example: Validate and use an API key."""
    print("\n" + "=" * 60)
    print("Example 2: Validating API Keys")
    print("=" * 60)
    
    manager = ApiKeyManager()
    
    # Generate a test key
    test_key, test_metadata = manager.generate_key(role='operator', name='Test Key')
    
    print(f"\n✓ Generated test key: {test_metadata.key_id}")
    
    # Validate the key
    validated = manager.validate_key(test_key)
    
    if validated:
        print(f"\n✓ Key validation successful!")
        print(f"  Key ID: {validated.key_id}")
        print(f"  Role: {validated.role}")
        print(f"  Last Used: {validated.last_used}")
        
        # Check permissions
        print(f"\n  Checking permissions:")
        for permission in ['read', 'write', 'execute', 'manage_keys']:
            has_perm = manager.check_permission(validated, permission)
            status = "✓" if has_perm else "✗"
            print(f"    {status} {permission}")
    else:
        print("\n✗ Key validation failed!")


def example_key_rotation():
    """Example: Rotate an API key."""
    print("\n" + "=" * 60)
    print("Example 3: Rotating API Keys")
    print("=" * 60)
    
    manager = ApiKeyManager()
    
    # Generate initial key
    old_key, old_metadata = manager.generate_key(role='operator', name='Original Key')
    
    print(f"\n✓ Original Key ID: {old_metadata.key_id}")
    print(f"  Role: {old_metadata.role}")
    
    # Rotate the key
    new_key, new_metadata = manager.rotate_key(old_metadata.key_id)
    
    print(f"\n✓ New Key ID: {new_metadata.key_id}")
    print(f"  Role: {new_metadata.role}")
    print(f"  Old key status: {old_metadata.status}")
    
    # Try to validate old key (should fail)
    validated_old = manager.validate_key(old_key)
    print(f"\n  Old key validation: {'✗ Failed (revoked)' if not validated_old else '✓ Still valid'}")
    
    # Validate new key (should succeed)
    validated_new = manager.validate_key(new_key)
    print(f"  New key validation: {'✓ Success' if validated_new else '✗ Failed'}")


def example_list_and_manage_keys():
    """Example: List and manage API keys."""
    print("\n" + "=" * 60)
    print("Example 4: Listing and Managing Keys")
    print("=" * 60)
    
    manager = ApiKeyManager()
    
    # Generate several keys
    manager.generate_key(role='viewer', name='Viewer 1')
    manager.generate_key(role='viewer', name='Viewer 2')
    manager.generate_key(role='operator', name='Operator 1')
    manager.generate_key(role='admin', name='Admin 1')
    
    # List all keys
    all_keys = manager.list_keys()
    print(f"\n✓ Total keys: {len(all_keys)}")
    
    # List by role
    viewer_keys = manager.list_keys(role='viewer')
    operator_keys = manager.list_keys(role='operator')
    admin_keys = manager.list_keys(role='admin')
    
    print(f"\n  Keys by role:")
    print(f"    Viewers: {len(viewer_keys)}")
    print(f"    Operators: {len(operator_keys)}")
    print(f"    Admins: {len(admin_keys)}")
    
    # Revoke a key
    if viewer_keys:
        key_to_revoke = viewer_keys[0]
        success = manager.revoke_key(key_to_revoke.key_id)
        if success:
            print(f"\n✓ Revoked key: {key_to_revoke.key_id}")
        else:
            print(f"\n✗ Failed to revoke key: {key_to_revoke.key_id}")
    
    # List active vs revoked
    active_keys = manager.list_keys(status='active')
    revoked_keys = manager.list_keys(status='revoked')
    
    print(f"\n  Keys by status:")
    print(f"    Active: {len(active_keys)}")
    print(f"    Revoked: {len(revoked_keys)}")


def example_n8n_webhook_integration():
    """Example: Using API keys with n8n webhooks."""
    print("\n" + "=" * 60)
    print("Example 5: n8n Webhook Integration")
    print("=" * 60)
    
    print("\nTo integrate with n8n:")
    print("\n1. Generate an API key (operator or admin role)")
    print("2. In n8n, add an HTTP Request node:")
    print("   - Method: POST")
    print("   - URL: http://your-mira-server:5000/webhook/n8n")
    print("   - Authentication: Generic Credential Type")
    print("   - Add Header:")
    print("     Name: Authorization")
    print("     Value: Bearer <your-api-key>")
    print("\n3. Set up your workflow payload:")
    
    payload_example = {
        "type": "generate_plan",
        "data": {
            "name": "n8n Automated Project",
            "goals": ["Automate workflows", "Integrate with Mira"],
            "duration_weeks": 8
        }
    }
    
    print(f"\n   {json.dumps(payload_example, indent=4)}")
    
    print("\n4. The webhook will:")
    print("   - Validate your API key")
    print("   - Check role permissions")
    print("   - Process the request")
    print("   - Log the action for audit")
    print("   - Return results to n8n")


def example_curl_commands():
    """Example: cURL commands for API key management."""
    print("\n" + "=" * 60)
    print("Example 6: cURL Commands")
    print("=" * 60)
    
    print("\n# Create a new API key (requires admin role)")
    print("""
curl -X POST http://localhost:5000/api/keys \\
  -H "Authorization: Bearer <admin-api-key>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "role": "operator",
    "name": "Production Bot",
    "expiry_days": 90
  }'
""")
    
    print("\n# List all API keys (requires admin role)")
    print("""
curl -X GET http://localhost:5000/api/keys \\
  -H "Authorization: Bearer <admin-api-key>"
""")
    
    print("\n# Validate your current API key")
    print("""
curl -X GET http://localhost:5000/api/auth/validate \\
  -H "Authorization: Bearer <your-api-key>"
""")
    
    print("\n# Rotate an API key (requires admin role)")
    print("""
curl -X POST http://localhost:5000/api/keys/<key-id>/rotate \\
  -H "Authorization: Bearer <admin-api-key>" \\
  -H "Content-Type: application/json" \\
  -d '{"role": "operator"}'
""")
    
    print("\n# Revoke an API key (requires admin role)")
    print("""
curl -X DELETE http://localhost:5000/api/keys/<key-id> \\
  -H "Authorization: Bearer <admin-api-key>"
""")
    
    print("\n# Call a webhook with authentication")
    print("""
curl -X POST http://localhost:5000/webhook/n8n \\
  -H "Authorization: Bearer <your-api-key>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "type": "generate_plan",
    "data": {
      "name": "My Project",
      "goals": ["Goal 1", "Goal 2"]
    }
  }'
""")


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Mira HITL API Key Management Examples")
    print("=" * 60)
    
    # Run examples
    example_generate_api_keys()
    example_validate_and_use_key()
    example_key_rotation()
    example_list_and_manage_keys()
    example_n8n_webhook_integration()
    example_curl_commands()
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
