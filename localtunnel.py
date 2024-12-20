#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Bibliothèques standard
import time

# Importer les variables de configuration depuis settings.py
from settings import PORT, LOG_FILE, EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SUBDOMAIN

# Importer les fonctions utilitaires depuis lib.py
from lib import start_tunnel, is_tunnel_active, stop_existing_tunnel, send_email, read_tunnel_url_from_log, test_tunnel_connectivity

# Importer le logger depuis logging_config.py
from logging_config import logger

# Import autres depuis dependency_check
from dependency_check import verify_all_dependencies

# Import des fonctions de métriques
from metrics import (
    log_tunnel_availability,
    log_custom_metric,
    log_tunnel_startup_time,
    log_connectivity_failure,
    log_url_change,
    log_tunnel_downtime
)

def manage_tunnel():
    try:
        # Vérifiez si un tunnel est déjà actif sur le port spécifié
        if is_tunnel_active(PORT):
            logger.info("Le tunnel est déjà actif.")
            current_url = read_tunnel_url_from_log()
            
            # Tester la connectivité du tunnel actuel
            if current_url and test_tunnel_connectivity(current_url):
                logger.info(f"Le tunnel fonctionne correctement : {current_url}")
                log_tunnel_availability(current_url)
                log_custom_metric("Tunnel actif", 1)
                return
        
        # Si aucun tunnel n'est actif, vérifier les dépendances
        logger.info("Aucun tunnel actif détecté. Vérification des dépendances en cours.")
        if not verify_all_dependencies():
            logger.error("Certaines dépendances sont manquantes ou incorrectes.")
            return

        # Arrêter le tunnel existant si nécessaire
        stop_existing_tunnel(PORT)
        
        # Récupérer l'URL précédente
        previous_url = read_tunnel_url_from_log()
        if previous_url:
            logger.info(f"Tentative de réutilisation de l'URL précédente : {previous_url}")
            global SUBDOMAIN
            SUBDOMAIN = previous_url.split("//")[1].split(".")[0]

        # Démarrer un nouveau tunnel
        start_time = time.time()
        new_url = start_tunnel(PORT, SUBDOMAIN)
        end_time = time.time()

        if new_url:
            logger.info(f"Nouveau tunnel créé. URL : {new_url}")
            log_tunnel_startup_time(start_time, end_time)

            if new_url != previous_url:
                send_email(new_url)
                log_url_change(previous_url, new_url)

            with open(LOG_FILE, "w") as log_file:
                log_file.write(new_url + "\n")

            log_custom_metric("Nouveau tunnel créé", 1)

    except Exception as e:
        logger.error(f"Erreur dans la gestion du tunnel: {str(e)}")
        log_tunnel_downtime()

if __name__ == "__main__":
    manage_tunnel()
    