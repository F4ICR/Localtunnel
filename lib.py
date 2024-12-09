#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Bibliothèques standard
import os
import re
import time
import logging

# Bibliothèques tierces
import smtplib
from email.mime.text import MIMEText
import requests

# Modules locaux
from settings import LOG_FILE, SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL

# Importer le module de journalisation
import logging

logger = logging.getLogger(__name__)  # Créer un logger pour ce module


''' Fonctions utilitaires générales '''

# Fonction pour écrire dans un fichier avec gestion des erreurs
def write_to_file(file_path, content):
    try:
        with open(file_path, "w") as f:
            f.write(content)
        logger.debug(f"Écriture réussie dans le fichier : {file_path}")
    except Exception as e:
        logger.error(f"Erreur lors de l'écriture dans le fichier {file_path} : {e}")


# Fonction pour lire un fichier avec gestion des erreurs
def read_from_file(file_path):
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier {file_path} : {e}")
        return None


'''Fonctions liées à la gestion des tunnels'''

# Fonction pour crée un fichier PID sécurisé avec des permissions restreintes
def create_secure_pid_file(pid_file, pid):
    try:
        # Définir les drapeaux pour créer un fichier sécurisé
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC
        mode = 0o600  # lecture/écriture uniquement pour le propriétaire
        
        # Créer le fichier avec les permissions définies
        fd = os.open(pid_file, flags, mode)
        with os.fdopen(fd, 'w') as f:
            f.write(f"{pid}\n")
        
        logger.info(f"Fichier PID créé : {pid_file} (PID: {pid})")
    except Exception as e:
        logger.error(f"Erreur lors de la création du fichier PID {pid_file} : {e}")
        raise


# Fonction pour vérifier si un processus est actif à partir de son PID
def is_process_running(pid):
    try:
        os.kill(pid, 0)  # Envoie un signal nul pour vérifier l'existence du processus
        return True
    except OSError:
        return False


# Fonction pour démarrer le tunnel Localtunnel
def start_tunnel(port, subdomain=None):
    """
    Démarre un tunnel Localtunnel pour exposer un port local.
    Si un sous-domaine est spécifié, il sera utilisé ; sinon, un sous-domaine aléatoire sera généré.
    """
    if not is_lt_installed():
        logger.error("Impossible de démarrer le tunnel : 'lt' n'est pas installé.")
        return
    
    with open(LOG_FILE, "w") as log_file:
        # Construire la commande pour démarrer Localtunnel
        cmd = ["lt", "--port", str(port)]
        if subdomain:
            cmd += ["--subdomain", subdomain]

        # Lancer le processus en arrière-plan et capturer le PID
        process = subprocess.Popen(
            cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp)

        pid_file = f"/tmp/localtunnel_{port}.pid"
        write_to_file(pid_file, str(process.pid))
        logger.info(
            f"Commande exécutée pour démarrer Localtunnel : {' '.join(cmd)} (PID: {process.pid})")

        # Attendre que le tunnel démarre et vérifier périodiquement l'URL
        max_retries = 10  # Nombre maximum de tentatives
        delay = 2  # Délai entre les tentatives (en secondes)
        for attempt in range(max_retries):
            url = read_tunnel_url_from_log()  # Lire l'URL depuis le fichier log
            if url:
                logger.info(f"Tunnel démarré avec succès. URL : {url}")
                return url  # Retourner l'URL si elle est trouvée

            logger.warning(
                f"Tentative {attempt + 1}/{max_retries} : URL non trouvée. Nouvelle tentative dans {delay} seconde(s).")
            time.sleep(delay)  # Attendre avant de réessayer

        # Si aucune URL n'est trouvée après toutes les tentatives, lever une exception
        error_message = (
            "Échec du démarrage du tunnel : aucune URL n'a été trouvée après plusieurs tentatives."
        )
        logger.error(error_message)
        raise Exception(error_message)


# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log():
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
        else:
            logger.warning(f"Le fichier log {LOG_FILE} n'existe pas.")
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier log : {e}")
    return None


# Fonction pour vérifier si le tunnel est actif via le fichier PID
def is_tunnel_active(port):
    pid_file = f"/tmp/localtunnel_{port}.pid"

    if os.path.exists(pid_file):
        pid = read_from_file(pid_file)
        if pid and is_process_running(int(pid)):
            logger.info(f"Le tunnel est actif sur le port {port} (PID: {pid}).")
            return True
        else:
            logger.warning(f"Le processus avec le PID {pid} n'est plus actif.")
            os.remove(pid_file)  # Supprimer le fichier PID obsolète
    else:
        logger.debug(f"Aucun fichier PID trouvé pour le port {port}.")
    return False


# Fonction pour arrêter le processus Localtunnel associé au port spécifié en utilisant son PID
def stop_existing_tunnel(port):
    pid_file = f"/tmp/localtunnel_{port}.pid"

    if os.path.exists(pid_file):
        pid = read_from_file(pid_file)
        if pid and is_process_running(int(pid)):
            os.kill(int(pid), 15)  # Envoyer un signal SIGTERM pour arrêter proprement le processus
            logger.info(
                f"Le processus du tunnel sur le port {port} a été arrêté (PID: {pid}).")
        else:
            logger.warning(
                f"Aucun processus actif trouvé pour le PID : {pid}. Suppression du fichier PID.")
        os.remove(pid_file)
    else:
        logger.warning(f"Aucun fichier PID trouvé pour le port {port}. Aucun processus à arrêter.")


'''Fonctions liées à la journalisation et au suivi'''

# Fonction pour enregistrer les changements d'URL dans un fichier dédié
def log_tunnel_change(previous_url, new_url):
    change_log_file = "/tmp/tunnel_changes.log"
    
    content = (
        f"Changement détecté : {time.strftime('%Y-%m-%d %H:%M:%S')} - "
        f"Ancienne URL : {previous_url or 'Aucune'} - Nouvelle URL : {new_url}\n")
    
    write_to_file(change_log_file, content)


'''Fonctions liées à la communication'''

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


# Fonction pour tester la connectivité HTTP au tunnel en effectuant plusieurs tentatives.
def test_tunnel_connectivity(tunnel_url, retries=3, delay=3, timeout=5):
    for attempt in range(retries):
        start_time = time.time()
        try:
            response = requests.get(tunnel_url, timeout=timeout)
            elapsed_time = time.time() - start_time
            if response.status_code == 200:
                logger.info(
                    f"Connectivité réussie au tunnel ({tunnel_url}). Temps écoulé : {elapsed_time:.2f} secondes.")
                return True
        except requests.RequestException as e:
            elapsed_time = time.time() - start_time
            logger.warning(
                f"Tentative {attempt + 1}/{retries} échouée après {elapsed_time:.2f} secondes : {e}")
            if attempt < retries - 1:
                time.sleep(delay)
    
    return False
