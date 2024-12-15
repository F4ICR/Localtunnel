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
from metrics import log_tunnel_availability, log_custom_metric, log_tunnel_startup_time, log_connectivity_failure, log_url_change

# Fonction principale pour gérer la connexion au tunnel
def manage_tunnel():
    # Vérifiez si un tunnel est déjà actif sur le port spécifié
    if is_tunnel_active(PORT):
        logger.info("Le tunnel est déjà actif.")
        # Lire l'URL actuelle du tunnel depuis le fichier de log
        current_url = read_tunnel_url_from_log()
        # Tester la connectivité du tunnel actuel et enregistrer la métrique
        if current_url and test_tunnel_connectivity(current_url):
            logger.info(f"Le tunnel fonctionne correctement : {current_url}")
            log_tunnel_availability(current_url)  # Enregistrer la disponibilité du tunnel
            log_custom_metric("Tunnel actif", 1)
            return  # Si tout va bien avec la connectivité actuelle
    else:
        # Si aucun tunnel n'est actif, vérifier les dépendances
        logger.info("Aucun tunnel actif détecté. Vérification des dépendances en cours.")
        if verify_all_dependencies():
            logger.info("Toutes les dépendances sont satisfaites.")
        else:
            logger.error("Certaines dépendances sont manquantes ou incorrectes.")
            return  # Arrêter l'exécution si les dépendances ne sont pas satisfaites

    # Si la connectivité échoue ou n'existe pas
    logger.warning("Le tunnel actif semble inaccessible. Redémarrage nécessaire.")
    stop_existing_tunnel(PORT)  # Arrêter le processus existant avant de créer un nouveau tunnel

    # Lire l'URL précédente du fichier log pour tenter de réutiliser le sous-domaine
    previous_url = read_tunnel_url_from_log()
    if previous_url:
        logger.info(f"Tentative de réutilisation de l'URL précédente : {previous_url}")
        global SUBDOMAIN
        SUBDOMAIN = previous_url.split("//")[1].split(".")[0]  # Extraire le sous-domaine précédent

    # Démarrer un nouveau tunnel et envoyer un email si nécessaire
    start_time = time.time()  # Commencer à mesurer le temps de démarrage du tunnel
    new_url = start_tunnel(PORT, SUBDOMAIN)
    end_time = time.time()  # Fin de la mesure du temps de démarrage

    if new_url:
        logger.info(f"Nouveau tunnel créé. URL : {new_url}")
        log_tunnel_startup_time(start_time, end_time)  # Enregistrer le temps de démarrage du tunnel

        # Comparer avec l'URL précédente pour décider d'envoyer un email et enregistrer le changement d'URL
        if new_url != previous_url:
            send_email(new_url)  # Envoyer un email avec la nouvelle URL
            log_url_change(previous_url, new_url)  # Enregistrer le changement d'URL

        # Mettre à jour le fichier log avec la nouvelle URL
        with open(LOG_FILE, "w") as log_file:
            log_file.write(new_url + "\n")

        # Enregistrer la métrique pour le nouveau tunnel créé
        log_custom_metric("Nouveau tunnel créé", 1)

if __name__ == "__main__":
    manage_tunnel()
    