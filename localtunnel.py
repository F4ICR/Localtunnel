#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Importer les variables de configuration depuis settings.py
from settings import PORT, LOG_FILE, EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SUBDOMAIN

# Importer les fonctions utilitaires depuis lib.py
from lib import start_tunnel, is_tunnel_active, stop_existing_tunnel, send_email, read_tunnel_url_from_log, test_tunnel_connectivity

# Fonction principale pour gérer la connexion au tunnel
def manage_tunnel():
    if is_tunnel_active(PORT):
        print("Le tunnel est déjà actif.")
        
        # Lire l'URL actuelle du tunnel depuis le fichier de log
        current_url = read_tunnel_url_from_log()
        if current_url and test_tunnel_connectivity(current_url):
            print(f"Le tunnel fonctionne correctement : {current_url}")
            return  # Si tout va bien, on quitte la fonction
        else:
            print("Le tunnel actif semble inaccessible. Redémarrage nécessaire.")
            stop_existing_tunnel(PORT)  # Arrêter le processus existant
    else:
        print("Le tunnel n'est pas actif.")

    # Vérifier si une URL précédente existe dans le fichier de log
    previous_url = read_tunnel_url_from_log()
    if previous_url:
        print(f"Tentative de réutilisation de l'URL précédente : {previous_url}")
        global SUBDOMAIN
        SUBDOMAIN = previous_url.split("//")[1].split(".")[0]  # Extraire le sous-domaine précédent

    # Démarrer un nouveau tunnel et envoyer un email si nécessaire
    new_url = start_tunnel(PORT, SUBDOMAIN)
    
    if new_url:
        if new_url != previous_url:
            print(f"L'URL a changé. Nouvelle URL : {new_url}")
            send_email(new_url)  # Envoyer un email avec la nouvelle URL
            
            # Mettre à jour le fichier log avec la nouvelle URL
            with open(LOG_FILE, "w") as log_file:
                log_file.write(new_url + "\n")
        else:
            print(f"L'URL reste inchangée : {new_url}")
    else:
        print("Échec de la création d'un nouveau tunnel.")

if __name__ == "__main__":
    manage_tunnel()
