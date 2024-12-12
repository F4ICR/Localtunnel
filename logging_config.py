#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# Configuration centralisée pour la journalisation

import logging
from logging.handlers import TimedRotatingFileHandler
import os

# Définir le chemin du fichier log
LOG_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(LOG_DIR, "application.log")

# Configurer la journalisation
logging.basicConfig(level=logging.DEBUG)  # Niveau par défaut : DEBUG

# Créer le gestionnaire de rotation
file_handler = TimedRotatingFileHandler(
    LOG_FILE,
    when='midnight',     # Rotation à minuit
    interval=1,          # Intervalle de 1 jour
    backupCount=3,       # Conserver 3 jours de logs
    encoding='utf-8'
)

# Définir le format des logs
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - [PID: %(process)d] - %(message)s"
)
file_handler.setFormatter(formatter)

# Créer le gestionnaire pour la console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Configurer le logger
logger = logging.getLogger("LocaltunnelApp")
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

metric_file_handler = logging.FileHandler("metrics.log")
metric_file_handler.setFormatter(formatter)
logger.addHandler(metric_file_handler)
