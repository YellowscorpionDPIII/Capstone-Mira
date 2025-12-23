"""OpenAPI/Swagger documentation for API Key Management endpoints."""
from flask import Flask
from flask_restx import Api, Resource, fields, Namespace
from flask_cors import CORS
from typing import Optional

# API metadata
authorizations = {
    'Bearer': {
        'type': 'apiKey',
        'in': 'header',
        'name': 'Authorization',
        'description': "Type in the *'Value'* input box below: **'Bearer &lt;JWT&gt;'**, where JWT is the token"
    }
}

def create_api_documentation(app: Flask) -> Api:
    """
    Create OpenAPI/Swagger documentation for the API.
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask-RESTX Api instance
    """
    api = Api(
        app,
        version='1.0',
        title='Mira API Key Management API',
        description='Production-grade API key management system with RBAC, rate limiting, and zero-downtime rotation',
        doc='/swagger/',
        authorizations=authorizations,
        security='Bearer',
        contact='YellowscorpionDPIII',
        license='MIT',
        license_url='https://opensource.org/licenses/MIT'
    )
    
    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Create namespaces
    keys_ns = api.namespace('api/keys', description='API Key Management Operations')
    webhook_ns = api.namespace('webhook', description='Authenticated Webhook Operations')
    health_ns = api.namespace('health', description='Health Check Operations')
    
    # Define models
    api_key_model = api.model('ApiKey', {
        'key_id': fields.String(required=True, description='Unique key identifier'),
        'role': fields.String(required=True, description='Role (viewer, operator, admin)', enum=['viewer', 'operator', 'admin']),
        'name': fields.String(description='Human-readable name'),
        'created_at': fields.String(description='Creation timestamp (ISO 8601)'),
        'expires_at': fields.String(description='Expiration timestamp (ISO 8601)'),
        'last_used': fields.String(description='Last used timestamp (ISO 8601)'),
        'status': fields.String(description='Key status', enum=['active', 'expired', 'revoked', 'rotating'])
    })
    
    api_key_create_request = api.model('ApiKeyCreateRequest', {
        'role': fields.String(required=True, description='Role for the new key', enum=['viewer', 'operator', 'admin']),
        'name': fields.String(description='Human-readable name for the key'),
        'expiry_days': fields.Integer(description='Days until expiration (0 for no expiration)', default=90)
    })
    
    api_key_create_response = api.model('ApiKeyCreateResponse', {
        'api_key': fields.String(required=True, description='The raw API key (shown only once)'),
        'key_id': fields.String(required=True, description='Key identifier'),
        'role': fields.String(required=True, description='Key role'),
        'expires_at': fields.String(description='Expiration timestamp'),
        'message': fields.String(description='Important security notice')
    })
    
    api_key_list_response = api.model('ApiKeyListResponse', {
        'keys': fields.List(fields.Nested(api_key_model)),
        'count': fields.Integer(description='Number of keys returned')
    })
    
    api_key_rotate_request = api.model('ApiKeyRotateRequest', {
        'role': fields.String(description='Optional new role for the rotated key', enum=['viewer', 'operator', 'admin'])
    })
    
    api_key_rotate_response = api.model('ApiKeyRotateResponse', {
        'new_api_key': fields.String(required=True, description='The new API key'),
        'new_key_id': fields.String(required=True, description='New key identifier'),
        'old_key_id': fields.String(required=True, description='Old key identifier'),
        'grace_period_minutes': fields.Integer(description='Minutes until old key is fully revoked'),
        'message': fields.String(description='Rotation information')
    })
    
    error_model = api.model('Error', {
        'message': fields.String(required=True, description='Error message'),
        'code': fields.String(description='Error code'),
        'details': fields.Raw(description='Additional error details')
    })
    
    health_response = api.model('HealthResponse', {
        'status': fields.String(description='Service status', enum=['healthy', 'degraded', 'unhealthy']),
        'timestamp': fields.String(description='Check timestamp'),
        'version': fields.String(description='API version'),
        'components': fields.Raw(description='Component health status')
    })
    
    cache_stats_response = api.model('CacheStatsResponse', {
        'memory_cache_size': fields.Integer(description='Number of keys in memory cache'),
        'rotation_state_size': fields.Integer(description='Number of keys in rotation'),
        'redis': fields.Raw(description='Redis cache statistics')
    })
    
    # Document endpoints
    
    @keys_ns.route('')
    class ApiKeyList(Resource):
        @keys_ns.doc('list_keys', security='Bearer')
        @keys_ns.param('role', 'Filter by role (viewer, operator, admin)', _in='query')
        @keys_ns.param('status', 'Filter by status (active, expired, revoked)', _in='query')
        @keys_ns.marshal_with(api_key_list_response)
        @keys_ns.response(200, 'Success')
        @keys_ns.response(401, 'Unauthorized', error_model)
        @keys_ns.response(403, 'Forbidden', error_model)
        @keys_ns.response(429, 'Rate Limit Exceeded', error_model)
        def get(self):
            """
            List all API keys (requires 'list' permission).
            
            Returns a list of API keys, optionally filtered by role and status.
            Viewer, operator, and admin roles can list keys.
            """
            pass
        
        @keys_ns.doc('create_key', security='Bearer')
        @keys_ns.expect(api_key_create_request)
        @keys_ns.marshal_with(api_key_create_response, code=201)
        @keys_ns.response(201, 'Key created successfully')
        @keys_ns.response(400, 'Invalid request', error_model)
        @keys_ns.response(401, 'Unauthorized', error_model)
        @keys_ns.response(403, 'Forbidden - requires manage_keys permission', error_model)
        @keys_ns.response(429, 'Rate Limit Exceeded', error_model)
        def post(self):
            """
            Generate a new API key (requires 'manage_keys' permission).
            
            Creates a new API key with the specified role and expiration.
            The raw API key is returned only once - store it securely!
            Only admin users can create keys.
            """
            pass
    
    @keys_ns.route('/<string:key_id>')
    @keys_ns.param('key_id', 'The API key identifier')
    class ApiKeyDetail(Resource):
        @keys_ns.doc('get_key', security='Bearer')
        @keys_ns.marshal_with(api_key_model)
        @keys_ns.response(200, 'Success')
        @keys_ns.response(401, 'Unauthorized', error_model)
        @keys_ns.response(404, 'Key not found', error_model)
        @keys_ns.response(429, 'Rate Limit Exceeded', error_model)
        def get(self, key_id):
            """
            Get details of a specific API key.
            
            Returns metadata for the specified API key (does not return the raw key).
            """
            pass
        
        @keys_ns.doc('delete_key', security='Bearer')
        @keys_ns.response(200, 'Key revoked successfully')
        @keys_ns.response(401, 'Unauthorized', error_model)
        @keys_ns.response(403, 'Forbidden - requires manage_keys permission', error_model)
        @keys_ns.response(404, 'Key not found', error_model)
        @keys_ns.response(429, 'Rate Limit Exceeded', error_model)
        def delete(self, key_id):
            """
            Revoke an API key (requires 'manage_keys' permission).
            
            Immediately revokes the specified API key.
            Only admin users can revoke keys.
            """
            pass
    
    @keys_ns.route('/<string:key_id>/rotate')
    @keys_ns.param('key_id', 'The API key identifier to rotate')
    class ApiKeyRotate(Resource):
        @keys_ns.doc('rotate_key', security='Bearer')
        @keys_ns.expect(api_key_rotate_request)
        @keys_ns.marshal_with(api_key_rotate_response)
        @keys_ns.response(200, 'Key rotated successfully')
        @keys_ns.response(400, 'Invalid request', error_model)
        @keys_ns.response(401, 'Unauthorized', error_model)
        @keys_ns.response(403, 'Forbidden - requires manage_keys permission', error_model)
        @keys_ns.response(404, 'Key not found', error_model)
        @keys_ns.response(429, 'Rate Limit Exceeded', error_model)
        def post(self, key_id):
            """
            Rotate an API key with zero-downtime (requires 'manage_keys' permission).
            
            Creates a new API key and marks the old one for revocation after a grace period.
            During the grace period (default 60 minutes), both keys are valid.
            This enables zero-downtime key rotation in production systems.
            """
            pass
    
    @keys_ns.route('/stats/cache')
    class CacheStats(Resource):
        @keys_ns.doc('get_cache_stats', security='Bearer')
        @keys_ns.marshal_with(cache_stats_response)
        @keys_ns.response(200, 'Success')
        @keys_ns.response(401, 'Unauthorized', error_model)
        @keys_ns.response(403, 'Forbidden - requires admin role', error_model)
        def get(self):
            """
            Get cache statistics (requires admin role).
            
            Returns statistics about the in-memory and Redis caches.
            """
            pass
    
    @health_ns.route('')
    class Health(Resource):
        @health_ns.doc('health_check')
        @health_ns.marshal_with(health_response)
        @health_ns.response(200, 'Service is healthy')
        @health_ns.response(503, 'Service is unhealthy', error_model)
        def get(self):
            """
            Health check endpoint.
            
            Returns the health status of the service and its components.
            Does not require authentication.
            """
            pass
    
    @webhook_ns.route('/<string:webhook_name>')
    @webhook_ns.param('webhook_name', 'The name of the webhook to trigger')
    class Webhook(Resource):
        @webhook_ns.doc('trigger_webhook', security='Bearer')
        @webhook_ns.response(200, 'Webhook processed successfully')
        @webhook_ns.response(202, 'Webhook accepted for processing')
        @webhook_ns.response(401, 'Unauthorized', error_model)
        @webhook_ns.response(403, 'Forbidden - insufficient permissions', error_model)
        @webhook_ns.response(404, 'Webhook not found', error_model)
        @webhook_ns.response(429, 'Rate Limit Exceeded', error_model)
        def post(self, webhook_name):
            """
            Trigger an authenticated webhook.
            
            Executes the specified webhook with authentication and RBAC.
            Required permissions depend on the webhook type.
            """
            pass
    
    return api


def setup_swagger_ui(app: Flask):
    """
    Setup Swagger UI configuration.
    
    Args:
        app: Flask application instance
    """
    app.config['SWAGGER_UI_DOC_EXPANSION'] = 'list'
    app.config['SWAGGER_UI_OPERATION_ID'] = True
    app.config['SWAGGER_UI_REQUEST_DURATION'] = True
    app.config['RESTX_MASK_SWAGGER'] = False
    app.config['RESTX_VALIDATE'] = True
    app.config['RESTX_JSON'] = {
        'indent': 2,
        'sort_keys': False
    }
