#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Bibliothèques standard
import time
import sys
from datetime import datetime

# Importer les variables de configuration depuis settings.py
from settings import (
    PORT,
    TUNNEL_OUTPUT_FILE,
    EMAIL,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    SUBDOMAIN,
    TUNNEL_CHECK_INTERVAL
)

# Importer les fonctions utilitaires depuis lib.py
from lib import (
    start_tunnel,
    is_tunnel_active,
    stop_existing_tunnel,
    send_email,
    read_tunnel_url_from_log,
    test_tunnel_connectivity
)

# Importer le logger depuis logging_config.py
from logging_config import logger

# Import autres depuis dependency_check
from dependency_check import verify_all_dependencies

# Import des métriques depuis metrics.py
from metrics import (
    log_tunnel_availability,
    log_custom_metric,
    log_tunnel_startup_time,
    log_connectivity_failure,
    log_url_change,
    log_tunnel_downtime
)

# Import de la gestion des durées depuis tunnel_duration_logger.py
from tunnel_duration_logger import TunnelDurationLogger

# Initialisation du gestionnaire de durées de tunnel
duration_logger = TunnelDurationLogger()


def manage_tunnel():
    """
    Gère le cycle de vie du tunnel Localtunnel.
    """
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
            else:
                log_tunnel_downtime()

        # Si aucun tunnel n'est actif, vérifier les dépendances
        logger.info("Aucun tunnel actif détecté. Vérification des dépendances en cours.")
        if not verify_all_dependencies():
            logger.error("Certaines dépendances sont manquantes ou incorrectes.")
            return

        # Arrêter le tunnel existant si nécessaire
        stop_existing_tunnel(PORT)

        # Récupérer l'URL précédente
        previous_url = read_tunnel_url_from_log()

        # Démarrer un nouveau tunnel et enregistrer son début avec son URL
        start_time = datetime.now()
        new_url = start_tunnel(PORT, SUBDOMAIN)
        
        if new_url:
            duration_logger.end_tunnel()  # Terminer le cycle précédent (s'il existe)
            duration_logger.start_tunnel(new_url)  # Démarrer un nouveau cycle avec l'URL actuelle
            
            end_time = datetime.now()
            logger.info(f"Nouveau tunnel créé. URL : {new_url}")
            log_tunnel_startup_time(start_time, end_time)

            # Notifier si l'URL a changé
            if new_url != previous_url:
                send_email(new_url)
                log_url_change(previous_url, new_url)

            # Écrire l'URL dans le fichier log principal
            with open(TUNNEL_OUTPUT_FILE, "w") as log_file:
                log_file.write(new_url + "\n")

            log_custom_metric("Nouveau tunnel créé", 1)

    except Exception as e:
        # Enregistrer l'erreur et signaler un temps d'arrêt du tunnel
        logger.error(f"Erreur dans la gestion du tunnel : {str(e)}")
        duration_logger.end_tunnel()  # Assurez-vous que la durée est enregistrée même en cas d'erreur.
        raise  # Relancer l'exception pour qu'elle soit capturée globalement


def main():
    """
    Point d'entrée principal de l'application avec gestion globale des exceptions.
    """
    try:
        logger.info("Démarrage de l'application Localtunnel Manager.")
        
        while True:
            # Enregistrer le début du cycle
            cycle_start_time = time.time()
            
            # Gérer le tunnel
            manage_tunnel()
            
            # Calculer le temps pris par les opérations
            cycle_duration = time.time() - cycle_start_time
            
            # Calculer le temps restant avant la prochaine vérification
            sleep_time = max(0, TUNNEL_CHECK_INTERVAL - cycle_duration)
            
            logger.debug(f"Durée du cycle : {cycle_duration:.2f} secondes. Pause avant le prochain cycle : {sleep_time:.2f} secondes.")
            
            # Attendre avant de relancer le cycle
            time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        logger.warning("Interruption par l'utilisateur (Ctrl+C). Arrêt du programme.")
    
    except Exception as e:
        logger.critical(f"Erreur critique non gérée : {str(e)}", exc_info=True)
    
    finally:
        logger.info("Arrêt propre de l'application Localtunnel Manager.")
        sys.exit(1)

if __name__ == "__main__":
    main()
    