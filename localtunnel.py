#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

from settings import PORT, LOG_FILE, EMAIL, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SUBDOMAIN
from lib import start_tunnel, is_tunnel_active, send_email, read_tunnel_url_from_log
import os

def manage_tunnel():
    if is_tunnel_active(PORT):
        print("Le tunnel est déjà actif.")
    else:
        print("Le tunnel n'est pas actif.")

        # Lire l'URL précédente en toute sécurité
        previous_url = read_tunnel_url_from_log(LOG_FILE)

        if previous_url:
            print(f"Tentative de réutilisation de l'URL précédente : {previous_url}")
            global SUBDOMAIN
            SUBDOMAIN = previous_url.split("//")[1].split(".")[0]  # Extraire le sous-domaine précédent

        # Démarrer un nouveau tunnel (avec ou sans sous-domaine précédent)
        new_url = start_tunnel(PORT, LOG_FILE, SUBDOMAIN)

        # Vérifier si une nouvelle URL a été générée et envoyer un email
        if new_url and (not previous_url or new_url != previous_url):
            print(f"Nouvelle URL générée : {new_url}")
            send_email(SMTP_USER, SMTP_PASSWORD, SMTP_SERVER, SMTP_PORT, EMAIL, new_url)
        else:
            print("Aucun email envoyé car l'URL n'a pas changé.")

if __name__ == "__main__":
    manage_tunnel()
