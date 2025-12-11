# Summary: Async Workflow Execution with Timeout Protection

## Overview
This PR enhances the `OrchestratorAgent` class to add timeout protection and prevent hanging agents during workflow execution. The implementation provides robust async workflow execution with comprehensive error handling, detailed logging, and partial progress tracking.

## Changes Made

### Core Implementation (mira/agents/orchestrator_agent.py)
1. **`_run_workflow_steps_async` method**: Executes workflow steps asynchronously using `asyncio.get_running_loop().run_in_executor()` for compatibility with modern asyncio patterns.

2. **`_execute_workflow_async` method**:
   - Wraps workflow execution with `asyncio.wait_for()` for timeout protection (default: 30 seconds)
   - Logs detailed error messages on timeout (workflow type, message type, completed steps)
   - Returns partial progress information when timeouts occur
   - Handles exceptions gracefully with proper error responses

3. **`process_async` method**: Async entry point for message processing with timeout support for workflow messages.

### Testing (mira/tests/test_async_workflow_timeout.py)
Created 15 comprehensive tests covering:
- ✅ Normal workflow completion before timeout
- ✅ Timeout scenarios with partial progress tracking
- ✅ Various timeout durations (0.001s to 1000s)
- ✅ Edge cases (empty workflows, very short timeouts)
- ✅ Concurrent workflow execution
- ✅ Exception handling
- ✅ Non-workflow message processing
- ✅ Invalid message handling

### Documentation (docs/ASYNC_WORKFLOW_TIMEOUT.md)
Comprehensive documentation including:
- Feature overview
- Usage examples (basic, custom timeout, timeout handling)
- API reference with example responses
- Error handling patterns
- Best practices
- Performance considerations
- Future enhancement suggestions

### Example Code (examples/async_workflow_example.py)
Demonstrates:
- Normal workflow execution with default timeout
- Custom timeout configuration
- Timeout scenario handling
- Non-workflow message processing

## Test Results

### All Tests Pass ✅
- **109 tests** in total (including 15 new async tests)
- **0 failures**
- **0 errors**
- All existing tests pass (backward compatibility maintained)

### Security Check ✅
- **CodeQL Analysis**: 0 alerts
- No security vulnerabilities introduced

### Code Quality ✅
- Addressed all code review feedback:
  - Fixed asyncio deprecation warnings (using `asyncio.get_running_loop()`)
  - Used `asyncio.sleep()` instead of `time.sleep()` in async tests
  - Proper error handling and logging

## Key Features

### 1. Timeout Protection
- Default 30-second timeout (configurable)
- Prevents indefinite hanging during workflow execution
- Uses `asyncio.wait_for()` for enforcement

### 2. Detailed Error Logging
On timeout, logs include:
- Workflow type
- Message type  
- List of completed steps
- Total number of completed steps
- Timeout duration

### 3. Partial Progress Reporting
Timeout responses include:
```python
{
    'status': 'timeout',
    'error': 'Workflow execution timed out after 30.0 seconds',
    'partial_progress': {
        'completed_steps': ['generate_plan', 'assess_risks'],
        'total_steps_completed': 2,
        'timeout_seconds': 30.0
    }
}
```

### 4. Backward Compatibility
- All existing synchronous methods remain unchanged
- No breaking changes to existing API
- All existing tests pass without modification

## Usage Example

```python
import asyncio
from mira.agents.orchestrator_agent import OrchestratorAgent

orchestrator = OrchestratorAgent()
# ... register agents ...

message = {
    'type': 'workflow',
    'data': {
        'workflow_type': 'project_initialization',
        'data': {'name': 'My Project', 'goals': ['Goal 1'], 'duration_weeks': 12}
    }
}

# Execute with default 30-second timeout
response = await orchestrator.process_async(message)

# Execute with custom 60-second timeout
response = await orchestrator.process_async(message, timeout=60.0)

# Handle timeout
if response.get('status') == 'timeout':
    print(f"Timeout occurred. Completed {len(response['steps'])} steps.")
    print(f"Partial progress: {response['partial_progress']}")
```

## Benefits

1. **Reliability**: Prevents hanging agents with timeout protection
2. **Observability**: Detailed logging for debugging timeout issues
3. **Resilience**: Graceful handling of timeouts with partial progress
4. **Performance**: Async execution allows concurrent workflows
5. **Flexibility**: Configurable timeout for different workflow complexities
6. **Maintainability**: Comprehensive tests ensure future changes don't break functionality

## Performance Impact

- **Minimal overhead**: Asyncio event loop adds negligible latency
- **Better resource utilization**: Non-blocking execution
- **Concurrent execution**: Multiple workflows can run simultaneously
- **Timeout enforcement**: Prevents resource waste from hanging operations

## Validation

### Manual Testing ✅
- Ran async workflow example successfully
- Verified timeout scenarios work as expected
- Confirmed partial progress tracking
- Tested concurrent execution

### Automated Testing ✅
- All 109 tests pass
- New async tests validate timeout protection
- Existing tests verify backward compatibility

### Security Testing ✅
- CodeQL analysis: 0 alerts
- No vulnerabilities introduced

## Files Changed

1. `mira/agents/orchestrator_agent.py` - Core implementation
2. `mira/tests/test_async_workflow_timeout.py` - Test suite
3. `docs/ASYNC_WORKFLOW_TIMEOUT.md` - Documentation
4. `examples/async_workflow_example.py` - Usage examples

## Conclusion

This PR successfully implements timeout protection for async workflow execution as specified in the requirements. The implementation:
- ✅ Uses `asyncio.wait_for` with 30-second default timeout
- ✅ Logs detailed error messages on timeout
- ✅ Returns partial progress information
- ✅ Includes comprehensive tests for various scenarios
- ✅ Maintains backward compatibility
- ✅ Passes all security checks
- ✅ Includes thorough documentation and examples

The enhancement significantly improves the reliability and observability of workflow execution in the Mira platform.
