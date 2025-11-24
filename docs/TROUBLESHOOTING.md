# Troubleshooting Guide

Common issues and their solutions for the multi-instance Twilio responder system.

## Table of Contents
- [Call Failures](#call-failures)
- [Deployment Issues](#deployment-issues)
- [Connectivity Issues](#connectivity-issues)
- [Authentication Issues](#authentication-issues)
- [Branch Status Issues](#branch-status-issues)
- [Notification Issues](#notification-issues)
- [Performance Issues](#performance-issues)

---

## Call Failures

For issues with calls not initiating, transfers failing, or customers hearing errors, see the dedicated guide:

**📞 [Call Failures Troubleshooting Guide](CALL_FAILURES_TROUBLESHOOTING.md)**

This covers:
- Warm Transfer / Queue Update issues
- Silent failures in automated calls
- Step-by-step debugging procedures
- Common error messages and solutions

Also see:
- [features/DEBUGGING_CALLS.md](features/DEBUGGING_CALLS.md) - Quick debugging guide

---

## Deployment Issues

### Docker Containers Not Starting

**Symptoms:**
- Containers exit immediately
- `docker ps` shows no running containers
- Error messages in logs

**Solutions:**

1. **Check logs for specific errors:**
```bash
docker-compose -f docker-compose.multi.yml logs
```

2. **Verify environment variables:**
```bash
# Check if .env file exists and has values
cat .env | grep -v "^#" | grep "="
```

3. **Test individual container:**
```bash
# Start just one service
docker-compose -f docker-compose.multi.yml up twilio-app-tuc
```

4. **Check Docker resources:**
```bash
docker system df
docker system prune  # If needed
```

### Port Conflicts

**Symptoms:**
- "Port already in use" errors
- Containers fail to bind to ports

**Solutions:**

1. **Check what's using the port:**
```bash
lsof -i :5000
# or
netstat -tulpn | grep 5000
```

2. **Change ports in docker-compose.multi.yml:**
```yaml
ports:
  - "5001:5000"  # Change host port
```

### Build Failures

**Symptoms:**
- "Build failed" messages
- Dependency installation errors

**Solutions:**

1. **Rebuild with no cache:**
```bash
docker-compose -f docker-compose.multi.yml build --no-cache
```

2. **Check requirements.txt:**
```bash
# Test locally
pip install -r requirements.txt
```

3. **Update Docker:**
```bash
docker --version  # Should be 20.10+
```

---

## Connectivity Issues

### Cannot Access Dashboard

**Symptoms:**
- Browser shows "Can't reach this page"
- Connection timeout errors
- 502 Bad Gateway

**Solutions:**

1. **Verify containers are running:**
```bash
docker ps | grep twilio_responder
```

2. **Check Cloudflare tunnel:**
```bash
docker logs twilio_responder_cloudflared
```

3. **Test local access:**
```bash
# From the host machine
curl http://localhost:5000/api/status
```

4. **Check DNS resolution:**
```bash
nslookup axiom-emergencies.com
dig axiom-emergencies.com
```

5. **Verify Cloudflare tunnel configuration:**
- Go to Cloudflare Dashboard → Zero Trust → Tunnels
- Ensure tunnel is "Healthy"
- Check public hostname configurations

### Branch Shows Offline

**Symptoms:**
- Branch card shows "Offline" status
- Cannot connect to branch URL
- Red status indicator

**Solutions:**

1. **Check branch container:**
```bash
docker ps | grep twilio_responder_tuc
docker logs twilio_responder_tuc --tail 50
```

2. **Verify network connectivity:**
```bash
# From admin container
docker exec twilio_responder_admin ping -c 3 twilio_responder_tuc
```

3. **Test branch endpoint:**
```bash
# From admin container
docker exec twilio_responder_admin curl http://twilio-app-tuc:5000/api/status
```

4. **Check environment variables:**
```bash
docker exec twilio_responder_tuc env | grep TWILIO
```

### Network Issues Between Containers

**Symptoms:**
- Admin dashboard can't connect to branches
- "Connection refused" errors
- Timeout errors

**Solutions:**

1. **Verify all containers are on same network:**
```bash
docker network inspect twilio-net
```

2. **Restart network:**
```bash
docker-compose -f docker-compose.multi.yml down
docker network rm twilio-net
docker-compose -f docker-compose.multi.yml up -d
```

3. **Check container DNS resolution:**
```bash
docker exec twilio_responder_admin nslookup twilio-app-tuc
```

---

## Authentication Issues

### Cannot Login to Admin Dashboard

**Symptoms:**
- "Invalid username or password"
- Login form reappears
- Session expires immediately

**Solutions:**

1. **Verify credentials:**
- Default username: `axiomadmin`
- Default password: `Dannyle44!`

2. **Check database:**
```bash
# Check if database exists
docker exec twilio_responder_admin ls -la /app/data/

# Reset database (creates new with defaults)
docker exec twilio_responder_admin rm /app/data/admin.db
docker restart twilio_responder_admin
```

3. **Clear browser cache:**
- Clear cookies for axiom-emergencies.com
- Try incognito/private window

4. **Check Flask secret key:**
```bash
docker exec twilio_responder_admin env | grep FLASK_SECRET_KEY
```

### Session Expires Too Quickly

**Symptoms:**
- Logged out after a few minutes
- Have to login repeatedly

**Solutions:**

1. **Check session configuration in app.py:**
```python
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
```

2. **Set session to permanent on login:**
```python
session.permanent = True
```

3. **Check browser settings:**
- Disable "Clear cookies on exit"
- Allow cookies for the domain

### Permission Denied Errors

**Symptoms:**
- "Permission denied" messages
- Cannot access certain branches
- Actions fail silently

**Solutions:**

1. **Check user permissions:**
```bash
# View user in database
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "SELECT * FROM users WHERE username='youruser';"
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "SELECT * FROM user_permissions WHERE user_id=X;"
```

2. **Grant permissions via admin account:**
- Login as admin
- Go to Users page
- Edit user permissions

3. **Check if user is admin:**
```bash
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "SELECT username, is_admin FROM users;"
```

---

## Branch Status Issues

### Branch Stuck in "Disabled" State

**Symptoms:**
- Cannot enable branch
- Branch remains disabled after clicking enable
- Emergency calls not processing

**Solutions:**

1. **Check branch status in database:**
```bash
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "SELECT * FROM branch_status;"
```

2. **Manually enable in database:**
```bash
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "UPDATE branch_status SET is_enabled=1 WHERE branch='tuc';"
```

3. **Clear branch state:**
```bash
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "UPDATE branch_status SET is_enabled=1, disabled_at=NULL, disabled_by=NULL WHERE branch='tuc';"
docker restart twilio_responder_admin
```

### Status Not Updating

**Symptoms:**
- Dashboard shows old status
- Auto-refresh not working
- Manual refresh doesn't help

**Solutions:**

1. **Check JavaScript console:**
- Open browser dev tools (F12)
- Look for errors in console
- Check network tab for failed requests

2. **Verify API endpoint:**
```bash
curl https://axiom-emergencies.com/api/branch/tuc/status
```

3. **Check branch is responding:**
```bash
docker exec twilio-app-tuc curl http://localhost:5000/api/status
```

4. **Restart admin dashboard:**
```bash
docker restart twilio_responder_admin
```

---

## Notification Issues

### SMS Notifications Not Sending

**Symptoms:**
- No SMS received when disabling branch
- "SMS notification not configured" in logs
- Twilio errors

**Solutions:**

1. **Verify Twilio credentials:**
```bash
docker exec twilio_responder_admin env | grep TWILIO
```

2. **Test Twilio account:**
```bash
# Use Twilio CLI or dashboard to send test SMS
```

3. **Check phone number format:**
- Must include country code: `+18017104034`
- No spaces or special characters

4. **Verify Twilio account status:**
- Check account balance
- Verify phone number is active
- Check SMS capabilities

5. **Check logs for errors:**
```bash
docker logs twilio_responder_admin | grep -i sms
```

### Wrong Phone Number Receiving Notifications

**Symptoms:**
- Notifications going to wrong number
- Multiple notifications
- No control over recipient

**Solutions:**

1. **Check NOTIFICATION_PHONE in docker-compose:**
```yaml
- NOTIFICATION_PHONE=+18017104034
```

2. **Update and redeploy:**
```bash
docker-compose -f docker-compose.multi.yml down
# Edit docker-compose.multi.yml
docker-compose -f docker-compose.multi.yml up -d
```

---

## Performance Issues

### Slow Dashboard Loading

**Symptoms:**
- Dashboard takes long to load
- Status checks timeout
- UI feels sluggish

**Solutions:**

1. **Check container resources:**
```bash
docker stats
```

2. **Increase container resources:**
```yaml
services:
  admin-dashboard:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
```

3. **Check network latency:**
```bash
docker exec twilio_responder_admin ping -c 10 twilio-app-tuc
```

4. **Reduce auto-refresh frequency:**
- Edit `admin-dashboard/static/js/dashboard.js`
- Change interval from 30000 to 60000 (1 minute)

### High CPU Usage

**Symptoms:**
- Docker containers using high CPU
- Server becomes unresponsive
- Other services affected

**Solutions:**

1. **Identify problematic container:**
```bash
docker stats --no-stream
```

2. **Check logs for errors:**
```bash
docker logs twilio_responder_<container> --tail 100
```

3. **Limit CPU usage:**
```yaml
services:
  admin-dashboard:
    deploy:
      resources:
        limits:
          cpus: '0.5'
```

4. **Restart container:**
```bash
docker restart twilio_responder_<container>
```

### Database Growing Too Large

**Symptoms:**
- Slow queries
- Database file is large
- Disk space issues

**Solutions:**

1. **Check database size:**
```bash
docker exec twilio_responder_admin ls -lh /app/data/admin.db
```

2. **Vacuum database:**
```bash
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "VACUUM;"
```

3. **Clean old data:**
```bash
# Delete old branch status checks (keep last 1000)
docker exec twilio_responder_admin sqlite3 /app/data/admin.db "DELETE FROM branch_status WHERE rowid NOT IN (SELECT rowid FROM branch_status ORDER BY last_check DESC LIMIT 1000);"
```

---

## Getting Help

If these solutions don't resolve your issue:

1. **Collect diagnostic information:**
```bash
# Save all logs
docker-compose -f docker-compose.multi.yml logs > diagnostic.log

# Save environment info
docker-compose -f docker-compose.multi.yml config > config.yaml

# Save container status
docker ps -a > containers.txt
docker stats --no-stream > stats.txt
```

2. **Check container health:**
```bash
docker inspect twilio_responder_admin | grep -A 10 Health
```

3. **Review documentation:**
- [deployment/DEPLOYMENT.md](deployment/DEPLOYMENT.md)
- [../QUICKSTART.md](../QUICKSTART.md)
- [../admin-dashboard/README.md](../admin-dashboard/README.md)

4. **Common command reference:**
```bash
# View all container logs
docker-compose -f docker-compose.multi.yml logs -f

# Restart everything
docker-compose -f docker-compose.multi.yml restart

# Full reset (WARNING: loses data)
docker-compose -f docker-compose.multi.yml down -v
docker-compose -f docker-compose.multi.yml up -d

# Backup before reset
docker cp twilio_responder_admin:/app/data/admin.db ./backup.db
```
