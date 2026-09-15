# Politique de sécurité

## Versions supportées

`kubernetes-dsoxlab-training` est en développement actif. Les correctifs de
sécurité sont appliqués à la dernière version de la branche `main`.

| Version | Supportée |
| --- | --- |
| dernière (`main`) | oui |
| plus anciennes | non |

## Signaler une vulnérabilité

**N'ouvrez pas d'issue publique pour une vulnérabilité de sécurité.**

Si vous pensez avoir trouvé une vulnérabilité, signalez-la en privé :

- De préférence : ouvrez un
  [avis de sécurité privé](https://github.com/stephrobert/kubernetes-dsoxlab-training/security/advisories/new)
  sur GitHub.
- Sinon, utilisez les coordonnées publiées sur
  <https://blog.stephane-robert.info>.

Merci d'inclure :

- une description de la vulnérabilité et de son impact,
- les étapes pour la reproduire (commande, environnement, `dsoxlab --version`),
- tout journal ou preuve de concept pertinent.

Nous vous tiendrons informé de l'avancement du correctif et vous créditerons
dans les notes de version si vous le souhaitez.

## Politique de divulgation

Nous pratiquons la divulgation coordonnée et nous engageons sur les délais
suivants, décomptés à partir de la réception de votre signalement :

| Étape | Délai visé |
| --- | --- |
| Accusé de réception de votre signalement | sous **48 heures** |
| Évaluation initiale et qualification de la sévérité | sous **5 jours** |
| Correctif publié, ou plan de remédiation écrit | sous **30 jours** |
| Divulgation publique de la vulnérabilité | sous **90 jours** |

Nous publions l'avis dès qu'un correctif est disponible, ou au plus tard à
l'échéance des **90 jours**, selon ce qui arrive en premier. Si une
vulnérabilité est activement exploitée, nous pouvons la divulguer plus tôt pour
protéger les utilisateurs. Si un correctif complexe demande plus de temps, nous
vous prévenons avant l'échéance et convenons d'une nouvelle date avec vous,
plutôt que de la laisser expirer sans rien dire.

## Périmètre

Ce dépôt livre du **contenu de labs** exécuté par la CLI externe `dsoxlab` :
scénarios, tests, playbooks de mise en place et de nettoyage, socle de cluster
kubeadm, clé SSH publique.

Sont **dans** le périmètre :

- du matériel de lab dangereux ou malveillant : un `setup.yaml`, un
  `cleanup.yaml`, un script de fixture ou un test qui ferait autre chose que ce
  qu'il annonce ;
- une fuite de secret, ou une clé privée commitée par erreur ;
- un défaut du socle `shared/` : il est inclus par tous les labs et s'exécute en
  `root` sur les deux machines.

Une remarque particulière sur ce catalogue : **plusieurs labs installent
délibérément un état cassé ou affaibli**, parce que c'est leur sujet. Un lab de
diagnostic casse le kubelet, un lab AppArmor charge un profil, un lab RBAC crée
un compte volontairement trop peu doté. Ce n'est pas une vulnérabilité : c'est
la matière de l'exercice, et chaque `cleanup.yaml` défait ce que son lab a posé.
Ces labs sont conçus pour des **machines jetables**, provisionnées par
`dsoxlab provision` et détruites par `dsoxlab destroy`, jamais pour une machine
qui sert à autre chose.

Sont **hors** périmètre : les vulnérabilités du moteur `dsoxlab` lui-même, qui
relèvent de [son propre dépôt](https://github.com/stephrobert/dsoxlab), et les
problèmes des dépendances tierces, à signaler à leurs projets respectifs.
