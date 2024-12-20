#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Configuration centralisée pour la journalisation
import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import os
import socket

# Définir le chemin du fichier log
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "application.log")
ERROR_LOG = os.path.join(LOG_DIR, "error.log")

# Format détaillé pour les logs
VERBOSE_FORMAT = (
    "%(asctime)s - %(name)s - %(levelname)s - "
    "[PID: %(process)d - Thread: %(thread)d] - "
#    "[Host: %(hostname)s] - "
#    "[Function: %(funcName)s - Line: %(lineno)d] - " # Ligne à décommenté si besoin d'info de debuggage
    "%(message)s"
)

# Classe pour ajouter l'hostname aux logs
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()
    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

# Configurer la journalisation
logging.basicConfig(level=logging.DEBUG)

# Créer le gestionnaire de rotation
file_handler = TimedRotatingFileHandler(
    LOG_FILE,
    when='midnight',
    interval=1,
    backupCount=5,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Gestionnaire pour les erreurs
error_handler = RotatingFileHandler(
    ERROR_LOG,
    maxBytes=5*1024*1024,
    backupCount=5,
    encoding='utf-8'
)
error_handler.setLevel(logging.ERROR)

# Créer le gestionnaire pour la console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Définir le format des logs
formatter = logging.Formatter(VERBOSE_FORMAT)
file_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configurer le logger
logger = logging.getLogger("LocaltunnelApp")
logger.setLevel(logging.DEBUG)

# Ajouter le filtre de contexte
context_filter = ContextFilter()
logger.addFilter(context_filter)

# Ajouter les gestionnaires
logger.addHandler(file_handler)
logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Désactiver la propagation
logger.propagate = True
