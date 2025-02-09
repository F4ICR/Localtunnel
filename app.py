#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

# -*- coding: utf-8 -*-

APP_VERSION = "1.2.4"
DEVELOPER_NAME = "Développé par F4ICR Pascal & OpenIA GPT-4"

from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import psutil
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

app = Flask(__name__)

# Nouveau système de verrouillage et cache
test_lock = Lock()
last_test = {
    "timestamp": None,
    "results": {
        "requests": False,
        "curl": False,
        "wget": False
    },
    "next_check": None
}

# Variables globales pour stocker les informations dynamiques CPU et mémoire
cpu_temperature = "Température non disponible."
memory_info = "Mémoire non disponible."

# Configuration du scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def update_dynamic_metrics():
    """Met à jour les informations CPU et mémoire dynamiquement."""
    global cpu_temperature, memory_info
    try:
        # Mise à jour de la température du CPU
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
        # Mise à jour des informations sur la mémoire
        mem = psutil.virtual_memory()
        total = round(mem.total / (1024 * 1024 * 1024), 2)
        available = round(mem.available / (1024 * 1024 * 1024), 2)
        memory_info = f"{available} Go disponibles sur {total} Go"
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération de la mémoire : {e}")
        memory_info = "Erreur."

def schedule_test():
    """Exécute les tests et met à jour le cache."""
    global last_test
    with test_lock:
        try:
            tunnel_url = read_tunnel_url_from_log()
            if tunnel_url and tunnel_url != "Aucun":
                success = test_tunnel_connectivity(tunnel_url)
                last_test = {
                    "timestamp": datetime.now(),
                    "results": {
                        "requests": success,
                        "curl": success,
                        "wget": success
                    },
                    "next_check": datetime.now() + timedelta(seconds=TUNNEL_CHECK_INTERVAL)
                }
        except Exception as e:
            app.logger.error(f"Erreur des tests planifiés : {e}")

# Planifier le premier test immédiatement puis toutes les 600s
scheduler.add_job(schedule_test, 'interval', seconds=TUNNEL_CHECK_INTERVAL, next_run_time=datetime.now())

# Ajouter une tâche au scheduler pour mettre à jour les métriques toutes les 10 secondes
scheduler.add_job(update_dynamic_metrics, 'interval', seconds=60, next_run_time=datetime.now())

# Appeler une fois au démarrage pour initialiser les valeurs dynamiques
update_dynamic_metrics()

# Variables globales originales conservées
request_count = 0
duration_logger = TunnelDurationLogger()

@app.before_request
def track_request():
    """Incrémenter le compteur de requêtes avant chaque requête."""
    global request_count
    request_count += 1

def get_previous_tunnels():
    """Lit les durées des tunnels précédents depuis le fichier."""
    try:
        with open(TUNNEL_DURATIONS_FILE, "r") as f:
            return f.readlines()[-5:]  # Retourne les 5 dernières entrées
    except FileNotFoundError:
        return ["Aucune donnée disponible."]
    except Exception as e:
        app.logger.error(f"Erreur lors de la lecture des durées des tunnels : {e}")
        return ["Erreur lors de la récupération des données."]

def get_tunnel_start_time():
    """Lit l'heure de démarrage du tunnel depuis un fichier."""
    try:
        with open("/tmp/tunnel_start_time.txt", "r") as f:
            start_time_str = f.read().strip()
            # Adapter au format ISO 8601 avec microsecondes
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

@app.route('/')
def index():
    """Page principale avec les informations sur le tunnel."""
    tunnel_active = is_tunnel_active(PORT)
    
    if tunnel_active:
        try:
            with open(TUNNEL_OUTPUT_FILE, "r") as file:
                tunnel_url = file.read().strip()
                app.logger.info(f"URL actuelle du tunnel : {tunnel_url}")
            
            start_time = get_tunnel_start_time()
            if start_time:
                uptime = datetime.now() - start_time
                uptime_str = f"{uptime.days} jours, {uptime.seconds // 3600} heures, {(uptime.seconds // 60) % 60} minutes"
            else:
                uptime_str = "Temps inconnu"
                
        except FileNotFoundError:
            app.logger.error(f"Fichier {TUNNEL_OUTPUT_FILE} introuvable.")
            tunnel_url = "Fichier non trouvé"
            uptime_str = "Temps inconnu"
        except Exception as e:
            app.logger.error(f"Erreur lors de la lecture de {TUNNEL_OUTPUT_FILE} : {e}")
            tunnel_url = "Erreur lors de la récupération de l'URL"
            uptime_str = "Temps inconnu"
    else:
        app.logger.warning("Aucun tunnel actif détecté.")
        tunnel_url = "Aucun"
        uptime_str = "Aucun"

    previous_tunnels = get_previous_tunnels()

    # Transmettre datetime au template avec les variables dynamiques CPU et mémoire
    return render_template(
        'index.html',
      	app_version=APP_VERSION,
      	developer_name=DEVELOPER_NAME,
      	tunnel_active=tunnel_active,
      	tunnel_url=tunnel_url,
      	uptime=uptime_str,
      	request_count=request_count,
      	previous_tunnels=previous_tunnels,
      	cpu_temperature=cpu_temperature,
      	memory_info=memory_info,
      	last_test=last_test,
      	datetime=datetime
    )

@app.route('/start', methods=['POST'])
def start():
    """Démarre un tunnel Localtunnel."""
    try:
        if is_tunnel_active(PORT):
            return jsonify({"status": "error", "message": "Tunnel déjà actif."})
        
        url = start_tunnel(PORT, SUBDOMAIN)
        
        if url:
            with open("/tmp/tunnel_start_time.txt", "w") as f:
                f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            
            return jsonify({"status": "success", "message": f"Tunnel démarré : {url}"})
        
        return jsonify({"status": "error", "message": "Échec du démarrage du tunnel."})
            
    except Exception as e:
        app.logger.error(f"Erreur lors du démarrage du tunnel : {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/stop', methods=['POST'])
def stop():
    """Arrête un tunnel Localtunnel."""
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
    """Retourne les résultats sans exécuter de tests"""
    try:
        with test_lock:
            if not last_test["timestamp"]:
                return jsonify({"status": "pending", "message": "Premier test en cours..."})
            
            return jsonify({
                "status": "success",
                "results": last_test["results"],
                "last_check": last_test["timestamp"].isoformat(),
                "next_check": last_test["next_check"].isoformat()
            })
            
    except Exception as e:
        app.logger.error(f"Erreur lors de la récupération des résultats : {e}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
