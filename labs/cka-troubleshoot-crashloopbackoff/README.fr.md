# Sortir un Deployment du CrashLoopBackOff

La leçon montre l'état `CrashLoopBackOff` : un conteneur qui démarre, plante,
et que le kubelet relance sans fin. Ce cours vous fait enquêter sur un tel
conteneur, et ajoute des cas que la leçon ne montre pas : les journaux de
l'exécution précédente, le délai entre deux relances qui s'allonge, et un
conteneur qui plante trop vite pour qu'on y entre, inspecté par une copie
dont la commande est changée.

Vous travaillez dans un namespace d'essai, `essai-boucle`, avec un Pod
`fichier-absent` qui ne trouve pas son fichier de configuration. Le challenge
porte sur une autre application : vous le ferez seul, à la fin.

Page associée : [CrashLoopBackOff](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/operer/crashloopbackoff-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run cka-troubleshoot-crashloopbackoff
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2.

Créez le namespace, une ConfigMap qui porte une clé `service.ini`, et un Pod
qui monte cette ConfigMap sur `/conf` et lit `/conf/app.ini`. S'il ne le
trouve pas, il sort avec le code 4. La commande attend une minute :

```bash
kubectl create namespace essai-boucle; kubectl create configmap reglages -n essai-boucle --from-literal=service.ini='port=9000'; cat <<YAML | kubectl apply -n essai-boucle -f -
apiVersion: v1
kind: Pod
metadata:
  name: fichier-absent
spec:
  containers:
    - name: app
      image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
      command: ["sh", "-c", "echo lecture de /conf/app.ini; cat /conf/app.ini || exit 4; sleep 3600"]
      volumeMounts:
        - {name: conf, mountPath: /conf}
  volumes:
    - name: conf
      configMap: {name: reglages}
YAML
sleep 60; kubectl get pod fichier-absent -n essai-boucle
```

```text
namespace/essai-boucle created
configmap/reglages created
pod/fichier-absent created
NAME             READY   STATUS   RESTARTS      AGE
fichier-absent   0/1     Error    3 (47s ago)   60s
```

Trois redémarrages en une minute : le Pod est en boucle.

## 📜 Exercice 1 : lire l'exécution d'avant

Attendez que le Pod soit en `CrashLoopBackOff`, entre deux relances, puis
lisez ses journaux, et ceux de l'exécution précédente (`--previous`) :

```bash
until [ "$(kubectl get pod fichier-absent -n essai-boucle -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}')" = CrashLoopBackOff ]; do sleep 2; done; kubectl logs fichier-absent -n essai-boucle; echo '--- précédente :'; kubectl logs fichier-absent -n essai-boucle --previous
```

```text
lecture de /conf/app.ini
cat: can't open '/conf/app.ini': No such file or directory
--- précédente :
lecture de /conf/app.ini
cat: can't open '/conf/app.ini': No such file or directory
```

Les deux disent la même chose : le fichier n'existe pas. `--previous` est
précieux quand le conteneur courant a déjà redémarré et n'a encore rien
écrit : il donne la fin de l'exécution qui a planté. Lisez aussi le code et
la raison de cette fin :

```bash
kubectl get pod fichier-absent -n essai-boucle -o jsonpath='code={.status.containerStatuses[0].lastState.terminated.exitCode} raison={.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text
code=4 raison=Error
```

Le code 4 est celui que le programme a choisi (`exit 4`). Un code propre au
programme désigne l'application. Un code 137 désignerait un arrêt forcé,
souvent par manque de mémoire.

## ⏱️ Exercice 2 : le délai entre deux relances s'allonge

Comptez les démarrages, et lisez le message d'attente du Pod :

```bash
until [ "$(kubectl get pod fichier-absent -n essai-boucle -o jsonpath='{.status.containerStatuses[0].state.waiting.reason}')" = CrashLoopBackOff ]; do sleep 2; done; kubectl get events -n essai-boucle --field-selector involvedObject.name=fichier-absent,reason=Started -o custom-columns=NOMBRE:.count,PREMIER:.firstTimestamp,DERNIER:.lastTimestamp; kubectl get pod fichier-absent -n essai-boucle -o jsonpath='relances={.status.containerStatuses[0].restartCount} attente={.status.containerStatuses[0].state.waiting.message}{"\n"}'
```

```text
NOMBRE   PREMIER                DERNIER
5        2026-11-21T04:51:45Z   2026-11-21T04:53:08Z
relances=4 attente=back-off 1m20s restarting failed container=app pod=fichier-absent_essai-boucle(3c04a7e7-3254-419c-8ebc-c0f47217ba2c)
```

Cinq démarrages, et le kubelet attend maintenant 1 minute 20 avant le
suivant. Il double le délai à chaque échec (10 s, 20 s, 40 s…), jusqu'à
5 minutes. Un Pod en boucle depuis longtemps ne redémarre donc plus que toutes
les 5 minutes : une correction peut sembler sans effet si l'on n'attend pas
la relance suivante.

## 🔍 Exercice 3 : entrer dans une copie qui ne plante pas

Essayez d'entrer dans le conteneur pour voir ce que contient `/conf` :

```bash
kubectl exec fichier-absent -n essai-boucle -- ls /conf; echo "exec : code $?"
```

```text
error: unable to upgrade connection: container not found ("app")
exec : code 1
```

Impossible : entre deux relances, le conteneur n'existe pas. `kubectl debug
--copy-to` crée une copie du Pod, avec une autre commande, ici un simple
`sleep` qui ne plante pas. Entrez dans la copie :

```bash
kubectl debug fichier-absent -n essai-boucle --copy-to=fichier-absent-copie --container=app -- sleep 3600 >/dev/null; kubectl wait --for=condition=Ready pod/fichier-absent-copie -n essai-boucle --timeout=60s; kubectl exec fichier-absent-copie -n essai-boucle -- ls -l /conf/
```

```text
pod/fichier-absent-copie condition met
total 0
lrwxrwxrwx    1 root     root            18 Nov 21 04:54 service.ini -> ..data/service.ini
```

`/conf` contient `service.ini`, et non `app.ini`. Vérifiez la ConfigMap :

```bash
kubectl get configmap reglages -n essai-boucle -o jsonpath='{.data}{"\n"}'
```

```text
{"service.ini":"port=9000"}
```

La cause est trouvée : la clé de la ConfigMap ne porte pas le nom que
l'application cherche. La copie a servi à regarder, sans toucher au Pod
d'origine, qui plante toujours.

## 🧹 Nettoyage

Supprimez le namespace d'essai. La copie part avec lui :

```bash
kubectl delete namespace essai-boucle
```

```text
namespace "essai-boucle" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset cka-troubleshoot-crashloopbackoff
dsoxlab check cka-troubleshoot-crashloopbackoff
```

```text
╭─ Résultat : cka-troubleshoot-crashloopbackoff ─╮
│  0 / 100 pts                                   │
│  ░░░░░░░░░░░░░░░░░░░░  0/5 tests               │
╰────────────────────────────────────────────────╯
```

0 sur 5 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : un Deployment en boucle, dont il faut trouver la
cause et la corriger sur le Deployment lui-même.

```bash
dsoxlab run cka-troubleshoot-crashloopbackoff
dsoxlab challenge cka-troubleshoot-crashloopbackoff
```
