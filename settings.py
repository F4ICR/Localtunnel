#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Version du script
version = '3.3'

import os

# Obtenir le chemin absolu du répertoire où se trouve ce fichier
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Créer le répertoire 'logs' s'il n'existe pas
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Fichiers de log
TUNNEL_OUTPUT_FILE = os.path.join(LOG_DIR, "tunnel_output.log")
APPLICATION_LOG = os.path.join(LOG_DIR, "application.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")
TUNNEL_DURATIONS_FILE = os.path.join(LOG_DIR, "tunnel_durations.log")
TIMESTAMP_FILE = "/tmp/tunnel_start_time.txt"
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

# Configuration du port
PORT = 3000  # Le port local à exposer

# Configuration email
EMAIL_NOTIFICATIONS = True  # Activer ou désactiver les emails
EMAIL = "pascal.paquet@gmail.com"  # Adresse email pour recevoir l'URL du tunnel
SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP
SMTP_PORT = 465  # Port SMTP sécurisé (SSL)
SMTP_USER = "pascal.paquet@gmail.com"  # Utilisateur SMTP
SMTP_PASSWORD = "xgprpgltwbhpahot"  # Mot de passe SMTP

# Sous-domaine pour le tunnel
SUBDOMAIN = None  # Sous-domaine souhaité (None pour un sous-domaine aléatoire)

# Configuration des logs
LOG_BACKUP_COUNT = 5  # Nombre de sauvegardes logs
LOG_MAX_BYTES = 2  # Taille max logs (en Mo)

# Paramètres pour démarrer le tunnel
MAX_RETRIES = 10  # Nombre de tentatives pour établir le tunnel
DELAY_RETRIES = 5 # Delai (en secondes) entre chaque tentative pour démarrer le tunnel
RETRY_WAIT_TIME = 30  # Temps d'attente (en seconde) après DELAY_RETRIES pour nouvelle tentative

# Paramètres pour tester la connectivité du tunnel
LT_PROCESS_CHECK_INTERVAL = 60  # Intervalle de vérification du processus Localtunnel (en secondes)
TUNNEL_CHECK_INTERVAL = 600  # Temps d'attente dans la boucle en mode daemon du fichier (en secondes)

''' Configuration conditionnelle des logs pour les besoins de débogage '''
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