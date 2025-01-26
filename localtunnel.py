#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Bibliothèques standard
import time
import sys
import threading
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
    TUNNEL_CHECK_INTERVAL,
    LT_PROCESS_CHECK_INTERVAL
)

# Importer les fonctions utilitaires depuis lib.py
from lib import (
    start_tunnel,
    is_tunnel_active,
    stop_existing_tunnel,
    send_email,
    read_tunnel_url_from_log,
    test_tunnel_connectivity,
    check_lt_process  # Vérifie si le processus Localtunnel est actif
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

# Liste globale pour suivre les tunnels actifs (éviter les doublons)
active_tunnels = []  # Contient les URLs des tunnels actuellement actifs

# Verrou pour synchroniser les accès à `active_tunnels`
lock = threading.Lock()


# Surveillance périodique du processus Localtunnel
def monitor_lt_process():
    """
    Vérifie périodiquement si le processus Localtunnel est actif.
    Si le processus n'est pas actif, tente de redémarrer le tunnel.
    """
    while True:
        try:
            with lock:
                # Vérifier si le processus Localtunnel est actif sur le port spécifié
                if not check_lt_process(PORT):
                    logger.warning("Le processus Localtunnel n'est pas actif. Tentative de redémarrage.")
                    stop_existing_tunnel(PORT)  # Arrêter tout tunnel existant
                    
                    # Démarrer un nouveau tunnel et mettre à jour la liste des tunnels actifs
                    new_url = start_tunnel(PORT, SUBDOMAIN)
                    if new_url and new_url not in active_tunnels:
                        active_tunnels.append(new_url)
                        logger.info(f"Nouveau tunnel démarré : {new_url}")
        except Exception as e:
            logger.error(f"Erreur lors de la surveillance du processus Localtunnel : {e}")
        
        # Pause avant la prochaine vérification (intervalle configurable)
        time.sleep(LT_PROCESS_CHECK_INTERVAL)


# Gérer le cycle de vie du tunnel (connectivité)
def manage_tunnel():
    """
    Gère le cycle de vie du tunnel Localtunnel.
    Vérifie si un tunnel est actif et fonctionnel. Si ce n'est pas le cas, démarre un nouveau tunnel.
    """
    try:
        with lock:
            subdomain = SUBDOMAIN

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
                    logger.warning("Le tunnel actif semble ne pas être fonctionnel.")
                    log_tunnel_downtime()

            # Si aucun tunnel n'est actif, vérifier les dépendances
            logger.info("Aucun tunnel actif détecté. Vérification des dépendances en cours.")
            if not verify_all_dependencies():
                logger.error("Certaines dépendances sont manquantes ou incorrectes.")
                return

            # Arrêter le tunnel existant si nécessaire
            stop_existing_tunnel(PORT)

            # Terminer l'enregistrement de l'ancien cycle de durée (s'il existe)
            duration_logger.end_tunnel()

            # Récupérer l'URL précédente pour comparaison
            previous_url = read_tunnel_url_from_log()

            # Démarrer un nouveau tunnel et enregistrer son début avec son URL
            start_time = datetime.now()
            new_url = start_tunnel(PORT, subdomain)

            if new_url:
                # Enregistrer le début du nouveau cycle de durée
                duration_logger.start_tunnel(new_url)

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

                active_tunnels.append(new_url)  # Ajouter à la liste des tunnels actifs
                log_custom_metric("Nouveau tunnel créé", 1)
            else:
                logger.error("Échec de la création d'un nouveau tunnel.")

    except Exception as e:
        logger.error(f"Erreur dans la gestion du tunnel : {e}", exc_info=True)
        # Assurez-vous que la durée du dernier tunnel est enregistrée même en cas d'erreur
        duration_logger.end_tunnel()


# Boucle principale pour gérer les tunnels et surveiller les processus
def main():
    """
    Point d'entrée principal de l'application avec gestion globale des exceptions.
    - Lance un thread séparé pour surveiller le processus Localtunnel.
    - Gère la connectivité du tunnel dans une boucle principale.
    """
    try:
        logger.info("Démarrage de l'application Localtunnel Manager.")

        # Lancer un thread séparé pour surveiller le processus Localtunnel
        threading.Thread(target=monitor_lt_process, daemon=True).start()

        # Boucle principale pour gérer la connectivité du tunnel
        while True:
            cycle_start_time = time.time()  # Début du cycle
            
            manage_tunnel()  # Appeler la fonction de gestion des tunnels
            
            cycle_duration = time.time() - cycle_start_time
            sleep_time = max(0, TUNNEL_CHECK_INTERVAL - cycle_duration)
            
            logger.debug(f"Durée du cycle : {cycle_duration:.2f} secondes. Pause avant le prochain cycle : {sleep_time:.2f} secondes.")
            
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        logger.warning("Interruption par l'utilisateur (Ctrl+C). Arrêt du programme.")

    except Exception as e:
        logger.critical(f"Erreur critique non gérée : {str(e)}", exc_info=True)

    finally:
        logger.info("Arrêt propre de l'application Localtunnel Manager.")
        sys.exit(1)


# Point d'entrée du script
if __name__ == "__main__":
    main()
    