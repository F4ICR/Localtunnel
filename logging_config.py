#!/usr/bin/env python3
# F4ICR & OpenAI GPT-4

import logging
import os
import re
import json
import time as time_module
from logging.handlers import TimedRotatingFileHandler, RotatingFileHandler
from datetime import time, datetime, timedelta
from settings import APPLICATION_LOG, ERROR_LOG, VERBOSE_FORMAT, LOG_BACKUP_COUNT, LOG_MAX_BYTES

# ────────────────────────────────────────────────────────────────────────────────
# Utiliser un fichier JSON temporaire pour stocker l'identifiant de session
# ────────────────────────────────────────────────────────────────────────────────
def get_shared_session_id():
    session_file = "/tmp/localtunnel_session_id.json"
    
    # Si le fichier existe, lire l'identifiant
    if os.path.exists(session_file):
        try:
            with open(session_file, 'r') as f:
                data = json.load(f)
                return data['session_id']
        except:
            pass
    
    # Sinon, générer un nouvel identifiant
    session_id = f"session_{datetime.now().strftime('%d%H%M%S')}"
    
    # Le stocker dans un fichier temporaire
    try:
        with open(session_file, 'w') as f:
            json.dump({'session_id': session_id}, f)
    except:
        pass
    
    return session_id

# ────────────────────────────────────────────────────────────────────────────────
# Classe pour ajouter des informations contextuelles aux logs
# ────────────────────────────────────────────────────────────────────────────────
class EnhancedContextFilter(logging.Filter):
    def __init__(self, app_state_file=None):
        super().__init__()
        self.app_state = {
            'session_id': get_shared_session_id(),
            'tunnel_port': "",
            'tunnel_url': ""
        }
        self.pid = os.getpid()
    
    def filter(self, record):
        if not hasattr(record, 'session_id'):
            record.session_id = self.app_state.get('session_id', 'unknown')
        record.pid = self.pid
        return True
    
    def save_app_state(self, key, value):
        """Sauvegarde une information dans l'état de l'application"""
        self.app_state[key] = value
        if key == 'session_id':
            session_file = "/tmp/localtunnel_session_id.json"
            try:
                with open(session_file, 'w') as f:
                    json.dump({'session_id': value}, f)
            except:
                pass

# ────────────────────────────────────────────────────────────────────────────────
# Logger temporaire pour la phase d'initialisation
# ────────────────────────────────────────────────────────────────────────────────
init_logger = logging.getLogger("init")
init_handler = logging.StreamHandler()
init_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
init_logger.addHandler(init_handler)
init_logger.setLevel(logging.INFO)
            
# ────────────────────────────────────────────────────────────────────────────────
# Gestionnaire personnalisé pour éviter les problèmes de troncature à la rotation
# ────────────────────────────────────────────────────────────────────────────────
class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, *args, **kwargs):
        self.on_rotation_callback = kwargs.pop('on_rotation_callback', None)
        super().__init__(*args, **kwargs)
        
        # Vérifier si une rotation est nécessaire au démarrage
        self._check_rollover_at_startup()
    
    def _check_rollover_at_startup(self):
        """Vérifie si une rotation est nécessaire au démarrage"""
        try:
            current_date = datetime.now().date()
            if os.path.exists(self.baseFilename):
                file_mtime = os.path.getmtime(self.baseFilename)
                file_date = datetime.fromtimestamp(file_mtime).date()
                
                # Si le fichier date d'avant aujourd'hui, forcer une rotation
                if file_date < current_date:
                    init_logger.info(f"Fichier de log daté du {file_date}, rotation forcée...")
                    self.doRollover()
        except Exception as e:
            init_logger.error(f"Vérification de rotation au démarrage: {e}")
    
    def doRollover(self):
        """Effectue la rotation des logs"""
        # Log d'information avant rotation
        init_logger.info(f"Début de la rotation des logs à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if self.stream:
            self.stream.flush()
            self.stream.close()
            self.stream = None
        
        # Exécuter le callback avant la rotation si défini
        if callable(self.on_rotation_callback):
            self.on_rotation_callback()
        
        # Obtenir la date pour le nom du fichier roté (aujourd'hui)
        current_date = datetime.now().date()
        yesterday = current_date - timedelta(days=1)
        dfn = self.rotation_filename(f"{self.baseFilename}.{yesterday.strftime('%Y-%m-%d')}")
        
        # Effectuer la rotation
        if os.path.exists(self.baseFilename):
            try:
                if os.path.exists(dfn):
                    os.remove(dfn)
                os.rename(self.baseFilename, dfn)
                init_logger.info(f"Fichier renommé en {dfn}")
            except Exception as e:
                init_logger.error(f"Impossible de renommer le fichier log: {e}")
        
        # Créer un nouveau fichier
        self.stream = self._open()
        
        # Calculer la prochaine rotation
        current_time = time_module.time()
        newRolloverAt = self.computeRollover(current_time)
        while newRolloverAt <= current_time:
            newRolloverAt = newRolloverAt + self.interval
        
        self.rolloverAt = newRolloverAt
        init_logger.info(f"Prochaine rotation prévue à {datetime.fromtimestamp(self.rolloverAt).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Supprimer les anciens fichiers si nécessaire
        if self.backupCount > 0:
            self.deleteOldBackups()
    
    def deleteOldBackups(self):
        """Supprime les anciens fichiers de logs selon backupCount"""
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name) if dir_name else os.listdir('.')
        
        # Filtrer les fichiers qui correspondent au pattern de rotation
        result = []
        prefix = base_name + "."
        for fileName in file_names:
            if fileName.startswith(prefix):
                suffix = fileName[len(prefix):]
                if self.extMatch.match(suffix):
                    result.append(os.path.join(dir_name, fileName))
        
        # Trier les fichiers par date (du plus récent au plus ancien)
        result.sort(reverse=True)
        
        # Supprimer les fichiers excédentaires
        for i in range(self.backupCount, len(result)):
            try:
                os.remove(result[i])
                init_logger.info(f"Ancien fichier supprimé: {result[i]}")
            except Exception as e:
                init_logger.error(f"Impossible de supprimer l'ancien fichier {result[i]}: {e}")

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
            init_logger.error(f"Extraction des infos du fichier {file_path}: {e}")

# ────────────────────────────────────────────────────────────────────────────────
# Fonction pour préparer la rotation des logs
# ────────────────────────────────────────────────────────────────────────────────
def prepare_for_rotation():
    """Fonction exécutée avant la rotation des logs pour sauvegarder les infos critiques"""
    init_logger.info(f"Préparation de la rotation des logs à {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    extractor = LogInfoExtractor()
    critical_info = extractor.extract_from_previous_logs()
    
    if critical_info:
        # Enregistrer les informations critiques dans l'état de l'application
        for key, value in critical_info.items():
            context_filter.save_app_state(key, value)
            init_logger.info(f"Information critique sauvegardée: {key}={value}")

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
    file_handler.suffix = "%Y-%m-%d"  # Format du suffixe pour les fichiers rotés
    file_handler.extMatch = re.compile(r"^\d{4}-\d{2}-\d{2}$")  # Expression régulière pour identifier les fichiers rotés
    init_logger.info(f"Gestionnaire de logs principal initialisé")
except Exception as e:
    init_logger.error(f"Impossible d'initialiser le gestionnaire principal : {e}")
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
    init_logger.error(f"Impossible d'initialiser le gestionnaire d'erreurs : {e}")
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

# Log d'information sur le démarrage du système de journalisation
logger.info(f"Système de journalisation initialisé avec succès. ID de session: {context_filter.app_state['session_id']}")