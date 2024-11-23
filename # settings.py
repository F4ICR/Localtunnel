# settings.py
#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Le port local que vous souhaitez exposer
PORT = 3000

# Fichier de log pour capturer la sortie du tunnel
LOG_FILE = "tunnel_output.log"

# Adresse email pour recevoir l'URL du tunnel
EMAIL = "votre_mail@domaine.com"

# Serveur SMTP (exemple avec Gmail)
SMTP_SERVER = "smtp.gmail.com"

# Port SMTP sécurisé (SSL)
SMTP_PORT = 465

# Votre adresse Gmail (ou autre fournisseur)
SMTP_USER = "votre_mail@domaine.com"

# Mot de passe ou App Password (si Gmail)
SMTP_PASSWORD = "votre_password"  # Remplacez par une variable d'environnement pour plus de sécurité

# Sous-domaine souhaité (None pour un sous-domaine aléatoire)
SUBDOMAIN = None
