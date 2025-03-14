#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# F4ICR & OpenIA GPT-4

APP_VERSION = "1.5.3"
DEVELOPER_NAME = "Développé par F4ICR Pascal & OpenIA GPT-4"

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
from urllib.parse import urlparse
import os
import validators
import psutil
import subprocess
import platform
from apscheduler.schedulers.background import BackgroundScheduler
from threading import Lock
from lib import (
    start_tunnel,
    stop_existing_tunnel,
    is_tunnel_active,
    read_tunnel_url_from_log,
    test_tunnel_connectivity,
)
from tunnel_duration_logger import TunnelDurationLogger
from settings import (
    PORT, 
    SUBDOMAIN, 
    TUNNEL_DURATIONS_FILE, 
    TUNNEL_OUTPUT_FILE, 
    TUNNEL_CHECK_INTERVAL, 
    APPLICATION_LOG,
    EMAIL_NOTIFICATIONS,
    EMAIL,
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USER,
    SMTP_PASSWORD,
    LOG_BACKUP_COUNT,
    LOG_MAX_BYTES
)

# Initialisation de l'application Flask
app = Flask(__name__)

# Verrou pour les tests concurrents et cache des résultats des tests
latency_lock = Lock()
last_latency = {"value": "N/A", "timestamp": None}
test_lock = Lock()
last_test = {
    "timestamp": None,
    "results": {"requests": False, "curl": False, "wget": False},
    "next_check": None,
}

# Variables dynamiques pour CPU et mémoire
cpu_temperature = "Température non disponible."
memory_info = "Mémoire non disponible."
system_uptime = "Durée inconnue"

# Scheduler pour les tâches planifiées
scheduler = BackgroundScheduler()
scheduler.start()

# Compteur de requêtes HTTP et gestion des durées de tunnels
request_count = 0
duration_logger = TunnelDurationLogger()

# Pour stocker l'historique des requêtes
requests_history = []
last_reset = datetime.now()
MAX_HISTORY_SIZE = 10000  # Limite pour éviter une consommation excessive de mémoire


@app.before_request
def track_request():
    global request_count, requests_history, last_reset
    
    # Réinitialiser le compteur et l'historique à minuit
    now = datetime.now()
    if now.date() > last_reset.date():
        request_count = 0
        requests_history = []  # Vider complètement l'historique
        last_reset = now
        app.logger.info(f"Compteur et historique de requêtes réinitialisés à {now}")
    
    # Incrémenter le compteur et sauvegarder pour l'historique
    request_count += 1
    
    # Ajouter à l'historique avec limitation de taille
    if len(requests_history) < MAX_HISTORY_SIZE:
        requests_history.append({
            'timestamp': now.isoformat(),
            'count': request_count
        })
    elif len(requests_history) == MAX_HISTORY_SIZE:
        # Remplacer le plus ancien élément par le nouveau
        requests_history.pop(0)
        requests_history.append({
            'timestamp': now.isoformat(),
            'count': request_count
        })


@app.route('/requests_data/')
def get_requests_data():
    """Retourne les données historiques des requêtes pour le graphique."""
    try:
        # Calculer la date limite (24h avant maintenant)
        one_day_ago = datetime.now() - timedelta(days=1)
        
        # Filtrer les données pour ne garder que les dernières 24h
        filtered_data = [
            {
                "timestamp": entry["timestamp"],
                "count": entry["count"]
            }
            for entry in requests_history
            if datetime.fromisoformat(entry["timestamp"]) >= one_day_ago
        ]
        
        return jsonify(filtered_data)
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des données de requêtes : {e}")
        return jsonify({"error": "Impossible de récupérer les données"}), 500


@app.route('/admin/logs')
def get_logs():
    try:
        # Lire les 1000 dernières lignes pour éviter une surcharge
        with open(APPLICATION_LOG, 'r') as f:
            logs = f.readlines()[-1000:]
            return ''.join(logs)
    except FileNotFoundError:
        app.logger.error(f"Fichier de log non trouvé : {APPLICATION_LOG}")
        return "Fichier de log non trouvé"
    except Exception as e:
        app.logger.error(f"Erreur lors de la lecture des logs : {e}")
        return f"Erreur lors de la lecture des logs : {str(e)}"


@app.route('/test_curl', methods=['POST'])
def test_curl():
    try:
        data = request.get_json()
        tunnel_url = data.get('url')
        
        if not tunnel_url or not validators.url(tunnel_url):
            return jsonify({'error': 'URL invalide'}), 400
            
        ip = subprocess.run(['curl', 'ifconfig.me'], 
                          capture_output=True,
                          text=True,
                          timeout=5).stdout.strip()
        
        # Construire et exécuter la commande curl
        full_url = f"{tunnel_url}/{ip}"
        result = subprocess.run(['curl', full_url], 
                              capture_output=True, 
                              text=True)
        
        return result.stdout
    except Exception as e:
        return f"Erreur: {str(e)}"


def measure_latency(host="localtunnel.me"):
    """Mesure la latence réseau via ping (méthode cross-platform)"""
    try:
        params = {'n': '4', 'w': '1000'} if platform.system().lower() == 'windows' else {'c': '4', 'W': '1'}
        cmd = ['ping', f'-{list(params.keys())[0]}', list(params.values())[0], 
               f'-{list(params.keys())[1]}', list(params.values())[1], host]
        
        output = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
        
        # Extraction de la latence moyenne
        if 'moyenne' in output:  # Français
            avg_line = [line for line in output.split('\n') if 'moyenne' in line][0]
            latency = float(avg_line.split(' = ')[-1].split('/')[1])
        elif 'avg' in output:  # Anglais
            avg_line = [line for line in output.split('\n') if 'avg' in line][0]
            latency = float(avg_line.split(' = ')[-1].split('/')[1])
        else:
            latency = None
            
        with latency_lock:
            last_latency.update({
                "value": f"{latency:.1f} ms" if latency else "Erreur",
                "timestamp": datetime.now()
            })
            
    except Exception as e:
        app.logger.error(f"Erreur mesure latence: {str(e)}")
        with latency_lock:
            last_latency["value"] = "N/A"


@app.route('/latency_data/')
def get_latency_data():
    """Retourne la dernière latence mesurée."""
    with latency_lock:
        if last_latency and last_latency.get("timestamp") and last_latency.get("value") is not None:
            # Données valides disponibles
            response = {
                "value": last_latency["value"],
                "timestamp": last_latency["timestamp"].isoformat()
            }
        else:
            # Aucune donnée valide disponible
            app.logger.warning("Aucune donnée de latence disponible actuellement.")
            response = {
                "value": None,
                "timestamp": None,
                "message": "Aucune donnée de latence disponible pour le moment."
            }

        return jsonify(response)


def get_system_uptime():
    """Récupère l'uptime système avec la commande uptime"""
    try:
        output = subprocess.check_output(["uptime", "-p"]).decode().strip()
        return output.replace("up ", "").capitalize()
    except (subprocess.CalledProcessError, FileNotFoundError):
        try:
            output = subprocess.check_output(["uptime"]).decode().lower()
            match = re.search(r"up\s+(.*?),\s+\d+ user", output)
            if match:
                return match.group(1).replace(",", "")
            return "Durée inconnue"
        except Exception as e:
            app.logger.error(f"Erreur uptime: {str(e)}")
            return "Erreur de mesure"
    except Exception as e:
        app.logger.error(f"Erreur générale uptime: {str(e)}")

        return "Erreur"


### Fonctions dynamiques ###
def update_dynamic_metrics():
    """Met à jour les informations CPU et mémoire et uptime."""
    global cpu_temperature, memory_info, system_uptime
    
    # Pour la température CPU
    try:
        if hasattr(psutil, "sensors_temperatures"):
            temps = psutil.sensors_temperatures()
            if "coretemp" in temps:
                cpu_temperature = f"{temps['coretemp'][0].current:.1f} °C"
            elif "cpu-thermal" in temps:
                cpu_temperature = f"{temps['cpu-thermal'][0].current:.1f} °C"
            else:
                cpu_temperature = "Température non disponible."
        else:
            cpu_temperature = "Température non disponible."
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération de la température CPU : {e}")
        cpu_temperature = "Erreur."

    # Pour la mémoire
    try:
        mem = psutil.virtual_memory()
        total = round(mem.total / (1024 ** 3), 2)
        available = round(mem.available / (1024 ** 3), 2)
        memory_info = f"{available} Go disponibles sur {total} Go"
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération de la mémoire : {e}")
        memory_info = "Erreur."

    # Pour l'uptime système
    try:
        system_uptime = get_system_uptime()  # Utilise la fonction existante
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération de l'uptime système : {e}")
        system_uptime = "Erreur."


@app.route('/system_metrics')
def system_metrics():
    """Retourne les métriques système actualisées au format JSON."""
    try:
        # Mettre à jour les métriques en temps réel
        update_dynamic_metrics()
        
        return jsonify({
            'current_time': datetime.now().strftime('%H:%M:%S'),
            'cpu_temperature': cpu_temperature,
            'memory_info': memory_info,
            'system_uptime': system_uptime
        })
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des métriques système : {e}")
        return jsonify({
            'current_time': datetime.now().strftime('%H:%M:%S'),
            'cpu_temperature': 'Erreur',
            'memory_info': 'Erreur',
            'system_uptime': 'Erreur'
        }), 500


def schedule_test():
    """Exécute les tests périodiques sur le tunnel."""
    global last_test
    with test_lock:
        try:
            tunnel_url = read_tunnel_url_from_log()
            if tunnel_url and tunnel_url != "Aucun":
                # Exécuter le test de connectivité
                test_result = test_tunnel_connectivity(tunnel_url)
                
                # Initialiser les résultats par défaut
                results = {
                    'requests': False,
                    'curl': False, 
                    'wget': False
                }
                
                # Mise à jour des résultats selon le retour
                if isinstance(test_result, dict):
                    results.update(test_result)
                elif isinstance(test_result, bool) and test_result:
                    results = {
                        'requests': True,
                        'curl': True,
                        'wget': True
                    }
                
                last_test["timestamp"] = datetime.now()
                last_test["results"] = results
                last_test["next_check"] = datetime.now() + timedelta(seconds=TUNNEL_CHECK_INTERVAL)
                
        except Exception as e:
            app.logger.error(f"Erreur lors des tests planifiés : {e}")
            last_test["timestamp"] = datetime.now()
            last_test["results"] = {'requests': False, 'curl': False, 'wget': False}
            last_test["next_check"] = datetime.now() + timedelta(seconds=TUNNEL_CHECK_INTERVAL)


def get_previous_tunnels():
    """Récupère toutes les entrées du fichier des durées des tunnels."""
    try:
        with open(TUNNEL_DURATIONS_FILE, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]  # Supprimer les lignes vides
    except FileNotFoundError:
        return []
    except Exception as e:
        app.logger.error(f"Erreur lors de la lecture des durées des tunnels : {e}")
        return []


@app.route('/tunnel_data/<int:days>', methods=['GET'])
def get_tunnel_data(days):
    try:
        cutoff_date = datetime.now() - timedelta(days=days)
        previous_tunnels = get_previous_tunnels()

        data = []
        for entry in previous_tunnels:
            try:
                parts = dict(item.strip().split(" : ") for item in entry.split(" | "))
                
                date_part = parts["Date"]
                tunnel_date = datetime.strptime(date_part, "%Y-%m-%d")
                
                if tunnel_date >= cutoff_date:
                    duration_part = parts["Durée"]
                    hours, minutes, seconds = map(
                        int,
                        duration_part.replace("h", "").replace("m", "").replace("s", "").split()
                    )
                    total_hours = round(hours + minutes / 60 + seconds / 3600, 2)
                    
                    data.append({
                        "date": date_part,
                        "duration": total_hours,
                        "start_time": parts["Heure de début"].split(".")[0],
                        "end_time": parts["Heure de fin"].split(".")[0],
                        "url": parts["URL"]
                    })
            except Exception as e:
                app.logger.warning(f"Erreur lors du traitement d'une entrée : {entry} - {e}")
        
        return jsonify(data)
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des données : {e}")
        return jsonify({"error": "Impossible de récupérer les données"}), 500


def get_tunnel_start_time():
    """Lit l'heure de démarrage du tunnel depuis un fichier."""
    try:
        with open("/tmp/tunnel_start_time.txt", "r") as f:
            start_time_str = f.read().strip()
            return datetime.fromisoformat(start_time_str)
    except FileNotFoundError:
        app.logger.warning("Fichier /tmp/tunnel_start_time.txt introuvable.")
        return None
    except ValueError as e:
        app.logger.error(f"Format de date invalide dans le fichier : {e}")
        return None
    except Exception as e:
        app.logger.error(f"Erreur lors de la lecture du fichier : {e}")
        return None


@app.route('/tunnel_uptime/')
def get_tunnel_uptime():
    try:
        with open("/tmp/tunnel_start_time.txt", "r") as f:
            start_time_str = f.read().strip()
            start_time = datetime.fromisoformat(start_time_str)
    except FileNotFoundError:
        app.logger.warning("Fichier /tmp/tunnel_start_time.txt introuvable.")
        return jsonify({"uptime": "N/A"})
    except ValueError as e:
        app.logger.error(f"Format invalide dans /tmp/tunnel_start_time.txt : {e}")
        return jsonify({"uptime": "N/A"})
    
    uptime_duration = datetime.now() - start_time
    days = uptime_duration.days
    hours, remainder = divmod(uptime_duration.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}j {hours}h {minutes}m"

    return jsonify({"uptime": uptime_str})


@app.route('/get_tunnel_url')
def get_tunnel_url():
    """Endpoint pour récupérer dynamiquement l'URL du tunnel."""
    tunnel_active = is_tunnel_active(PORT)
    if tunnel_active:
        try:
            with open(TUNNEL_OUTPUT_FILE, "r") as file:
                # Lire et nettoyer l'URL
                raw_url = file.read().strip()
                # Supprimer le texte 'your url is: ' si présent
                tunnel_url = raw_url.replace('your url is: ', '')
        except Exception as e:
            app.logger.error(f"Erreur lecture fichier : {e}")
            tunnel_url = "Erreur"
    else:
        tunnel_url = "Aucun"

    return jsonify({"tunnel_url": tunnel_url})


@app.route('/')
def index():
    """Page principale affichant les informations du tunnel."""
    tunnel_active = is_tunnel_active(PORT)
    system_uptime = get_system_uptime()  # Nouvelle fonction pour l'uptime système
    previous_tunnels = get_previous_tunnels()

    # Valeurs par défaut
    tunnel_url = "Aucun"
    tunnel_uptime = "Aucun"

    if tunnel_active:
        try:
            with open(TUNNEL_OUTPUT_FILE, "r") as file:
                tunnel_url = file.read().strip()
            
            start_time = get_tunnel_start_time()
            if start_time:
                delta = datetime.now() - start_time
                tunnel_uptime = (
                    f"{delta.days}j "
                    f"{delta.seconds // 3600}h "
                    f"{(delta.seconds // 60) % 60}min"
                )
            else:
                tunnel_uptime = "Heure inconnue"
                app.logger.warning("Heure de démarrage du tunnel non trouvée")

        except Exception as e:
            app.logger.error(f"Erreur lecture fichier : {e}")
            tunnel_url, tunnel_uptime = "Erreur", "Erreur"

    return render_template(
        'index.html',
        PORT=PORT,
        SUBDOMAIN=SUBDOMAIN,
        EMAIL_NOTIFICATIONS=EMAIL_NOTIFICATIONS,
        EMAIL=EMAIL,
        SMTP_SERVER=SMTP_SERVER,
        SMTP_PORT=SMTP_PORT,
        SMTP_USER=SMTP_USER,
        SMTP_PASSWORD=SMTP_PASSWORD,
        LOG_BACKUP_COUNT=LOG_BACKUP_COUNT,
        LOG_MAX_BYTES=LOG_MAX_BYTES,
        network_latency=last_latency,
        system_uptime=system_uptime,  # Uptime système
        tunnel_uptime=tunnel_uptime,  # Durée du tunnel
        app_version=APP_VERSION,
        developer_name=DEVELOPER_NAME,
        tunnel_active=tunnel_active,
        tunnel_url=tunnel_url,
        request_count=request_count,
        previous_tunnels=previous_tunnels,
        cpu_temperature=cpu_temperature,
        memory_info=memory_info,
        last_test=last_test,
        datetime=datetime,
    )


@app.route('/start', methods=['POST'])
def start():
    """Démarre un nouveau tunnel."""
    try:
        if is_tunnel_active(PORT):
            return jsonify({"status": "error", "message": "Tunnel déjà actif."})
        
        url = start_tunnel(PORT, SUBDOMAIN)
        
        if url:
            with open("/tmp/tunnel_start_time.txt", "w") as f:
                f.write(datetime.now().isoformat())
            
            return jsonify({"status": "success", "message": f"Tunnel démarré : {url}"})
        
        return jsonify({"status": "error", "message": "Échec du démarrage du tunnel."})
            
    except Exception as e:
        app.logger.error(f"Erreur lors du démarrage du tunnel : {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/stop', methods=['POST'])
def stop():
    """Arrête le tunnel actif."""
    try:
        if not is_tunnel_active(PORT):
            return jsonify({"status": "error", "message": "Aucun tunnel actif à arrêter."})
        
        stop_existing_tunnel(PORT)
        
        return jsonify({"status": "success", "message": "Tunnel arrêté avec succès."})
        
    except Exception as e:
        app.logger.error(f"Erreur lors de l'arrêt du tunnel : {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route('/check_url', methods=['GET'])
def check_url():
    """Retourne les résultats des derniers tests."""
    with test_lock:
        if not last_test["timestamp"]:
            return jsonify({"status": "pending", "message": "Premier test en cours..."})
        
        return jsonify({
            "status": "success",
            "results": last_test["results"],
            "last_check": last_test["timestamp"].isoformat(),
            "next_check": last_test["next_check"].isoformat(),
        })


@app.route('/admin/save-config', methods=['POST'])
def save_config():
    try:
        # Récupérer les données envoyées par le formulaire
        config_data = request.get_json()

        # Convertir "on"/"off" en True/False pour EMAIL_NOTIFICATIONS
        email_notifications = config_data.get('email_notifications', 'off') == 'on'

        # Préparer les données à sauvegarder
        new_config = {
            "email_notifications": email_notifications,
            "email": config_data.get('email', ''),
            "smtp_server": config_data.get('smtp_server', ''),
            "smtp_port": int(config_data.get('smtp_port', 0)),
            "smtp_user": config_data.get('smtp_user', ''),
            "smtp_password": config_data.get('smtp_password', '')
        }

        # Mettre à jour settings.py
        if update_settings(new_config):
            app.logger.info("Configuration mise à jour avec succès.")
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Échec de la mise à jour"}), 500

    except Exception as e:
        app.logger.error(f"Erreur lors de la sauvegarde : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def update_settings(new_config):
    """Met à jour les valeurs dans le fichier settings.py tout en conservant les commentaires."""
    try:
        settings_file = "settings.py"
        with open(settings_file, "r") as f:
            lines = f.readlines()

        # Modifier uniquement les lignes correspondant aux paramètres à mettre à jour
        with open(settings_file, "w") as f:
            for line in lines:
                if line.startswith("EMAIL_NOTIFICATIONS"):
                    # Remplace True/False tout en conservant le commentaire
                    f.write(f"EMAIL_NOTIFICATIONS = {str(new_config['email_notifications'])}  # Mettre à False pour désactiver les emails\n")
                elif line.startswith("EMAIL ="):
                    # Remplace l'email tout en conservant le commentaire
                    f.write(f"EMAIL = \"{new_config['email']}\"  # Adresse email pour recevoir l'URL du tunnel\n")
                elif line.startswith("SMTP_SERVER ="):
                    # Remplace le serveur SMTP tout en conservant le commentaire
                    f.write(f"SMTP_SERVER = \"{new_config['smtp_server']}\"  # Serveur SMTP (exemple avec Gmail)\n")
                elif line.startswith("SMTP_PORT ="):
                    # Remplace le port SMTP tout en conservant le commentaire
                    f.write(f"SMTP_PORT = {new_config['smtp_port']}  # Port SMTP sécurisé (SSL)\n")
                elif line.startswith("SMTP_USER ="):
                    # Remplace l'utilisateur SMTP tout en conservant le commentaire
                    f.write(f"SMTP_USER = \"{new_config['smtp_user']}\"  # Adresse email utilisée pour l'envoi\n")
                elif line.startswith("SMTP_PASSWORD ="):
                    # Remplace le mot de passe SMTP tout en conservant le commentaire
                    f.write(f"SMTP_PASSWORD = \"{new_config['smtp_password']}\"  # Mot de passe ou App Password (si Gmail)\n")
                else:
                    # Garder toutes les autres lignes inchangées (y compris les commentaires)
                    f.write(line)

        return True
    except Exception as e:
        app.logger.error(f"Erreur lors de la mise à jour de settings.py : {e}")
        return False
    

@app.route('/admin/save-logs-config', methods=['POST'])
def save_logs_config():
    try:
        # Récupérer les données envoyées par le formulaire ou via JSON
        config_data = request.get_json()

        # Préparer les données à sauvegarder
        new_config = {
            "log_backup_count": int(config_data.get('log_backup_count', 0)),
            "log_max_bytes": int(config_data.get('log_max_bytes', 0)) * (1024 * 1024)  # Conversion Mo -> octets
        }

        # Mettre à jour settings.py
        if update_logs_settings(new_config):
            app.logger.info("Configuration des logs mise à jour avec succès.")
            return jsonify({"status": "success"}), 200
        else:
            return jsonify({"status": "error", "message": "Échec de la mise à jour"}), 500

    except Exception as e:
        app.logger.error(f"Erreur lors de la sauvegarde de la configuration des logs : {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def update_logs_settings(new_config):
    """Met à jour les valeurs des logs dans le fichier settings.py tout en conservant les commentaires."""
    try:
        settings_file = "settings.py"
        with open(settings_file, "r") as f:
            lines = f.readlines()

        # Modifier uniquement les lignes correspondant aux paramètres des logs
        with open(settings_file, "w") as f:
            for line in lines:
                if line.startswith("LOG_BACKUP_COUNT"):
                    # Remplace le nombre de sauvegardes tout en conservant le commentaire
                    f.write(f"LOG_BACKUP_COUNT = {new_config['log_backup_count']}  # Nombre de sauvegardes de logs à conserver\n")
                elif line.startswith("LOG_MAX_BYTES"):
                    # Remplace la taille maximale des fichiers log tout en conservant le commentaire
                    f.write(f"LOG_MAX_BYTES = {new_config['log_max_bytes']}  # Taille maximale des fichiers log (en octets)\n")
                else:
                    # Garder toutes les autres lignes inchangées (y compris les commentaires)
                    f.write(line)

        return True
    except Exception as e:
        app.logger.error(f"Erreur lors de la mise à jour de settings.py : {e}")
        return False


if __name__ == '__main__':
    # Planification des tâches périodiques au démarrage
    scheduler.add_job(schedule_test, 'interval', seconds=TUNNEL_CHECK_INTERVAL, next_run_time=datetime.now())
    scheduler.add_job(update_dynamic_metrics, 'interval', seconds=60, next_run_time=datetime.now())
    scheduler.add_job(measure_latency, 'interval', minutes=1, next_run_time=datetime.now())

    # Initialisation au démarrage
    update_dynamic_metrics()

    # Lancement de l'application Flask
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    