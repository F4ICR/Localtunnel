#!/usr/bin/env python3
# F4ICR & OpenAI GPT-4

import logging
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from datetime import datetime, timedelta, time as datetime_time
import socket
import os
import time
from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, LOG_BACKUP_COUNT, LOG_MAX_BYTES

# Classe pour ajouter l'hostname aux logs
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

# Classe personnalisée pour corriger le problème de rotation des logs
class FixedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def computeRollover(self, currentTime):
        # Calcule précisément la prochaine rotation à minuit (heure locale)
        t = datetime.fromtimestamp(currentTime)
        tomorrow = t + timedelta(days=1)
        rollover_time = datetime.combine(tomorrow.date(), self.atTime)
        return rollover_time.timestamp()

    def getFilesToDelete(self):
        # Utilise la méthode par défaut pour déterminer les fichiers à supprimer
        return super().getFilesToDelete()

# Configurer la journalisation générale (niveau global par défaut)
logging.basicConfig(level=logging.DEBUG)

# Créer le gestionnaire de rotation corrigé pour les logs généraux
try:
    file_handler = FixedTimedRotatingFileHandler(
        APPLICATION_LOG,
        when='midnight',
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
        atTime=datetime_time(0, 0, 0)  # Rotation précisément à 00:00:00
    )
    file_handler.setLevel(logging.DEBUG)
except Exception as e:
    print(f"Erreur lors de la configuration du gestionnaire de fichier : {e}")
    file_handler = None

# Gestionnaire pour les erreurs (rotation par taille)
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

# Créer le gestionnaire pour la console (affichage direct)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

# Définir le format des logs depuis settings.py
formatter = logging.Formatter(VERBOSE_FORMAT)

if file_handler:
    file_handler.setFormatter(formatter)
if error_handler:
    error_handler.setFormatter(formatter)

console_handler.setFormatter(formatter)

# Configurer le logger principal (LocaltunnelApp)
logger = logging.getLogger("LocaltunnelApp")
logger.setLevel(logging.DEBUG)

# Ajouter le filtre contextuel (hostname)
context_filter = ContextFilter()
logger.addFilter(context_filter)

# Ajouter les gestionnaires au logger principal
if file_handler:
    logger.addHandler(file_handler)
if error_handler:
    logger.addHandler(error_handler)

logger.addHandler(console_handler)

# Désactiver la propagation vers les loggers parents si nécessaire
logger.propagate = False

# Exemple d'utilisation du logger corrigé :
if __name__ == "__main__":
    logger.info("Le système de journalisation corrigé est opérationnel.")
