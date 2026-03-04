#!/bin/bash
# CosherAlert — Kamatera VPS deployment script
# Run as root on Ubuntu 22.04: bash deploy.sh
# Server IP: 45.83.40.230

set -e

APP_USER="cosherlert"
APP_DIR="/opt/cosherlert"
DATA_DIR="/var/cosherlert"
ENV_FILE="/etc/cosherlert/env"
REPO_URL="https://github.com/tamarHoffman/cosherlert.git"
SERVER_IP="185.162.124.69"

echo "==> [1/8] System update & dependencies"
apt-get update -qq
apt-get install -y python3 python3-venv python3-pip git nginx curl

echo "==> [2/8] Create app user and directories"
id -u $APP_USER &>/dev/null || useradd --system --shell /bin/bash --home $APP_DIR $APP_USER
mkdir -p $APP_DIR $DATA_DIR /etc/cosherlert
chown $APP_USER:$APP_USER $APP_DIR $DATA_DIR

echo "==> [3/8] Clone / update repo"
if [ -d "$APP_DIR/.git" ]; then
    cd $APP_DIR && sudo -u $APP_USER git pull
else
    sudo -u $APP_USER git clone $REPO_URL $APP_DIR
fi

echo "==> [4/8] Python venv + install"
cd $APP_DIR
sudo -u $APP_USER python3 -m venv venv
sudo -u $APP_USER venv/bin/pip install -q --upgrade pip
sudo -u $APP_USER venv/bin/pip install -q -e .

echo "==> [5/8] Create env file (if not exists)"
if [ ! -f "$ENV_FILE" ]; then
    cat > $ENV_FILE << 'ENVEOF'
YEMOT_SYSTEM_ID=0772221657
YEMOT_PASSWORD=REPLACE_ME
YEMOT_CALLER_ID_A=0772221657
YEMOT_CALLER_ID_B=
OREF_POLL_INTERVAL=5
DB_PATH=/var/cosherlert/cosherlert.db
IVR_WEBHOOK_PORT=8080
IVR_BASE_URL=http://185.162.124.69
LOG_LEVEL=INFO
ENVEOF
    chmod 600 $ENV_FILE
    echo ""
    echo "  *** IMPORTANT: edit $ENV_FILE and set YEMOT_PASSWORD before starting ***"
    echo ""
fi

echo "==> [6/8] Nginx reverse proxy (HTTP — port 80 → 8080)"
cat > /etc/nginx/sites-available/cosherlert << 'NGINXEOF'
server {
    listen 80;
    server_name 185.162.124.69;

    location /ivr/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080/ivr/start;
    }
}
NGINXEOF
ln -sf /etc/nginx/sites-available/cosherlert /etc/nginx/sites-enabled/cosherlert
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==> [7/8] systemd service"
cat > /etc/systemd/system/cosherlert.service << 'SVCEOF'
[Unit]
Description=CosherAlert — Rocket Pre-Warning for Kosher Phones
After=network.target

[Service]
User=cosherlert
WorkingDirectory=/opt/cosherlert
EnvironmentFile=/etc/cosherlert/env
ExecStart=/opt/cosherlert/venv/bin/python -m cosherlert.main
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable cosherlert

echo "==> [8/8] Done!"
echo ""
echo "Next steps:"
echo "  1. Edit $ENV_FILE  — set YEMOT_PASSWORD"
echo "  2. systemctl start cosherlert"
echo "  3. systemctl status cosherlert"
echo "  4. curl http://$SERVER_IP/ivr/start?ApiPhone=0500000000"
echo "  5. In Yemot dashboard: set IVR extension api_url=http://$SERVER_IP/ivr/start"
echo ""
