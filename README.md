# Localtunnel
## En remplacement du script RemoteNgrok, devenu trop limité dans sa version gratuite
Prise de contrôle distant derrière un routeur 4G via ***Localtunnel*** qui est totalement gratuit pour le moment.

Bonjour à tous,

L’objectif de ce tutoriel est de créer un tunnel en utilisant une solution gratuite derrière un routeur 4G. En effet, lorsqu’on utilise une connexion 4G, on ne se connecte pas directement à Internet. On est d’abord placé sur le réseau privé de l’opérateur, qui se charge ensuite de router le trafic vers Internet.

Cela a pour conséquence qu’il est impossible d’ouvrir des ports sur ce point de sortie, ce qui rend le trafic entrant inaccessible :( Une solution pour contourner ce problème est d’utiliser un service de tunnel, comme Localtunnel. Le principe consiste à établir une connexion permanente entre votre réseau local (LAN) et un serveur externe (***Localtunnel***), créant ainsi un tunnel. Ce tunnel permettra au trafic entrant de transiter par le serveur ***Localtunnel*** avant d’être acheminé vers votre réseau local.

Ayant depuis quelque temps fait l'acquisition d'un [M5Stack](https://m5stack.com/) dans le but d'y installer le projet [RRFRemote](https://github.com/armel/RRFRemote) de Armel [F4HWN](https://www.qrz.com/db/F4HWN), ceci afin de pouvoir suivre l'activité du [RRF](http://rrf4.f5nlg.ovh:82/) (Réseau des Répéteurs Francophones) et de piloter mon link [F1ZUJ](https://www.qrz.com/db/F1ZUJ) à distance, j'ai rapidement été confronté au problème d'accéder a mon LAN derrière un routeur 4G.

Ce tunnel bien entendu est dédié dans le cadre du projet ***RRFRemote*** mais pourrait tout aussi bien être utilisé pour d'autres besoins.
Toutefois une petite précision : ***Localtunnel*** ne permet pas de tunneliser des connexions TCP génériques (comme SSH ou FTP), car il est spécifiquement conçu pour les services web utilisant HTTP/HTTPS. 
En ce qui concerne la configuration du fichier _.ini_ pour le ***RRFRemote***, l'URL devra être en HTTP

## Pré-requis
• **Python 3** : Assurez-vous que Python 3 est installé sur votre machine ainsi que **requests** nécessaire pour tester la connectivité HTTP du tunnel mais également **APScheduler** une bibliothèque Python qui permet de planifier l’exécution de code Python à des moments précis, que ce soit une seule fois ou périodiquement, **Flask** un framework web léger et Jinja2 son moteur de templates qui s'installera automatiquement avec **Flask**.

`pip install requests APScheduler Flask`
 
• **Localtunnel** : Installez Localtunnel en utilisant la commande suivante :

`npm install -g localtunnel`

Téléchargez le projet Localtunnel depuis votre répertoire de travail qui est /root/ dans notre exemple :

`git clone https://github.com/F4ICR/Localtunnel.git`

Rendre executable le script **install.sh** en se rendant dans le répertoire ***Localtunnel***

`cd Localtunnel/`

`chmod +x install.sh`

`./install.sh`

Cette dernière commande créera les services nécessaires au bon fonctionnement de l’application ***Localtunnel*** puis lancera les services afin de prévenir toute interruption de son fonctionnement. J’ai également inclus une boucle dans le script 'localtunnel.py' qui tourne en mode deamon afin de verifier la connectivité du tunnel toutes les 300s (5mn).

Petite précision concernant le script **install.sh** : l’installation des services se fait en partant du principe que vous avez installé mon projet GitHub **localtunnel** depuis le repertoire `/root/`, si tel n'était pas le cas, il vous appartient de modifié les chemins d'execution dans **install.sh**

`ExecStart=/usr/bin/python3 /root/Localtunnel/localtunnel.py`
`ExecStart=/usr/bin/python3 /root/Localtunnel/app.py`

## Configuration
Renseignez les variables suivantes soit en éditant le fichier 'settings.py' avec 'nano' depuis la ligne de commande ou depuis votre navigateur web en étant sur le même reseau que le serveur sur lequel vous avec installé ***Localtunnel*** via son IP et le numéro de port 5000, exemple : http://192.168.1.101:5000/
Puis cliquez sur l’icône en forme de roue dentée, saisissez le mot de passe 'password' et rendez-vous dans l'onglet 'Configuration'

`nano settings.py`

> `PORT = 3000  # Le port local que vous souhaitez exposer`

> `EMAIL = "votre_mail.com"  # Remplacez par votre adresse email`
 
> `SMTP_SERVER = "smtp.gmail.com"  # Serveur SMTP (exemple avec Gmail)`

> `SMTP_PORT = 465  # Port SMTP sécurisé (SSL)`

> `SMTP_USER = "votre_mail.com"  # Votre adresse Gmail (ou autre fournisseur)`

> `SMTP_PASSWORD = "password"  # Mot de passe ou App Password (si Gmail)`

Ne modifié les autres variables que si vous savez ce que vous faites.

## Présentation du Programme

Le programme utilise ***Localtunnel*** pour exposer un port local à Internet. Il s’assure qu’un tunnel est actif, teste sa connectivité, et le redémarre si nécessaire. En cas de changement d’URL, il met à jour un fichier de log et envoie une notification par email.

Le script vérifiera si le tunnel est actif ou non :

**• Si la valeur de retour est 1**, aucune action supplémentaire ne sera effectuée.

**• Si la valeur de retour est 0**, le script tentera :

• De récupérer le nom de sous-domaine précédemment attribué, inscrit dans le fichier `tunnel_output.log`, afin de conserver la même URL (si ce fichier existe).

• Il verifiera aussi la connectivité du tunnel de facon réguliere, si le tunnel est inactif ou inaccessible :

•	Il arrêtera l’ancien processus.

•	Créera un nouveau tunnel.

•	Mettra à jour l’URL dans `tunnel_output.log`.

•	Enverra un email avec la nouvelle URL.

•   D'autres fonctions sont également incluses telles que :

•   Vérification des dépendances python pour les besoin du programme.

•   Vérification de la validité des certificats SSL de Locatunnel.

•   Ajout d'une configuration conditionnelle des logs pour les besoins éventuel de débugage

•   Création spécifique d’un journal de log dédié aux statistiques de fonctionnement des tunnels, incluant leur durée ainsi que les URL associées.

• De récupérer le nom de sous-domaine précédemment attribué, inscrit dans le fichier **tunnel_output.log**, afin de conserver la même URL (si ce fichier existe).

• Lors d’un premier lancement, ce fichier n’existe pas encore. Dans ce cas, un email vous sera envoyé contenant l’adresse URL du tunnel.

**Remarque** : Si l’adresse du tunnel ne change pas, aucun email ne sera envoyé.

L’idée de départ était de créer un script shell, ce qui aurait probablement été plus adapté et aussi plus simple pour moi. Cependant, n’ayant jamais utilisé l’IA pour du développement et voulant explorer les possibilités qu’elle pouvait offrir, j’ai décidé d’essayer ***OpenIA GPT-4*** qui est un des modèle d'IA de ***Perplexity*** pour écrire ces scripts en Python.
Je dois dire que l’expérience a été géniale et instructive, même si cela ne c’est pas fait en une seule requête. J’ai dû affiner chacune de mes demandes en étant de plus en plus précis sur ce que je voulais et je ne cesse pas d'améliorer l'ensemble du programme au fil du temps. 
Au final et pour une première, je trouve le résultat plutôt satisfaisant.