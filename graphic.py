#!/usr/bin/env python3
# F4ICR & OpenIA GPT-4

import re
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime, timedelta, date
from settings import TUNNEL_DURATIONS_FILE

# Fonction pour extraire les données avec ou sans filtre
def extraire_donnees(fichier_log, jours_glissants=None, date_cible=None, duree_minimale=1):
    donnees_par_date = defaultdict(list)
    pattern = r"Date : (\d{4}-\d{2}-\d{2}) .* Durée : (\d+)h (\d+)m (\d+)s"

    with open(fichier_log, "r") as file:
        for ligne in file:
            match = re.search(pattern, ligne)
            if match:
                date_str = match.group(1)
                heures = int(match.group(2))
                minutes = int(match.group(3))
                secondes = int(match.group(4))
                duree_en_heures = heures + minutes / 60 + secondes / 3600

                if jours_glissants is not None:
                    # Mode "jours glissants"
                    date_actuelle = datetime.now()
                    date_limite = date_actuelle - timedelta(days=jours_glissants)
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    if date_obj >= date_limite and duree_en_heures >= duree_minimale:
                        donnees_par_date[date_str].append((heures, minutes, secondes))
                elif date_cible is not None:
                    # Mode "date spécifique"
                    if date_str == date_cible and duree_en_heures >= duree_minimale:
                        donnees_par_date[date_str].append((heures, minutes, secondes))

    return donnees_par_date

# Fonction pour formater une durée en texte
def format_duree(heures, minutes, secondes):
    return f"{heures}h {minutes}m"

# Fonction pour générer un graphique cumulé
def generer_graphique_cumule(donnees_par_date, output_file, jours_glissants, duree_minimale):
    dates = list(donnees_par_date.keys())
    bottom = [0] * len(dates)
    plt.figure(figsize=(12, 6))
    colors = plt.cm.tab20.colors

    for date_index, (date, tunnels) in enumerate(donnees_par_date.items()):
        for i, tunnel in enumerate(tunnels):
            heures, minutes, secondes = tunnel
            duree_en_heures = heures + minutes / 60 + secondes / 3600
            plt.bar(date_index, duree_en_heures, bottom=bottom[date_index], color=colors[i % len(colors)], edgecolor='black')
            plt.text(date_index, bottom[date_index] + duree_en_heures / 2,
                     format_duree(heures, minutes, secondes), ha='center', va='center', fontsize=8)
            bottom[date_index] += duree_en_heures

    plt.title(
        f"Durées cumulées des tunnels par date\n(Filtre : durée ≥ {duree_minimale}h, {jours_glissants} jours glissants)",
        fontsize=16)

    plt.ylabel("Durée totale (heures)", fontsize=12)
    plt.xticks(range(len(dates)), dates, rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Graphique cumulé sauvegardé sous : {output_file}")

# Fonction pour générer un graphique non cumulé
def generer_graphique_non_cumule(donnees_par_date, output_file):
    if not donnees_par_date:
        print("Aucune donnée disponible pour la date spécifiée.")
        return

    date, sessions = list(donnees_par_date.items())[0]
    indices = range(len(sessions))
    durees_en_heures = [h + m / 60 + s / 3600 for h, m, s in sessions]
    etiquettes_durees = [format_duree(h, m, s) for h, m, s in sessions]

    plt.figure(figsize=(10, 6))
    plt.bar(indices, durees_en_heures, color='skyblue', edgecolor='black')
    for i, duree in enumerate(durees_en_heures):
        plt.text(i, duree + 0.1, etiquettes_durees[i], ha='center', va='bottom', fontsize=8)

    plt.title(f"Durées des tunnels pour le {date}", fontsize=16)
    plt.ylabel("Durée (heures)", fontsize=12)
    plt.xticks(indices, [f"Tunnel {i+1}" for i in indices], rotation=45)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(output_file)
    print(f"Graphique non cumulé sauvegardé sous : {output_file}")

# Fonction principale interactive
def main():
    while True:
        print("\nChoisissez une option :")
        print("1. Graphique cumulé avec filtres (jours glissants)")
        print("2. Graphique non cumulé pour une date spécifique")
        print("3. Quitter")

        choix = input("Entrez votre choix (1/2/3) : ").strip()

        if choix == "1":
            try:
                jours_glissants_input = input("Entrez le nombre de jours glissants (par défaut : 30) : ")
                jours_glissants = int(jours_glissants_input) if jours_glissants_input.strip() else 30
            except ValueError:
                print("Entrée invalide. Utilisation de la valeur par défaut : 30 jours.")
                jours_glissants = 30

            try:
                duree_minimale_input = input("Entrez la durée minimale à afficher (en heures) (par défaut : ≥ 1) : ")
                duree_minimale = float(duree_minimale_input) if duree_minimale_input.strip() else 1.0
            except ValueError:
                print("Entrée invalide. Utilisation de la valeur par défaut : ≥ 1 heure.")
                duree_minimale = 1.0

            donnees_par_date = extraire_donnees(TUNNEL_DURATIONS_FILE,
                                               jours_glissants=jours_glissants,
                                               duree_minimale=duree_minimale)
            output_image = "filtered_cumulative_bargraph.jpg"
            generer_graphique_cumule(donnees_par_date,
                                     output_image,
                                     jours_glissants,
                                     duree_minimale)

        elif choix == "2":
            # Obtenir l'année et le mois actuels
            maintenant = datetime.now()
            annee_actuelle = maintenant.year
            mois_actuel = maintenant.month

            # Calculer le dernier jour du mois actuel
            dernier_jour_du_mois = (datetime(annee_actuelle, mois_actuel + 1, 1) - timedelta(days=1)).day if mois_actuel < 12 else 31

            while True:  # Boucle pour garantir une saisie valide
                try:
                    jour_saisi = int(input(f"Entrez un jour du mois actuel ({mois_actuel:02d}/{annee_actuelle}), entre 1 et {dernier_jour_du_mois} : "))
                    if 1 <= jour_saisi <= dernier_jour_du_mois:
                        # Construire la date cible automatiquement
                        date_cible = f"{annee_actuelle}-{mois_actuel:02d}-{jour_saisi:02d}"
                        break
                    else:
                        print(f"Veuillez entrer un jour valide entre 1 et {dernier_jour_du_mois}.")
                except ValueError:
                    print("Entrée invalide. Veuillez entrer un nombre.")

            try:
                duree_minimale_input = input("Entrez la durée minimale à afficher (en heures) (par défaut : ≥ 0) : ")
                duree_minimale = float(duree_minimale_input) if duree_minimale_input.strip() else 0.0
            except ValueError:
                print("Entrée invalide. Utilisation de la valeur par défaut : ≥ 0 heure.")
                duree_minimale = 0.0

            donnees_par_date = extraire_donnees(TUNNEL_DURATIONS_FILE,
                                               date_cible=date_cible,
                                               duree_minimale=duree_minimale)
            output_image = f"daily_bargraph_{date_cible}.jpg"
            generer_graphique_non_cumule(donnees_par_date,
                                         output_image)

        elif choix == "3":
            print("Au revoir !")
            break

        else:
            print("Choix invalide. Veuillez entrer 1 ou 2 ou 3.")

if __name__ == "__main__":
    main()
