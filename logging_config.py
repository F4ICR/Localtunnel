#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Configuration centralisée pour la journalisation
import logging
import os

# Définir le chemin du fichier log
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "application.log")

# Configurer la journalisation
logging.basicConfig(
    level=logging.INFO,  # Niveau par défaut : INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Écriture dans un fichier
        logging.StreamHandler()        # Affichage dans la console
    ]
)

# Obtenir le logger principal
logger = logging.getLogger("LocaltunnelApp")