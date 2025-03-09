#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import os
from datetime import datetime, timedelta
from logging_config import logger
from settings import TUNNEL_DURATIONS_FILE


class TunnelDurationLogger:
    """
    Classe dédiée pour gérer l'enregistrement des durées des tunnels et leurs URLs.
    """

    def __init__(self):
        self.tunnel_start_time = None
        self.tunnel_end_time = None
        self.current_url = None

    def start_tunnel(self, url: str):
        """
        Enregistre le début d'un tunnel avec son URL.
        """
        self.tunnel_start_time = datetime.now()
        self.current_url = url
        try:
            with open("/tmp/tunnel_start_time.txt", "w") as f:
                f.write(self.tunnel_start_time.isoformat())
            logger.info(f"Heure de démarrage enregistrée dans /tmp/tunnel_start_time.txt : {self.tunnel_start_time.isoformat()}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement dans /tmp/tunnel_start_time.txt : {e}")
        logger.info(f"Début du tunnel enregistré avec l'URL : {url}")


    def end_tunnel(self):
        """
        Enregistre la fin d'un tunnel, calcule sa durée et l'associe à son URL.
        """
        if not self.tunnel_start_time:
            logger.warning("Impossible d'enregistrer la fin du tunnel : aucune heure de début enregistrée.")
            return
    
        self.tunnel_end_time = datetime.now()
        duration = self.tunnel_end_time - self.tunnel_start_time
        self.log_tunnel_details(duration)

        # Supprimer le fichier temporaire après la fin du tunnel
        try:
            os.remove("/tmp/tunnel_start_time.txt")
            logger.info("Fichier /tmp/tunnel_start_time.txt supprimé après la fin du tunnel.")
        except FileNotFoundError:
            logger.warning("Fichier /tmp/tunnel_start_time.txt introuvable lors de la tentative de suppression.")
    
        # Réinitialiser les timestamps et l'URL pour le prochain cycle
        self.tunnel_start_time = None
        self.tunnel_end_time = None
        self.current_url = None


    def log_tunnel_details(self, duration: timedelta):
        """
        Enregistre les détails complets du tunnel dans un fichier distinct.
        """
        # Convertir la durée en heures, minutes et secondes
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        duration_str = f"{hours}h {minutes}m {seconds}s"
        
        try:
            with open(TUNNEL_DURATIONS_FILE, "a") as f:
                f.write(
                    f"Date : {self.tunnel_start_time.date()} | "
                    f"URL : {self.current_url} | "
                    f"Heure de début : {self.tunnel_start_time.time()} | "
                    f"Heure de fin : {self.tunnel_end_time.time()} | "
                    f"Durée : {duration_str}\n"
                )
            logger.info(
                f"Détails du tunnel enregistrés : Date : {self.tunnel_start_time.date()}, "
                f"URL : {self.current_url}, Heure de début : {self.tunnel_start_time.time()}, "
                f"Heure de fin : {self.tunnel_end_time.time()}, Durée : {duration_str}"
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des détails du tunnel : {e}")
            