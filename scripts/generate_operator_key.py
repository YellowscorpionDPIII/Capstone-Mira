#!/usr/bin/env python3
"""
CLI utility for managing Mira operator keys.

Usage:
    python scripts/generate_operator_key.py
"""
import sys
import os

# Add parent directory to path to import mira modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mira.core.webhook_handler import WebhookHandler


def main():
    """Generate a new operator key."""
    print("=== Mira Operator Key Generator ===")
    print()
    
    # Initialize webhook handler
    handler = WebhookHandler()
    
    # Generate new key
    key = handler.generate_operator_key()
    
    print(f"Generated new operator key: {key}")
    print()
    print("This key has been saved to config/operator_keys.txt")
    print()
    print("Usage examples:")
    print(f"  curl -X POST http://localhost:5000/webhook/n8n \\")
    print(f"    -H 'Content-Type: application/json' \\")
    print(f"    -H 'X-Operator-Key: {key}' \\")
    print(f"    -d '{{\"test\": \"data\"}}'")
    print()
    print("For n8n integration:")
    print(f"  1. In n8n, create a new webhook node")
    print(f"  2. Set the webhook URL to: http://mira-app:5000/webhook/n8n")
    print(f"  3. Add a custom header: X-Operator-Key = {key}")
    print()


if __name__ == '__main__':
    main()
