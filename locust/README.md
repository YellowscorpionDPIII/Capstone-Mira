# Locust Load Testing for Mira Webhook API

This directory contains load testing scripts for the Mira webhook API, specifically designed to simulate n8n webhook traffic at 1000 requests per minute.

## Overview

The load test simulates realistic n8n workflow patterns including:
- Project plan generation (highest volume)
- Risk assessment
- Status report generation
- Multi-agent orchestration
- Health checks

## Quick Start

### Prerequisites

```bash
pip install locust
```

### Run Load Test

**With Web UI:**
```bash
locust -f load_test.py --host=http://localhost:5000
# Then open http://localhost:8089 in your browser
```

**Headless Mode (1000 req/min target):**
```bash
locust -f load_test.py --host=http://localhost:5000 \
       --users 17 --spawn-rate 5 --run-time 5m --headless
```

**Using Environment Variables:**
```bash
export MIRA_HOST="http://localhost:5000"
export MIRA_WEBHOOK_SECRET="your-webhook-secret"
export MIRA_LOAD_TEST_USERS="17"
export MIRA_LOAD_TEST_SPAWN_RATE="5"
export MIRA_LOAD_TEST_RUNTIME="10m"

python load_test.py
```

## Test Configuration

### Target Performance

- **Request Rate:** 1000 req/min (16.67 req/sec)
- **Concurrent Users:** 17 users
- **Wait Time:** 3.5-4 seconds between requests per user
- **Test Duration:** 5-10 minutes recommended

### Load Distribution

The test uses weighted task distribution:
- `generate_project_plan` (5x): 41.7% of requests
- `assess_project_risks` (3x): 25% of requests
- `generate_status_report` (2x): 16.7% of requests
- `orchestrate_workflow` (1x): 8.3% of requests
- `health_check` (1x): 8.3% of requests

## Advanced Usage

### Custom Load Shape

The script includes a `StepLoadShape` class for gradual load increase:

```python
# Automatically used when running with custom load shape
locust -f load_test.py --host=http://localhost:5000 \
       --load-shape StepLoadShape
```

Load steps:
1. 0-60s: 5 users (warm-up)
2. 60-120s: 10 users (ramp-up)
3. 120-180s: 17 users (target load)
4. 180-480s: 17 users (sustained load)
5. 480-540s: 5 users (cool-down)

### Stress Testing

For stress testing beyond normal load:

```bash
locust -f load_test.py --host=http://localhost:5000 \
       --users 50 --spawn-rate 10 --run-time 10m \
       --headless
```

### Distributed Testing

**Master Node:**
```bash
locust -f load_test.py --host=http://localhost:5000 --master
```

**Worker Nodes:**
```bash
locust -f load_test.py --worker --master-host=<master-ip>
```

## Metrics and Reporting

### Key Metrics

- **Response Time:** Average, min, max response times
- **Requests/sec:** Actual request rate vs target
- **Failure Rate:** Percentage of failed requests
- **Status Codes:** Distribution of HTTP responses

### Performance Targets

- ✅ Average response time < 1000ms
- ✅ Failure rate < 1%
- ✅ Request rate ≥ 15 req/sec (900 req/min)

### Export Results

**HTML Report:**
```bash
locust -f load_test.py --host=http://localhost:5000 \
       --users 17 --spawn-rate 5 --run-time 5m \
       --headless --html=report.html
```

**CSV Export:**
```bash
locust -f load_test.py --host=http://localhost:5000 \
       --users 17 --spawn-rate 5 --run-time 5m \
       --headless --csv=results
```

This creates:
- `results_stats.csv`: Request statistics
- `results_stats_history.csv`: Historical data
- `results_failures.csv`: Failure details

## Authentication

The load test supports HMAC-SHA256 signature authentication:

```bash
export MIRA_WEBHOOK_SECRET="your-webhook-secret"
locust -f load_test.py --host=http://localhost:5000
```

Signatures are automatically generated for each request using the `X-Hub-Signature-256` header.

## Troubleshooting

### High Failure Rate

**Symptoms:** > 1% failure rate

**Solutions:**
- Verify webhook secret matches server configuration
- Check server logs for errors
- Reduce concurrent users
- Increase wait time between requests

### Low Request Rate

**Symptoms:** < 15 req/sec actual rate

**Solutions:**
- Increase number of users
- Decrease wait time between requests
- Check network latency
- Verify server can handle load

### Slow Response Times

**Symptoms:** Average response time > 1000ms

**Solutions:**
- Optimize server configuration
- Scale server resources
- Check database performance
- Profile application code

## Integration with CI/CD

See `.github/workflows/load-test.yml` for automated load testing on pull requests.

## Related Documentation

- [API Key Management](../docs/API_KEY_MANAGEMENT.md)
- [Webhook API Documentation](../docs/API_KEY_MANAGEMENT.md#webhook-api-authentication)
- [n8n Integration](../n8n/README.md)

## Support

For issues or questions, please open an issue on GitHub:
https://github.com/YellowscorpionDPIII/Capstone-Mira/issues
