# Rendre un conteneur immuable sans le faire tomber

La leçon montre comment fermer un conteneur : racine en lecture seule,
capacités du noyau retirées. Ce cours se concentre sur le système de fichiers
et les capacités, et ajoute des cas que la leçon ne montre pas : trouver, par
ses erreurs, où une application écrit, lui rendre ce seul répertoire, retirer
toutes les capacités puis en rendre une seule, et un réglage du noyau
(sysctl) que le kubelet refuse.

Vous travaillez dans un namespace d'essai, `essai-fige`, avec un serveur
Apache (`httpd`) et des Pods busybox. Le challenge porte sur une autre
application : vous le ferez seul, à la fin.

Page associée : [Security Context](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/security-context/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cks-security-context-immutable
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et httpd 2.4.66.

## 💥 Exercice 1 : une racine en lecture seule, et l'application tombe

Créez le namespace et un Pod Apache avec `readOnlyRootFilesystem: true`, sans
aucun volume. Attendez 15 secondes, puis lisez la fin de ses journaux :

```bash
kubectl create namespace essai-fige; cat <<YAML | kubectl apply -n essai-fige -f -
apiVersion: v1
kind: Pod
metadata:
  name: apache
spec:
  containers:
    - name: apache
      image: httpd:2.4.66
      securityContext:
        readOnlyRootFilesystem: true
      volumeMounts: []
  volumes: []
YAML
sleep 15; kubectl get pod apache -n essai-fige; kubectl logs apache -n essai-fige --tail=3
```

```text
namespace/essai-fige created
pod/apache created
NAME     READY   STATUS             RESTARTS     AGE
apache   0/1     CrashLoopBackOff   1 (7s ago)   15s
AH00558: httpd: Could not reliably determine the server's fully qualified domain name, using 10.244.38.123. Set the 'ServerName' directive globally to suppress this message
[Sat Nov 21 03:09:06.067497 2026] [core:error] [pid 1:tid 1] (30)Read-only file system: AH00099: could not create /usr/local/apache2/logs/httpd.pid.G6A2yI
[Sat Nov 21 03:09:06.067542 2026] [core:error] [pid 1:tid 1] AH00100: httpd: could not log pid to file /usr/local/apache2/logs/httpd.pid
```

Le Pod redémarre en boucle. Les journaux nomment le fichier que httpd n'a pas
pu créer : `/usr/local/apache2/logs/httpd.pid`, la trace de son numéro de
processus. C'est la méthode à suivre pour n'importe quelle application :
fermer la racine, puis lire ce qui échoue.

## 📂 Exercice 2 : rendre à l'application le seul répertoire où elle écrit

Recréez le Pod avec un volume `emptyDir` monté sur
`/usr/local/apache2/logs`. Une fois prêt, essayez d'écrire ailleurs, puis
listez le répertoire rendu :

```bash
kubectl delete pod apache -n essai-fige; cat <<YAML | kubectl apply -n essai-fige -f -
apiVersion: v1
kind: Pod
metadata:
  name: apache
spec:
  containers:
    - name: apache
      image: httpd:2.4.66
      securityContext:
        readOnlyRootFilesystem: true
      volumeMounts: [{name: journaux, mountPath: /usr/local/apache2/logs}]
  volumes: [{name: journaux, emptyDir: {}}]
YAML
kubectl wait --for=condition=Ready pod/apache -n essai-fige --timeout=120s; kubectl exec apache -n essai-fige -- sh -c 'touch /usr/local/apache2/htdocs/x; echo code $?; ls /usr/local/apache2/logs'
```

```text
pod "apache" deleted from essai-fige namespace
pod/apache created
pod/apache condition met
code 1
touch: cannot touch '/usr/local/apache2/htdocs/x': Read-only file system
httpd.pid
```

Apache tourne. L'écriture dans `htdocs` est refusée : le reste de la racine
reste fermé. Le fichier `httpd.pid` est dans le volume. Un `emptyDir` ne
survit pas au Pod, et c'est voulu : le répertoire ne sert qu'au processus en
cours.

## 🔑 Exercice 3 : retirer toutes les capacités, puis en rendre une

Créez un Pod busybox qui retire toutes les capacités (`drop: [ALL]`), et
essayez de changer le propriétaire de `/tmp` :

```bash
kubectl run sondeur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"capabilities":{"drop":["ALL"]}}}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sondeur -n essai-fige --timeout=120s; kubectl exec sondeur -n essai-fige -- chown 1234 /tmp; echo "chown : code $?"
```

```text
pod/sondeur created
pod/sondeur condition met
chown: /tmp: Operation not permitted
command terminated with exit code 1
chown : code 1
```

Refusé, alors que le processus tourne en root : sans la capacité `CHOWN`,
root lui-même ne peut pas changer un propriétaire. Recréez le Pod en rendant
cette seule capacité (`add: [CHOWN]`), et lisez les capacités actives :

```bash
kubectl delete pod sondeur -n essai-fige; kubectl run sondeur --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"containers":[{"name":"c","image":"busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4","command":["sleep","3600"],"securityContext":{"capabilities":{"drop":["ALL"],"add":["CHOWN"]}}}]}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/sondeur -n essai-fige --timeout=120s; kubectl exec sondeur -n essai-fige -- chown 1234 /tmp; echo "chown : code $?"; kubectl exec sondeur -n essai-fige -- grep CapEff /proc/1/status
```

```text
pod "sondeur" deleted from essai-fige namespace
pod/sondeur created
pod/sondeur condition met
chown : code 0
CapEff:	0000000000000001
```

Le `chown` passe, et `CapEff` vaut 1 : un seul bit, celui de `CHOWN`. Retirer
tout puis rendre ce qui manque donne une liste courte et lisible, au lieu de
la liste par défaut du runtime.

## 🎛️ Exercice 4 : un sysctl que le kubelet refuse

Un Pod peut demander des réglages du noyau propres à son espace réseau, par
`securityContext.sysctls`. Demandez `net.core.somaxconn` :

```bash
kubectl run reglage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"securityContext":{"sysctls":[{"name":"net.core.somaxconn","value":"2048"}]}}}' -- sleep 3600; sleep 10; kubectl get pod reglage -n essai-fige; kubectl get pod reglage -n essai-fige -o jsonpath='{.status.reason}: {.status.message}{"\n"}'
```

```text
pod/reglage created
NAME      READY   STATUS            RESTARTS   AGE
reglage   0/1     SysctlForbidden   0          10s
SysctlForbidden: Pod was rejected: forbidden sysctl: "net.core.somaxconn" not allowlisted
```

Le kubelet rejette le Pod (`SysctlForbidden`) : ce réglage n'est pas dans la
liste de ceux qu'il juge sûrs. Demandez maintenant
`net.ipv4.ip_unprivileged_port_start`, qui en fait partie :

```bash
kubectl delete pod reglage -n essai-fige; kubectl run reglage --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 -n essai-fige --overrides='{"spec":{"securityContext":{"sysctls":[{"name":"net.ipv4.ip_unprivileged_port_start","value":"80"}]}}}' -- sleep 3600; kubectl wait --for=condition=Ready pod/reglage -n essai-fige --timeout=120s; kubectl exec reglage -n essai-fige -- cat /proc/sys/net/ipv4/ip_unprivileged_port_start
```

```text
pod "reglage" deleted from essai-fige namespace
pod/reglage created
pod/reglage condition met
80
```

Accepté, et la valeur est bien 80 dans le Pod. Ce réglage laisse un processus
sans privilège écouter sur le port 80 : il évite de garder une capacité comme
`NET_BIND_SERVICE` pour un serveur web.

## 🧹 Nettoyage

Supprimez le namespace d'essai :

```bash
kubectl delete namespace essai-fige
```

```text
namespace "essai-fige" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cks-security-context-immutable
dsoxlab check cks-security-context-immutable
```

```text
╭─ Résultat : cks-security-context-immutable ─╮
│  0 / 100 pts                                │
│  ░░░░░░░░░░░░░░░░░░░░  0/2 tests            │
╰─────────────────────────────────────────────╯
```

0 sur 2 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un serveur web à fermer, qui doit continuer à
répondre.

```bash
dsoxlab run cks-security-context-immutable
dsoxlab challenge cks-security-context-immutable
```
