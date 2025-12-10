"""Example demonstrating metrics usage in Mira platform."""
from mira.utils.metrics import (
    timer, 
    timed,
    record_latency,
    increment_error_counter,
    get_all_metrics,
    get_latency_stats,
    get_error_count,
    reset_metrics
)
from mira.core.base_agent import BaseAgent
from mira.core.message_broker import MessageBroker
import time
import json
from typing import Dict, Any


class DemoAgent(BaseAgent):
    """Demo agent for testing metrics."""
    
    def process(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Process a message."""
        # Simulate some work
        time.sleep(0.1)
        
        if message.get('simulate_error'):
            return self.create_response('error', None, 'Simulated error')
        
        return self.create_response(
            'success',
            {'result': f"Processed {message['type']}"}
        )


def main():
    """Demonstrate metrics collection in Mira."""
    print("=" * 60)
    print("Mira Metrics Collection Example")
    print("=" * 60)
    print()
    
    # Reset metrics to start fresh
    reset_metrics()
    
    # Example 1: Using timer context manager
    print("1. Using timer context manager...")
    with timer('custom_operation'):
        time.sleep(0.2)
    print("   ✓ Timer recorded for 'custom_operation'")
    print()
    
    # Example 2: Using timed decorator
    print("2. Using timed decorator...")
    
    @timed('decorated_function')
    def slow_function():
        time.sleep(0.15)
        return "done"
    
    result = slow_function()
    print(f"   ✓ Function returned: {result}")
    print()
    
    # Example 3: Recording metrics manually
    print("3. Recording metrics manually...")
    record_latency('manual_metric', 0.25)
    increment_error_counter('manual_errors', 1)
    print("   ✓ Manual metrics recorded")
    print()
    
    # Example 4: Using metrics with agents
    print("4. Using metrics with agents...")
    agent = DemoAgent('demo_agent')
    
    # Process successful message
    message1 = {'type': 'test', 'data': {}}
    result1 = agent.process_with_metrics(message1)
    print(f"   ✓ Processed message: {result1['status']}")
    
    # Process message with error
    message2 = {'type': 'test', 'data': {}, 'simulate_error': True}
    result2 = agent.process_with_metrics(message2)
    print(f"   ✓ Processed error message: {result2['status']}")
    print()
    
    # Example 5: Using metrics with message broker
    print("5. Using metrics with message broker...")
    broker = MessageBroker()
    received = []
    
    def handler(msg):
        received.append(msg)
    
    broker.subscribe('test_event', handler)
    broker.start()
    
    broker.publish('test_event', {'value': 'test'})
    time.sleep(0.5)  # Give broker time to process
    
    broker.stop()
    print(f"   ✓ Broker processed {len(received)} messages")
    print()
    
    # Display all metrics
    print("6. Displaying collected metrics...")
    print()
    
    all_metrics = get_all_metrics()
    
    # Display latency metrics
    print("   📊 Latency Metrics:")
    print("   " + "-" * 56)
    if all_metrics['latencies']:
        for metric_name, stats in sorted(all_metrics['latencies'].items()):
            print(f"   {metric_name}:")
            print(f"      Count: {stats['count']}")
            print(f"      Min:   {stats['min']:.4f}s")
            print(f"      Max:   {stats['max']:.4f}s")
            print(f"      Avg:   {stats['avg']:.4f}s")
            print()
    else:
        print("   No latency metrics collected")
        print()
    
    # Display error counters
    print("   ❌ Error Counters:")
    print("   " + "-" * 56)
    if all_metrics['errors']:
        for counter_name, count in sorted(all_metrics['errors'].items()):
            print(f"   {counter_name}: {count}")
        print()
    else:
        print("   No errors recorded")
        print()
    
    # Query specific metrics
    print("7. Querying specific metrics...")
    print()
    
    custom_stats = get_latency_stats('custom_operation')
    print(f"   'custom_operation' latency: {custom_stats['avg']:.4f}s")
    
    agent_errors = get_error_count('agent.demo_agent.errors')
    print(f"   Agent errors: {agent_errors}")
    print()
    
    # Export to JSON
    print("8. Exporting metrics to JSON...")
    metrics_json = json.dumps(all_metrics, indent=2)
    print("   Sample JSON export (first 30 lines):")
    print("   " + "-" * 56)
    for i, line in enumerate(metrics_json.split('\n')[:30]):
        print(f"   {line}")
    if len(metrics_json.split('\n')) > 30:
        print("   ...")
    print()
    
    print("=" * 60)
    print("✅ Metrics collection complete!")
    print("=" * 60)
    print()
    print("💡 Key Features Demonstrated:")
    print("   ✓ Timer context manager for measuring code blocks")
    print("   ✓ Decorator for measuring function execution")
    print("   ✓ Manual metric recording")
    print("   ✓ Automatic metrics for agents")
    print("   ✓ Automatic metrics for message broker")
    print("   ✓ Error counter tracking")
    print("   ✓ Metrics retrieval and export")
    print()
    print("💡 Future Integration:")
    print("   - Ready for Prometheus integration")
    print("   - Pluggable architecture for other monitoring systems")
    print("   - Thread-safe for concurrent operations")
    print()


if __name__ == '__main__':
    main()

