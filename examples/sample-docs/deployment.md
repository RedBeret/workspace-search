# Deployment Guide

This document covers deployment strategies for production services.

## Stateful vs Stateless Services

When deploying services, the first distinction is whether the service maintains state:

- **Stateless services** can be scaled horizontally with simple load balancers. Each request is independent.
- **Stateful services** require careful orchestration. Examples include databases, message queues, and session stores.

## Rolling Deployments

Rolling deployments update instances incrementally without downtime.

### How It Works

1. Take a fraction of instances out of rotation
2. Update them to the new version
3. Run health checks
4. Return them to rotation
5. Repeat until all instances are updated

### When to Use

Rolling deployments work well when:
- The new version is backward-compatible with the old one
- You can tolerate briefly running multiple versions simultaneously
- You want zero-downtime with minimal infrastructure overhead

### Risks

- Mixed-version state can cause subtle bugs
- Rollback requires another rolling update
- Not suitable if the database schema changes break the old version

## Blue-Green Deployments

Maintain two identical environments — blue (current) and green (next).

### How It Works

1. Deploy new version to the idle environment (green)
2. Run tests against green
3. Switch the load balancer to point to green
4. Blue becomes the idle environment for the next deployment

### Advantages

- Instant rollback — flip the load balancer back
- No mixed-version traffic
- Full testing before any production traffic hits the new version

### Challenges

- Requires double the infrastructure during deployment
- Database migrations must handle both versions simultaneously

## Canary Deployments

Route a small percentage of traffic to the new version before full rollout.

### Use Case

Canary is ideal when:
- You want real user feedback before full rollout
- The risk of a bug is high but measurable
- You have good observability to detect issues quickly

## Database Migration Strategies

### Expand-Contract Pattern

For safe schema changes:

1. **Expand**: Add new column (nullable, no breaking change)
2. **Migrate**: Backfill existing rows
3. **Contract**: Remove old column once all code uses the new one

### Zero-Downtime Migrations

- Never rename columns — add new, copy data, drop old
- Never add NOT NULL without a default
- Test migrations on a replica before production

## Health Checks and Readiness Probes

Every service should implement:

- **Liveness probe**: "Am I alive?" — if this fails, restart the container
- **Readiness probe**: "Am I ready to serve traffic?" — if this fails, remove from load balancer

```python
@app.get("/health/live")
async def liveness():
    return {"status": "ok"}

@app.get("/health/ready")
async def readiness():
    # Check database connectivity
    try:
        db.execute("SELECT 1")
        return {"status": "ready"}
    except Exception:
        return JSONResponse({"status": "not ready"}, status_code=503)
```
