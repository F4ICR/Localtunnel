#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

from logging_config import logger
import time

# Stocker les timestamps pour calculer la disponibilité
tunnel_start_time = None
tunnel_end_time = None

def log_tunnel_availability(url):
    """
    Enregistre la disponibilité d'un tunnel donné.
    """
    global tunnel_start_time
    tunnel_start_time = time.time()
    logger.info(f"Tunnel disponible à l'URL : {url} (Démarré à {time.strftime('%Y-%m-%d %H:%M:%S')})")

def log_tunnel_downtime():
    """
    Enregistre la durée totale pendant laquelle le tunnel est resté actif.
    """
    global tunnel_start_time, tunnel_end_time
    if tunnel_start_time:
        tunnel_end_time = time.time()
        uptime = tunnel_end_time - tunnel_start_time
        logger.info(f"Le tunnel a été actif pendant {uptime:.2f} secondes.")
        # Réinitialiser les timestamps
        tunnel_start_time = None
        tunnel_end_time = None

def log_tunnel_startup_time(start_time, end_time):
    """
    Enregistre le temps nécessaire pour démarrer un tunnel.
    """
    startup_duration = end_time - start_time
    logger.info(f"Temps de démarrage du tunnel : {startup_duration:.2f} secondes.")

def log_connectivity_failure(attempt, max_attempts):
    """
    Enregistre un échec lors du test de connectivité.
    """
    logger.warning(f"Échec de connectivité ({attempt}/{max_attempts}).")

def log_url_change(previous_url, new_url):
    """
    Logge les changements d'URL.
    """
    logger.info(f"Changement d'URL détecté : Ancienne URL : {previous_url}, Nouvelle URL : {new_url}")

def log_custom_metric(metric_name, value):
    """
    Enregistre une métrique personnalisée avec un nom et une valeur.
    """
    try:
        logger.info(f"Métrique personnalisée - {metric_name} : {value}")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la métrique {metric_name} : {e}")
