#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Configuration centralisée pour la journalisation
import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
import os
import socket

from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, LOG_BACKUP_COUNT, LOG_MAX_BYTES
LOG_FILE = APPLICATION_LOG
ERROR_LOG = ERROR_LOG
formatter = logging.Formatter(VERBOSE_FORMAT)

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
    backupCount=LOG_BACKUP_COUNT,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)

# Gestionnaire pour les erreurs
error_handler = RotatingFileHandler(
    ERROR_LOG,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUP_COUNT,
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
logger.propagate = False
