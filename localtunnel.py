#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Importer les variables de configuration depuis settings.py
from settings import PORT, LOG_FILE, EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SUBDOMAIN

# Importer les fonctions utilitaires depuis lib.py
from lib import start_tunnel, is_tunnel_active, send_email, read_tunnel_url_from_log

# Fonction principale pour gérer la connexion au tunnel
def manage_tunnel():
    if is_tunnel_active(PORT):
        print("Le tunnel est déjà actif.")
    else:
        print("Le tunnel n'est pas actif.")

        # Vérifier si une URL précédente existe dans le fichier de log
        previous_url = read_tunnel_url_from_log(LOG_FILE)
        if previous_url:
            print(f"Tentative de réutilisation de l'URL précédente : {previous_url}")
            global SUBDOMAIN
            SUBDOMAIN = previous_url.split("//")[1].split(".")[0]  # Extraire le sous-domaine précédent

        # Démarrer un nouveau tunnel et récupérer l'URL
        new_url = start_tunnel(PORT, LOG_FILE, SUBDOMAIN)

        # Si une nouvelle URL est obtenue (même au premier lancement), envoyer un email
        if new_url:
            print(f"L'URL du tunnel : {new_url}")
            send_email(SMTP_USER, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, EMAIL, new_url)
        else:
            print("Erreur : Impossible d'obtenir une URL pour le tunnel.")

# Exécution principale du script
if __name__ == "__main__":
    manage_tunnel()

