#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import importlib
import sys
from logging_config import logger

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
    return python_ok and modules_ok
