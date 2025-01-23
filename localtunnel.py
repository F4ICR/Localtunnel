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
    TUNNEL_CHECK_INTERVAL,  # Intervalle pour vérifier la connectivité
    LT_PROCESS_CHECK_INTERVAL  # Intervalle pour surveiller le processus Localtunnel
)

# Importer les fonctions utilitaires depuis lib.py
from lib import (
    start_tunnel,
    stop_existing_tunnel,
    check_lt_process,  # Vérifie si le processus Localtunnel est actif
    read_tunnel_url_from_log,
    test_tunnel_connectivity,
    send_email  # Notification par email en cas de changement d'URL
)

# Importer le logger depuis logging_config.py
from logging_config import logger

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


# Nouvelle fonction : Surveillance périodique du processus Localtunnel
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


# Fonction existante : Gérer le cycle de vie du tunnel (connectivité)
def manage_tunnel():
    """
    Gère le cycle de vie du tunnel Localtunnel.
    Vérifie si un tunnel est actif et fonctionnel. Si ce n'est pas le cas, démarre un nouveau tunnel.
    """
    try:
        with lock:
            subdomain = SUBDOMAIN
            expected_url = f"https://{subdomain}.loca.lt"

            # Vérifiez si le tunnel attendu est déjà actif (évite les doublons)
            if expected_url in active_tunnels:
                logger.info(f"Le tunnel {expected_url} est déjà actif.")
                return

            # Lire l'URL actuelle du tunnel depuis le fichier log
            current_url = read_tunnel_url_from_log()

            # Tester la connectivité du tunnel actuel
            if current_url and test_tunnel_connectivity(current_url):
                logger.info(f"Le tunnel fonctionne correctement : {current_url}")
                log_tunnel_availability(current_url)
                log_custom_metric("Tunnel actif", 1)
                return

            # Si aucun tunnel fonctionnel n'est détecté, démarrer un nouveau tunnel
            logger.info("Aucun tunnel fonctionnel détecté. Démarrage d'un nouveau tunnel.")
            previous_url = current_url  # Sauvegarder l'URL précédente pour comparaison

            stop_existing_tunnel(PORT)  # Arrêter tout tunnel existant (au cas où)
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

                active_tunnels.append(new_url)  # Ajouter à la liste des tunnels actifs

                log_custom_metric("Nouveau tunnel créé", 1)

    except Exception as e:
        logger.error(f"Erreur dans la gestion du tunnel : {e}")
        duration_logger.end_tunnel()  # Assurez-vous que la durée est enregistrée même en cas d'erreur.


# Fonction principale : Boucle principale pour gérer les tunnels et surveiller les processus
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
            manage_tunnel()  # Appeler la fonction de gestion des tunnels
            
            # Pause avant la prochaine vérification de connectivité (intervalle configurable)
            time.sleep(TUNNEL_CHECK_INTERVAL)

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
