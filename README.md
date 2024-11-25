# Localtunnel
## En remplacement du script RemoteNgrok (Ngrok) qui est maintenant trop limité dans sa version gratuite

Prise de contrôle distant derrière un routeur 4G via ***Localtunnel*** qui est totalement gratuit pour le moment

Bonjour à tous,

le but de ce tuto est de réaliser un tunnel via une solution gratuite derrière un routeur 4G. Lorsque l'on est en 4G, on ne sort pas directement sur Internet, on est sur le réseau privé de l'opérateur et le trafic est ensuite routé vers Internet.

La conséquence est que l'on ne peut pas ouvrir de ports sur ce point de sortie et que le trafic entrant n'est pas possible :( Une solution pour contourner ce problème est d'utiliser un service tunnel comme ***Localtunnel***. Le principe est d'initier une connexion permanente à un serveur externe (_Localtunnel_) depuis son LAN pour ouvrir un tunnel, cela permettra au trafic entrant de rentrer sur le serveur ***Localtunnel***, passer dans le tunnel pour arriver sur son LAN.

Ayant depuis quelque temps fait l'acquisition d'un [M5Stack](https://m5stack.com/) dans le but d'y installer le projet [RRFRemote](https://github.com/armel/RRFRemote) de Armel [F4HWN](https://www.qrz.com/db/F4HWN), ceci afin de pouvoir suivre l'activité du [RRF](http://rrf4.f5nlg.ovh:82/) (Réseau des Répéteurs Francophones) et de piloter mon link [F1ZUJ](https://www.qrz.com/db/F1ZUJ) à distance, j'ai rapidement été confronté au problème d'accéder a mon LAN derrière un routeur 4G.

Ce tunnel bien entendu est dédié dans le cadre du projet ***RRFRemote*** mais pourrait tout aussi bien être utilisé pour d'autres besoins.
Toutefois une petite précision : ***Localtunnel*** ne permet pas de tunneliser des connexions TCP génériques (comme SSH ou FTP), car il est spécifiquement conçu pour les services web utilisant HTTP/HTTPS. 
En ce qui concerne la configuration du fichier _.ini_ pour le ***RRFRemote***, l'URL devra être en HTTP

## Pré-requis
Avant d’utiliser ce script, vous devez installer certaines dépendances :

• **Python 3** : Assurez-vous que Python 3 est installé sur votre machine.
 
• **Localtunnel** : Installez Localtunnel en utilisant la commande suivante :

`npm install -g localtunnel`

Téléchargez le projet Localtunnel depuis votre répertoire de travail qui est /root/ dans notre exemple :

`git clone https://github.com/F4ICR/Localtunnel.git`

Rendre executable le script localtunnel.py en se rendant dans le répertoire Localtunnel

`cd Localtunnel/`

`chmod +x localtunnel.py`

Renseigné les variables aux lignes 5, 11, 14, 17, 20 et 23 en éditant le fichier settings.py avec 'nano'

`nano settings.py`

> `PORT = 3000  # Le port local que vous souhaitez exposer` (Ligne 5)

> `EMAIL = "votre_mail.com"  # Remplacez par votre adresse email` (Ligne 11)
 
> `SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP (exemple avec Gmail)` (Ligne 14)

> `SMTP_PORT = 465  # Port SMTP sécurisé (SSL)` (Ligne 17)

> `SMTP_USER = "votre_mail.com"  # Votre adresse Gmail (ou autre fournisseur)` (Ligne 20)

> `SMTP_PASSWORD = "password"  # Mot de passe ou App Password (si Gmail)` (Ligne 23)

L’exécution du script se déroule comme suit : démarrage du tunnel avec la création du fichier tunnel_output.log pour y enregistrer l’URL qui permettra la connexion depuis l'exterieur. Pour prévenir une éventuelle interruption du tunnel, nous allons créer une entrée dans la crontab pour relancer le script toutes les 5 minutes.

`nano /etc/crontab`

Puis ajouter la ligne suivant:

> `*/5 * * * * root /root/Localtunnel/localtunnel.py >/dev/null 2>&1`

Relancer le service crontab pour que ce changement soit effectif

`service cron restart`

Le script vérifiera si le tunnel est actif ou non :

**• Si la valeur de retour est 1**, aucune action supplémentaire ne sera effectuée.

**• Si la valeur de retour est 0**, le script tentera :


• De récupérer le nom de sous-domaine précédemment attribué, inscrit dans le fichier **tunnel_output.log**, afin de conserver la même URL (si ce fichier existe).

• Lors d’un premier lancement, ce fichier n’existe pas encore. Dans ce cas, un email vous sera envoyé contenant l’adresse URL du tunnel.

**Remarque** : Si l’adresse du tunnel ne change pas, aucun email ne sera envoyé.

L’idée de départ était de créer un script shell, ce qui aurait probablement été plus adapté et aussi plus simple pour moi. Cependant, n’ayant jamais utilisé l’IA pour du développement et voulant explorer les possibilités qu’elle pouvait offrir, j’ai décidé d’essayer ***OpenIA GPT-4*** qui est un des modèle d'IA de ***Perplexity*** pour écrire ce script en Python.
Je dois dire que l’expérience a été géniale et instructive, même si cela ne c’est pas fait en une seule requête. J’ai dû affiner chacune de mes demandes en étant de plus en plus précis sur ce que je voulais. Au final et pour une première, je trouve le résultat plutôt satisfaisant.
