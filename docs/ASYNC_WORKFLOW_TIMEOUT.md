# Async Workflow Execution with Timeout Protection

## Overview

The `OrchestratorAgent` now supports asynchronous workflow execution with built-in timeout protection to prevent hanging agents during workflow execution. This enhancement ensures that workflows complete within a specified time limit and provides detailed error logging and partial progress tracking when timeouts occur.

## Recent Enhancements

### Enhanced Timeout Handling
- **Sub-second timeout support**: Timeouts less than 1 second are explicitly supported with warning logs
- **Negative timeout validation**: Negative timeout values now raise a ValueError
- **Graceful task cancellation**: Child tasks are properly canceled when timeouts occur to prevent resource leaks

### Improved Partial Progress Extraction
- **Robust error handling**: Parsing failures during step extraction are logged with detailed context
- **Guaranteed list type**: `partial_progress.completed_steps` always returns a list, even on errors
- **Fallback handling**: Malformed step data results in safe fallback values

### Structured Logging
- **Event-based logging**: Timeout and error events use structured logging with extra fields
- **Key fields included**: `workflow_type`, `message_type`, `timeout_seconds`, `completed_steps_count`, `event_type`
- **Sensitive data masking**: Full message contents and payload details are excluded from logs
- **Step names only**: Only step identifiers are logged, not step data

### API and Behavior Clarity
- **Explicit documentation**: All possible response structures are documented (success, timeout, error)
- **Field structure**: Clear definition of `status` and `partial_progress` fields
- **Response normalization**: Consistent structure between `steps` and `partial_progress.completed_steps`

### Backward Compatibility
- **Sync path unaffected**: Synchronous workflow execution (`process()`) works identically as before
- **Opt-in semantics**: Timeout protection only applies when using `process_async()`
- **Shared helpers safe**: `_run_workflow_steps_async()` can be used by both sync and async paths

## Features

### 1. Asynchronous Workflow Execution
- Executes workflow steps asynchronously using Python's `asyncio` library
- Non-blocking execution allows for better resource utilization
- Supports concurrent workflow execution

### 2. Timeout Protection
- Default timeout of 30 seconds (configurable)
- Uses `asyncio.wait_for()` to enforce timeout limits
- Prevents indefinite hanging during workflow execution

### 3. Detailed Error Logging
When a timeout occurs, the system logs:
- Workflow type
- Message type
- List of completed steps
- Total number of completed steps
- Timeout duration

### 4. Partial Progress Reporting
If a workflow times out, the response includes:
- List of completed steps
- Total number of steps completed
- Timeout duration in seconds
- Results from completed steps

## Usage

### Basic Usage

```python
import asyncio
from mira.agents.orchestrator_agent import OrchestratorAgent
from mira.agents.project_plan_agent import ProjectPlanAgent
from mira.agents.risk_assessment_agent import RiskAssessmentAgent
from mira.agents.status_reporter_agent import StatusReporterAgent

# Initialize orchestrator and register agents
orchestrator = OrchestratorAgent()
orchestrator.register_agent(ProjectPlanAgent())
orchestrator.register_agent(RiskAssessmentAgent())
orchestrator.register_agent(StatusReporterAgent())

# Create workflow message
message = {
    'type': 'workflow',
    'data': {
        'workflow_type': 'project_initialization',
        'data': {
            'name': 'My Project',
            'goals': ['Goal 1', 'Goal 2'],
            'duration_weeks': 12
        }
    }
}

# Execute workflow asynchronously with default 30-second timeout
async def run_workflow():
    response = await orchestrator.process_async(message)
    return response

response = asyncio.run(run_workflow())
```

### Custom Timeout

```python
# Execute workflow with custom 60-second timeout
async def run_workflow():
    response = await orchestrator.process_async(message, timeout=60.0)
    return response

response = asyncio.run(run_workflow())
```

### Handling Timeouts

```python
async def run_workflow_with_timeout_handling():
    response = await orchestrator.process_async(message, timeout=30.0)
    
    if response.get('status') == 'timeout':
        print("Workflow timed out!")
        print(f"Error: {response['error']}")
        
        # Access partial progress
        partial = response.get('partial_progress', {})
        completed_steps = partial.get('completed_steps', [])
        print(f"Completed steps: {completed_steps}")
        print(f"Total completed: {partial.get('total_steps_completed', 0)}")
    else:
        print("Workflow completed successfully!")
        for step in response['steps']:
            print(f"Step: {step['step']} - Status: {step['status']}")

asyncio.run(run_workflow_with_timeout_handling())
```

### Non-Workflow Messages

The `process_async` method also supports non-workflow messages:

```python
# Process regular message asynchronously
plan_message = {
    'type': 'generate_plan',
    'data': {
        'name': 'Test Project',
        'goals': ['Goal 1'],
        'duration_weeks': 8
    }
}

async def run_plan():
    response = await orchestrator.process_async(plan_message)
    return response

response = asyncio.run(run_plan())
```

## API Reference

### `OrchestratorAgent.process_async(message, timeout=30.0)`

Process a message asynchronously with timeout protection.

**Parameters:**
- `message` (Dict[str, Any]): Message to process containing 'type' and 'data' fields
- `timeout` (float, optional): Timeout in seconds. Default: 30.0
  - Sub-second timeouts (< 1.0s) are supported but may cause immediate timeout for complex workflows
  - Negative timeouts will raise a ValueError

**Returns:**
- Dict[str, Any]: Response from processing the message

**Example Response (Success - No Timeout):**
```python
{
    'workflow_type': 'project_initialization',
    'steps': [
        {
            'step': 'generate_plan',
            'status': 'success',
            'result': {...}
        },
        {
            'step': 'assess_risks',
            'status': 'success',
            'result': {...}
        },
        {
            'step': 'generate_report',
            'status': 'success',
            'result': {...}
        }
    ]
}
```

**Example Response (Timeout):**
```python
{
    'workflow_type': 'project_initialization',
    'status': 'timeout',
    'error': 'Workflow execution timed out after 30.0 seconds',
    'steps': [
        {
            'step': 'generate_plan',
            'status': 'success',
            'result': {...}
        }
    ],
    'partial_progress': {
        'completed_steps': ['generate_plan'],  # Guaranteed to be a list
        'total_steps_completed': 1,
        'timeout_seconds': 30.0
    }
}
```

**Example Response (Error/Exception):**
```python
{
    'workflow_type': 'project_initialization',
    'status': 'error',
    'error': 'Error message describing what went wrong',
    'steps': [...]  # Steps completed before error (may be empty)
}
```

### `OrchestratorAgent._execute_workflow_async(data, timeout=30.0)`

Execute a multi-step workflow asynchronously with timeout protection.

**Parameters:**
- `data` (Dict[str, Any]): Workflow definition
- `timeout` (float, optional): Timeout in seconds. Default: 30.0

**Returns:**
- Dict[str, Any]: Workflow execution results

### `OrchestratorAgent._run_workflow_steps_async(workflow_type, workflow_data, results)`

Execute workflow steps asynchronously.

**Parameters:**
- `workflow_type` (str): Type of workflow to execute
- `workflow_data` (Dict[str, Any]): Data for workflow execution
- `results` (Dict[str, Any]): Results dictionary to populate

**Returns:**
- Dict[str, Any]: Updated results dictionary

## Error Handling

### Timeout Errors
When a timeout occurs, the following happens:

1. **Task Cancellation**: The workflow task is gracefully canceled to prevent resource leaks
   - `task.cancel()` is called on the running workflow task
   - Awaits the task to handle `CancelledError` properly

2. **Structured Logging**: A detailed error message is logged with:
   - `workflow_type`: The type of workflow that timed out
   - `message_type`: Always 'workflow' for workflow messages
   - `timeout_seconds`: The timeout duration that was exceeded
   - `completed_steps_count`: Number of steps completed before timeout
   - `completed_steps`: List of step names (identifiers only, no data)
   - `event_type`: Set to 'workflow_timeout'

3. **Response Structure**: The response includes:
   - `status`: 'timeout'
   - `error`: Descriptive error message
   - `partial_progress`: Object with completion details
     - `completed_steps`: List of completed step names (guaranteed to be a list)
     - `total_steps_completed`: Count of completed steps
     - `timeout_seconds`: The timeout value used
   - `steps`: Array of completed steps with their results

### Other Exceptions
General exceptions are caught and handled gracefully:

1. **Task Cancellation**: Similar cleanup as timeout errors
2. **Structured Logging**: Error logged with:
   - `workflow_type`: The type of workflow
   - `message_type`: 'workflow'
   - `error_type`: Exception class name
   - `exception`: String representation of the exception
   - `event_type`: Set to 'workflow_error'
3. **Response Structure**: 
   - `status`: 'error'
   - `error`: Exception message
   - `steps`: Steps completed before error (may be empty)
   - **Note**: No `partial_progress` field for errors (distinct from timeouts)

### Partial Progress Extraction Errors
If errors occur while extracting completed steps:

1. **Invalid steps format**: Logged with `error_type: 'invalid_steps_format'`
2. **Invalid step format**: Logged with `error_type: 'invalid_step_format'`
3. **Extraction failure**: Logged with `error_type: 'step_extraction_failed'`
4. **Fallback**: Returns empty list `[]` to ensure consistent type

### Sub-second Timeout Warnings
When timeout is less than 1 second:

1. **Warning logged** with:
   - `workflow_type`: The workflow type
   - `timeout_seconds`: The sub-second timeout value
   - `warning_type`: Set to 'sub_second_timeout'
2. **Workflow continues**: Not an error, just a warning about potential immediate timeout

## Best Practices

### 1. Choose Appropriate Timeouts
- **Short workflows** (1-3 steps): 10-30 seconds
- **Medium workflows** (4-6 steps): 30-60 seconds
- **Long workflows** (7+ steps): 60-120 seconds

### 2. Handle Timeout Responses
Always check for timeout status and handle partial progress:

```python
if response.get('status') == 'timeout':
    # Log the partial progress
    logger.warning(f"Workflow timed out with {len(response['steps'])} completed steps")
    # Potentially retry with longer timeout or resume from partial progress
```

### 3. Monitor Performance
Use the logging output to identify slow workflow steps:

```python
# Check logs for patterns like:
# "Workflow timeout after 30s: workflow_type='project_initialization', 
#  message_type='workflow', completed_steps=['generate_plan'], total_completed=1"
```

### 4. Concurrent Execution
The async design allows multiple workflows to run concurrently:

```python
async def run_multiple_workflows():
    tasks = [
        orchestrator.process_async(message1, timeout=30.0),
        orchestrator.process_async(message2, timeout=30.0),
        orchestrator.process_async(message3, timeout=30.0)
    ]
    results = await asyncio.gather(*tasks)
    return results

results = asyncio.run(run_multiple_workflows())
```

## Testing

The implementation includes comprehensive test coverage:

- Normal workflow completion
- Timeout scenarios
- Various timeout durations
- Edge cases (empty workflows, very short timeouts)
- Concurrent execution
- Exception handling
- Partial progress tracking

Run tests with:

```bash
python -m unittest mira.tests.test_async_workflow_timeout
```

## Backward Compatibility

The new async methods do not affect existing synchronous workflow execution:
- `process()` method remains unchanged
- `_execute_workflow()` method remains unchanged
- All existing tests pass without modification

## Examples

See `examples/async_workflow_example.py` for comprehensive usage examples demonstrating:
- Normal workflow execution with default timeout
- Custom timeout configuration
- Timeout scenario handling
- Non-workflow message processing

Run the example:

```bash
python examples/async_workflow_example.py
```

## Performance Considerations

### Benefits
- **Non-blocking**: Async execution doesn't block the event loop
- **Concurrent**: Multiple workflows can run simultaneously
- **Timeout protection**: Prevents indefinite hangs
- **Resource efficient**: Better utilization of system resources

### Overhead
- Minimal overhead from asyncio event loop
- Executor thread pool for synchronous agent methods
- Negligible impact on single workflow execution

## Future Enhancements

Potential improvements for future versions:
- Per-step timeout configuration
- Retry logic for failed steps
- Workflow resumption from partial progress
- Progress callbacks during execution
- Distributed workflow execution
- Dynamic timeout adjustment based on step complexity
