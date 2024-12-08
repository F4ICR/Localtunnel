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
    level=logging.DEBUG,  # Niveau par défaut : DEBUG
    format="%(asctime)s - %(name)s - %(levelname)s - [PID: %(process)d] - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Écriture dans un fichier
        logging.StreamHandler()        # Affichage dans la console
    ]
)

logger = logging.getLogger("LocaltunnelApp")
