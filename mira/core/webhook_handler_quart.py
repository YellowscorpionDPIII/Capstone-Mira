"""Webhook handler for external integrations using Quart with OpenAPI documentation."""
from typing import Dict, Any, Callable, Optional
from quart import Quart, request, jsonify, render_template_string
from dataclasses import dataclass
import logging
import hmac
import hashlib
import json


@dataclass
class WebhookRequest:
    """Webhook request data model."""
    service: str
    data: Dict[str, Any]


@dataclass
class WebhookResponse:
    """Webhook response data model."""
    status: str
    service: str
    message: Optional[str] = None


# OpenAPI specification
OPENAPI_SPEC = {
    "openapi": "3.0.0",
    "info": {
        "title": "Mira Webhook API",
        "version": "1.0.0",
        "description": "Multi-Agent Workflow Platform - Webhook API for external integrations including n8n, GitHub, Trello, Jira, and more.",
        "contact": {
            "name": "Mira Team",
            "url": "https://github.com/YellowscorpionDPIII/Capstone-Mira"
        }
    },
    "servers": [
        {
            "url": "http://localhost:5000",
            "description": "Local development server"
        }
    ],
    "paths": {
        "/webhook/{service}": {
            "post": {
                "summary": "Process webhook from external service",
                "description": "Handle incoming webhook from external service and route to appropriate handler. Supports HMAC-SHA256 signature verification.",
                "parameters": [
                    {
                        "name": "service",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "enum": ["n8n", "github", "trello", "jira", "custom"]},
                        "description": "Service name for webhook routing"
                    }
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "description": "Workflow type"},
                                    "data": {"type": "object", "description": "Workflow data"}
                                },
                                "required": ["type", "data"]
                            },
                            "examples": {
                                "generate_plan": {
                                    "value": {
                                        "type": "generate_plan",
                                        "data": {
                                            "name": "Project Alpha",
                                            "goals": ["Goal 1", "Goal 2"],
                                            "duration_weeks": 12
                                        }
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Webhook processed successfully",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "service": {"type": "string"},
                                        "data": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "403": {"description": "Invalid signature"},
                    "404": {"description": "Unknown service"},
                    "500": {"description": "Internal server error"}
                },
                "security": [
                    {"HmacSignature": []},
                    {"ApiKey": []}
                ]
            }
        },
        "/health": {
            "get": {
                "summary": "Health check endpoint",
                "description": "Check if the webhook service is healthy and list registered handlers",
                "responses": {
                    "200": {
                        "description": "Service is healthy",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "service": {"type": "string"},
                                        "handlers": {"type": "array", "items": {"type": "string"}}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "/api/services": {
            "get": {
                "summary": "List registered webhook services",
                "description": "Get a list of all registered webhook service handlers",
                "responses": {
                    "200": {
                        "description": "Successfully retrieved service list",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "services": {"type": "array", "items": {"type": "string"}},
                                        "count": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "securitySchemes": {
            "HmacSignature": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Hub-Signature-256",
                "description": "HMAC-SHA256 signature: sha256=<hmac-sha256-hash>"
            },
            "ApiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key"
            }
        }
    }
}


# Swagger UI HTML template
SWAGGER_UI_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mira Webhook API - Documentation</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui.css">
    <style>
        body { margin: 0; padding: 0; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-bundle.js"></script>
    <script src="https://unpkg.com/swagger-ui-dist@5.10.3/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                spec: {{ spec | tojson }},
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout"
            });
            window.ui = ui;
        }
    </script>
</body>
</html>
"""


class WebhookHandler:
    """
    Handle incoming webhooks from external services with OpenAPI documentation.
    
    Provides endpoints for receiving webhooks and routing them to appropriate handlers.
    Includes automatic OpenAPI spec generation at /docs endpoint.
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize the webhook handler.
        
        Args:
            secret_key: Secret key for webhook signature verification
        """
        self.app = Quart(__name__)
        self.secret_key = secret_key
        self.handlers: Dict[str, Callable] = {}
        self.logger = logging.getLogger("mira.webhook")
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up Quart routes for webhooks with OpenAPI documentation."""
        
        @self.app.route('/webhook/<service>', methods=['POST'])
        async def handle_webhook(service: str):
            """Handle incoming webhook from external service."""
            try:
                # Verify signature if secret key is configured
                if self.secret_key and 'X-Hub-Signature-256' in request.headers:
                    body = await request.get_data()
                    if not self._verify_signature(body, request.headers['X-Hub-Signature-256']):
                        return jsonify({'error': 'Invalid signature', 'status': 'error'}), 403
                
                data = await request.get_json() or {}
                self.logger.info(f"Received webhook from {service}")
                
                # Route to appropriate handler
                if service in self.handlers:
                    response = await self.handlers[service](data)
                    return jsonify({
                        'status': 'processed',
                        'service': service,
                        'data': response
                    }), 200
                else:
                    return jsonify({
                        'error': 'Unknown service',
                        'status': 'error',
                        'service': service
                    }), 404
                    
            except Exception as e:
                self.logger.error(f"Error handling webhook: {e}")
                return jsonify({
                    'error': 'Internal server error',
                    'status': 'error',
                    'message': str(e)
                }), 500
        
        @self.app.route('/health', methods=['GET'])
        async def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'service': 'mira-webhook',
                'handlers': list(self.handlers.keys())
            }), 200
        
        @self.app.route('/api/services', methods=['GET'])
        async def list_services():
            """List all registered webhook services."""
            return jsonify({
                'services': list(self.handlers.keys()),
                'count': len(self.handlers)
            }), 200
        
        @self.app.route('/docs', methods=['GET'])
        async def openapi_docs():
            """Serve OpenAPI documentation (Swagger UI)."""
            return await render_template_string(SWAGGER_UI_HTML, spec=OPENAPI_SPEC)
        
        @self.app.route('/openapi.json', methods=['GET'])
        async def openapi_spec():
            """Serve OpenAPI specification as JSON."""
            return jsonify(OPENAPI_SPEC), 200
                
    def _verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature.
        
        Args:
            payload: Request payload
            signature: Signature from header
            
        Returns:
            True if signature is valid
        """
        if not self.secret_key:
            return True
            
        expected = 'sha256=' + hmac.new(
            self.secret_key.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
        
    def register_handler(self, service: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]):
        """
        Register a webhook handler for a service.
        
        Args:
            service: Service name (e.g., 'github', 'trello', 'n8n')
            handler: Handler function (can be async or sync)
        """
        self.handlers[service] = handler
        self.logger.info(f"Handler registered for service: {service}")
        
    def run(self, host: str = '0.0.0.0', port: int = 5000):
        """
        Start the webhook server.
        
        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self.logger.info(f"Starting webhook server on {host}:{port}")
        self.logger.info(f"OpenAPI docs available at http://{host}:{port}/docs")
        self.app.run(host=host, port=port)

