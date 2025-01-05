#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

from logging_config import logger
from settings import TIMESTAMP_FILE, TIMESTAMP_FORMAT
from datetime import datetime, timedelta
import os

# Stocker les timestamps pour calculer la disponibilité
tunnel_start_time = None
tunnel_end_time = None

''' Fonctions Principales de Gestion du Temps '''

def save_start_time():
    """
    Sauvegarde l'heure de démarrage du tunnel.
    """
    global tunnel_start_time
    tunnel_start_time = datetime.now()
    try:
        with open(TIMESTAMP_FILE, "w") as f:
            f.write(tunnel_start_time.isoformat())
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'heure de démarrage : {e}")

def get_start_time():
    """
    Récupère le timestamp de démarrage depuis le fichier.
    """
    try:
        if os.path.exists(TIMESTAMP_FILE):
            with open(TIMESTAMP_FILE, "r") as f:
                return datetime.fromisoformat(f.read().strip())
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du timestamp : {e}")
    return None

def log_tunnel_startup_time(start_time: datetime, end_time: datetime):
    """
    Enregistre le temps nécessaire pour démarrer un tunnel.
    """
    startup_duration = (end_time - start_time).total_seconds()
    logger.info(f"Temps de démarrage du tunnel : {startup_duration:.2f} secondes.")

def log_tunnel_availability(url: str):
    """
    Enregistre la disponibilité d'un tunnel donné.
    """
    start_time = get_start_time()
    if not start_time:
        save_start_time()
        start_time = datetime.now()
    
    start_time_str = start_time.strftime(TIMESTAMP_FORMAT)
    logger.info(f"Tunnel disponible à l'URL : {url} (Démarré à {start_time_str})")

''' Fonctions de Changement d'État '''

def log_url_change(previous_url: str, new_url: str):
    """
    Logge les changements d'URL et calcule la durée du tunnel précédent.
    """
    global tunnel_start_time, tunnel_end_time
    
    if tunnel_start_time:
        tunnel_end_time = datetime.now()
        duration = tunnel_end_time - tunnel_start_time
        
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60
        
        logger.info(f"Le tunnel précédent ({previous_url}) a été actif pendant {hours}h {minutes}m {seconds}s.")
        
        # Réinitialiser les timestamps pour le prochain cycle
        tunnel_start_time = None
        tunnel_end_time = None
    
    # Loguer le changement d'URL
    logger.info(f"Changement d'URL détecté : Ancienne URL : {previous_url}, Nouvelle URL : {new_url}")
    
    # Démarrer le suivi pour le nouveau tunnel
    tunnel_start_time = datetime.now()

def log_tunnel_downtime():
    """
    Enregistre la durée totale pendant laquelle le tunnel est resté actif.
    """
    start_time = get_start_time()
    if start_time:
        duration = datetime.now() - start_time
        
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        seconds = duration.seconds % 60
        
        logger.info(f"Le tunnel a été actif pendant {hours}h {minutes}m {seconds}s.")
        
    if os.path.exists(TIMESTAMP_FILE):
        os.remove(TIMESTAMP_FILE)

''' Fonctions Auxiliaires '''

def log_connectivity_failure(attempt: int, max_attempts: int):
    """
    Enregistre un échec lors du test de connectivité.
    """
    logger.warning(f"Échec de connectivité ({attempt}/{max_attempts}).")

def log_custom_metric(metric_name: str, value: any):
    """
    Enregistre une métrique personnalisée avec un nom et une valeur.
    """
    try:
        logger.info(f"Métrique personnalisée - {metric_name} : {value}")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la métrique {metric_name} : {e}")
        