# Localtunnel
## En remplacement du script RemoteNgrok, devenu trop limité dans sa version gratuite
Prise de contrôle distant derrière un routeur 4G via ***Localtunnel*** qui est totalement gratuit pour le moment

Bonjour à tous,

L’objectif de ce tutoriel est de créer un tunnel en utilisant une solution gratuite derrière un routeur 4G. En effet, lorsqu’on utilise une connexion 4G, on ne se connecte pas directement à Internet. On est d’abord placé sur le réseau privé de l’opérateur, qui se charge ensuite de router le trafic vers Internet.

Cela a pour conséquence qu’il est impossible d’ouvrir des ports sur ce point de sortie, ce qui rend le trafic entrant inaccessible :( Une solution pour contourner ce problème est d’utiliser un service de tunnel, comme Localtunnel. Le principe consiste à établir une connexion permanente entre votre réseau local (LAN) et un serveur externe (***Localtunnel***), créant ainsi un tunnel. Ce tunnel permettra au trafic entrant de transiter par le serveur ***Localtunnel*** avant d’être acheminé vers votre réseau local.

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

Renseigné les variables suivantes en éditant le fichier settings.py avec 'nano'

`nano localtunnel.py`

> `PORT = 3000  # Le port local que vous souhaitez exposer`

> `EMAIL = "votre_mail.com"  # Remplacez par votre adresse email`
 
> `SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP (exemple avec Gmail)`

> `SMTP_PORT = 465  # Port SMTP sécurisé (SSL)`

> `SMTP_USER = "votre_mail.com"  # Votre adresse Gmail (ou autre fournisseur)`

> `SMTP_PASSWORD = "password"  # Mot de passe ou App Password (si Gmail)`

## Présentation du Programme

Le programme utilise Localtunnel pour exposer un port local à Internet. Il s’assure qu’un tunnel est actif, teste sa connectivité, et le redémarre si nécessaire. En cas de changement d’URL, il met à jour un fichier de log et envoie une notification par email.

Pour prévenir une éventuelle interruption du tunnel, nous allons créer une entrée dans la crontab pour relancer le script toutes les 5 minutes.

`nano /etc/crontab`

Puis ajouter la ligne suivant:

> `*/5 * * * * root /root/Localtunel/localtunnel.py >/dev/null 2>&1`

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
