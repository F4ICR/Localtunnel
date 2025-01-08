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

# Modules locaux
from settings import (
  TUNNEL_OUTPUT_FILE, 
  SMTP_SERVER, 
  SMTP_PORT, 
  SMTP_USER, 
  SMTP_PASSWORD, 
  EMAIL, 
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
        max_retries = 10
        delay = 3
        for attempt in range(max_retries):
            url = read_tunnel_url_from_log()
            if url:
                logger.info(f"Tunnel démarré avec succès. URL : {url}")
                log_tunnel_availability(url)
                return url
            logger.warning(f"Tentative {attempt + 1}/{max_retries} : URL non trouvée. Nouvelle tentative dans {delay} seconde(s).")
            time.sleep(delay)

        # Gestion des erreurs spécifiques aux serveurs Localtunnel
        error_message = (
            "Échec du démarrage du tunnel : aucune URL n'a été trouvée après plusieurs tentatives. "
            "Cela peut être dû à une indisponibilité temporaire des serveurs Localtunnel."
        )
        logger.error(error_message)

        # Ajouter une attente avant de retenter si les serveurs semblent indisponibles
        retry_wait_time = 60  # Temps d'attente avant de retenter (en secondes)
        logger.info(f"Attente de {retry_wait_time} secondes avant une nouvelle tentative...")
        time.sleep(retry_wait_time)

        # Nouvelle tentative après attente
        for attempt in range(max_retries):
            url = read_tunnel_url_from_log()
            if url:
                logger.info(f"Tunnel redémarré avec succès après attente. URL : {url}")
                log_tunnel_availability(url)
                return url
            logger.warning(f"Tentative supplémentaire {attempt + 1}/{max_retries} : URL non trouvée.")
            time.sleep(delay)

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
def test_tunnel_connectivity(tunnel_url):
    """
    Teste la connectivité du tunnel avec gestion du temps via datetime.
    """
    for attempt in range(TUNNEL_RETRIES):
        start_time = datetime.now()
        try:
            response = requests.get(tunnel_url, timeout=TUNNEL_TIMEOUT)
            elapsed_time = (datetime.now() - start_time).total_seconds()
            
            if response.status_code == HTTP_SUCCESS_CODE:
                logger.info(
                    f"Connectivité réussie au tunnel ({tunnel_url}). "
                    f"Temps écoulé : {elapsed_time:.2f} secondes.")
                return True
                
        except requests.RequestException as e:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            logger.warning(
                f"Tentative {attempt + 1}/{TUNNEL_RETRIES} échouée "
                f"après {elapsed_time:.2f} secondes : {e}")
                
            if attempt < TUNNEL_RETRIES - 1:
                time.sleep(TUNNEL_DELAY)
    
    return False

    
    return False
  