#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

from logging_config import logger
import time
import os

# Stocker les timestamps pour calculer la disponibilité
tunnel_start_time = None
tunnel_end_time = None
TIMESTAMP_FILE = "/tmp/tunnel_start_time.txt"

def save_start_time():
    """
    Sauvegarde l'heure de démarrage du tunnel.
    """
    global tunnel_start_time
    tunnel_start_time = time.time()
    try:
        with open("/tmp/tunnel_start_time.txt", "w") as f:
            f.write(str(tunnel_start_time))
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'heure de démarrage : {e}")

def get_start_time():
    """
    Récupère le timestamp de démarrage depuis le fichier.
    """
    try:
        if os.path.exists(TIMESTAMP_FILE):
            with open(TIMESTAMP_FILE, "r") as f:
                return float(f.read().strip())
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du timestamp : {e}")
    return None

def log_tunnel_availability(url):
    """
    Enregistre la disponibilité d'un tunnel donné.
    """
    start_time = get_start_time()
    if not start_time:
        save_start_time()
        start_time = time.time()
    
    start_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))
    logger.info(f"Tunnel disponible à l'URL : {url} (Démarré à {start_time_str})")

def log_tunnel_downtime():
    """
    Enregistre la durée totale pendant laquelle le tunnel est resté actif.
    """
    global tunnel_start_time, tunnel_end_time
    start_time = get_start_time()
    if start_time:
        uptime = time.time() - start_time
        logger.info(f"Le tunnel a été actif pendant {uptime:.2f} secondes.")
        if os.path.exists(TIMESTAMP_FILE):
            os.remove(TIMESTAMP_FILE)

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

# metrics.py

def log_url_change(previous_url, new_url):
    """
    Logge les changements d'URL et calcule la durée du tunnel précédent.
    """
    global tunnel_start_time, tunnel_end_time

    if tunnel_start_time:
        # Calculer la durée du tunnel précédent
        tunnel_end_time = time.time()
        uptime = tunnel_end_time - tunnel_start_time
        logger.info(f"Le tunnel précédent ({previous_url}) a été actif pendant {uptime:.2f} secondes.")
        # Réinitialiser les timestamps pour le prochain cycle
        tunnel_start_time = None
        tunnel_end_time = None

    # Loguer le changement d'URL
    logger.info(f"Changement d'URL détecté : Ancienne URL : {previous_url}, Nouvelle URL : {new_url}")

    # Démarrer le suivi pour le nouveau tunnel
    tunnel_start_time = time.time()


def log_custom_metric(metric_name, value):
    """
    Enregistre une métrique personnalisée avec un nom et une valeur.
    """
    try:
        logger.info(f"Métrique personnalisée - {metric_name} : {value}")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement de la métrique {metric_name} : {e}")
        
