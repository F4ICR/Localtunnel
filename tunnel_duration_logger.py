#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import os
import threading
import time
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
        self.backup_interval = 300  # Sauvegarde toutes les 5 minutes
        self.backup_thread = None
        self.running = False
        self.last_system_check = datetime.now()
        self.system_check_interval = 1800  # Vérification de cohérence toutes les 30 minutes
        
        # Vérifier s'il existe une session précédente non terminée
        self.check_previous_session()
        
        # Démarrer le thread de sauvegarde périodique
        self.start_backup_thread()

    def check_previous_session(self):
        """
        Vérifie s'il existe un fichier de session précédente non terminée et l'enregistre.
        """
        try:
            if os.path.exists("/tmp/tunnel_start_time.txt"):
                with open("/tmp/tunnel_start_time.txt", "r") as f:
                    start_time_str = f.read().strip()
                    previous_start_time = datetime.fromisoformat(start_time_str)
                
                # Récupérer l'URL depuis le fichier de sauvegarde si disponible
                url = "URL inconnue"
                if os.path.exists("/tmp/tunnel_backup.txt"):
                    with open("/tmp/tunnel_backup.txt", "r") as f:
                        for line in f:
                            if start_time_str in line:
                                parts = line.split("|")
                                for part in parts:
                                    if "URL:" in part:
                                        url = part.split("URL:")[1].strip()
                                        break
                                break
                
                logger.warning(f"Session précédente non terminée détectée, démarrée à {previous_start_time}")
                
                # Enregistrer la session précédente
                self.tunnel_start_time = previous_start_time
                self.current_url = url
                self.tunnel_end_time = datetime.now()
                duration = self.tunnel_end_time - self.tunnel_start_time
                
                # Enregistrer avec une note spéciale
                self.log_tunnel_details(duration, recovered=True)
                
                # Supprimer le fichier temporaire
                os.remove("/tmp/tunnel_start_time.txt")
                logger.info("Fichier /tmp/tunnel_start_time.txt supprimé après récupération.")
                
                # Réinitialiser pour la nouvelle session
                self.tunnel_start_time = None
                self.tunnel_end_time = None
                self.current_url = None
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'une session précédente : {e}")

    def start_backup_thread(self):
        """
        Démarre un thread pour sauvegarder périodiquement les informations du tunnel actif.
        """
        self.running = True
        self.backup_thread = threading.Thread(target=self.periodic_backup, daemon=True)
        self.backup_thread.start()
        logger.info("Thread de sauvegarde périodique démarré")

    def periodic_backup(self):
        """
        Sauvegarde périodiquement les informations du tunnel actif et vérifie la cohérence.
        """
        while self.running:
            try:
                # Sauvegarde périodique si un tunnel est actif
                if self.tunnel_start_time and self.current_url:
                    current_time = datetime.now()
                    duration = current_time - self.tunnel_start_time
                    
                    # Formater la durée
                    total_seconds = int(duration.total_seconds())
                    hours, remainder = divmod(total_seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    duration_str = f"{hours}h {minutes}m {seconds}s"
                    
                    # Écrire dans le fichier de sauvegarde
                    with open("/tmp/tunnel_backup.txt", "a") as f:
                        f.write(
                            f"Sauvegarde à {current_time.isoformat()} | "
                            f"Début: {self.tunnel_start_time.isoformat()} | "
                            f"URL: {self.current_url} | "
                            f"Durée actuelle: {duration_str}\n"
                        )
                    logger.debug(f"Sauvegarde périodique effectuée pour le tunnel {self.current_url} (durée actuelle: {duration_str})")
                
                # Vérification de cohérence à intervalles plus longs
                if (datetime.now() - self.last_system_check).total_seconds() > self.system_check_interval:
                    self.check_consistency()
                    self.last_system_check = datetime.now()
                
            except Exception as e:
                logger.error(f"Erreur lors de la sauvegarde périodique : {e}")
            
            time.sleep(self.backup_interval)

    def check_consistency(self):
        """
        Vérifie la cohérence entre les logs système et le fichier de durées.
        """
        try:
            # Vérifier si les fichiers existent
            if not os.path.exists(TUNNEL_DURATIONS_FILE):
                logger.warning(f"Le fichier de durées {TUNNEL_DURATIONS_FILE} n'existe pas.")
                return
                
            # Comparer avec les logs système (exemple avec /var/log/syslog)
            system_log_file = "/var/log/syslog"
            if not os.path.exists(system_log_file):
                system_log_file = "/var/log/messages"  # Alternative sur certains systèmes
                
            if not os.path.exists(system_log_file):
                logger.warning("Aucun fichier de log système standard trouvé pour la vérification de cohérence.")
                return
                
            # Lire les dernières entrées du fichier de durées
            with open(TUNNEL_DURATIONS_FILE, "r") as f:
                duration_entries = f.readlines()[-10:]  # Limiter aux 10 dernières entrées
                
            # Lire les logs système pertinents (recherche de mots clés)
            with open(system_log_file, "r") as f:
                system_logs = f.read()
                
            # Vérifier la cohérence
            inconsistencies = []
            for entry in duration_entries:
                # Extraire la date et l'heure de début
                parts = entry.split("|")
                date_part = parts[0].strip().replace("Date : ", "")
                time_part = parts[2].strip().replace("Heure de début : ", "")
                
                # Vérifier si cette entrée est mentionnée dans les logs système
                if date_part not in system_logs or time_part not in system_logs:
                    inconsistencies.append(entry.strip())
                    
            if inconsistencies:
                logger.warning(f"Incohérences détectées entre les logs système et le fichier de durées ({len(inconsistencies)} entrées)")
                for entry in inconsistencies:
                    logger.warning(f"Entrée potentiellement incohérente : {entry}")
            else:
                logger.info("Vérification de cohérence réussie : aucune incohérence détectée")
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de cohérence : {e}")

    def start_tunnel(self, url: str):
        """
        Enregistre le début d'un tunnel avec son URL.
        """
        # Vérifier s'il y a déjà un tunnel actif
        if self.tunnel_start_time:
            logger.warning(f"Un tunnel est déjà actif depuis {self.tunnel_start_time}. Fermeture de l'ancien tunnel.")
            self.end_tunnel()
            
        self.tunnel_start_time = datetime.now()
        self.current_url = url
        
        # Enregistrer l'heure de démarrage dans un fichier
        try:
            with open("/tmp/tunnel_start_time.txt", "w") as f:
                f.write(self.tunnel_start_time.isoformat())
            logger.info(f"Heure de démarrage enregistrée dans /tmp/tunnel_start_time.txt : {self.tunnel_start_time.isoformat()}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement dans /tmp/tunnel_start_time.txt : {e}")
            
        # Journalisation détaillée
        logger.info(f"DÉBUT TUNNEL | URL: {url} | Timestamp: {self.tunnel_start_time.isoformat()} | PID: {os.getpid()}")

    def end_tunnel(self):
        """
        Enregistre la fin d'un tunnel, calcule sa durée et l'associe à son URL.
        """
        if not self.tunnel_start_time:
            logger.warning("Impossible d'enregistrer la fin du tunnel : aucune heure de début enregistrée.")
            return
    
        self.tunnel_end_time = datetime.now()
        duration = self.tunnel_end_time - self.tunnel_start_time
        
        # Journalisation détaillée
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}m {seconds}s"
        
        logger.info(
            f"FIN TUNNEL | URL: {self.current_url} | "
            f"Début: {self.tunnel_start_time.isoformat()} | "
            f"Fin: {self.tunnel_end_time.isoformat()} | "
            f"Durée: {duration_str} | "
            f"PID: {os.getpid()}"
        )
        
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

    def log_tunnel_details(self, duration: timedelta, recovered=False):
        """
        Enregistre les détails complets du tunnel dans un fichier distinct.
    
        Args:
            duration: La durée du tunnel
            recovered: Indique si cette entrée provient d'une récupération de session
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
        
            log_message = (
                f"Détails du tunnel enregistrés : Date : {self.tunnel_start_time.date()}, "
                f"URL : {self.current_url}, Heure de début : {self.tunnel_start_time.time()}, "
                f"Heure de fin : {self.tunnel_end_time.time()}, Durée : {duration_str}"
            )
        
            if recovered:
                logger.warning(log_message + " (session récupérée)")  # Ajouter l'info de récupération uniquement dans le log
            else:
                logger.info(log_message)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement des détails du tunnel : {e}")

    
    def __del__(self):
        """
        Destructeur pour arrêter proprement le thread de sauvegarde.
        """
        self.running = False
        if self.tunnel_start_time:
            # Sauvegarder une dernière fois si un tunnel est actif
            self.end_tunnel()