# Installer et configurer kubectl

Ce cours vous fait pratiquer, sur la machine du lab, chaque geste de la leçon :
relever une version, télécharger un binaire épinglé, vérifier son empreinte,
l'installer, brancher une complétion et un alias, puis atteindre le cluster.
Vous travaillez sur une **autre version** et sous un **autre nom** que ceux du
challenge : le challenge reste entier pour la fin.

Page associée : [Installer et configurer kubectl](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kubectl-installation-configuration/).

## 🔧 Avant de commencer

```bash
dsoxlab run k8s-installer-kubectl
```

La commande prépare la machine `k8s-kind.lab` et vous y connecte. Un cluster
kind nommé `lab` tourne déjà, en Kubernetes `v1.37.0`, et votre fichier
`~/.kube/config` pointe dessus. kubectl, lui, a été retiré : c'est tout l'objet
du lab. Les sorties ci-dessous ont été relevées sur cette machine (Debian 13.7,
amd64) le 19 novembre 2026.

## 📚 Exercice 1 : choisir une version dans l'écart permis

Le client kubectl peut différer d'**une version mineure au plus** du serveur.
Le cluster est en 1.37 : un client 1.36, 1.37 ou 1.38 lui parle. Relevez la
version stable du moment, puis la dernière version de la branche 1.36.

```bash
curl -fsSL https://dl.k8s.io/release/stable.txt
```

```text
v1.37.2
```

```bash
curl -fsSL https://dl.k8s.io/release/stable-1.36.txt
```

```text
v1.36.6
```

La réponse du serveur ne se termine pas par un retour à la ligne : votre
invite s'affiche juste derrière la version, c'est normal.

La première version est celle que le challenge vous demandera. Pour
l'exercice, vous prenez la seconde, `v1.36.6` : une version mineure sous le
cluster, donc dans l'écart permis. Le fichier `stable-1.36.txt` donne le
dernier correctif d'une branche précise, ce qui sert quand on doit rester sur
une version mineure.

## 📚 Exercice 2 : télécharger le binaire et son empreinte, version épinglée

Écrivez la version une seule fois, puis téléchargez le binaire et le fichier
`.sha256` publié à côté, dans un répertoire d'essai.

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

Les deux fichiers viennent forcément de la même version, puisque la variable
`BASE` les nomme tous les deux. Faites maintenant exprès une faute de frappe
dans la version, pour voir ce que fait l'option `-f` :

```bash
curl -fsSLO "https://dl.k8s.io/release/v1.36.66/bin/linux/amd64/kubectl"
```

```text
curl: (22) The requested URL returned error: 404
```

`curl` échoue avec le code 22 au lieu d'écrire la page d'erreur sous le nom
`kubectl`. Sans `-f`, vous auriez un fichier `kubectl` qui n'est pas un
programme.

## 📚 Exercice 3 : vérifier l'empreinte avant d'installer

Le fichier `.sha256` ne contient que l'empreinte : `echo` ajoute le nom du
fichier que `sha256sum --check` attend.

```bash
echo "$(cat kubectl.sha256)  kubectl" | sha256sum --check
```

```text
kubectl: OK
```

Voyez maintenant ce que donne un fichier altéré. Copiez le binaire, ajoutez-lui
un seul octet, et vérifiez la copie contre la même empreinte :

```bash
cp kubectl kubectl-abime
printf x >> kubectl-abime
echo "$(cat kubectl.sha256)  kubectl-abime" | sha256sum --check
```

```text
kubectl-abime: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

Un octet de différence suffit à changer l'empreinte. Devant un `FAILED`, on
supprime le fichier et on recommence le téléchargement : on n'installe jamais
un binaire dont l'empreinte ne correspond pas.

## 📚 Exercice 4 : installer le binaire sans sudo, sous un autre nom

Installez la copie vérifiée dans votre répertoire personnel, sous le nom
`kubectl136`, puis supprimez le répertoire d'essai.

```bash
mkdir -p ~/.local/bin
install -m 0755 ~/essai-kubectl/kubectl ~/.local/bin/kubectl136
ls -l ~/.local/bin/kubectl136
cd ~ && rm -r ~/essai-kubectl
```

```text
-rwxr-xr-x 1 ansible ansible 59592866 Nov 19 09:21 /home/ansible/.local/bin/kubectl136
```

`install` copie le fichier et règle ses droits en une seule commande. Ici le
binaire vous appartient, puisque vous l'avez installé sans `sudo` : votre
compte peut le modifier. Le challenge demande l'inverse, un binaire qui
appartient à `root`, dans `/usr/local/bin`.

Demandez maintenant au shell où il cherche les programmes :

```bash
echo "$PATH" | tr ":" "\n"
```

```text
/usr/local/bin
/usr/bin
/bin
/usr/games
```

`~/.local/bin` n'y est pas : votre session a été ouverte avant que le
répertoire existe. Le fichier `~/.profile` de Debian l'ajoute à chaque
ouverture de session, à condition qu'il existe :

```bash
grep -n -A2 "local/bin" ~/.profile
```

```text
25:if [ -d "$HOME/.local/bin" ] ; then
26:    PATH="$HOME/.local/bin:$PATH"
27-fi
```

Remplacez donc votre shell par un shell de connexion, qui relit `~/.profile`,
puis demandez quel fichier s'exécute :

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

`command -v` donne le chemin du programme que le shell trouve. C'est le premier
réflexe quand une commande répond `command not found` ou affiche une version
inattendue.

## 📚 Exercice 5 : constater ce que le PATH ne trouve pas

Votre client s'appelle `kubectl136`. Demandez au shell s'il connaît `kubectl` :

```bash
command -v kubectl || echo "kubectl introuvable"
ls -l /usr/local/bin/
```

```text
kubectl introuvable
total 10288
-rwxr-xr-x 1 root root 10530942 Nov 19 09:19 kind
```

Aucun programme ne porte le nom `kubectl`, et `/usr/local/bin` ne contient que
`kind`. Installer un binaire ailleurs et sous un autre nom ne le rend pas
disponible pour tout le monde sous son nom attendu : c'est ce que le challenge
vous demandera de faire correctement.

## 📚 Exercice 6 : brancher une complétion et un alias, pour ce shell seulement

La complétion bash de kubectl s'appuie sur le paquet `bash-completion`.
Regardez d'abord s'il est là :

```bash
type _init_completion
```

```text
bash: type: _init_completion: not found
```

Le paquet n'est pas installé sur cette machine : sans lui, la touche Tab ne
complète pas vraiment les sous-commandes. Le challenge vous demandera de
l'installer. Ici, vous apprenez seulement à **enregistrer** une complétion et
un alias, et à voir ce qu'ils deviennent.

Chargez le script de complétion de votre client, créez l'alias `kc` et
branchez-le sur la complétion de kubectl :

```bash
source <(kubectl136 completion bash)
alias kc=kubectl136
complete -o default -F __start_kubectl kc
complete -p kc
```

```text
complete -o default -F __start_kubectl kc
```

L'alias `kc` est branché sur la fonction de complétion de kubectl. Ouvrez
maintenant un **nouveau** shell interactif et posez la même question :

```bash
bash -i -c 'complete -p kc; alias kc'
```

```text
bash: complete: kc: no completion specification
bash: alias: kc: not found
```

Le nouveau shell ne connaît ni la complétion ni l'alias. Ce que vous tapez dans
un shell disparaît avec lui. Pour qu'une complétion ou un alias serve dans
chaque nouveau terminal, il faut l'écrire dans `~/.bashrc` : c'est ce que le
challenge vérifie, dans un nouveau shell.

## 📚 Exercice 7 : atteindre le serveur et lire l'écart de versions

Lancez `version` sans `--client` : kubectl interroge aussi le serveur.

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

La ligne `Server Version` prouve que kubectl a atteint l'API du cluster :
client en 1.36, serveur en 1.37, une version mineure d'écart, donc compatible.
`cluster-info` donne l'adresse de l'API. Le port est tiré au hasard à la
création du cluster, le vôtre sera différent.

## 🧹 Nettoyage

Retirez ce que les exercices ont posé, puis vérifiez que la machine est
revenue à l'état de départ du challenge :

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

Zéro sur six : rien de ce que les exercices ont fait ne compte pour le
challenge, et rien ne reste sur la machine.

## 🎯 Le challenge

Faites maintenant le challenge seul : installer kubectl `v1.37` pour tout le
système, avec sa complétion et l'alias `k` dans chaque nouveau shell.

```bash
dsoxlab run k8s-installer-kubectl
dsoxlab challenge k8s-installer-kubectl
```
