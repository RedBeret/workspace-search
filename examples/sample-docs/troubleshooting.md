# Troubleshooting Guide

Common issues and how to resolve them.

## Performance Problems

### Slow Response Times

If response times are higher than expected:

1. **Check resource usage**: CPU, memory, disk I/O
   ```bash
   top -o cpu
   iostat -x 1
   ```

2. **Profile the application**: Identify hot paths
   ```bash
   python -m cProfile -o profile.out my_script.py
   python -m pstats profile.out
   ```

3. **Check database query performance**: Look for slow queries
   ```sql
   SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;
   ```

4. **Review connection pool settings**: Ensure pool isn't exhausted

### High Memory Usage

Common causes:
- Memory leaks in long-running processes
- Large in-memory caches without eviction
- Unbound query results (missing LIMIT clauses)

## Connection Issues

### Database Connection Refused

1. Verify the database is running: `systemctl status postgresql`
2. Check the connection string (host, port, credentials)
3. Verify firewall rules allow the connection
4. Check connection pool limits — you may have exhausted available connections

### Timeout Errors

Network timeouts usually indicate:
- The target service is overloaded
- Network path has high latency
- The operation is genuinely slow (check your query plan)

Increase timeouts cautiously — they hide root causes. Fix the root cause instead.

## Authentication Failures

### 401 Unauthorized

- Token has expired — refresh it
- Wrong token sent (dev token in production, etc.)
- Token format is wrong (missing "Bearer " prefix)

### 403 Forbidden

- User is authenticated but lacks permission
- RBAC policy hasn't propagated yet
- IP allowlist blocking the request

## Logging and Debugging

### Enable Debug Logging

```bash
LOG_LEVEL=DEBUG python app.py
```

Or in code:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Correlating Logs Across Services

Use a shared request ID passed through headers:
```python
import uuid

request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
logger.info("Handling request", extra={"request_id": request_id})
```

### Reading Stack Traces

Read stack traces bottom-up: the bottom is where the error occurred, the top is the entry point. Your code is usually in the middle.

## Disk Space Issues

```bash
# Find large files
du -sh /* 2>/dev/null | sort -rh | head -20

# Find large log files
find /var/log -name "*.log" -size +100M

# Clear Docker resources
docker system prune -a --volumes
```

## Common Error Messages

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `ECONNREFUSED` | Target service not running | Start the service |
| `Connection pool exhausted` | Too many concurrent requests | Increase pool size or scale horizontally |
| `OOM Killed` | Process exceeded memory limit | Increase limit or fix memory leak |
| `Too many open files` | File descriptor limit hit | Increase ulimit or close handles properly |
| `SSL certificate verify failed` | Expired or self-signed cert | Renew cert or add to trust store |
