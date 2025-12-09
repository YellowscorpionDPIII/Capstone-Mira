"""Example Flask application demonstrating API key management with rate limiting."""
from flask import Flask, request, jsonify
from mira.auth.api_key_manager import APIKeyManager
from mira.auth.rate_limiter import get_limiter

app = Flask(__name__)

# Initialize rate limiter
limiter = get_limiter(app)

# Initialize API key manager
# WARNING: In production, use environment variables or secure config for jwt_secret
api_key_manager = APIKeyManager(jwt_secret="your-secret-key-here")


@app.route('/api/keys/generate', methods=['POST'])
@limiter.limit("10 per minute")
def generate_key():
    """
    Generate a new API key.
    
    Rate limited to 10 requests per minute per IP.
    
    Request body:
    {
        "user_id": "string",
        "role": "string" (optional, default: "user"),
        "metadata": {} (optional)
    }
    
    Returns:
    {
        "api_key": "string",
        "user_id": "string",
        "role": "string",
        "created_at": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        
        user_id = data['user_id']
        role = data.get('role', 'user')
        metadata = data.get('metadata', {})
        
        result = api_key_manager.generate_api_key(
            user_id=user_id,
            role=role,
            metadata=metadata
        )
        
        return jsonify(result), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/keys/rotate', methods=['POST'])
@limiter.limit("10 per minute")
def rotate_key():
    """
    Rotate an existing API key.
    
    Rate limited to 10 requests per minute per IP.
    
    Request body:
    {
        "api_key": "string",
        "user_id": "string"
    }
    
    Returns:
    {
        "api_key": "string",
        "user_id": "string",
        "role": "string",
        "created_at": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'api_key' not in data or 'user_id' not in data:
            return jsonify({'error': 'api_key and user_id are required'}), 400
        
        result = api_key_manager.rotate_api_key(
            old_key=data['api_key'],
            user_id=data['user_id']
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/api/keys/verify', methods=['POST'])
def verify_key():
    """
    Verify an API key.
    
    Request body:
    {
        "api_key": "string"
    }
    
    Returns:
    {
        "valid": true,
        "user_id": "string",
        "role": "string"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'api_key' not in data:
            return jsonify({'error': 'api_key is required'}), 400
        
        key_data = api_key_manager.verify_api_key(data['api_key'])
        
        if key_data:
            return jsonify({
                'valid': True,
                'user_id': key_data['user_id'],
                'role': key_data['role']
            }), 200
        else:
            return jsonify({'valid': False}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/keys/list/<user_id>', methods=['GET'])
def list_keys(user_id: str):
    """
    List all API keys for a user (admin endpoint).
    
    Note: Keys are hashed and not retrievable. The response shows
    a masked hash preview (first/last 8 chars) for reference only.
    
    Returns:
    [
        {
            "user_id": "string",
            "role": "string",
            "created_at": "string",
            "last_used": "string",
            "key_hash_preview": "string"
        }
    ]
    """
    try:
        keys = api_key_manager.list_keys_for_user(user_id, mask=True)
        return jsonify(keys), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tokens/generate', methods=['POST'])
def generate_token():
    """
    Generate a JWT token.
    
    Request body:
    {
        "user_id": "string",
        "role": "string" (optional, default: "user"),
        "expiry_hours": int (optional, default: 24),
        "additional_claims": {} (optional)
    }
    
    Returns:
    {
        "token": "string",
        "expires_in_hours": int
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'user_id' not in data:
            return jsonify({'error': 'user_id is required'}), 400
        
        user_id = data['user_id']
        role = data.get('role', 'user')
        expiry_hours = data.get('expiry_hours', 24)
        additional_claims = data.get('additional_claims', {})
        
        token = api_key_manager.generate_jwt_token(
            user_id=user_id,
            role=role,
            expiry_hours=expiry_hours,
            additional_claims=additional_claims
        )
        
        return jsonify({
            'token': token,
            'expires_in_hours': expiry_hours
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tokens/verify', methods=['POST'])
def verify_token():
    """
    Verify a JWT token.
    
    Request body:
    {
        "token": "string"
    }
    
    Returns:
    {
        "valid": true,
        "payload": {
            "sub": "string",
            "role": "string",
            "iat": int,
            "exp": int
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({'error': 'token is required'}), 400
        
        payload = api_key_manager.verify_jwt_token(data['token'])
        
        if payload:
            return jsonify({
                'valid': True,
                'payload': payload
            }), 200
        else:
            return jsonify({'valid': False}), 401
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
