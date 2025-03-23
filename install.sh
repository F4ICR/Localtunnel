#!/bin/bash

# Chemins vers les fichiers de services
LOCAL_SERVICE="/etc/systemd/system/localtunnel.service"
APP_SERVICE="/etc/systemd/system/app.service"

# Vérification et création du fichier localtunnel.service
if [ -f "$LOCAL_SERVICE" ]; then
    echo "[INFO] Le service localtunnel.service existe déjà. Création ignorée."
else
    echo "[INFO] Création du service localtunnel.service..."
    cat << EOF > "$LOCAL_SERVICE"
[Unit]
Description=Localtunnel Manager Service
After=network.target

[Service]
Type=simple
ExecStartPre=/bin/rm -f /tmp/localtunnel_session_id.json
ExecStart=/usr/bin/python3 /root/Localtunnel/localtunnel.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
fi

# Vérification et création du fichier app.service
if [ -f "$APP_SERVICE" ]; then
    echo "[INFO] Le service app.service existe déjà. Création ignorée."
else
    echo "[INFO] Création du service app.service..."
    cat << EOF > "$APP_SERVICE"
[Unit]
Description=API Manager Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /root/Localtunnel/app.py
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF
fi

# Rechargement des services systemd pour prendre en compte les éventuelles modifications ou ajouts.
systemctl daemon-reload

# Activation des services (s'ils ne sont pas déjà activés)
systemctl enable localtunnel.service app.service

# Démarrage immédiat des services créés (ou redémarrage s'ils étaient déjà actifs)
systemctl restart localtunnel.service app.service

echo "✅ Installation terminée : les services localtunnel et app sont activés et démarrés."
