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

        # Lancer le processus en arrière-plan et capturer le PID
        process = subprocess.Popen(cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)
        pid_file = f"/tmp/localtunnel_{port}.pid"

        # Création sécurisée du fichier PID avec permissions restreintes
        with os.fdopen(os.open(pid_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
            f.write(str(process.pid))

        logger.info(f"Commande exécutée pour démarrer Localtunnel : {' '.join(cmd)} (PID: {process.pid})")

        # Attendre que le tunnel démarre et vérifier périodiquement l'URL
        max_retries = 10  # Nombre maximum de tentatives
        delay = 1  # Délai entre les tentatives (en secondes)

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
        logger.info(f"Vérification de l'état du tunnel sur le port {port}. Résultat : {'actif' if result.returncode == 0 else 'inactif'}.")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du processus : {e}")
        return False

# Fonction pour vérifier si un processus est actif à partir de son PID
def is_process_running(pid):
    """
    Vérifie si un processus avec le PID donné est en cours d'exécution.
    """
    try:
        os.kill(pid, 0)  # Envoie un signal nul pour vérifier l'existence du processus
        return True
    except OSError:
        return False

# Fonction pour arrêter un processus existant du tunnel
def stop_existing_tunnel(port):
    """
    Arrête le processus Localtunnel associé au port spécifié en utilisant son PID.
    """
    try:
        pid_file = f"/tmp/localtunnel_{port}.pid"
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())

            # Vérification si le processus est actif avant de l'arrêter
            if is_process_running(pid):
                os.kill(pid, 15)  # Envoyer un signal SIGTERM pour arrêter proprement le processus
                logger.info(f"Le processus du tunnel sur le port {port} a été arrêté (PID: {pid}).")
            else:
                logger.warning(f"Aucun processus actif trouvé pour le PID : {pid}. Suppression du fichier PID.")

            os.remove(pid_file)
        else:
            logger.warning(f"Aucun fichier PID trouvé pour le port {port}. Aucun processus à arrêter.")
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
            logger.info(f"L'URL a été envoyée à {EMAIL}. Tunnel URL : {tunnel_url}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email : {e}")

# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log():
    """
    Lit l'URL du tunnel à partir du fichier log généré par Localtunnel.
    """
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as log_file:
            log_content = log_file.read()
            match = re.search(r"https://[^\s]+", log_content)
            if match:
                logger.debug("URL trouvée dans le fichier log.")
                return match.group(0)
    logger.debug("Aucune URL trouvée dans le fichier log.")
    return None

# Fonction pour tester la connectivité du tunnel via HTTP
def test_tunnel_connectivity(tunnel_url, retries=3, delay=3, timeout=5):
    try:
        for attempt in range(retries):
            start_time = time.time()
            try:
                response = requests.get(tunnel_url, timeout=timeout)
                elapsed_time = time.time() - start_time
                if response.status_code == 200:
                    logger.info(f"Connectivité réussie au tunnel ({tunnel_url}). Temps écoulé : {elapsed_time:.2f} secondes.")
                    return True
            except requests.RequestException as e:
                elapsed_time = time.time() - start_time
                logger.warning(f"Tentative {attempt + 1}/{retries} échouée après {elapsed_time:.2f} secondes : {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        return False  # Échec après toutes les tentatives
    except Exception as e:
        logger.error(f"Erreur inattendue lors du test de connectivité : {e}")
        return False
