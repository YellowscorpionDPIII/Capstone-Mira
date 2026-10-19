"""
Example demonstrating production-grade features in Mira.

This example shows how to use:
1. Secrets Manager with retry logic
2. Structured Logging with correlation context
3. Priority-based Shutdown Handler
4. Health Check endpoint
"""

import os
import sys
from mira.utils.secrets_manager import initialize_secrets_manager, get_secret
from mira.utils.structured_logging import (
    setup_structured_logging,
    CorrelationContext,
    get_structured_logger,
    with_correlation_context
)
from mira.utils.shutdown_handler import (
    initialize_shutdown_handler,
    register_shutdown_callback,
    on_shutdown
)


def example_secrets_management():
    """Example: Using secrets manager with retry logic."""
    print("\n=== Secrets Management Example ===")
    
    # Initialize with environment variables (default)
    initialize_secrets_manager(backend="env")
    
    # Set a test secret
    os.environ['API_KEY'] = 'secret_api_key_12345'
    os.environ['DB_PASSWORD'] = 'secure_password'
    
    # Fetch secrets with automatic retry
    api_key = get_secret('API_KEY', max_retries=3, delay=0.1)
    print(f"✓ Fetched API_KEY: {api_key[:10]}...")
    
    # Fetch with default value if not found
    optional_key = get_secret('OPTIONAL_KEY', default='default_value', max_retries=1)
    print(f"✓ Fetched OPTIONAL_KEY (with default): {optional_key}")
    
    # In production, you would initialize with Vault or K8s:
    # initialize_secrets_manager(
    #     backend="vault",
    #     config={"url": "https://vault.example.com", "token": "..."}
    # )
    # or
    # initialize_secrets_manager(backend="k8s", config={"namespace": "default"})


def example_structured_logging():
    """Example: Using structured logging with correlation context."""
    print("\n=== Structured Logging Example ===")
    
    # Setup structured logging (optionally with JSON format)
    setup_structured_logging(level='INFO', format_json=False)
    
    logger = get_structured_logger('example')
    
    # Log without context
    logger.info("Application started")
    
    # Log with correlation context
    with CorrelationContext(
        agent_id="project_plan_agent",
        task_id="task_456",
        workflow_id="workflow_789"
    ):
        logger.info("Processing task", task_name="Create project plan")
        logger.info("Task completed successfully")
    
    print("✓ Structured logging with correlation context demonstrated")


class ExampleAgent:
    """Example agent class using correlation context decorator."""
    
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.logger = get_structured_logger(f'agent.{agent_id}')
    
    @with_correlation_context()
    def process_task(self, task_id):
        """Process a task with automatic correlation context."""
        # The decorator automatically sets agent_id from self.agent_id
        # and includes it in all log messages
        self.logger.info(f"Processing task {task_id}")
        # Your task processing logic here
        return {"status": "completed", "task_id": task_id}


def example_decorator_logging():
    """Example: Using @with_correlation_context decorator."""
    print("\n=== Decorator-based Logging Example ===")
    
    agent = ExampleAgent("risk_assessment_agent")
    result = agent.process_task("task_789")
    print(f"✓ Task processed: {result}")


def example_shutdown_handler():
    """Example: Using priority-based shutdown handler."""
    print("\n=== Shutdown Handler Example ===")
    
    # Initialize shutdown handler (registers signal handlers)
    initialize_shutdown_handler()
    
    call_order = []
    
    # Register shutdown callbacks with different priorities
    # Lower priority number = executes first
    
    def drain_agent_queues():
        call_order.append("1. Drain agent queues")
        print("  Draining agent queues...")
    
    def close_database_connections():
        call_order.append("2. Close database connections")
        print("  Closing database connections...")
    
    def cleanup_temp_files():
        call_order.append("3. Cleanup temp files")
        print("  Cleaning up temporary files...")
    
    def flush_logs():
        call_order.append("4. Flush logs")
        print("  Flushing logs...")
    
    # Register with priorities (0-9: critical, 10-19: high, 20-29: medium, 30+: low)
    register_shutdown_callback(drain_agent_queues, priority=5, name="drain_agents")
    register_shutdown_callback(close_database_connections, priority=15, name="close_db")
    register_shutdown_callback(cleanup_temp_files, priority=25, name="cleanup_temp")
    register_shutdown_callback(flush_logs, priority=35, name="flush_logs")
    
    print("✓ Registered 4 shutdown callbacks with priorities")
    print("  - Priority 5: Drain agent queues")
    print("  - Priority 15: Close database connections")
    print("  - Priority 25: Cleanup temp files")
    print("  - Priority 35: Flush logs")
    
    # Note: In production, shutdown is triggered by SIGTERM/SIGINT
    # For demonstration, we can manually trigger it:
    # from mira.utils.shutdown_handler import get_shutdown_handler
    # get_shutdown_handler().execute_shutdown()


@on_shutdown(priority=10, name="cleanup_example_resources")
def cleanup_resources():
    """Example: Using @on_shutdown decorator."""
    print("  Cleaning up example resources...")


def example_decorator_shutdown():
    """Example: Using @on_shutdown decorator."""
    print("\n=== Decorator-based Shutdown Example ===")
    print("✓ Registered cleanup function with @on_shutdown decorator")
    print("  Function 'cleanup_resources' will run on shutdown with priority 10")


def example_health_check():
    """Example: Health check endpoint information."""
    print("\n=== Health Check Endpoint Example ===")
    print("When webhook server is enabled, health check is available at:")
    print("  GET /healthz")
    print()
    print("Example response:")
    print('''{
  "status": "healthy",
  "checks": {
    "configuration": "ok",
    "agents": "ok",
    "agent_count": 4,
    "broker": "running"
  }
}''')
    print()
    print("Use for Kubernetes probes:")
    print("  livenessProbe:")
    print("    httpGet:")
    print("      path: /healthz")
    print("      port: 5000")
    print("  readinessProbe:")
    print("    httpGet:")
    print("      path: /healthz")
    print("      port: 5000")


def main():
    """Run all examples."""
    print("=" * 60)
    print("Mira Production Features Examples")
    print("=" * 60)
    
    example_secrets_management()
    example_structured_logging()
    example_decorator_logging()
    example_shutdown_handler()
    example_decorator_shutdown()
    example_health_check()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed successfully!")
    print("=" * 60)


if __name__ == '__main__':
    main()
