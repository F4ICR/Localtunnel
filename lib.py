#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import subprocess
import os
import re
import smtplib
from email.mime.text import MIMEText
import time
import requests  # Pour tester la connectivité HTTP
from settings import LOG_FILE, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL
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
        process = subprocess.Popen(
            cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp
        )

        pid_file = f"/tmp/localtunnel_{port}.pid"

        # Création sécurisée du fichier PID avec permissions restreintes
        with os.fdopen(os.open(pid_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
            f.write(str(process.pid))

        logger.info(
            f"Commande exécutée pour démarrer Localtunnel : {' '.join(cmd)} (PID: {process.pid})"
        )

    # Attendre que le tunnel démarre et vérifier périodiquement l'URL
    max_retries = 10  # Nombre maximum de tentatives
    delay = 1  # Délai entre les tentatives (en secondes)

    for attempt in range(max_retries):
        url = read_tunnel_url_from_log()  # Lire l'URL depuis le fichier log

        if url:
            logger.info(f"Tunnel démarré avec succès. URL : {url}")
            return url  # Retourner l'URL si elle est trouvée

        logger.warning(
            f"Tentative {attempt + 1}/{max_retries} : URL non trouvée. Nouvelle tentative dans {delay} seconde(s)."
        )
        time.sleep(delay)  # Attendre avant de réessayer

    # Si aucune URL n'est trouvée après toutes les tentatives, lever une exception
    error_message = (
        "Échec du démarrage du tunnel : aucune URL n'a été trouvée après plusieurs tentatives."
    )
    logger.error(error_message)
    raise Exception(error_message)


# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log():
    """
    Lit l'URL du tunnel à partir du fichier log généré par Localtunnel.
    """
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as log_file:
                lines = log_file.readlines()

                # Parcourir les lignes en sens inverse pour trouver la dernière URL valide
                for line in reversed(lines):
                    match = re.search(r"https://[^\s]+", line)
                    if match:
                        logger.debug(f"URL trouvée dans le fichier log : {match.group(0)}")
                        return match.group(0)

                logger.debug("Aucune URL trouvée dans le fichier log.")
                return None

        else:
            logger.warning(f"Le fichier log {LOG_FILE} n'existe pas.")
            return None

    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier log : {e}")
        return None


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


# Fonction pour vérifier si le tunnel est actif via le fichier PID
def is_tunnel_active(port):
    pid_file = f"/tmp/localtunnel_{port}.pid"
    if os.path.exists(pid_file):
        try:
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
                if is_process_running(pid):
                    logger.info(f"Le tunnel est actif sur le port {port} (PID: {pid}).")
                    return True
                else:
                    logger.warning(f"Le processus avec le PID {pid} n'est plus actif.")
                    os.remove(pid_file)  # Supprimer le fichier PID obsolète
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du fichier PID : {e}")
    else:
        logger.debug(f"Aucun fichier PID trouvé pour le port {port}.")
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


# Fonction pour enregistrer les changements d'URL dans un fichier dédié
def log_tunnel_change(previous_url, new_url):
    """
    Enregistre les changements d'URL du tunnel dans un fichier dédié.
    """
    change_log_file = "/tmp/tunnel_changes.log"  # Chemin du fichier de journal des changements
    try:
        with open(change_log_file, "a") as f:
            f.write(
                f"Changement détecté : {time.strftime('%Y-%m-%d %H:%M:%S')} - Ancienne URL : {previous_url or 'Aucune'} - Nouvelle URL : {new_url}\n"
            )
            logger.info(f"Changement d'URL enregistré dans {change_log_file}.")
    except Exception as e:
        logger.error(f"Erreur lors de l'enregistrement du changement d'URL : {e}")


# Fonction pour envoyer un email avec l'URL du tunnel
def send_email(tunnel_url):
    msg = MIMEText(f"Le tunnel est accessible à l'adresse suivante : {tunnel_url}")
    msg["Subject"] = "Localtunnel URL"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, EMAIL, msg.as_string())
            logger.info(f"L'URL a été envoyée à {EMAIL}. Tunnel URL : {tunnel_url}")
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi de l'email : {e}")


# Fonction pour tester la connectivité HTTP au tunnel
def test_tunnel_connectivity(tunnel_url, retries=3, delay=3, timeout=5):
    try:
        for attempt in range(retries):
            start_time = time.time()
            try:
                response = requests.get(tunnel_url, timeout=timeout)
                elapsed_time = time.time() - start_time
                if response.status_code == 200:
                    logger.info(
                        f"Connectivité réussie au tunnel ({tunnel_url}). Temps écoulé : {elapsed_time:.2f} secondes."
                    )
                    return True
            except requests.RequestException as e:
                elapsed_time = time.time() - start_time
                logger.warning(
                    f"Tentative {attempt + 1}/{retries} échouée après {elapsed_time:.2f} secondes : {e}"
                )
                if attempt < retries - 1:
                    time.sleep(delay)
        return False  # Échec après toutes les tentatives

    except Exception as e:
        logger.error(f"Erreur inattendue lors du test de connectivité : {e}")
        return False
