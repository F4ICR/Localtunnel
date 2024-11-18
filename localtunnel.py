#!/usr/bin/env python3

import subprocess
import time
import re
import os
import smtplib
from email.mime.text import MIMEText

# Variables
PORT = 3000  # Le port local que vous souhaitez exposer
LOG_FILE = "tunnel_output.log"  # Fichier de log pour capturer la sortie du tunnel
EMAIL = "votre_mail.com"  # Remplacez par votre adresse email
SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP (exemple avec Gmail)
SMTP_PORT = 465  # Port SMTP sécurisé (SSL)
SMTP_USER = "votre_mail.com"  # Votre adresse Gmail (ou autre fournisseur)
SMTP_PASSWORD = "password"  # Mot de passe ou App Password (si Gmail)
SUBDOMAIN = None  # Sous-domaine souhaité (None pour un sous-domaine aléatoire)

# Fonction pour démarrer le tunnel Localtunnel
def start_tunnel():
    with open(LOG_FILE, "w") as log_file:
        # Démarrer Localtunnel avec ou sans sous-domaine spécifique en arrière-plan
        cmd = ["lt", "--port", str(PORT)]
        if SUBDOMAIN:
            cmd += ["--subdomain", SUBDOMAIN]
        subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)

    time.sleep(2)  # Attendre quelques secondes pour que le tunnel démarre

    # Lire l'URL du tunnel dans le fichier de log
    with open(LOG_FILE, "r") as log_file:
        log_content = log_file.read()
        match = re.search(r"https://[^\s]+", log_content)
        if match:
            tunnel_url = match.group(0)
            print(f"Tunnel démarré à l'adresse : {tunnel_url}")
            send_email(tunnel_url)  # Envoyer l'URL par email
            return tunnel_url
        else:
            print("Erreur : Impossible de trouver l'URL du tunnel.")
            return None

# Fonction pour vérifier si le tunnel est déjà actif en utilisant pgrep
def is_tunnel_active():
    try:
        result = subprocess.run(["pgrep", "-f", f"lt --port {PORT}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0  # Si pgrep trouve un processus, returncode sera 0
    except Exception as e:
        print(f"Erreur lors de la vérification du processus : {e}")
        return False

# Fonction pour envoyer un email avec l'URL du tunnel
def send_email(tunnel_url):
    msg = MIMEText(f"Le tunnel est accessible à l'adresse suivante : {tunnel_url}")
    msg['Subject'] = 'Localtunnel URL'
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, EMAIL, msg.as_string())
            print(f"L'URL a été envoyée à {EMAIL}.")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")

# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as log_file:
            log_content = log_file.read()
            match = re.search(r"https://[^\s]+", log_content)
            if match:
                return match.group(0)
    return None

# Fonction principale pour gérer la connexion au tunnel
def manage_tunnel():
    if is_tunnel_active():
        print("Le tunnel est déjà actif.")
    else:
        print("Le tunnel n'est pas actif.")
        
        # Vérifier si une URL précédente existe dans le fichier de log
        previous_url = read_tunnel_url_from_log()

        if previous_url:
            print(f"Tentative de réutilisation de l'URL précédente : {previous_url}")
            global SUBDOMAIN
            SUBDOMAIN = previous_url.split("//")[1].split(".")[0]  # Extraire le sous-domaine précédent
        
        new_url = start_tunnel()

        if new_url and new_url != previous_url:
            print(f"L'URL a changé. Nouvelle URL : {new_url}")
            send_email(new_url)

# Exécution principale du script
if __name__ == "__main__":
    manage_tunnel()
