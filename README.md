# Localtunnel
En remplacement du script RemoteNgrok (Ngrok) qui est maintenant trop limité en version gratuite

Prise de contrôle distant derrière un routeur 4G via Localtunnel qui est totalement gratuit pour le moment

Bonjour à tous,

le but de ce tuto est de réaliser un tunnel via une solution gratuite derrière un routeur 4G. Lorsque l'on est en 4G, on ne sort pas directement sur Internet, on est sur le réseau privé de l'opérateur et le trafic est ensuite routé vers Internet.

La conséquence est que l'on ne peut pas ouvrir de ports sur ce point de sortie et que le trafic entrant n'est pas possible :( Une solution pour contourner ce problème est d'utiliser un service tunnel comme Localtunnel. Le principe est d'initier une connexion permanente à un serveur externe (Localtunnel) depuis son LAN pour ouvrir un tunnel, cela permettra au trafic entrant de rentrer sur le serveur Localtunnel, passer dans le tunnel pour arriver sur son LAN.

Ayant depuis quelque temps fait l'acquisition d'un M5Stack dans le but d'y installer le projet RRFRemote de Armel F4HWN, ceci afin de pouvoir suivre l'activité du RRF (Réseau des Répéteurs Francophones) et de piloter mon link F1ZUJ à distance, j'ai rapidement été confronté au problème d'accéder a mon LAN derrière un routeur 4G.

Ce tunnel bien entendu est dédié dans le cadre du projet RRFRemote mais pourrait tout aussi bien être utilisé pour d'autres besoins, mais Localtunnel ne fonctionne qu'avec les protocoles HTTP et HTTPS.

