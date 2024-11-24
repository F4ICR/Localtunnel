#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Version
version = '1.0.7'

import os

# Obtenir le chemin absolu du répertoire où se trouve ce fichier
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Construire un chemin absolu pour LOG_FILE
LOG_FILE = os.path.join(SCRIPT_DIR, "tunnel_output.log")

# Le port local que vous souhaitez exposer
PORT = 3000

# Fichier de log pour capturer la sortie du tunnel
LOG_FILE = "tunnel_output.log"

# Adresse email pour recevoir l'URL du tunnel
EMAIL = "votre_mail@blabla.com"

# Serveur SMTP (exemple avec Gmail)
SMTP_SERVER = "smtp.gmail.com"

# Port SMTP sécurisé (SSL)
SMTP_PORT = 465

# Votre adresse Gmail (ou autre fournisseur)
SMTP_USER = "votre_mail@blabla.com"

# Mot de passe ou App Password (si Gmail)
SMTP_PASSWORD = "votre_password"  # Remplacez par une variable d'environnement pour plus de sécurité

# Sous-domaine souhaité (None pour un sous-domaine aléatoire)
SUBDOMAIN = None
