#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# F4ICR & OpenAI GPT-4

APP_VERSION = "1.3.5"
DEVELOPER_NAME = "Développé par F4ICR Pascal & OpenAI GPT-4"

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
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
from settings import PORT, SUBDOMAIN, TUNNEL_DURATIONS_FILE, TUNNEL_OUTPUT_FILE, TUNNEL_CHECK_INTERVAL

# Initialisation de l'application Flask
app = Flask(__name__)

# Verrou pour les tests concurrents et cache des résultats des tests
latency_lock = Lock()
last_latency = {"value": None, "timestamp": None}
test_lock = Lock()
last_test = {
    "timestamp": None,
    "results": {"requests": False, "curl": False, "wget": False},
    "next_check": None,
}

# Variables dynamiques pour CPU et mémoire
cpu_temperature = "Température non disponible."
memory_info = "Mémoire non disponible."

# Scheduler pour les tâches planifiées
scheduler = BackgroundScheduler()
scheduler.start()

# Compteur de requêtes HTTP et gestion des durées de tunnels
request_count = 0
duration_logger = TunnelDurationLogger()


def measure_latency(host="8.8.8.8"):
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
    """Met à jour les informations CPU et mémoire."""
    global cpu_temperature, memory_info
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

    try:
        mem = psutil.virtual_memory()
        total = round(mem.total / (1024 ** 3), 2)
        available = round(mem.available / (1024 ** 3), 2)
        memory_info = f"{available} Go disponibles sur {total} Go"
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération de la mémoire : {e}")
        memory_info = "Erreur."


def schedule_test():
    """Exécute les tests périodiques sur le tunnel."""
    global last_test
    with test_lock:
        try:
            tunnel_url = read_tunnel_url_from_log()
            if tunnel_url and tunnel_url != "Aucun":
                results = test_tunnel_connectivity(tunnel_url)
                
                last_test.update({
                    "timestamp": datetime.now(),
                    "results": results,  # Utilisation directe du dictionnaire
                    "next_check": datetime.now() + timedelta(seconds=TUNNEL_CHECK_INTERVAL),
                })
        except Exception as e:
            app.logger.error(f"Erreur lors des tests planifiés : {e}")


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
    """Retourne les données historiques des tunnels pour les X derniers jours."""
    try:
        # Calculer la date limite
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Lire les données du fichier
        previous_tunnels = get_previous_tunnels()

        data = []
        for entry in previous_tunnels:
            try:
                # Extraire la date et la durée
                if "Date" in entry and "Durée" in entry:
                    date_part = entry.split("|")[0].split(":")[1].strip()
                    duration_part = entry.split("|")[-1].split(":")[1].strip()

                    # Convertir la date en objet datetime
                    tunnel_date = datetime.strptime(date_part, "%Y-%m-%d")
                    
                    # Filtrer par date limite
                    if tunnel_date >= cutoff_date:
                        # Convertir la durée en heures
                        hours, minutes, seconds = map(
                            int,
                            duration_part.replace("h", "").replace("m", "").replace("s", "").split()
                        )
                        total_hours = round(hours + minutes / 60 + seconds / 3600, 2)
                        
                        # Ajouter au tableau final
                        data.append({"date": date_part, "duration": total_hours})
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


### Routes Flask ###
@app.before_request
def track_request():
    """Incrémente le compteur avant chaque requête."""
    global request_count
    request_count += 1


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


if __name__ == '__main__':
    # Planification des tâches périodiques au démarrage
    scheduler.add_job(schedule_test, 'interval', seconds=TUNNEL_CHECK_INTERVAL, next_run_time=datetime.now())
    scheduler.add_job(update_dynamic_metrics, 'interval', seconds=60, next_run_time=datetime.now())
    scheduler.add_job(measure_latency, 'interval', minutes=1, next_run_time=datetime.now())

    # Initialisation au démarrage
    update_dynamic_metrics()

    # Lancement de l'application Flask
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    