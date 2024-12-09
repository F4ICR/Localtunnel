#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import importlib
import sys
import subprocess
from logging_config import logger


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
    

def check_python_version():
    """Vérifie la version de Python"""
    required_version = (3, 6)
    if sys.version_info < required_version:
        logger.error(f"Python {required_version[0]}.{required_version[1]} ou supérieur est requis")
        return False
    return True


def check_required_modules():
    """Vérifie la présence des modules requis"""
    required_modules = {
        'requests': None,
        'smtplib': None,
        'email.mime.text': None
    }
    
    all_modules_present = True
    for module in required_modules:
        try:
            importlib.import_module(module)
            logger.debug(f"Module {module} trouvé")
        except ImportError as e:
            logger.error(f"Module requis manquant : {module}")
            all_modules_present = False
    
    return all_modules_present


def verify_all_dependencies():
    """Vérifie toutes les dépendances"""
    python_ok = check_python_version()
    modules_ok = check_required_modules()
    lt_ok = is_lt_installed()
    return python_ok and modules_ok and lt_ok
