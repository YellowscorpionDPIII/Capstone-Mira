# Production Deployment Guide

## Quick Start with Docker Compose

The fastest way to get Mira API Key Management running in production:

```bash
# Clone the repository
git clone https://github.com/YellowscorpionDPIII/Capstone-Mira.git
cd Capstone-Mira

# Create configuration
cp config.example.json config/config.json
# Edit config/config.json with your settings

# Start services
docker-compose up -d

# Check health
curl http://localhost:5000/health

# Access Swagger documentation
open http://localhost:5000/swagger/
```

## Docker Compose Profiles

Different profiles for different environments:

### Development
```bash
docker-compose --profile dev up -d
```
Includes: App, Redis, Redis Commander (UI at http://localhost:8081)

### Staging
```bash
docker-compose --profile staging up -d  
```
Includes: App, Redis, Redis Commander

### Production
```bash
docker-compose --profile production up -d
```
Includes: App, Redis, Nginx reverse proxy

### Monitoring
```bash
docker-compose --profile monitoring up -d
```
Includes: App, Redis, Prometheus (http://localhost:9090), Grafana (http://localhost:3000)

## Environment Variables

Configure via environment variables or `.env` file:

```bash
# Application
FLASK_ENV=production
FLASK_APP=mira.app
LOG_LEVEL=INFO

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=          # Optional

# API Key Settings
API_KEY_DEFAULT_EXPIRY_DAYS=90
API_KEY_ROTATION_GRACE_MINUTES=60

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_STORAGE=redis://redis:6379/1

# Security
CORS_ENABLED=true
CORS_ORIGINS=*           # Configure appropriately
SECRET_KEY=              # Generate strong secret

# Monitoring
ENABLE_PROMETHEUS=false
PROMETHEUS_PORT=9090
```

## Production Checklist

### Before Deployment

- [ ] Generate strong `SECRET_KEY`
- [ ] Configure appropriate `CORS_ORIGINS`
- [ ] Set up SSL/TLS certificates for Nginx
- [ ] Configure Redis password
- [ ] Set up log aggregation
- [ ] Configure backup strategy for Redis data
- [ ] Set up monitoring alerts
- [ ] Review and adjust rate limits per role
- [ ] Configure firewall rules

### Security

```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Test security headers
curl -I https://your-domain.com/health

# Expected headers:
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
```

### Performance Tuning

#### Redis Configuration
```bash
# Increase Redis max memory if needed
docker-compose exec redis redis-cli CONFIG SET maxmemory 512mb
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### Application Workers
```bash
# For high traffic, run multiple workers
docker-compose up -d --scale mira-app=3
```

## Monitoring

### Prometheus Metrics

Access at `http://localhost:9090`

Key metrics to monitor:
- API request rate
- API error rate  
- Cache hit/miss ratio
- Key generation rate
- Key validation latency
- Rate limit rejections

### Grafana Dashboards

Access at `http://localhost:3000` (default: admin/admin)

Pre-configured dashboards:
- API Overview
- Cache Performance
- Security Events
- Rate Limiting

### Health Checks

```bash
# Application health
curl http://localhost:5000/health

# Redis health
docker-compose exec redis redis-cli ping

# Detailed health with auth
curl -H "Authorization: Bearer <admin-key>" \
  http://localhost:5000/api/keys/stats/cache
```

## Backup and Recovery

### Redis Data Backup

```bash
# Manual backup
docker-compose exec redis redis-cli BGSAVE

# Copy backup file
docker cp mira-redis:/data/dump.rdb ./backup/

# Restore from backup
docker cp ./backup/dump.rdb mira-redis:/data/
docker-compose restart redis
```

### Configuration Backup

```bash
# Backup all configuration
tar -czf mira-backup-$(date +%Y%m%d).tar.gz \
  config/ \
  docker-compose.yml \
  .env \
  nginx/
```

## Scaling

### Horizontal Scaling

```bash
# Use Redis for rate limiting (required for multi-instance)
RATE_LIMIT_STORAGE=redis://redis:6379/1

# Scale application instances
docker-compose up -d --scale mira-app=5

# Use Nginx for load balancing
docker-compose --profile production up -d
```

### Nginx Load Balancer Config

See `nginx/nginx.conf` for load balancer configuration.

## Load Testing

### Run Load Tests

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py \
  --host=http://localhost:5000 \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --headless

# With web UI
locust -f tests/load/locustfile.py --host=http://localhost:5000
# Open http://localhost:8089
```

### Performance Targets

- P50 latency: < 50ms
- P95 latency: < 200ms
- P99 latency: < 500ms
- Throughput: > 1000 req/s per instance
- Cache hit rate: > 80%

## Troubleshooting

### Common Issues

#### Redis Connection Failed
```bash
# Check Redis is running
docker-compose ps redis

# Check Redis logs
docker-compose logs redis

# Test connection
docker-compose exec mira-app redis-cli -h redis ping
```

#### Rate Limit Issues
```bash
# Check rate limit storage
curl -H "Authorization: Bearer <admin-key>" \
  http://localhost:5000/api/keys/stats/cache

# Reset rate limits (dev only!)
docker-compose exec redis redis-cli FLUSHDB
```

#### High Memory Usage
```bash
# Check Redis memory
docker-compose exec redis redis-cli INFO memory

# Check application memory
docker stats mira-app

# Adjust Redis maxmemory
docker-compose exec redis redis-cli CONFIG SET maxmemory 256mb
```

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG docker-compose up

# Access container
docker-compose exec mira-app /bin/bash

# View logs
docker-compose logs -f mira-app
```

## Zero-Downtime Deployment

### Rolling Update

```bash
# Pull latest image
docker-compose pull mira-app

# Update one instance at a time
docker-compose up -d --no-deps --scale mira-app=2 mira-app
sleep 30
docker-compose up -d --no-deps --scale mira-app=1 mira-app
```

### Key Rotation

```bash
# Rotate key with 60-minute grace period
curl -X POST http://localhost:5000/api/keys/<key-id>/rotate \
  -H "Authorization: Bearer <admin-key>" \
  -H "Content-Type: application/json"

# Update client systems with new key within grace period
# Old key remains valid for 60 minutes

# Verify both keys work
curl -H "Authorization: Bearer <old-key>" http://localhost:5000/health
curl -H "Authorization: Bearer <new-key>" http://localhost:5000/health
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/YellowscorpionDPIII/Capstone-Mira/issues
- Documentation: See `docs/API_KEY_MANAGEMENT.md`
