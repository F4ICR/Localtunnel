#!/usr/bin/env python3
# F4ICR & OpenAI GPT-4

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from datetime import time
import socket
from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, LOG_BACKUP_COUNT, LOG_MAX_BYTES

# ────────────────────────────────────────────────────────────────────────────────
# Classe pour ajouter automatiquement le nom d'hôte aux enregistrements de logs
# ────────────────────────────────────────────────────────────────────────────────
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

# ────────────────────────────────────────────────────────────────────────────────
# Gestionnaire personnalisé pour éviter les problèmes de troncature à la rotation
# ────────────────────────────────────────────────────────────────────────────────
class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    def doRollover(self):
        if self.stream:
            self.stream.flush()
            self.stream.close()
            self.stream = None
        super().doRollover()

# ────────────────────────────────────────────────────────────────────────────────
# Configuration des gestionnaires de logs (fichier journal, erreurs et console)
# ────────────────────────────────────────────────────────────────────────────────

# Gestionnaire principal : rotation quotidienne à minuit précise
try:
    file_handler = SafeTimedRotatingFileHandler(
        filename=APPLICATION_LOG,
        when='midnight',
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
        atTime=time(0, 0, 0)
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.suffix = "%Y-%m-%d"  # Nom du fichier avec la date du jour précédent après rotation
except Exception as e:
    print(f"[ERREUR] Impossible d'initialiser le gestionnaire principal : {e}")
    file_handler = None

# Gestionnaire des erreurs : rotation basée sur la taille maximale du fichier
try:
    error_handler = RotatingFileHandler(
        filename=ERROR_LOG,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
except Exception as e:
    print(f"[ERREUR] Impossible d'initialiser le gestionnaire d'erreurs : {e}")
    error_handler = None

# Gestionnaire console pour affichage temps réel des logs à l'écran
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# ────────────────────────────────────────────────────────────────────────────────
# Formatage uniforme des messages de logs (fichier journal, erreurs et console)
# ────────────────────────────────────────────────────────────────────────────────
formatter = logging.Formatter(VERBOSE_FORMAT)

for handler in [file_handler, error_handler, console_handler]:
    if handler:
        handler.setFormatter(formatter)

# ────────────────────────────────────────────────────────────────────────────────
# Configuration finale du logger principal avec filtres et gestionnaires associés
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger("LocaltunnelApp")
logger.setLevel(logging.DEBUG)
logger.addFilter(ContextFilter())

for handler in [file_handler, error_handler, console_handler]:
    if handler:
        logger.addHandler(handler)

logger.propagate = False  # Évite la duplication des messages dans les loggers parents
