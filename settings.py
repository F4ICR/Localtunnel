#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Version du script
version = '1.1.8'

import os

# Obtenir le chemin absolu du répertoire où se trouve ce fichier
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Fichiers de log
LOG_FILE = os.path.join(SCRIPT_DIR, "tunnel_output.log")
APPLICATION_LOG = os.path.join(SCRIPT_DIR, "application.log")
ERROR_LOG = os.path.join(SCRIPT_DIR, "error.log")

# Configuration du port
PORT = 3000  # Le port local à exposer

# Configuration email
EMAIL = "votre_mail@blabla.com"  # Adresse email pour recevoir l'URL du tunnel
SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP (exemple avec Gmail)
SMTP_PORT = 465  # Port SMTP sécurisé (SSL)
SMTP_USER = "votre_mail@blabla.com"  # Adresse email utilisée pour l'envoi
SMTP_PASSWORD = "mot_de_passe"  # Mot de passe ou App Password (si Gmail)

# Sous-domaine pour le tunnel
SUBDOMAIN = None  # Sous-domaine souhaité (None pour un sous-domaine aléatoire)

# Configuration des logs
LOG_BACKUP_COUNT = 6  # Nombre de sauvegardes de logs à conserver
LOG_MAX_BYTES = 5 * 1024 * 1024  # Taille maximale des fichiers log (en octets)

# Paramètres pour tester la connectivité du tunnel
TUNNEL_RETRIES = 5  # Nombre de tentatives pour tester la connectivité
TUNNEL_DELAY = 3  # Délai (en secondes) entre chaque tentative
TUNNEL_TIMEOUT = 6  # Timeout (en secondes) pour les requêtes HTTP
HTTP_SUCCESS_CODE = 200  # Code HTTP attendu pour une réponse réussie

# Configuration conditionnelle des logs pour les besoins de débogage

# Variables pour activer/désactiver certaines parties du format
INCLUDE_FILENAME = False  # Inclure le nom du fichier dans les logs
INCLUDE_DEBUG_INFO = False  # Inclure les informations de debug (fonction et ligne)

# Format des logs avec gestion conditionnelle
VERBOSE_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "[PID: %(process)d - Thread: %(thread)d] - "
    + ("[File: %(filename)s] - " if INCLUDE_FILENAME else "")
    + ("[Function: %(funcName)s - Line: %(lineno)d] - " if INCLUDE_DEBUG_INFO else "")
    + "%(message)s"
)
