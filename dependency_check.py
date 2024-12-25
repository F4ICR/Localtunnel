#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import importlib
import sys
import subprocess
from logging_config import logger  # Import du logger configuré dans logging_config.py


def is_lt_installed():
    """
    Vérifie si l'outil 'lt' (Localtunnel) est installé et s'il y a des tunnels actifs.
    """
    try:
        # Vérifie si 'lt' est accessible via le PATH
        subprocess.run(["lt", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Vérifie s'il y a des tunnels actifs
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
            # Gestion spéciale pour les modules intégrés
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
    else:
        logger.error("Certaines dépendances sont manquantes ou incorrectes.")
