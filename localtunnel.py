#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Importer les variables de configuration depuis settings.py
from settings import PORT, LOG_FILE, EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SUBDOMAIN

# Importer les fonctions utilitaires depuis lib.py
from lib import start_tunnel, is_tunnel_active, stop_existing_tunnel, send_email, read_tunnel_url_from_log, test_tunnel_connectivity

# Importer le logger depuis logging_config.py
from logging_config import logger

# Importer les fonctions utilitaires depuis dependency_check.py
from dependency_check import verify_all_dependencies

# Fonction principale pour gérer la connexion au tunnel
def manage_tunnel():
    
    # Vérification des dépendances
    if not verify_all_dependencies():
        logger.error("Certaines dépendances sont manquantes. Arrêt du programme.")
        return
    
    # Vérification de l'installation de localtunnel
    if not is_lt_installed():
        logger.error("Localtunnel n'est pas installé. Arrêt du programme.")
        return
    
    # Vérifier si un tunnel est déjà actif sur le port spécifié
    if is_tunnel_active(PORT):
        logger.info("Le tunnel est déjà actif.")
        
        # Lire l'URL actuelle du tunnel depuis le fichier de log
        current_url = read_tunnel_url_from_log()
        
        # Tester la connectivité du tunnel actuel
        if current_url and test_tunnel_connectivity(current_url):
            logger.info(f"Le tunnel fonctionne correctement : {current_url}")
            return  # Si tout va bien avec la connectivité actuelle
        
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
    new_url = start_tunnel(PORT, SUBDOMAIN)
    if new_url:
        logger.info(f"Nouveau tunnel créé. URL : {new_url}")
        
        # Comparer avec l'URL précédente pour décider d'envoyer un email
        if new_url != previous_url:
            send_email(new_url)  # Envoyer un email avec la nouvelle URL
        
        # Mettre à jour le fichier log avec la nouvelle URL
        with open(LOG_FILE, "w") as log_file:
            log_file.write(new_url + "\n")

if __name__ == "__main__":
    manage_tunnel()
