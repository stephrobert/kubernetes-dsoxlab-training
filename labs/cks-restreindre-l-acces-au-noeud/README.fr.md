# Restreindre qui se connecte à un worker, et avec quels droits

La leçon montre comment réserver SSH à un groupe et réduire les droits `sudo`
d'un compte. Ce cours ajoute trois gestes qu'elle ne montre pas : demander à
sshd ce qu'il déciderait pour un utilisateur donné, sans le recharger ; faire
refuser un fichier sudoers mal écrit avant qu'il ne casse `sudo` ; et lire les
droits réels d'un compte, argument par argument.

Vous travaillez sur `k8s-w1.lab`, par `ssh` depuis le control plane, avec un
compte et un groupe d'essai. Le challenge porte sur un autre nœud et d'autres
comptes : vous le ferez seul, à la fin.

Page associée : [Durcir les nœuds d'un cluster Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/securiser/durcir-les-noeuds/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-restreindre-l-acces-au-noeud
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). `ssh` atteint les workers sans mot de passe.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
22 novembre 2026, avec Kubernetes v1.37.2, Ubuntu 24.04 et OpenSSH 9.6.

Créez d'abord le compte `essai-visiteur` et le groupe `essai-astreinte` sur
`k8s-w1.lab` :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo groupadd -f essai-astreinte; sudo useradd -m -s /bin/bash essai-visiteur 2>/dev/null; id essai-visiteur'
```

```text
uid=1002(essai-visiteur) gid=1003(essai-visiteur) groups=1003(essai-visiteur)
```

## 🔍 Exercice 1 : ce que sshd ferait, sans le recharger

`sshd -T` affiche la configuration que sshd appliquerait, une fois tous ses
fichiers lus. C'est la seule façon fiable de la connaître : sshd garde la
**première** valeur lue pour un mot-clé, et l'ordre des fichiers de
`sshd_config.d/` décide. Relevez les quatre réglages qui comptent ici :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo sshd -T | grep -E "^(passwordauthentication|permitrootlogin|allowgroups|allowusers)"'
```

```text
permitrootlogin without-password
passwordauthentication no
```

Ni `allowgroups` ni `allowusers` n'apparaissent : tout compte qui a une clé
peut entrer. Ajoutez une restriction dans un fichier d'essai, faites-la
vérifier par `sshd -t` (qui ne fait que lire la configuration), puis demandez
à sshd ce qu'il déciderait pour une connexion précise avec `-C` :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'printf "AllowGroups essai-astreinte\n" | sudo tee /etc/ssh/sshd_config.d/90-essai.conf >/dev/null; sudo sshd -t; echo "sshd -t : code $?"; sudo sshd -T -C user=essai-visiteur,host=poste,addr=10.0.0.9 | grep -E "^allowgroups"'
```

```text
sshd -t : code 0
allowgroups essai-astreinte
```

`sshd -t` rend 0 : le fichier se lit, sshd redémarrerait sans erreur. `-C
user=...,host=...,addr=...` décrit une connexion, et sshd répond avec les
règles qui s'appliqueraient à elle. Vous testez ainsi une règle avant de
recharger le service, donc avant de risquer de vous enfermer dehors.

Retirez le fichier d'essai et vérifiez que la restriction a disparu :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo rm -f /etc/ssh/sshd_config.d/90-essai.conf; sudo sshd -T | grep -c "^allowgroups"'
```

```text
0
```

`grep -c` compte 0 ligne (et rend le code 1 quand il ne trouve rien) :
la configuration est revenue à l'état de départ, sans que sshd ait été
rechargé une seule fois.

## 🛑 Exercice 2 : un fichier sudoers refusé avant de faire du mal

Un fichier de `/etc/sudoers.d/` mal écrit fait échouer **tout** `sudo` sur la
machine, y compris le vôtre. `visudo -c -f` vérifie un fichier sans
l'installer. Écrivez une règle à laquelle il manque les deux-points après
`NOPASSWD` :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'echo "essai-visiteur ALL=(root) NOPASSWD /usr/bin/journalctl -u kubelet" > /tmp/essai-sudoers; sudo visudo -c -f /tmp/essai-sudoers'
```

```text
/tmp/essai-sudoers:1:66: syntax error
essai-visiteur ALL=(root) NOPASSWD /usr/bin/journalctl -u kubelet
                                                                 ^
```

`visudo` refuse, montre la ligne et rend le code 1. Corrigez la règle, et ne
l'installez que si la vérification passe :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'echo "essai-visiteur ALL=(root) NOPASSWD: /usr/bin/journalctl -u kubelet" > /tmp/essai-sudoers; sudo visudo -c -f /tmp/essai-sudoers && sudo install -m 0440 /tmp/essai-sudoers /etc/sudoers.d/essai-visiteur'
```

```text
/tmp/essai-sudoers: parsed OK
```

`parsed OK`, puis `install -m 0440` pose le fichier avec les droits que sudo
exige. Le `&&` garantit qu'un fichier refusé n'arrive jamais dans
`/etc/sudoers.d/`.

## 🔐 Exercice 3 : ce que le compte peut faire avec sudo

`sudo -l -U` liste les droits d'un compte, tels que sudo les calcule à partir
de tous ses fichiers :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo -l -U essai-visiteur | tail -2'
```

```text
User essai-visiteur may run the following commands on k8s-w1:
    (root) NOPASSWD: /usr/bin/journalctl -u kubelet
```

Une seule règle : `journalctl -u kubelet`, sans mot de passe. Essayez-la telle
quelle, puis avec un argument de plus, puis une autre commande :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo -u essai-visiteur sudo -n /usr/bin/journalctl -u kubelet >/dev/null; echo "la ligne exacte : code $?"; sudo -u essai-visiteur sudo -n /usr/bin/journalctl -u kubelet -n 1 >/dev/null; echo "un argument de plus : code $?"; sudo -u essai-visiteur sudo -n /usr/bin/systemctl restart kubelet; echo "une autre commande : code $?"'
```

```text
la ligne exacte : code 0
sudo: a password is required
un argument de plus : code 1
sudo: a password is required
une autre commande : code 1
```

La ligne exacte passe (code 0). Avec `-n 1` en plus, sudo refuse : une règle
qui porte des arguments n'autorise **que** ces arguments. C'est ce qui permet
de donner une seule commande à un compte, mais c'est aussi un piège : une
règle trop précise refuse un usage légitime, et une règle sans argument
(`/usr/bin/journalctl`) autoriserait n'importe quelle option.

## 🧹 Nettoyage

Retirez le fichier sudoers, le compte et le groupe d'essai :

```bash
ssh -o StrictHostKeyChecking=no k8s-w1.lab 'sudo rm -f /etc/sudoers.d/essai-visiteur /tmp/essai-sudoers; sudo userdel -r essai-visiteur 2>/dev/null; sudo groupdel essai-astreinte; id essai-visiteur 2>&1'
```

```text
id: ‘essai-visiteur’: no such user
```

`id` ne trouve plus le compte : `k8s-w1.lab` est revenu à son état de départ.

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-restreindre-l-acces-au-noeud
dsoxlab check cks-restreindre-l-acces-au-noeud
```

```text
╭─ Résultat : cks-restreindre-l-acces-au-noeud ─╮
│  0 / 100 pts                                  │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests              │
╰───────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un worker où tout compte entre par SSH, avec un mot
de passe, et un compte d'astreinte qui a bien trop de droits.

```bash
dsoxlab run cks-restreindre-l-acces-au-noeud
dsoxlab challenge cks-restreindre-l-acces-au-noeud
```
