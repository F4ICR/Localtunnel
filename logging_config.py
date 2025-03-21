#!/usr/bin/env python3
# F4ICR & OpenAI GPT-4

import logging
import os
import re
import json
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from datetime import time, datetime, timedelta
from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, LOG_BACKUP_COUNT, LOG_MAX_BYTES

# ────────────────────────────────────────────────────────────────────────────────
# Classe pour ajouter des informations contextuelles aux logs
# ────────────────────────────────────────────────────────────────────────────────
class EnhancedContextFilter(logging.Filter):
    def __init__(self, app_state_file="app_state.json"):
        super().__init__()
        self.app_state_file = app_state_file
        self.app_state = self._load_app_state()
        self.pid = os.getpid()  # Récupère le PID du processus actuel
    
    def filter(self, record):
        # Ajout d'un identifiant unique de session et du PID
        if not hasattr(record, 'session_id'):
            record.session_id = self.app_state.get('session_id', 'unknown')
        record.pid = self.pid  # Ajoute le PID à chaque enregistrement
        return True
    
    def _load_app_state(self):
        """Charge l'état de l'application depuis un fichier JSON"""
        if os.path.exists(self.app_state_file):
            try:
                with open(self.app_state_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        # État par défaut avec un nouvel ID de session simplifié
        return {'session_id': f"{datetime.now().strftime('%Y%m%d%H%M%S')}"}
    
    def save_app_state(self, key, value):
        """Sauvegarde une information dans l'état de l'application"""
        self.app_state[key] = value
        try:
            with open(self.app_state_file, 'w') as f:
                json.dump(self.app_state, f)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde de l'état: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# Gestionnaire personnalisé pour éviter les problèmes de troncature à la rotation
# ────────────────────────────────────────────────────────────────────────────────
class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, *args, **kwargs):
        self.on_rotation_callback = kwargs.pop('on_rotation_callback', None)
        super().__init__(*args, **kwargs)
    
    def doRollover(self):
        if self.stream:
            self.stream.flush()
            self.stream.close()
            self.stream = None
        
        # Exécuter le callback avant la rotation si défini
        if callable(self.on_rotation_callback):
            self.on_rotation_callback()
            
        super().doRollover()

# ────────────────────────────────────────────────────────────────────────────────
# Classe pour extraire et conserver les informations importantes des logs
# ────────────────────────────────────────────────────────────────────────────────
class LogInfoExtractor:
    def __init__(self, log_dir=None):
        self.log_dir = log_dir or os.path.dirname(APPLICATION_LOG)
        self.url_pattern = re.compile(r'https://[a-zA-Z0-9.-]+\.loca\.lt')
        self.port_pattern = re.compile(r'tunnel est actif sur le port (\d+)')
        self.critical_info = {}
    
    def extract_from_previous_logs(self, days_back=2):
        """Extrait les informations critiques des logs précédents"""
        today = datetime.now().date()
        
        for i in range(1, days_back + 1):
            log_date = today - timedelta(days=i)
            log_date_str = log_date.strftime("%Y-%m-%d")
            
            # Chercher dans les fichiers de log avec date
            potential_log_files = [
                f"{APPLICATION_LOG}.{log_date_str}",
                f"{os.path.splitext(APPLICATION_LOG)[0]}.{log_date_str}{os.path.splitext(APPLICATION_LOG)[1]}"
            ]
            
            for log_file in potential_log_files:
                if os.path.exists(log_file):
                    self._extract_from_file(log_file)
        
        # Aussi vérifier le log actuel
        if os.path.exists(APPLICATION_LOG):
            self._extract_from_file(APPLICATION_LOG)
            
        return self.critical_info
    
    def _extract_from_file(self, file_path):
        """Extrait les informations d'un fichier de log spécifique"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # Recherche d'URL
                    url_match = self.url_pattern.search(line)
                    if url_match and 'tunnel_url' not in self.critical_info:
                        self.critical_info['tunnel_url'] = url_match.group(0)
                    
                    # Recherche de port
                    port_match = self.port_pattern.search(line)
                    if port_match and 'tunnel_port' not in self.critical_info:
                        self.critical_info['tunnel_port'] = port_match.group(1)
        except Exception as e:
            print(f"Erreur lors de l'extraction des infos du fichier {file_path}: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# Fonction pour préparer la rotation des logs
# ────────────────────────────────────────────────────────────────────────────────
def prepare_for_rotation():
    """Fonction exécutée avant la rotation des logs pour sauvegarder les infos critiques"""
    extractor = LogInfoExtractor()
    critical_info = extractor.extract_from_previous_logs()
    
    if critical_info:
        # Enregistrer les informations critiques dans l'état de l'application
        for key, value in critical_info.items():
            context_filter.save_app_state(key, value)

# ────────────────────────────────────────────────────────────────────────────────
# Configuration des gestionnaires de logs (fichier journal, erreurs et console)
# ────────────────────────────────────────────────────────────────────────────────

# Initialisation du filtre de contexte amélioré
context_filter = EnhancedContextFilter()

# Gestionnaire principal : rotation quotidienne à minuit précise
try:
    file_handler = SafeTimedRotatingFileHandler(
        filename=APPLICATION_LOG,
        when='midnight',
        interval=1,
        backupCount=LOG_BACKUP_COUNT,
        encoding='utf-8',
        atTime=time(0, 0, 0),
        on_rotation_callback=prepare_for_rotation
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
# Format simplifié sans hostname, mais avec session_id
formatter = logging.Formatter('%(asctime)s - %(levelname)s - [PID: %(pid)d - %(session_id)s] - %(message)s')

for handler in [file_handler, error_handler, console_handler]:
    if handler:
        handler.setFormatter(formatter)

# Définir le format des logs en mode debug
formatter = logging.Formatter(VERBOSE_FORMAT)
if file_handler:
    file_handler.setFormatter(formatter)
if error_handler:
    error_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

# ────────────────────────────────────────────────────────────────────────────────
# Configuration finale du logger principal avec filtres et gestionnaires associés
# ────────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger()  # Logger racine sans nom spécifique
logger.setLevel(logging.DEBUG)
logger.addFilter(context_filter)

for handler in [file_handler, error_handler, console_handler]:
    if handler:
        logger.addHandler(handler)

logger.propagate = False  # Évite la duplication des messages dans les loggers parents

# ────────────────────────────────────────────────────────────────────────────────
# Restauration des informations critiques au démarrage
# ────────────────────────────────────────────────────────────────────────────────
def restore_critical_info():
    """Restaure et log les informations critiques des sessions précédentes"""
    extractor = LogInfoExtractor()
    critical_info = extractor.extract_from_previous_logs()
    
    if critical_info:
        logger.info("Informations critiques restaurées des logs précédents:")
        for key, value in critical_info.items():
            logger.info(f"  - {key}: {value}")
            # Sauvegarder dans l'état de l'application
            context_filter.save_app_state(key, value)
    else:
        logger.warning("Aucune information critique trouvée dans les logs précédents")

# Appel de la fonction de restauration au démarrage
restore_critical_info()
