# Installer et configurer kubectl

kubectl est la commande qui sert à parler à un cluster Kubernetes. Dans ce
cours, vous refaites un par un les gestes de la leçon : choisir une version,
télécharger le programme, vérifier qu'il n'a pas été abîmé, l'installer, lui
ajouter un raccourci, puis vérifier qu'il joint le cluster.

Pour vous entraîner, vous installez une **autre version** de kubectl, sous un
**autre nom**. Le challenge, lui, vous demandera la vraie installation : vous
le ferez seul, à la fin.

Page associée : [Installer et configurer kubectl](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-installation-configuration/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-installer-kubectl
```

Vous êtes maintenant connecté à la machine `k8s-kind.lab`. Un cluster nommé
`lab` y tourne déjà, en Kubernetes `v1.37.0`. Votre fichier `~/.kube/config`
contient de quoi s'y connecter. Il ne manque qu'une chose : kubectl, que le lab
a retiré.

Les sorties montrées dans ce cours ont été relevées sur cette machine (Debian
13.7) le 19 novembre 2026.

## 📚 Exercice 1 : choisir une version de kubectl

Les versions de Kubernetes s'écrivent en trois nombres, par exemple `1.37.2`.
Le deuxième nombre, `37`, s'appelle la **version mineure**. kubectl et le
cluster peuvent avoir une version mineure d'écart, pas plus. Le cluster est en
1.37 : kubectl peut donc être en 1.36, 1.37 ou 1.38.

Demandez au site de Kubernetes la dernière version stable :

```bash
curl -fsSL https://dl.k8s.io/release/stable.txt
```

```text
v1.37.2
```

Puis la dernière version de la branche 1.36 :

```bash
curl -fsSL https://dl.k8s.io/release/stable-1.36.txt
```

```text
v1.36.6
```

La réponse ne finit pas par un retour à la ligne. Votre invite s'affiche donc
juste derrière la version : c'est normal.

La `v1.37.2` est celle que le challenge vous demandera. Pour vous entraîner,
vous prenez la `v1.36.6` : elle n'a qu'une version mineure d'écart avec le
cluster, elle peut donc lui parler.

## 📚 Exercice 2 : télécharger kubectl et son empreinte

kubectl se télécharge sous la forme d'un seul fichier, déjà prêt à lancer : on
appelle ça un **binaire**. Le site publie aussi, à côté, son **empreinte** :
une suite de chiffres et de lettres calculée à partir du contenu du fichier.
Elle sert à vérifier que le fichier n'a pas été abîmé en route.

Créez un répertoire d'essai et téléchargez les deux fichiers. La version
n'est écrite qu'une fois, dans une variable : vous êtes sûr que le binaire et
l'empreinte viennent de la même version.

```bash
mkdir ~/essai-kubectl && cd ~/essai-kubectl
KUBECTL_VERSION=v1.36.6
BASE="https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64"
curl -fsSLO "${BASE}/kubectl"
curl -fsSLO "${BASE}/kubectl.sha256"
ls -l
```

```text
total 58204
-rw-rw-r-- 1 ansible ansible 59592866 Nov 19 09:21 kubectl
-rw-rw-r-- 1 ansible ansible       64 Nov 19 09:21 kubectl.sha256
```

Vous avez le binaire `kubectl` (environ 57 Mo) et son empreinte,
`kubectl.sha256` (64 caractères).

Faites maintenant une faute de frappe exprès dans la version, pour voir ce qui
se passe :

```bash
curl -fsSLO "https://dl.k8s.io/release/v1.36.66/bin/linux/amd64/kubectl"
```

```text
curl: (22) The requested URL returned error: 404
```

La version `v1.36.66` n'existe pas, et `curl` s'arrête sur une erreur. C'est
l'option `-f` qui le fait s'arrêter. Sans elle, `curl` aurait enregistré la
page d'erreur sous le nom `kubectl`, et vous auriez un faux kubectl.

## 📚 Exercice 3 : vérifier l'empreinte avant d'installer

Comparez le binaire téléchargé avec l'empreinte publiée :

```bash
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
```

```text
kubectl: OK
```

`OK` : le fichier est bien celui que le projet a publié.

Voyez maintenant ce qui se passe avec un fichier abîmé. Faites une copie du
binaire, ajoutez-lui une seule lettre à la fin, et vérifiez la copie :

```bash
cp kubectl kubectl-abime
printf x >> kubectl-abime
echo "$(cat kubectl.sha256)  kubectl-abime" | sha256sum --check
```

```text
kubectl-abime: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

Une seule lettre en plus suffit : l'empreinte ne correspond plus, et la
vérification affiche `FAILED`. Si cela vous arrive, n'installez pas le
fichier. Supprimez-le et téléchargez-le à nouveau.

## 📚 Exercice 4 : installer kubectl dans votre répertoire personnel

Installez la copie vérifiée dans `~/.local/bin`, sous le nom `kubectl136`.
`install` copie le fichier et le rend lançable en une seule commande. Supprimez
ensuite le répertoire d'essai.

```bash
mkdir -p ~/.local/bin
install -m 0755 ~/essai-kubectl/kubectl ~/.local/bin/kubectl136
ls -l ~/.local/bin/kubectl136
cd ~ && rm -r ~/essai-kubectl
```

```text
-rwxr-xr-x 1 ansible ansible 59592866 Nov 19 09:21 /home/ansible/.local/bin/kubectl136
```

Le fichier appartient à votre compte (`ansible`), puisque vous l'avez installé
sans `sudo`. Le challenge vous demandera l'inverse : une installation pour
toute la machine, dans `/usr/local/bin`, avec `sudo`.

Quand vous tapez une commande, le shell la cherche dans une liste de
répertoires. Cette liste s'appelle le **PATH**. Affichez-la, un répertoire par
ligne :

```bash
echo "$PATH" | tr ":" "\n"
```

```text
/usr/local/bin
/usr/bin
/bin
/usr/games
```

`~/.local/bin` n'est pas dans la liste. Le PATH a été fixé à l'ouverture de
votre session, et à ce moment-là le répertoire n'existait pas encore. Sous
Debian, c'est le fichier `~/.profile` qui l'ajoute, s'il existe :

```bash
grep -n -A2 "local/bin" ~/.profile
```

```text
25:if [ -d "$HOME/.local/bin" ] ; then
26:    PATH="$HOME/.local/bin:$PATH"
27-fi
```

Ce fichier n'est lu qu'à l'ouverture d'une session. Ouvrez-en une nouvelle
avec `exec bash -l`, puis demandez où se trouve `kubectl136` :

```bash
exec bash -l
command -v kubectl136
kubectl136 version --client
```

```text
/home/ansible/.local/bin/kubectl136
Client Version: v1.36.6
Kustomize Version: v5.8.1
```

`command -v` affiche le chemin du programme que le shell va lancer. Pensez-y
quand une commande répond `command not found`, ou affiche une autre version
que celle que vous attendiez.

## 📚 Exercice 5 : vérifier que `kubectl` reste introuvable

Votre programme s'appelle `kubectl136`. Demandez au shell s'il connaît une
commande `kubectl` :

```bash
command -v kubectl || echo "kubectl introuvable"
ls -l /usr/local/bin/
```

```text
kubectl introuvable
total 10288
-rwxr-xr-x 1 root root 10530942 Nov 19 09:19 kind
```

Le shell ne trouve aucune commande `kubectl`, et `/usr/local/bin` ne contient
que `kind`. Ce que vous avez installé ne sert qu'à vous, sous un autre nom.
Le challenge vous demandera une commande `kubectl` utilisable par tous.

## 📚 Exercice 6 : créer un raccourci et une complétion, puis voir qu'ils disparaissent

Deux aides rendent kubectl plus agréable :

- un **alias**, c'est-à-dire un raccourci : vous tapez `kc`, le shell lance
  `kubectl136` ;
- la **complétion** : vous tapez le début d'une commande, la touche Tab
  complète la suite.

Sous Debian, la complétion a besoin du paquet `bash-completion`. Regardez s'il
est installé :

```bash
type _init_completion
```

```text
bash: type: _init_completion: not found
```

Il ne l'est pas : la touche Tab ne complétera pas vraiment les commandes. Le
challenge vous demandera de l'installer. Ici, vous apprenez seulement à créer
l'alias et à déclarer la complétion.

Chargez la complétion de kubectl, créez l'alias `kc`, puis dites au shell que
`kc` se complète comme kubectl :

```bash
source <(kubectl136 completion bash)
alias kc=kubectl136
complete -o default -F __start_kubectl kc
complete -p kc
```

```text
complete -o default -F __start_kubectl kc
```

La dernière ligne confirme que `kc` utilise la complétion de kubectl.
Ouvrez maintenant un **nouveau** shell et posez la même question :

```bash
bash -i -c 'complete -p kc; alias kc'
```

```text
bash: complete: kc: no completion specification
bash: alias: kc: not found
```

Le nouveau shell ne connaît ni l'alias ni la complétion. Tout ce que vous tapez
dans un terminal est oublié quand il se ferme. Pour les garder, il faut les
écrire dans le fichier `~/.bashrc`, que bash lit à chaque ouverture. C'est ce
que le challenge vérifiera, dans un nouveau shell.

## 📚 Exercice 7 : vérifier que kubectl joint le cluster

Lancez `version` sans `--client` : kubectl demande aussi sa version au
cluster.

```bash
kubectl136 version
kubectl136 cluster-info
```

```text
Client Version: v1.36.6
Kustomize Version: v5.8.1
Server Version: v1.37.0
Kubernetes control plane is running at https://127.0.0.1:39177
CoreDNS is running at https://127.0.0.1:39177/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```

La ligne `Server Version` montre que kubectl a bien joint le cluster. Vous
voyez aussi l'écart : kubectl en 1.36, cluster en 1.37, une seule version
mineure d'écart. `cluster-info` donne l'adresse du cluster. Le numéro de port
change à chaque création de cluster : le vôtre sera différent.

## 🧹 Nettoyage

Supprimez ce que vous avez installé, quittez la machine, puis vérifiez que le
lab est revenu à son état de départ :

```bash
rm ~/.local/bin/kubectl136
rmdir ~/.local/bin
exit
dsoxlab check k8s-installer-kubectl
```

```text
╭─ Résultat : k8s-installer-kubectl ─╮
│  0 / 100 pts                       │
│  ░░░░░░░░░░░░░░░░░░░░  0/6 tests   │
╰────────────────────────────────────╯
```

0 sur 6 : c'est le résultat attendu. Rien de ce que vous avez fait dans le
cours ne reste sur la machine.

## 🎯 Le challenge

À vous, seul cette fois : installer kubectl `v1.37` pour toute la machine, avec
l'alias `k` et la complétion, qui doivent marcher dans chaque nouveau
terminal.

```bash
dsoxlab run k8s-installer-kubectl
dsoxlab challenge k8s-installer-kubectl
```
