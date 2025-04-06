#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import os
import threading
import time
from datetime import datetime, timedelta
from logging_config import logger
from settings import TUNNEL_DURATIONS_FILE, TUNNEL_OUTPUT_FILE


class TunnelDurationLogger:
    """
    Classe dédiée pour gérer l'enregistrement des durées des tunnels et leurs URLs.
    """

    def __init__(self):
        self.tunnel_start_time = None
        self.tunnel_end_time = None
        self.current_url = None
        self.last_known_url = None
        self.backup_interval = 300  # Sauvegarde toutes les 5 minutes
        self.backup_thread = None
        self.running = False
        self.last_system_check = datetime.now()
        self.system_check_interval = 1800  # Vérification de cohérence toutes les 30 minutes
        
        # Vérifier s'il existe une session précédente non terminée
        self.check_previous_session()
        
        # Démarrer le thread de sauvegarde périodique
        self.start_backup_thread()

    def read_last_known_url(self):
        """
        Lit la dernière URL connue depuis le fichier de sortie du tunnel.
        """
        try:
            if os.path.exists(TUNNEL_OUTPUT_FILE):
                with open(TUNNEL_OUTPUT_FILE, 'r') as f:
                    url = f.read().strip()
                    if url:
                        return url
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de l'URL depuis {TUNNEL_OUTPUT_FILE}: {e}")
        return None

    def read_last_url_from_durations(self):
        """
        Lit la dernière URL valide depuis le fichier des durées de tunnel.
        """
        try:
            if os.path.exists(TUNNEL_DURATIONS_FILE):
                with open(TUNNEL_DURATIONS_FILE, 'r') as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if "URL :" in line and "URL : URL inconnue" not in line:
                            parts = line.split("URL :")
                            if len(parts) > 1:
                                url_part = parts[1].split("|")[0].strip()
                                if url_part:
                                    return url_part
        except Exception as e:
            logger.error(f"Erreur lors de la lecture de la dernière URL depuis {TUNNEL_DURATIONS_FILE}: {e}")
        return None

    def check_previous_session(self):
        """
        Vérifie s'il existe un fichier de session précédente non terminée et l'enregistre.
        """
        try:
            if os.path.exists("/tmp/tunnel_start_time.txt"):
                with open("/tmp/tunnel_start_time.txt", "r") as f:
                    start_time_str = f.read().strip()
                    previous_start_time = datetime.fromisoformat(start_time_str)
                
                # Récupérer l'URL depuis plusieurs sources
                url = "URL inconnue"
                
                # 1. Essayer d'abord le fichier de sauvegarde
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
                
                # 2. Si toujours inconnue, essayer le fichier de sortie du tunnel
                if url == "URL inconnue":
                    last_url = self.read_last_known_url()
                    if last_url:
                        url = last_url
                        logger.info(f"URL récupérée depuis le fichier de sortie du tunnel : {url}")
                
                # 3. En dernier recours, utiliser la dernière URL du fichier de durées
                if url == "URL inconnue":
                    last_url = self.read_last_url_from_durations()
                    if last_url:
                        url = last_url
                        logger.info(f"URL récupérée depuis le fichier de durées : {url}")
                
                logger.warning(f"Session précédente non terminée détectée, démarrée à {previous_start_time}")
                
                # Enregistrer la session précédente
                self.tunnel_start_time = previous_start_time
                self.current_url = url
                self.last_known_url = url if url != "URL inconnue" else None
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
        Ignore les sessions très courtes et génère un rapport consolidé.
        """
        try:
            # Vérifications préliminaires des fichiers
            if not os.path.exists(TUNNEL_DURATIONS_FILE):
                return
            
            system_log_file = "/var/log/syslog"
            if not os.path.exists(system_log_file):
                system_log_file = "/var/log/messages"
                if not os.path.exists(system_log_file):
                    return
            
            # Lire les entrées du fichier de durées
            with open(TUNNEL_DURATIONS_FILE, "r") as f:
                duration_entries = f.readlines()[-10:]  # Limiter aux 10 dernières entrées
            
            # Lire les logs système pertinents
            with open(system_log_file, "r") as f:
                system_logs = f.read()
            
            # Vérifier la cohérence
            significant_inconsistencies = []
            for entry in duration_entries:
                # Ignorer les sessions très courtes (moins de 10 secondes)
                if "Durée : 0h 0m " in entry:
                    try:
                        seconds = int(entry.split("Durée : 0h 0m ")[1].split("s")[0])
                        if seconds < 10:
                            continue
                    except (IndexError, ValueError):
                        pass
                
                parts = entry.split("|")
                date_part = parts[0].strip().replace("Date : ", "").replace("[RÉCUPÉRÉ] Date : ", "")
            
                # Vérifier uniquement les entrées des 2 derniers jours
                if date_part not in system_logs:
                    significant_inconsistencies.append(entry.strip())
        
            # Générer un rapport consolidé uniquement si des incohérences significatives sont trouvées
            if significant_inconsistencies:
                logger.warning(f"Rapport de cohérence : {len(significant_inconsistencies)} entrées significatives non retrouvées dans les logs système")
                # Journaliser uniquement les 3 premières pour éviter la verbosité
                for i, entry in enumerate(significant_inconsistencies[:3]):
                    logger.warning(f"Exemple d'incohérence #{i+1}: {entry}")
                if len(significant_inconsistencies) > 3:
                    logger.warning(f"... et {len(significant_inconsistencies) - 3} autres entrées")
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
        self.last_known_url = url  # Mémoriser cette URL
        
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
        Ignore les sessions très courtes et utilise la dernière URL connue si nécessaire.
        
        Args:
            duration: La durée du tunnel
            recovered: Indique si cette entrée provient d'une récupération de session
        """
        # Ignorer les sessions très courtes (moins de 10 secondes)
        if duration.total_seconds() < 10:
            logger.debug(f"Session ignorée car trop courte ({duration.total_seconds()} secondes)")
            return
            
        # Convertir la durée en heures, minutes et secondes
        total_seconds = int(duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        duration_str = f"{hours}h {minutes}m {seconds}s"
        
        # Déterminer l'URL à utiliser
        url_to_log = self.current_url
        if url_to_log is None or url_to_log == "URL inconnue":
            # Essayer de récupérer l'URL depuis différentes sources
            url_to_log = self.last_known_url or self.read_last_known_url() or self.read_last_url_from_durations() or "URL inconnue"
            if url_to_log != "URL inconnue":
                logger.info(f"URL récupérée pour la session : {url_to_log}")
        
        # Ajouter un préfixe pour les sessions récupérées
        prefix = "[RÉCUPÉRÉ] " if recovered else ""
        
        try:
            with open(TUNNEL_DURATIONS_FILE, "a") as f:
                f.write(
                    f"{prefix}Date : {self.tunnel_start_time.date()} | "
                    f"URL : {url_to_log} | "
                    f"Heure de début : {self.tunnel_start_time.time()} | "
                    f"Heure de fin : {self.tunnel_end_time.time()} | "
                    f"Durée : {duration_str}\n"
                )
            
            log_message = (
                f"Détails du tunnel enregistrés : {prefix}Date : {self.tunnel_start_time.date()}, "
                f"URL : {url_to_log}, Heure de début : {self.tunnel_start_time.time()}, "
                f"Heure de fin : {self.tunnel_end_time.time()}, Durée : {duration_str}"
            )
            
            if recovered:
                logger.warning(log_message)  # Utiliser warning pour les sessions récupérées
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
