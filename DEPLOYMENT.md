# SacredWork (ClairBook) Deployment Runbook

## Pre-Launch Checklist

### Environment & Secrets
- [ ] Create `.env` file with all required variables (see `.env.example`)
- [ ] Generate a new `DJANGO_SECRET_KEY` (never reuse development key)
- [ ] Set `DEBUG=False` for production
- [ ] Set `ALLOWED_HOSTS` to your domain(s)
- [ ] Configure `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` for SMTP
- [ ] Set `DEFAULT_FROM_EMAIL` to official support email
- [ ] Set `SITE_URL` to your production domain (e.g., https://clairbook.app)
- [ ] Configure `ANALYTICS_GA4_MEASUREMENT_ID` or `ANALYTICS_PLAUSIBLE_DOMAIN` if needed

### Database & Backups
- [ ] Set up PostgreSQL database (recommended over SQLite for production)
- [ ] Configure automated daily backups to S3 or cloud storage
- [ ] Test backup restoration process
- [ ] Set `DATABASE_URL` in `.env` if using external database

### Security Hardening
- [ ] CORS headers configured for your frontend domain
- [ ] SSL/TLS certificate installed (Let's Encrypt recommended)
- [ ] SECURE_SSL_REDIRECT, HSTS, security cookies enabled (automatic when DEBUG=False)
- [ ] Firewall rules restrict admin access (`/admin/`) to known IPs
- [ ] SMTP credentials not hardcoded anywhere

### Static Files & Media
- [ ] Run `python manage.py collectstatic --noinput` before deployment
- [ ] Configure CDN (CloudFront, Cloudflare) if needed for static files
- [ ] S3 bucket configured for media file uploads (optional but recommended)

### Application Setup
- [ ] Run `python manage.py migrate` to create database schema
- [ ] Seed initial data (categories, admin users) with `python _seed_admin.py`
- [ ] Test email functionality with test to production email endpoint
- [ ] Verify Sentry or error monitoring is connected

---

## Deployment Procedures

### Heroku Deployment (Recommended for MVP)

#### Initial Setup
```bash
heroku apps:create clairbook-mvp
heroku git:remote -a clairbook-mvp
heroku stack:set heroku-22  # Use more modern stack
heroku buildpacks:add heroku/python
heroku buildpacks:add heroku/nodejs  # If using Tailwind CSS or JS build
```

#### Environment Variables
```bash
heroku config:set DJANGO_SECRET_KEY=<your-generated-key>
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS=clairbook-mvp.herokuapp.com,clairbook.app
heroku config:set EMAIL_HOST=smtp.mailgun.org
heroku config:set EMAIL_HOST_USER=postmaster@mg.your-domain.com
heroku config:set EMAIL_HOST_PASSWORD=<mailgun-smtp-password>
heroku config:set DEFAULT_FROM_EMAIL="clairbook <hello@clairbook.com>"
heroku config:set SITE_URL=https://clairbook.app
```

#### Add PostgreSQL Database
```bash
heroku addons:create heroku-postgresql:standard-0
# Wait for provisioning (~10 minutes)
```

#### Deploy
```bash
git push heroku main    # Replace 'main' with your main branch name
# Heroku will automatically:
# - Install dependencies from requirements.txt
# - Run release command (migrate + collectstatic)
# - Start web dyno
```

#### Verify Deployment
```bash
heroku logs --tail         # Watch logs in real-time
heroku run python manage.py shell  # SSH into app
```

---

### Docker Deployment (Alternative)

#### Build Image
```bash
docker build -t clairbook:latest .
docker tag clairbook:latest gcr.io/your-project/clairbook:latest
docker push gcr.io/your-project/clairbook:latest
```

#### Deploy to Cloud Run (GCP) / Container Service
```bash
gcloud run deploy clairbook --image gcr.io/your-project/clairbook:latest \
  --platform managed \
  --region us-central1 \
  --set-env-vars DJANGO_SECRET_KEY=...,DEBUG=False,... \
  --allow-unauthenticated
```

---

### Manual VPS Deployment (DigitalOcean, AWS EC2, etc.)

#### 1. Server Setup
```bash
# SSH into server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y
apt install -y python3-pip python3-venv postgresql postgresql-contrib nginx supervisor

# Create app user
useradd -m -s /bin/bash clairbook
su - clairbook
```

#### 2. Deploy Code
```bash
cd /home/clairbook
git clone https://github.com/your-repo/sacredwork_app.git .
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 3. Environment & Database
```bash
# Create production database
sudo -u postgres createdb clairbook_prod
sudo -u postgres createuser clairbook_user
# Set password for user

# Create .env file with all secrets
nano .env
# Add: DATABASE_URL=postgresql://clairbook_user:password@localhost/clairbook_prod
# Add all other env vars from checklist
```

#### 4. Run Migrations & Setup
```bash
source .venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python _seed_admin.py
```

#### 5. Configure Supervisor (background process)
```bash
sudo nano /etc/supervisor/conf.d/clairbook.conf
```
```ini
[program:clairbook]
directory=/home/clairbook
command=/home/clairbook/.venv/bin/gunicorn config.wsgi --workers 3 --bind 127.0.0.1:8000
user=clairbook
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/clairbook.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start clairbook
```

#### 6. Configure Nginx Reverse Proxy
```bash
sudo nano /etc/nginx/sites-available/clairbook
```
```nginx
server {
    listen 80;
    server_name clairbook.app www.clairbook.app;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /home/clairbook/staticfiles/;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/clairbook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 7. SSL Certificate (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d clairbook.app -d www.clairbook.app
```

---

## Post-Deployment Verification

### Health Checks
```bash
# Test homepage
curl https://clairbook.app/

# Test privacy policy
curl https://clairbook.app/privacy/

# Test admin login
curl https://clairbook.app/admin/  # Should redirect to login

# Test HTTPS redirect
curl -I http://clairbook.app/  # Should 301 → HTTPS
```

### Email Verification
```bash
# Sign up test practitioner on waitlist
# Check email inbox (spam folder too!)
# Click verification link
# Verify confirmation page
```

### Admin Dashboard
1. Log in to `/admin/`
2. Verify KPI dashboard loads at `/catalog/analytics/`
3. Verify GDPR audit logs at `/admin/gdpr-audit/`
4. Create test practitioner in waitlist via admin
5. Mark as "Invited" and verify email is sent

### Monitor Logs
```bash
# Heroku
heroku logs --tail

# VPS
tail -f /var/log/clairbook.log
tail -f /var/log/nginx/error.log
```

---

## Ongoing Operations

### Daily Tasks
- [ ] Monitor Sentry/error tracking for crashes
- [ ] Check GDPR audit log (Compliance > GDPR Audit)
- [ ] Review KPI dashboard for anomalies (sales, traffic, onboarding flows)

### Weekly Tasks
- [ ] Review waitlist queue (Admin > Waitlist Profiles)
- [ ] Approve/invite practitioners as needed
- [ ] Monitor database size and backup status

### Monthly Tasks
- [ ] Review email logs for bounces/failures
- [ ] Audit user accounts for spam/abuse
- [ ] Update dependencies for security patches
- [ ] Verify backup restoration works

---

## Emergency Procedures

### Database Corruption / Data Loss
```bash
# Restore from backup
heroku pg:backups:restore <backup-id> DATABASE_URL

# Manual restore from S3 backup
aws s3 cp s3://backups/clairbook-2026-03-17.sql.gz .
gunzip clairbook-*.sql.gz
psql clairbook_prod < clairbook-*.sql
```

### Credential Compromise
```bash
# Rotate Django secret key immediately
heroku config:set DJANGO_SECRET_KEY=<new-key>

# Rotate database password
ALTER USER clairbook_user WITH PASSWORD 'new-password';
heroku config:set DATABASE_URL=postgresql://clairbook_user:new-password@...
```

### DoS / Traffic Spike
```bash
# Restrict traffic via firewall
sudo ufw default deny incoming
sudo ufw allow from your-office-ip to any port 22
sudo ufw allow to any port 443

# Increase Heroku dyno size
heroku ps:scale web=3 worker=2

# Check logs
heroku logs --tail | grep "suspicious"
```

---

## Rollback Procedure

### If deployment is broken:
```bash
# Heroku: Redeploy previous version
git log --oneline | head -5  # Find previous commit
git reset --hard <commit-hash>
git push heroku HEAD:main --force

# Restart
heroku restart
heroku logs --tail
```

---

## Support Contacts & Escalation

- **Server Issues**: [Your hosting provider support]
- **Database Issues**: Database admin contact
- **Email Delivery**: Mailgun support or email provider
- **Security Incidents**: security@clairbook.app → immediate patch & notify users
- **On-call Rotation**: [Define your on-call schedule]

---

## Monitoring & Alerts

### Recommended Monitoring Tools
- **Error Tracking**: Sentry.io (free tier available)
- **Uptime Monitoring**: StatusPage.io or Uptime Robot
- **Performance**: New Relic or Datadog
- **Logs**: LogTail or Papertrail (for VPS)

### Critical Alerts to Configure
- [ ] Application error rate > 1%
- [ ] Database response time > 2 seconds
- [ ] 5xx errors > 10 per minute
- [ ] SSL certificate expiring soon (auto-renewal enabled?)
- [ ] Disk space > 80% full
- [ ] Memory usage > 85%

---

## Version & Change Log
- **v1.0.0** (2026-03-17): MVP Launch
  - Professional waitlist with email verification
  - Admin onboarding workflow & KPI dashboard
  - Compliance: Privacy Policy, Terms, GDPR export/delete
  - Status transition notifications

---

**Last Updated**: March 17, 2026  
**Maintained By**: [Your name/team]
