# TiKòb Deployment Guide

## Overview
This guide covers deploying TiKòb to Heroku with PostgreSQL database, environment configuration, and production best practices.

## Prerequisites
- Heroku account and Heroku CLI installed
- Git repository with TiKòb code
- Production-ready SECRET_KEY

## Deployment Steps

### 1. Prepare Application for Production

#### Update `requirements.txt`
```bash
pip freeze > requirements.txt
```

Required production packages:
- `flask`
- `flask-sqlalchemy`
- `flask-wtf`
- `werkzeug`
- `gunicorn` (production WSGI server)
- `psycopg2-binary` (PostgreSQL adapter)

#### Create `Procfile`
```
web: gunicorn app.app:app --bind 0.0.0.0:$PORT --workers 4 --timeout 120
```

#### Create `runtime.txt`
```
python-3.11.13
```

### 2. Create Heroku Application

```bash
heroku login
heroku create tikob-production
heroku addons:create heroku-postgresql:mini
```

### 3. Configure Environment Variables

```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Set environment variables
heroku config:set SESSION_SECRET=your_generated_secret_key
heroku config:set FLASK_ENV=production
heroku config:set PYTHONUNBUFFERED=1
```

### 4. Database Migration

TiKòb uses SQLAlchemy with auto-create tables. For production:

1. Update `app.py` to use Heroku's DATABASE_URL:
```python
import os
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///tikob.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
```

2. Deploy and run migrations:
```bash
git push heroku main
heroku run python -c "from app.app import app, db; app.app_context().push(); db.create_all()"
```

### 5. Deploy Application

```bash
git add .
git commit -m "Configure for Heroku deployment"
git push heroku main
```

### 6. Verify Deployment

```bash
heroku open
heroku logs --tail
```

## Environment Variables Reference

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `SESSION_SECRET` | Flask session encryption key | Yes | `abc123...` (64 chars) |
| `DATABASE_URL` | PostgreSQL connection string | Auto-set | `postgresql://user:pass@host/db` |
| `FLASK_ENV` | Environment mode | Yes | `production` |
| `MAX_UPLOAD_SIZE` | Max file upload size (bytes) | No | `5242880` (5MB) |

## Database Backup Strategy

### Manual Backup
```bash
heroku pg:backups:capture --app tikob-production
heroku pg:backups:download --app tikob-production
```

### Automatic Backups
```bash
heroku pg:backups:schedule DATABASE_URL --at '02:00 America/New_York' --app tikob-production
```

### Restore from Backup
```bash
heroku pg:backups:restore <backup_name> DATABASE_URL --app tikob-production
```

## Performance Optimization

### Database Connection Pooling
Update `app.py`:
```python
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True
}
```

### CDN for Static Assets
Consider using AWS S3 or Cloudflare CDN for:
- Bootstrap CSS/JS
- Custom static files
- Uploaded receipt images

### Caching Strategy
Add Flask-Caching for:
- Dashboard queries
- Group statistics
- Badge calculations

## Security Checklist

- [x] HTTPS enabled (automatic on Heroku)
- [x] CSRF protection enabled (Flask-WTF)
- [x] Security headers configured
- [x] Password hashing with Werkzeug
- [x] File upload validation
- [x] SQL injection protection (SQLAlchemy ORM)
- [ ] Rate limiting (add Flask-Limiter)
- [ ] Session timeout configuration

## Monitoring & Logging

### View Logs
```bash
heroku logs --tail --app tikob-production
```

### Add Monitoring
```bash
heroku addons:create papertrail
heroku addons:create newrelic:wayne
```

### Error Tracking
Consider integrating:
- Sentry for error tracking
- Datadog for APM
- LogDNA for log management

## Scaling

### Horizontal Scaling
```bash
heroku ps:scale web=2
```

### Vertical Scaling
```bash
heroku ps:resize web=standard-2x
```

### Database Scaling
```bash
heroku addons:create heroku-postgresql:standard-0
```

## Maintenance Mode

```bash
# Enable maintenance mode
heroku maintenance:on

# Run maintenance tasks
heroku run python scripts/cleanup_receipts.py

# Disable maintenance mode
heroku maintenance:off
```

## Rollback Strategy

```bash
# View releases
heroku releases

# Rollback to previous version
heroku rollback v123
```

## Custom Domain Setup

```bash
heroku domains:add www.tikob.com
heroku certs:auto:enable
```

Update DNS:
- Add CNAME record pointing to Heroku DNS target
- Enable SSL/TLS

## Post-Deployment Checklist

1. [ ] All environment variables set
2. [ ] Database migrations run successfully
3. [ ] Admin user created
4. [ ] Test group creation and joining
5. [ ] Test transaction recording
6. [ ] Test file uploads
7. [ ] Verify email notifications (if enabled)
8. [ ] Check error logs
9. [ ] Test backup/restore process
10. [ ] Configure monitoring alerts

## Support & Troubleshooting

### Common Issues

**Issue**: Application crashes on startup
```bash
heroku logs --tail
# Check for missing environment variables or dependency issues
```

**Issue**: Database connection errors
```bash
heroku pg:info
# Verify DATABASE_URL is set correctly
```

**Issue**: File uploads failing
```bash
# Check upload folder permissions and MAX_UPLOAD_SIZE
heroku config
```

### Get Help
- Heroku Status: https://status.heroku.com
- Heroku Support: https://help.heroku.com
- TiKòb Issues: [GitHub repository]

## Cost Estimation

### Hobby Tier (Recommended for MVP)
- Dyno: $7/month
- PostgreSQL Mini: $5/month
- **Total: ~$12/month**

### Production Tier
- Standard-1X Dyno: $25/month
- PostgreSQL Standard-0: $50/month
- Papertrail Logging: $7/month
- **Total: ~$82/month**

## Next Steps

1. Set up continuous deployment from GitHub
2. Configure automated testing in CI/CD
3. Implement rate limiting
4. Add email notification service (SendGrid/Mailgun)
5. Set up staging environment
6. Implement feature flags
