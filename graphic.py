#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import re
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime, timedelta
from settings import TUNNEL_DURATIONS_FILE

# Fonction pour extraire les données du fichier log
def extraire_donnees(fichier_log, jours_glissants):
    # Dictionnaire pour stocker les durées par date
    donnees_par_date = defaultdict(list)

    # Expression régulière pour extraire les informations nécessaires
    pattern = r"Date : (\d{4}-\d{2}-\d{2}) .* Durée : (\d+)h (\d+)m (\d+)s"

    # Calcul de la date limite (jours glissants)
    date_actuelle = datetime.now()
    date_limite = date_actuelle - timedelta(days=jours_glissants)

    with open(fichier_log, "r") as file:
        for ligne in file:
            match = re.search(pattern, ligne)
            if match:
                date_str = match.group(1)
                date = datetime.strptime(date_str, "%Y-%m-%d")
                
                # Filtrer uniquement les dates dans la période définie
                if date >= date_limite:
                    heures = int(match.group(2))
                    minutes = int(match.group(3))
                    secondes = int(match.group(4))

                    # Convertir la durée en heures (fractionnaire)
                    duree_en_heures = heures + minutes / 60 + secondes / 3600

                    # Filtrer les durées inférieures à 1 heure
                    if duree_en_heures >= 1:
                        donnees_par_date[date_str].append((heures, minutes, secondes))  # Stocker la durée en format horaire

    return donnees_par_date

# Fonction pour convertir la durée en format texte (par exemple, "1h 30m")
def format_duree(heures, minutes, secondes):
    return f"{heures}h {minutes}m"

# Fonction pour générer et sauvegarder le graphique
def generer_graphique(donnees_par_date, output_file):
    dates = list(donnees_par_date.keys())
    sessions = list(donnees_par_date.values())

    # Initialiser la base des barres empilées
    bottom = [0] * len(dates)

    plt.figure(figsize=(12, 6))
    colors = plt.cm.tab20.colors  # Palette de couleurs pour différencier les segments

    for date_index, (date, tunnels) in enumerate(donnees_par_date.items()):
        for i, tunnel in enumerate(tunnels):
            heures, minutes, secondes = tunnel
            duree_en_heures = heures + minutes / 60 + secondes / 3600

            # Ajouter une barre empilée pour chaque tunnel
            plt.bar(date_index, duree_en_heures, bottom=bottom[date_index], color=colors[i % len(colors)], edgecolor='black')

            # Ajouter le texte de la durée au format "xh ym" sur la barre
            plt.text(
                date_index,
                bottom[date_index] + duree_en_heures / 2,
                format_duree(heures, minutes, secondes),
                ha='center',
                va='center',
                fontsize=8,
                color='black'
            )

            # Mettre à jour la base pour la prochaine barre empilée
            bottom[date_index] += duree_en_heures

    # Personnalisation du graphique
    plt.title(f"Durées cumulées des tunnels par date (derniers {jours_glissants} jours ≥ à 1h)", fontsize=16)
    plt.ylabel("Durée totale (heures)", fontsize=12)
    plt.xticks(range(len(dates)), dates, rotation=45, fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Sauvegarde en image JPG
    plt.tight_layout()
    plt.savefig(output_file, format='jpg')
    print(f"Graphique sauvegardé sous : {output_file}")

# Demander à l'utilisateur le nombre de jours glissants
try:
    jours_glissants_input = input("Entrez le nombre de jours glissants pour le graphique (par défaut : 30) : ")
    jours_glissants = int(jours_glissants_input) if jours_glissants_input.strip() else 30
except ValueError:
    print("Entrée invalide. Utilisation de la valeur par défaut : 30 jours.")
    jours_glissants = 30

# Chemin vers le fichier log (à adapter selon votre environnement)
fichier_log = TUNNEL_DURATIONS_FILE

# Chemin de sortie pour l'image
output_image = "filtered_cumulative_bargraph.jpg"

# Extraction des données et génération du graphique
donnees_par_date = extraire_donnees(fichier_log, jours_glissants)
generer_graphique(donnees_par_date, output_image)
