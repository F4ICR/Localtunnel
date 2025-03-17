#!/usr/bin/env python3
# F4ICR & OpenAI GPT-4

import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime, timedelta, time as datetime_time
import socket
from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, GENERAL_LOG_BACKUP_COUNT, LOG_MAX_BYTES

# Classe pour ajouter l'hostname aux logs
class ContextFilter(logging.Filter):
    hostname = socket.gethostname()

    def filter(self, record):
        record.hostname = ContextFilter.hostname
        return True

# Classe personnalisée pour corriger le problème de rotation des logs
class FixedTimedRotatingFileHandler(TimedRotatingFileHandler):
    def computeRollover(self, currentTime):
        """
        Calcule précisément la prochaine rotation à minuit (heure locale).
        """
        t = datetime.fromtimestamp(currentTime)
        tomorrow = t + timedelta(days=1)
        rollover_time = datetime.combine(tomorrow.date(), self.atTime)
        return rollover_time.timestamp()

    def doRollover(self):
        """
        Effectue la rotation et renomme le fichier avec la date correcte correspondant au contenu.
        """
        if self.stream:
            self.stream.close()
            self.stream = None

        # Calculer la date correspondant au contenu (jour écoulé)
        yesterday = datetime.now() - timedelta(days=1)
        dated_filename = f"{self.baseFilename}.{yesterday.strftime('%Y-%m-%d')}"

        # Renommer le fichier actuel avec la date du contenu
        if os.path.exists(self.baseFilename):
            os.rename(self.baseFilename, dated_filename)

        # Supprimer les anciens fichiers si nécessaire
        if self.backupCount > 0:
            for s in self.getFilesToDelete():
                os.remove(s)

        # Réouvrir le fichier pour continuer à écrire les logs
        if not self.delay:
            self.stream = self._open()

# Configurer la journalisation générale (niveau global par défaut)
logging.basicConfig(level=logging.DEBUG)

# Créer le gestionnaire de rotation corrigé pour les logs généraux
try:
    file_handler = FixedTimedRotatingFileHandler(
        APPLICATION_LOG,
        when='midnight',
        interval=1,
        backupCount=GENERAL_LOG_BACKUP_COUNT,
        encoding='utf-8',
        atTime=datetime_time(0, 0, 0)  # Rotation précisément à 00:00:00
    )
    file_handler.setLevel(logging.DEBUG)
except Exception as e:
    print(f"Erreur lors de la configuration du gestionnaire de fichier : {e}")
    file_handler = None

# Gestionnaire pour les erreurs (sans rotation)
try:
    error_handler = logging.FileHandler(
        ERROR_LOG,  # Un seul fichier pour toutes les erreurs
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
    logger.info("Le système de journalisation est opérationnel.")
