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
        # Tester la connectivité du tunnel actuel
        if current_url and test_tunnel_connectivity(current_url):
            print(f"Le tunnel fonctionne correctement : {current_url}")
            return  # Si tout va bien avec la connectivité actuelle
        else:
            print("Le tunnel actif semble inaccessible. Redémarrage nécessaire.")
            # Envoyer un email pour informer que le tunnel était inaccessible
            if current_url:
                send_email(f"Le tunnel précédent à l'adresse {current_url} était inaccessible.")
            stop_existing_tunnel(PORT)  # Arrêter le processus existant avant de créer un nouveau tunnel

    # Démarrer un nouveau tunnel et envoyer un email si nécessaire
    new_url = start_tunnel(PORT)
    if new_url:
        print(f"Nouveau tunnel créé. URL : {new_url}")
        # Mettre à jour le fichier log avec la nouvelle URL
        with open(LOG_FILE, "w") as log_file:
            log_file.write(new_url + "\n")
        send_email(new_url)  # Envoyer un email avec la nouvelle URL

if __name__ == "__main__":
    manage_tunnel()
