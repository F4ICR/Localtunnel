#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import subprocess
import os
import re
import smtplib
from email.mime.text import MIMEText
import time
import requests  # Pour tester la connectivité HTTP

# Importer LOG_FILE et d'autres variables depuis settings.py
from settings import LOG_FILE, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL

# Fonction pour démarrer le tunnel Localtunnel
def start_tunnel(port, subdomain=None):
    with open(LOG_FILE, "w") as log_file:
        cmd = ["lt", "--port", str(port)]
        if subdomain:
            cmd += ["--subdomain", subdomain]
        subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
    time.sleep(2)  # Attendre que le tunnel démarre
    return read_tunnel_url_from_log()

# Fonction pour vérifier si le tunnel est déjà actif en utilisant pgrep
def is_tunnel_active(port):
    try:
        result = subprocess.run(["pgrep", "-f", f"lt --port {port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Erreur lors de la vérification du processus : {e}")
        return False

# Nouvelle fonction pour arrêter un processus existant du tunnel
def stop_existing_tunnel(port):
    try:
        result = subprocess.run(["pkill", "-f", f"lt --port {port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print(f"Le processus du tunnel sur le port {port} a été arrêté.")
        else:
            print(f"Aucun processus à arrêter pour le port {port}.")
    except Exception as e:
        print(f"Erreur lors de l'arrêt du processus : {e}")

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

# Nouvelle fonction pour tester la connectivité du tunnel via HTTP avec réessai
def test_tunnel_connectivity(tunnel_url):
    try:
        # Première tentative de connexion
        response = requests.get(tunnel_url, timeout=5)
        if response.status_code == 200:
            return True
        
        # Si la première tentative échoue, effectuer deux autres tentatives
        for _ in range(2):  # Répéter deux fois pour un total de trois tentatives
            time.sleep(3)  # Attendre 3 secondes avant de réessayer
            response = requests.get(tunnel_url, timeout=5)
            if response.status_code == 200:
                return True
        
        return False  # Retourne False si toutes les tentatives échouent
    except Exception as e:
        print(f"Erreur lors du test de connectivité : {e}")
        return False
    