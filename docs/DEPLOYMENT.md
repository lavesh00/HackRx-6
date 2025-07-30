# Deployment Guide

## System Requirements

### Minimum Requirements
- RAM: 8GB
- CPU: i5 processor or equivalent
- Storage: 10GB free space
- Network: Stable internet connection
- OS: Ubuntu 20.04+ or CentOS 7+

### Recommended Requirements
- RAM: 16GB
- CPU: i7 processor or equivalent
- Storage: 50GB SSD
- Network: High-speed internet

## Quick Deployment

### 1. Automated Setup

Download and run setup script
curl -sSL https://raw.githubusercontent.com/your-repo/llm-query-system/main/scripts/setup_environment.sh | bash

### 2. Manual Setup

#### Install Dependencies
Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3.9 python3.9-venv python3.9-dev
sudo apt-get install -y build-essential libmagic1 libmagic-dev
sudo apt-get install -y nginx redis-server

CentOS/RHEL
sudo yum install -y python39 python39-devel
sudo yum install -y gcc gcc-c++ file-devel
sudo yum install -y nginx redis

#### Create Project Structure
sudo mkdir -p /opt/llm-query-system
sudo chown $USER:$USER /opt/llm-query-system
cd /opt/llm-query-system

Clone repository
git clone https://github.com/your-repo/llm-query-system.git .

Create virtual environment
python3.9 -m venv venv
source venv/bin/activate

Install Python dependencies
pip install -r requirements.txt


#### Configure Environment
cp .env.example .env

Edit .env with your settings
nano .env

#### Setup Services
Create systemd service
sudo cp deploy/llm-query-system.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable llm-query-system

Setup Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/llm-query-system
sudo ln -s /etc/nginx/sites-available/llm-query-system /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

## Docker Deployment

### Build and Run
Build image
docker build -t llm-query-system .

Run with Docker Compose
docker-compose up -d

docker-compose.prod.yml
version: '3.8'
services:
app:
build: .
restart: unless-stopped
environment:
- DEBUG=False
- API_WORKERS=4
volumes:
- ./data:/app/data
- ./logs:/app/logs
deploy:
resources:
limits:
memory: 6G
reservations:
memory: 2G
nginx:
image: nginx:alpine
ports:
- "80:80"
- "443:443"
volumes:
- ./nginx.conf:/etc/nginx/nginx.conf
- ./ssl:/etc/nginx/ssl
depends_on:
- app

redis:
image: redis:7-alpine
restart: unless-stopped
volumes:
- redis_data:/data
command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru

volumes:
redis_data:

## SSL/TLS Setup

### Let's Encrypt (Recommended)
Install Certbot
sudo apt-get install -y certbot python3-certbot-nginx

Get certificate
sudo certbot --nginx -d your-domain.com

Auto-renewal
sudo crontab -e

Add: 0 12 * * * /usr/bin/certbot renew --quiet

### Self-Signed Certificate
Generate certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048
-keyout /etc/ssl/private/llm-query-system.key
-out /etc/ssl/certs/llm-query-system.crt


## Monitoring

### Log Management
View application logs
sudo journalctl -u llm-query-system -f

View Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

### Performance Monitoring
System resources
htop
iotop
free -h
df -h

Service status
sudo systemctl status llm-query-system
sudo systemctl status nginx
sudo systemctl status redis

## Backup and Recovery

### Data Backup
Backup script
#!/bin/bash
BACKUP_DIR="/backup/llm-query-system"
DATE=$(date +%Y%m%d_%H%M%S)

Create backup directory
mkdir -p $BACKUP_DIR

Backup data
tar -czf $BACKUP_DIR/data_$DATE.tar.gz /opt/llm-query-system/data/
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /opt/llm-query-system/logs/

Backup configuration
cp /opt/llm-query-system/.env $BACKUP_DIR/env_$DATE

### Recovery
Restore data
cd /opt/llm-query-system
tar -xzf /backup/llm-query-system/data_YYYYMMDD_HHMMSS.tar.gz --strip-components=3

Restart service
sudo systemctl restart llm-query-system

## Troubleshooting

### Common Issues

1. **Service won't start**
Check logs
sudo journalctl -u llm-query-system --no-pager

Check permissions
sudo chown -R $USER:$USER /opt/llm-query-system

2. **Out of memory errors**
Check memory usage
free -h

Restart service to clear memory
sudo systemctl restart llm-query-system

3. **API timeout errors**
Check Google API key
grep GOOGLE_API_KEY /opt/llm-query-system/.env

Check network connectivity
curl https://generativelanguage.googleapis.com/

### Performance Tuning

1. **Memory Optimization**
- Reduce `EMBEDDING_BATCH_SIZE` in .env
- Enable Redis caching
- Adjust `CHUNK_SIZE` for smaller chunks

2. **CPU Optimization**
- Increase `MAX_WORKERS` in .env
- Use multiple Gunicorn workers
- Enable nginx gzip compression

3. **Network Optimization**
- Use CDN for static assets
- Enable HTTP/2 in nginx
- Implement connection pooling