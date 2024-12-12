#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4


import time
import logging
import requests
from logging_config import logger

# Fonction pour mesurer la disponibilité du tunnel
def log_tunnel_availability(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            logger.info(f"Tunnel disponible : {url}. Temps de réponse : {elapsed_time:.2f} secondes.")
            return True
        else:
            logger.warning(f"Tunnel indisponible : {url}. Code HTTP : {response.status_code}")
            return False
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la vérification du tunnel {url} : {e}")
        return False

# Fonction pour enregistrer d'autres métriques
def log_custom_metric(metric_name, value):
    logger.info(f"Métrique personnalisée - {metric_name}: {value}")
