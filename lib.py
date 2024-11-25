#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import subprocess
import os
import re
import smtplib
from email.mime.text import MIMEText
import time

# Importer LOG_FILE depuis settings.py
from settings import LOG_FILE

# Fonction pour démarrer le tunnel Localtunnel
def start_tunnel(port, log_file, subdomain=None):
    with open(log_file, "w") as log_file:
        # Démarrer Localtunnel avec ou sans sous-domaine spécifique en arrière-plan
        cmd = ["lt", "--port", str(port)]
        if subdomain:
            cmd += ["--subdomain", subdomain]
        subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
    time.sleep(2)  # Attendre quelques secondes pour que le tunnel démarre

    # Lire l'URL du tunnel dans le fichier de log
    return read_tunnel_url_from_log(log_file.name)

# Fonction pour vérifier si le tunnel est déjà actif en utilisant pgrep
def is_tunnel_active(port):
    try:
        result = subprocess.run(["pgrep", "-f", f"lt --port {port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0  # Si pgrep trouve un processus, returncode sera 0
    except Exception as e:
        print(f"Erreur lors de la vérification du processus : {e}")
        return False

# Fonction pour envoyer un email avec l'URL du tunnel
def send_email(smtp_user, smtp_password, smtp_server, smtp_port, email_to, tunnel_url):
    msg = MIMEText(f"Le tunnel est accessible à l'adresse suivante : {tunnel_url}")
    msg['Subject'] = 'Localtunnel URL'
    msg['From'] = smtp_user
    msg['To'] = email_to

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, email_to, msg.as_string())
            print(f"L'URL a été envoyée à {email_to}.")
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")

# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log(log_file):
    # Vérifier si le fichier existe et n'est pas vide
    if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
        with open(log_file, "r") as file:
            log_content = file.read()
            match = re.search(r"https://[^\s]+", log_content)
            if match:
                return match.group(0)
    else:
        print("Le fichier de log est absent ou vide.")
    return None
