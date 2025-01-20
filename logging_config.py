#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import os
import socket
from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, LOG_BACKUP_COUNT, LOG_MAX_BYTES

# Classe pour ajouter l'hostname aux logs
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

# Configurer la journalisation
logging.basicConfig(level=logging.DEBUG)

# Créer le gestionnaire de rotation pour les logs généraux
try:
    file_handler = TimedRotatingFileHandler(
        APPLICATION_LOG,
        when='midnight',
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
except Exception as e:
    print(f"Erreur lors de la configuration du gestionnaire de fichier : {e}")
    file_handler = None

# Gestionnaire pour les erreurs
try:
    error_handler = RotatingFileHandler(
        ERROR_LOG,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
except Exception as e:
    print(f"Erreur lors de la configuration du gestionnaire d'erreurs : {e}")
    error_handler = None

# Créer le gestionnaire pour la console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Définir le format des logs
formatter = logging.Formatter(VERBOSE_FORMAT)
if file_handler:
    file_handler.setFormatter(formatter)
if error_handler:
    error_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# Configurer le logger principal
logger = logging.getLogger("LocaltunnelApp")
logger.setLevel(logging.DEBUG)

# Ajouter le filtre contextuel
context_filter = ContextFilter()
logger.addFilter(context_filter)

# Ajouter les gestionnaires au logger principal
if file_handler:
    logger.addHandler(file_handler)
if error_handler:
    logger.addHandler(error_handler)
logger.addHandler(console_handler)

# Désactiver la propagation si nécessaire
logger.propagate = False
