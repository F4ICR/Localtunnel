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

# Importer le module de journalisation
import logging

logger = logging.getLogger(__name__)  # Créer un logger pour ce module

# Fonction pour démarrer le tunnel Localtunnel
def start_tunnel(port, subdomain=None):
    """
    Démarre un tunnel Localtunnel pour exposer un port local.
    Si un sous-domaine est spécifié, il sera utilisé ; sinon, un sous-domaine aléatoire sera généré.
    """
    with open(LOG_FILE, "w") as log_file:
        # Construire la commande pour démarrer Localtunnel
        cmd = ["lt", "--port", str(port)]
        if subdomain:
            cmd += ["--subdomain", subdomain]

        # Lancer le processus en arrière-plan
        subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
        logger.info(f"Commande exécutée pour démarrer Localtunnel : {' '.join(cmd)}")

    # Attendre que le tunnel démarre et vérifier périodiquement l'URL
    max_retries = 10  # Nombre maximum de tentatives
    delay = 1         # Délai entre les tentatives (en secondes)

    for attempt in range(max_retries):
        url = read_tunnel_url_from_log()  # Lire l'URL depuis le fichier log
        if url:
            logger.info(f"Tunnel démarré avec succès. URL : {url}")
            return url  # Retourner l'URL si elle est trouvée
        logger.warning(f"Tentative {attempt + 1}/{max_retries} : URL non trouvée. Nouvelle tentative dans {delay} seconde(s).")
        time.sleep(delay)  # Attendre avant de réessayer

    # Si aucune URL n'est trouvée après toutes les tentatives, lever une exception
    error_message = "Échec du démarrage du tunnel : aucune URL n'a été trouvée après plusieurs tentatives."
    logger.error(error_message)
    raise Exception(error_message)

# Fonction pour vérifier si le tunnel est déjà actif en utilisant pgrep
def is_tunnel_active(port):
    try:
        result = subprocess.run(["pgrep", "-f", f"lt --port {port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du processus : {e}")
        return False

# Nouvelle fonction pour arrêter un processus existant du tunnel
def stop_existing_tunnel(port):
    try:
        result = subprocess.run(["pkill", "-f", f"lt --port {port}"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            logger.info(f"Le processus du tunnel sur le port {port} a été arrêté.")
        else:
            logger.warning(f"Aucun processus à arrêter pour le port {port}.")
    except Exception as e:
        logger.error(f"Erreur lors de l'arrêt du processus : {e}")

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
            logger.info(f"L'URL a été envoyée à {EMAIL}.")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email : {e}")

# Fonction pour lire l'URL depuis le fichier log existant (inchangée)
def read_tunnel_url_from_log():
    """
    Lit l'URL du tunnel à partir du fichier log généré par Localtunnel.
    """
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as log_file:
            log_content = log_file.read()
            match = re.search(r"https://[^\s]+", log_content)
            if match:
                return match.group(0)
    return None

# Fonction pour tester la connectivité du tunnel via HTTP en effectuant plusieurs tentatives
def test_tunnel_connectivity(tunnel_url, retries=3, delay=3, timeout=5):
    """
    Teste la connectivité HTTP du tunnel en effectuant plusieurs tentatives.
    """
    try:
        for attempt in range(retries):
            try:
                response = requests.get(tunnel_url, timeout=timeout)
                if response.status_code == 200:
                    return True
            except requests.RequestException as e:
                logger.warning(f"Tentative {attempt + 1}/{retries} échouée : {e}")
                if attempt < retries - 1:  # Attente avant la prochaine tentative
                    time.sleep(delay)
        return False  # Échec après toutes les tentatives
    except Exception as e:
        logger.error(f"Erreur inattendue lors du test de connectivité : {e}")
        return False
