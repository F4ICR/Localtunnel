#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Bibliothèques standard
import os
import re
import time
import subprocess
import logging
from datetime import datetime

# Bibliothèques tierces
from metrics import save_start_time, log_tunnel_availability
import smtplib
from email.mime.text import MIMEText
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Modules locaux
from settings import (
  TUNNEL_OUTPUT_FILE, 
  SMTP_SERVER, 
  SMTP_PORT, 
  SMTP_USER, 
  SMTP_PASSWORD, 
  EMAIL,
  EMAIL_NOTIFICATIONS,
  MAX_RETRIES, 
  DELAY_RETRIES,
  TUNNEL_RETRIES, 
  TUNNEL_DELAY, 
  TUNNEL_TIMEOUT, 
  HTTP_SUCCESS_CODE
)

# Importer le module de journalisation
from logging_config import logger


''' Fonctions utilitaires générales '''

# Fonction permettant de vérifier la présence de 'lt'
def is_lt_installed():
    """
    Vérifie si l'outil 'lt' (Localtunnel) est installé et accessible.
    Retourne True si 'lt' est trouvé, False sinon.
    """
    try:
        # Vérifie si 'lt' est accessible via le PATH
        subprocess.run(["lt", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        logger.info("L'outil 'lt' (Localtunnel) est installé.")
        return True
    except FileNotFoundError:
        logger.error("L'outil 'lt' (Localtunnel) n'est pas installé. Veuillez l'installer avec 'npm install -g localtunnel'.")
        return False
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors de la vérification de 'lt' : {e}")
        return False


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
    """
    # Import au début de la fonction
    from metrics import save_start_time, log_tunnel_availability
    
    # Récupérer l'URL précédente avant toute chose
    previous_url = read_tunnel_url_from_log()

    # Vérifier si un tunnel est déjà actif
    if is_tunnel_active(port):
        if previous_url:
            logger.info(f"Réutilisation du tunnel existant sur le port {port} : {previous_url}")
            log_tunnel_availability(previous_url)
            return previous_url

    # Vérifier si 'lt' est installé
    if not is_lt_installed():
        logger.error("Impossible de démarrer le tunnel : 'lt' n'est pas installé.")
        return

    # Utiliser le sous-domaine de l'URL précédente si aucun n'est spécifié
    if not subdomain and previous_url:
        try:
            subdomain = previous_url.split("//")[1].split(".")[0]
            logger.info(f"Réutilisation du sous-domaine précédent : {subdomain}")
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du sous-domaine : {e}")

    with open(TUNNEL_OUTPUT_FILE, "w") as log_file:
        cmd = ["lt", "--port", str(port)]
        if subdomain:
            cmd += ["--subdomain", subdomain]

        try:
            process = subprocess.Popen(
                cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp
            )
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du processus Localtunnel : {e}")
            raise Exception("Échec du démarrage du processus Localtunnel.")

        # Enregistrer l'heure de démarrage
        save_start_time()

        pid_file = f"/tmp/localtunnel_{port}.pid"
        write_to_file(pid_file, str(process.pid))
        logger.info(f"Commande exécutée pour démarrer Localtunnel : {' '.join(cmd)} (PID: {process.pid})")

        # Attendre et vérifier l'URL        
        for attempt in range(MAX_RETRIES):
            url = read_tunnel_url_from_log()
            if url:
                logger.info(f"Tunnel démarré avec succès. URL : {url}")
                log_tunnel_availability(url)
                return url
            logger.warning(f"Tentative {attempt + 1}/{MAX_RETRIES} : URL non trouvée. Nouvelle tentative dans {DELAY_RETRIES} seconde(s).")
            time.sleep(DELAY_RETRIES)

        # Gestion des erreurs spécifiques aux serveurs Localtunnel
        error_message = (
            "Échec du démarrage du tunnel : aucune URL n'a été trouvée après plusieurs tentatives. "
            "Cela peut être dû à une indisponibilité temporaire des serveurs Localtunnel."
        )
        logger.error(error_message)

        # Ajouter une boucle de 5 cycles pour réessayer avec une attente prolongée
        retry_wait_time = 60  # Temps d'attente avant chaque nouvelle tentative (en secondes)
        for retry_cycle in range(5):
            logger.info(f"Cycle de réessai {retry_cycle + 1}/5 : Attente de {retry_wait_time} secondes avant une nouvelle tentative...")
            time.sleep(retry_wait_time)

            for attempt in range(MAX_RETRIES):
                url = read_tunnel_url_from_log()
                if url:
                    logger.info(f"Tunnel redémarré avec succès après attente. URL : {url}")
                    log_tunnel_availability(url)
                    return url
                logger.warning(f"Tentative supplémentaire {attempt + 1}/{MAX_RETRIES} : URL non trouvée.")
                time.sleep(DELAY_RETRIES)

        # Si toutes les tentatives échouent, lever une exception critique
        raise Exception("Impossible de démarrer le tunnel après plusieurs tentatives.")


         
# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log():
    try:
        if os.path.exists(TUNNEL_OUTPUT_FILE):
            with open(TUNNEL_OUTPUT_FILE, "r") as log_file:
                lines = log_file.readlines()
                # Parcourir les lignes en sens inverse pour trouver la dernière URL valide
                for line in reversed(lines):
                    match = re.search(r"https://[^\s]+", line)
                    if match:
                        logger.debug(f"URL trouvée dans le fichier log : {match.group(0)}")
                        return match.group(0)
        else:
            logger.warning(f"Le fichier log {TUNNEL_OUTPUT_FILE} n'existe pas.")
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
    if not EMAIL_NOTIFICATIONS:
        logger.info("L'envoi des emails est désactivé.")
        return
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


# Fonction pour tester la connectivité HTTP au tunnel en effectuant plusieurs tentatives
def test_tunnel_connectivity(tunnel_url, retries=5, timeout=10, backoff_factor=0.5):
    """
    Teste la connectivité du tunnel avec gestion des tentatives via urllib3 Retry.
    
    :param tunnel_url: URL du tunnel à tester.
    :param retries: Nombre total de tentatives avant d'abandonner.
    :param timeout: Temps maximum (en secondes) pour chaque requête.
    :param backoff_factor: Facteur pour le délai exponentiel entre les tentatives.
    :return: True si la connexion réussit, False sinon.
    """
    # Configuration de la stratégie de retry pour les anciennes versions d'urllib3
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Codes HTTP qui déclenchent un retry
        method_whitelist=["GET"]  # Ancien paramètre pour versions < 1.26
    )

    # Création d'une session avec un adaptateur HTTP configuré pour le retry
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        response = session.get(tunnel_url, timeout=timeout)
        if response.status_code == 200:
            logger.info(f"Connectivité réussie au tunnel ({tunnel_url}).")
            return True
        else:
            logger.warning(f"Échec de la connexion avec le code HTTP {response.status_code}.")
            return False

    except requests.RequestException as e:
        logger.error(f"Erreur lors de la connexion au tunnel : {e}")
        
        return False
    
    return False
  