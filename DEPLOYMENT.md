# Production Deployment Guide

## Pre-Deployment Checklist

### Environment Setup
- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed from requirements.txt
- [ ] .env file configured with valid GROQ_API_KEY
- [ ] config.yaml reviewed and adjusted for production

### Security
- [ ] .env file added to .gitignore
- [ ] API keys rotated and secured
- [ ] No hardcoded credentials in source code
- [ ] CORS settings configured if needed
- [ ] HTTPS enabled for production (recommended)

### Performance
- [ ] STT model (tiny.en) downloaded and cached
- [ ] TTS model (Kokoro) downloaded and cached
- [ ] VAD model (Silero) cached
- [ ] Database initialized and permissions set
- [ ] Disk space sufficient for logs and database

### Monitoring
- [ ] Logging configured to file
- [ ] Error tracking enabled (e.g., Sentry)
- [ ] Health check endpoint available
- [ ] Metrics collection configured

## Deployment Options

### Option 1: Direct Server Deployment

```bash
# On production server
git clone <repository>
cd voixai
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

pip install -r requirements.txt
# Configure .env file
python main.py
```

### Option 2: Docker Deployment

Create Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t voixai .
docker run -p 8000:8000 --env-file .env voixai
```

### Option 3: Process Manager (systemd)

Create `/etc/systemd/system/voixai.service`:

```ini
[Unit]
Description=VoixAI Voice Ordering System
After=network.target

[Service]
Type=simple
User=voixai
WorkingDirectory=/opt/voixai
Environment=PATH=/opt/voixai/venv/bin
ExecStart=/opt/voixai/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl enable voixai
sudo systemctl start voixai
```

## Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## SSL/TLS (Let's Encrypt)

```bash
sudo certbot --nginx -d your-domain.com
```

## Environment Variables

Required in production `.env`:

```properties
GROQ_API_KEY=gsk_production_key_here
```

Optional:

```properties
LOG_LEVEL=INFO
DATABASE_PATH=/data/orders.db
MAX_AUDIO_DURATION=30
```

## Monitoring

### Health Check

Add to `main.py`:

```python
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
```

### Log Rotation

Configure logrotate:

```
/var/log/voixai/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

## Backup Strategy

### Database Backup

```bash
# Daily backup
sqlite3 orders.db ".backup '/backups/orders-$(date +%Y%m%d).db'"
```

### Automated Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/backups/voixai"
mkdir -p $BACKUP_DIR
sqlite3 /opt/voixai/orders.db ".backup '$BACKUP_DIR/orders-$(date +%Y%m%d-%H%M%S).db'"
find $BACKUP_DIR -name "orders-*.db" -mtime +7 -delete
```

## Troubleshooting

### High Latency
- Check CPU usage during TTS generation
- Consider GPU for TTS (Kokoro supports CUDA)
- Reduce TTS quality settings in config

### WebSocket Disconnections
- Check nginx proxy timeout settings
- Verify firewall allows WebSocket connections
- Monitor for memory leaks

### Database Locks
- Ensure single writer access
- Check for long-running transactions
- Monitor SQLite WAL mode

## Scaling Considerations

### Horizontal Scaling
- Use Redis for session management
- Separate STT/TTS workers
- Load balancer with sticky sessions

### Vertical Scaling
- CPU: More cores for parallel STT/TTS
- RAM: Cache models in memory
- GPU: Significant TTS speedup

## Security Hardening

1. Run as non-root user
2. Enable firewall (ufw/iptables)
3. Regular security updates
4. API key rotation schedule
5. Input validation and sanitization
6. Rate limiting on WebSocket connections

## Support

For issues and feature requests, refer to the project repository.
