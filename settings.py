#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Version
version = '1.0.9'

import os

# Obtenir le chemin absolu du répertoire où se trouve ce fichier
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Construire un chemin absolu pour LOG_FILE
LOG_FILE = os.path.join(SCRIPT_DIR, "tunnel_output.log")

# Autres variables globales
PORT = 3000  # Le port local que vous souhaitez exposer
EMAIL = "votre_mail"  # Adresse email pour recevoir l'URL du tunnel
SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP (exemple avec Gmail)
SMTP_PORT = 465  # Port SMTP sécurisé (SSL)
SMTP_USER = "votre_mail"  # Votre adresse Gmail (ou autre fournisseur)
SMTP_PASSWORD = "votre_password"  # Mot de passe ou App Password (si Gmail)
SUBDOMAIN = None  # Sous-domaine souhaité (None pour un sous-domaine aléatoire)

