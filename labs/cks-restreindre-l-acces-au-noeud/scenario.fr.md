# Restreindre qui se connecte à un worker, et avec quels droits

## La situation

Le second worker **`k8s-w2.lab`** a été installé à partir d'un ancien modèle
de serveur. Vous ouvrez une session dessus depuis le control plane avec
`ssh k8s-w2.lab`, sous votre compte **`ansible`**, qui a `sudo`.

Sur ce nœud :

- SSH accepte **tous les comptes**, **par mot de passe**, et **root** peut se
  connecter. Le fichier `/etc/ssh/sshd_config.d/05-heritage.conf` vient de
  l'ancien modèle ;
- le compte d'astreinte **`stagiaire`** a **tous les droits sudo**, et par
  deux chemins. Son seul besoin réel : lire l'état du kubelet avec
  `sudo /usr/bin/systemctl status kubelet`.

Deux comptes administrent le nœud et doivent garder l'accès : **`ansible`**
(l'automatisation, et votre session) et **`student`** (l'administrateur
humain).

## Ce que vous devez obtenir

1. Seuls les membres du groupe **`k8s-admins`** ouvrent une session SSH sur
   `k8s-w2.lab`. Ce groupe contient `ansible` et `student`, et **pas**
   `stagiaire`.
2. sshd n'accepte que les **clés** : plus de mot de passe, et **root** ne se
   connecte pas.
3. `stagiaire` garde son compte, perd tous ses autres droits, et peut lancer
   **sans mot de passe** `sudo /usr/bin/systemctl status kubelet`, rien de plus.

## Les repères

Une erreur dans `AllowGroups` vous enferme hors du nœud. Gardez votre première
session **ouverte** pendant tout le travail, et ne la fermez qu'après avoir
réussi une seconde connexion. `sshd -t` vérifie la syntaxe avant le
rechargement, et un rechargement ne coupe pas les sessions ouvertes.

`sudo sshd -T` montre la configuration **lue sur le disque**. Le démon en
marche peut en garder une autre : après un rechargement, `pgrep -a sshd` doit
montrer **un seul** processus `sshd -D [listener]`. Un ancien, resté d'un
redémarrage, garde l'ancienne configuration et sert une partie des connexions. sshd lit les fichiers de `sshd_config.d` par ordre alphabétique et
garde la **première** valeur lue de chaque mot-clé.

Pour les droits sudo, `sudo -l -U stagiaire` montre tout ce qu'un compte peut
faire, quelle qu'en soit la source. Vérifiez un fichier sudoers avec
`visudo -cf` avant de le mettre en place : un fichier cassé peut priver tous
les comptes de sudo.

Une fois le nœud fermé, regardez aussi ce que permettent les identifiants du
kubelet, depuis `k8s-w2.lab` :
`sudo kubectl --kubeconfig /etc/kubernetes/kubelet.conf get nodes`, puis
`get node k8s-w2.lab`. L'autorisateur Node ne lui laisse lire que son propre
nœud. Ce geste n'est pas noté.

## Comment vous saurez que ça marche

Les tests ouvrent de vraies sessions SSH sur `k8s-w2.lab` avec une clé d'essai
posée chez `stagiaire`, `student` et `ansible`, lisent `sshd -T`, et essaient
les droits sudo de `stagiaire`.

```bash
dsoxlab check cks-restreindre-l-acces-au-noeud
```

Si vous vous êtes enfermé dehors : `dsoxlab destroy --optional-hosts`, puis
`dsoxlab run cks-restreindre-l-acces-au-noeud` remonte une machine neuve.
