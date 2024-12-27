#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import importlib
import sys
import subprocess
import os
import ssl
import socket
from logging_config import logger  # Import du logger configuré dans logging_config.py

LOG_FILE = "application.log"  # Nom du fichier de log
TUNNEL_OUTPUT_FILE = "tunnel_output.log"  # Fichier contenant le nom de domaine

def is_lt_installed():
    """
    Vérifie si l'outil 'lt' (Localtunnel) est installé et s'il y a des tunnels actifs.
    """
    try:
        subprocess.run(["lt", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        tunnels_actifs = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        if "lt --port" not in tunnels_actifs.stdout:
            logger.info("L'outil 'lt' (Localtunnel) est installé.")
        return True
    except FileNotFoundError:
        logger.error("L'outil 'lt' n'est pas installé. Installation : 'npm install -g localtunnel'")
        return False
    except Exception as e:
        logger.error(f"Une erreur s'est produite lors de la vérification de 'lt' : {e}")
        return False

def check_python_version():
    """
    Vérifie si la version de Python est compatible.
    """
    required_version = (3, 6)
    if sys.version_info < required_version:
        logger.error(f"Python {required_version[0]}.{required_version[1]} ou supérieur est requis. "
                     "Téléchargez-le sur python.org")
        return False
    return True

def check_required_modules():
    """
    Vérifie si les modules requis sont installés.
    """
    required_modules = {
        'requests': 'pip install requests',
        'smtplib': 'Module intégré à Python',
        'email.mime.text': 'Module intégré à Python'
    }

    all_modules_present = True
    for module, install_cmd in required_modules.items():
        try:
            if module in ['smtplib', 'email.mime.text']:
                __import__(module.split('.')[0])
            else:
                importlib.import_module(module)
            logger.debug(f"Module {module} trouvé")
        except ImportError:
            if install_cmd != 'Module intégré à Python':
                logger.error(f"Module requis manquant : {module}. Installation : '{install_cmd}'")
            else:
                logger.error(f"Module requis manquant : {module}. Ce module devrait être présent dans l'installation Python")
            all_modules_present = False
    return all_modules_present

def get_domain_from_tunnel_output(file_path):
    """
    Lit le fichier tunnel_output.log et extrait le nom de domaine.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Le fichier '{file_path}' n'existe pas.")
            return None
        
        with open(file_path, "r") as file:
            for line in file:
                # Supposons que la ligne contenant le domaine commence par "https://"
                if "https://" in line or "http://" in line:
                    domain = line.strip().split("//")[-1].split("/")[0]
                    logger.info(f"Nom de domaine extrait : {domain}")
                    return domain
        
        logger.error("Aucun nom de domaine trouvé dans le fichier.")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de la lecture du fichier '{file_path}' : {e}")
        return None

def verify_ssl_certificate(hostname):
    """
    Vérifie la validité d'un certificat SSL pour un domaine donné.
    """
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443)) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                ssock.do_handshake()
                logger.info(f"Le certificat SSL pour {hostname} est valide.")
                return True
    except ssl.SSLError as e:
        logger.error(f"Erreur SSL lors de la vérification du certificat pour {hostname} : {e}")
        return False
    except Exception as e:
        logger.error(f"Une erreur inattendue s'est produite lors de la vérification SSL : {e}")
        return False

def verify_all_dependencies():
    """
    Vérifie toutes les dépendances nécessaires au bon fonctionnement du script.
    """
    python_ok = check_python_version()
    modules_ok = check_required_modules()
    lt_ok = is_lt_installed()

    return python_ok and modules_ok and lt_ok

if __name__ == "__main__":
    if verify_all_dependencies():
        logger.info("Toutes les dépendances sont satisfaites.")

        # Lire le nom de domaine depuis tunnel_output.log
        domain = get_domain_from_tunnel_output(TUNNEL_OUTPUT_FILE)
        
        if domain:
            # Vérifier le certificat SSL pour ce domaine
            if verify_ssl_certificate(domain):
                logger.info(f"Le certificat SSL pour {domain} est valide.")
            else:
                logger.error(f"Le certificat SSL pour {domain} n'est pas valide.")
                
        else:
            logger.error("Impossible de vérifier un certificat SSL car aucun domaine n'a été trouvé.")
            
    else:
        logger.error("Certaines dépendances sont manquantes ou incorrectes.")
        