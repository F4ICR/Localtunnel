#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Bibliothèques standard
import os
import re
import time
import random
import subprocess
import logging
from datetime import datetime
import shutil

# Bibliothèques tierces
from metrics import save_start_time, log_tunnel_availability
import smtplib
from email.mime.text import MIMEText
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urlparse

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
  RETRY_WAIT_TIME
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
    Démarre un tunnel Localtunnel pour exposer un port local avec un mécanisme d'attente exponentielle et jitter.
    """
    # Récupérer l'URL précédente depuis le fichier log
    previous_url = read_tunnel_url_from_log()

    # Vérifier si un tunnel est déjà actif sur le port spécifié
    if is_tunnel_active(port):
        if previous_url:
            logger.info(f"Réutilisation du tunnel existant sur le port {port} : {previous_url}")
            log_tunnel_availability(previous_url)
            return previous_url

    # Vérifier si 'lt' (Localtunnel) est installé
    if not is_lt_installed():
        logger.error("Impossible de démarrer le tunnel : 'lt' n'est pas installé.")
        return None

    # Déterminer le sous-domaine à utiliser si aucun n'est spécifié
    if not subdomain and previous_url:
        try:
            parsed_url = urlparse(previous_url)
            if parsed_url.scheme in ["http", "https"] and parsed_url.netloc:
                subdomain = parsed_url.hostname.split(".")[0] if parsed_url.hostname else None
                logger.info(f"Réutilisation du sous-domaine précédent : {subdomain}")
            else:
                logger.warning(f"L'URL précédente n'est pas valide : {previous_url}")
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction du sous-domaine : {e}", exc_info=True)

    # Préparer la commande pour démarrer Localtunnel
    cmd = ["lt", "--port", str(port)]
    if subdomain:
        cmd += ["--subdomain", subdomain]

    try:
        # Démarrer le processus Localtunnel et rediriger la sortie vers un fichier log
        with open(TUNNEL_OUTPUT_FILE, "w") as log_file:
            process = subprocess.Popen(
                cmd, stdout=log_file, stderr=subprocess.STDOUT, preexec_fn=os.setpgrp
            )

        # Vérifier si le processus a démarré correctement
        time.sleep(1)  # Attendre un moment pour permettre au processus de se stabiliser
        if process.poll() is not None:  # Si le processus s'est terminé immédiatement
            logger.error("Le processus Localtunnel s'est terminé prématurément.")
            raise Exception("Échec du démarrage du processus Localtunnel.")

        # Enregistrer l'heure de démarrage et le PID dans un fichier sécurisé
        save_start_time()
        pid_file = f"/tmp/localtunnel_{port}.pid"
        write_to_file(pid_file, str(process.pid))
        logger.info(f"Processus Localtunnel démarré avec succès (PID: {process.pid}). Commande : {' '.join(cmd)}")

        # Attendre et vérifier l'URL générée par Localtunnel avec backoff exponentiel et jitter
        for attempt in range(MAX_RETRIES):
            url = read_tunnel_url_from_log()
            if url:
                logger.info(f"Tunnel démarré avec succès. URL : {url}")
                log_tunnel_availability(url)
                return url

            # Calculer le délai avec backoff exponentiel et jitter
            base_delay = DELAY_RETRIES * (1 ** attempt)  # Backoff exponentiel
            jitter = random.uniform(0, base_delay)      # Ajouter une part aléatoire (jitter)
            delay = min(base_delay + jitter, RETRY_WAIT_TIME)  # Limiter à RETRY_WAIT_TIME

            logger.warning(f"Tentative {attempt + 1}/{MAX_RETRIES} : URL non trouvée. Nouvelle tentative dans {delay:.2f} seconde(s).")
            time.sleep(delay)

        # Gestion des erreurs spécifiques aux serveurs Localtunnel
        error_message = (
            "Échec du démarrage du tunnel : aucune URL n'a été trouvée après plusieurs tentatives. "
            "Cela peut être dû à une indisponibilité temporaire des serveurs Localtunnel."
        )
        logger.error(error_message)

        # Ajouter une boucle de 5 cycles pour réessayer avec une attente prolongée
        for retry_cycle in range(5):
            logger.info(f"Cycle de réessai {retry_cycle + 1}/5 : Attente de {RETRY_WAIT_TIME} secondes avant une nouvelle tentative...")
            time.sleep(RETRY_WAIT_TIME)

            for attempt in range(MAX_RETRIES):
                url = read_tunnel_url_from_log()
                if url:
                    logger.info(f"Tunnel redémarré avec succès après attente. URL : {url}")
                    log_tunnel_availability(url)
                    return url

                # Calculer le délai avec backoff exponentiel et jitter pour les cycles supplémentaires
                base_delay = DELAY_RETRIES * (1.1 ** attempt)
                jitter = random.uniform(0, base_delay)
                delay = min(base_delay + jitter, RETRY_WAIT_TIME)

                logger.warning(f"Tentative supplémentaire {attempt + 1}/{MAX_RETRIES} : URL non trouvée. Nouvelle tentative dans {delay:.2f} seconde(s).")
                time.sleep(delay)

        # Si toutes les tentatives échouent, lever une exception critique
        raise Exception("Impossible de démarrer le tunnel après plusieurs tentatives.")

    except Exception as e:
        logger.error(f"Erreur lors du démarrage du processus Localtunnel : {e}", exc_info=True)
        return None

         
# Fonction pour lire l'URL depuis le fichier log existant
def read_tunnel_url_from_log():
    """
    Lit le fichier log pour trouver une URL valide.
    """
    try:
        if os.path.exists(TUNNEL_OUTPUT_FILE):
            with open(TUNNEL_OUTPUT_FILE, "r") as log_file:
                lines = log_file.readlines()
                for line in reversed(lines):
                    # Supprimer le texte "your url is:" si présent
                    if "your url is:" in line.lower():
                        line = line.split("your url is:")[-1].strip()
                    
                    # Vérifier si la ligne contient une URL valide
                    parsed_url = urlparse(line.strip())
                    if parsed_url.scheme in ["http", "https"] and parsed_url.netloc:
                        logger.debug(f"URL trouvée dans le fichier log : {parsed_url.geturl()}")
                        return parsed_url.geturl()
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


def check_lt_process(port):
    """
    Vérifie si un processus 'lt --port <port>' est actif.
    Logge uniquement si le processus est inactif.
    Retourne True si le processus est trouvé, False sinon.
    """
    # Vérifier si 'pgrep' est disponible sur le système
    if not shutil.which('pgrep'):
        logger.error("'pgrep' n'est pas disponible sur ce système.")
        return False

    try:
        # Exécuter la commande 'pgrep' pour vérifier le processus
        result = subprocess.run(
            ['pgrep', '-f', f'lt --port {port}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            # Le processus est actif, ne pas logguer ici pour éviter la redondance
            return True
        else:
            # Le processus est inactif, logguer un message d'avertissement
            logger.warning(f"Le processus 'lt --port {port}' n'est pas actif.")
            return False
    except Exception as e:
        # Logger l'erreur au lieu de la retourner
        logger.error(f"Erreur lors de la vérification du processus Localtunnel : {e}")
        return False


def test_tunnel_connectivity(tunnel_url, retries=10, timeout=15, backoff_factor=2.0):
    """
    Teste la connectivité HTTP du tunnel avec :
    1. Une stratégie de retry via requests.
    2. Un double test avec curl et wget pour valider la connectivité.

    :param tunnel_url: URL du tunnel à tester.
    :param retries: Nombre total de tentatives avant d'abandonner.
    :param timeout: Temps maximum (en secondes) pour chaque requête.
    :param backoff_factor: Facteur pour le délai exponentiel entre les tentatives.
    :return: True si au moins 2 tests sur 3 réussissent, False sinon.
    """
    
    # Validation de l'URL avec urllib.parse
    parsed_url = urlparse(tunnel_url)
    if not (parsed_url.scheme in ["http", "https"] and parsed_url.netloc):
        logger.error(f"L'URL fournie n'est pas valide : {tunnel_url}")
        return False

    logger.info(f"Test de connectivité pour l'URL : {tunnel_url}")

    # 1. Test avec requests et stratégie de retry
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],  # Codes HTTP à réessayer
        method_whitelist=["GET"]  # Méthodes HTTP autorisées pour le retry
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    try:
        response = session.get(tunnel_url, timeout=timeout)
        if response.status_code == 200:
            logger.info(f"Connectivité réussie avec requests ({tunnel_url}).")
            requests_success = True
        else:
            logger.warning(f"Échec avec requests : Code HTTP {response.status_code}.")
            requests_success = False
    except requests.RequestException as e:
        logger.error(f"Erreur lors du test avec requests : {e}")
        requests_success = False

    # 2. Test complémentaire avec curl et stratégie de retry
    curl_command = [
        "curl", "-o", "/dev/null", "-s", "-w", "%{http_code}",
        "--retry", str(retries), "--retry-max-time", str(timeout), "--connect-timeout", str(timeout), tunnel_url
    ]
    try:
        curl_result = subprocess.run(curl_command, capture_output=True, text=True, timeout=timeout)
        if curl_result.stdout.strip() == "200":
            logger.info("Connectivité réussie avec curl.")
            curl_success = True
        else:
            logger.warning(f"Échec avec curl : Code HTTP {curl_result.stdout.strip()}.")
            curl_success = False
    except Exception as e:
        logger.error(f"Erreur lors du test avec curl : {e}")
        curl_success = False

    # 3. Test complémentaire avec wget et stratégie de retry
    wget_command = [
        "wget", "--spider",
        "--tries", str(retries), "--timeout", str(timeout), tunnel_url
    ]
    try:
        wget_result = subprocess.run(wget_command, capture_output=True, text=True, timeout=timeout)
        if wget_result.returncode == 0:  # Code retour 0 indique succès pour wget
            logger.info("Connectivité réussie avec wget.")
            wget_success = True
        else:
            logger.warning(f"Échec avec wget : Code retour {wget_result.returncode}.")
            wget_success = False
    except Exception as e:
        logger.error(f"Erreur lors du test avec wget : {e}")
        wget_success = False

    # Résultat final basé sur les trois tests, mais avec plus de souplesse
    # Considérer comme succès si au moins 2 tests sur 3 réussissent
    success_count = sum([requests_success, curl_success, wget_success])
    
    if success_count >= 2:
        logger.info(f"{success_count}/3 tests réussis : L'URL est considérée comme accessible.")
        return True
    else:
        logger.warning(f"Seulement {success_count}/3 tests réussis : L'URL n'est pas considérée comme accessible.")
    
    return False
    