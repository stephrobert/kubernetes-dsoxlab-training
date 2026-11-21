# Rendre une application conforme au 12-factor sur Kubernetes

La leçon fait reprendre une application facteur par facteur : configuration,
ressource attachée, état, arrêt propre et tâche d'administration. Ce cours
pousse chacun de ces gestes là où il casse : une configuration absente, un
cache mal adressé que la sonde de l'application ne voit pas, des noms de clés
inhabituels, un `preStop` trop long pour le délai d'arrêt, et un Job qu'on ne
peut pas corriger en place.

Vous travaillez dans un namespace d'essai, `essai-douze`, avec une application
`vitrine` (podinfo) et un cache Redis `cache`. Le challenge porte sur une
autre application : vous le ferez seul, à la fin.

Page associée : [Rendre une application conforme au 12-factor sur Kubernetes](https://www.stephane-robert.info/docs/conteneurs/cloud-native/application-12-factor-kubernetes/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run k8s-rendre-une-application-conforme-12-facteurs
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
21 novembre 2026, avec Kubernetes v1.37.2 et podinfo 6.17.0.

Créez d'abord le namespace d'essai et un cache Redis, exposé par un Service :

```bash
kubectl create namespace essai-douze
kubectl create deployment cache --image=redis:7.4.11-alpine@sha256:858f009f9709ce576febc734aa78b8f6d624b82571f9ddb6bda4377c833b3499 -n essai-douze; kubectl expose deployment cache --port=6379 -n essai-douze; kubectl rollout status deployment/cache -n essai-douze --timeout=120s
```

```text
namespace/essai-douze created
deployment.apps/cache created
service/cache exposed
Waiting for deployment "cache" rollout to finish: 0 of 1 updated replicas are available...
deployment "cache" successfully rolled out
```

## 📚 Exercice 1 : une configuration qui n'existe pas encore

Déployez `vitrine`. Sa configuration vient d'une ConfigMap, `vitrine-config`,
par `envFrom`. Cette ConfigMap n'existe pas encore :

```bash
mkdir -p ~/essai-douze && cat > ~/essai-douze/vitrine.yaml <<YAML
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: essai-douze
spec:
  replicas: 1
  selector:
    matchLabels: {app: vitrine}
  template:
    metadata:
      labels: {app: vitrine}
    spec:
      containers:
        - name: vitrine
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          envFrom:
            - configMapRef:
                name: vitrine-config
YAML
kubectl apply -f ~/essai-douze/vitrine.yaml
```

```text
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitrine
  namespace: essai-douze
spec:
  replicas: 1
  selector:
    matchLabels: {app: vitrine}
  template:
    metadata:
      labels: {app: vitrine}
    spec:
      containers:
        - name: vitrine
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          envFrom:
            - configMapRef:
                name: vitrine-config
YAML
kubectl apply -f ~/essai-douze/vitrine.yaml
deployment.apps/vitrine created
```

Le Deployment est accepté. Regardez le Pod après quelques secondes :

```bash
sleep 15; kubectl get pods -n essai-douze -l app=vitrine
```

```text
NAME                       READY   STATUS                       RESTARTS   AGE
vitrine-7bb897cb9d-7r788   0/1     CreateContainerConfigError   0          15s
```

`CreateContainerConfigError` : le kubelet ne peut pas construire
l'environnement du conteneur. L'événement dit pourquoi :

```bash
kubectl get events -n essai-douze --field-selector reason=Failed -o custom-columns=MESSAGE:.message | tail -2
```

```text
MESSAGE
Error: configmap "vitrine-config" not found
```

Créez la ConfigMap. Le Pod démarre seul, sans être recréé :

```bash
kubectl create configmap vitrine-config -n essai-douze --from-literal=PODINFO_UI_MESSAGE=bonjour --from-literal=PODINFO_CACHE_SERVER=tcp://cache:6379; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s; kubectl get pods -n essai-douze -l app=vitrine
```

```text
configmap/vitrine-config created
Waiting for deployment "vitrine" rollout to finish: 0 of 1 updated replicas are available...
deployment "vitrine" successfully rolled out
NAME                       READY   STATUS    RESTARTS   AGE
vitrine-7bb897cb9d-7r788   1/1     Running   0          24s
```

Le Pod garde son nom : le kubelet a réessayé, et a trouvé la ConfigMap.
Exposez l'application pour la suite :

```bash
kubectl expose deployment vitrine --name=vitrine-svc --port=80 --target-port=9898 -n essai-douze
```

```text
service/vitrine-svc exposed
```

## 📚 Exercice 2 : `optional`, et ce qu'il cache

Une référence `optional: true` laisse démarrer le conteneur même si la
ConfigMap manque. Supprimez la ConfigMap, puis rendez la référence
facultative :

```bash
kubectl delete configmap vitrine-config -n essai-douze; kubectl patch deployment vitrine -n essai-douze --type json -p '[{"op":"add","path":"/spec/template/spec/containers/0/envFrom/0/configMapRef/optional","value":true}]'; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap "vitrine-config" deleted from essai-douze namespace
deployment.apps/vitrine patched
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

L'application tourne. Mais elle tourne sans aucune configuration :

```bash
kubectl exec deploy/vitrine -n essai-douze -- env | grep '^PODINFO_' ; echo "grep : code $?"
```

```text
grep : code 1
```

Aucune variable `PODINFO_`. Rien ne signale l'absence : le Pod est `Running`
et la panne se verra plus tard, dans le comportement de l'application.
`optional` convient à un réglage vraiment facultatif, jamais à la
configuration dont l'application a besoin.

## 📚 Exercice 3 : un cache mal adressé

Recréez la ConfigMap avec une erreur : le port 6380 au lieu de 6379.
Redémarrez le Deployment pour que le nouveau Pod la lise :

```bash
kubectl create configmap vitrine-config -n essai-douze --from-literal=PODINFO_UI_MESSAGE=bonjour --from-literal=PODINFO_CACHE_SERVER=tcp://cache:6380; kubectl rollout restart deployment/vitrine -n essai-douze; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap/vitrine-config created
deployment.apps/vitrine restarted
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Écrivez une valeur dans le cache de podinfo, puis relisez-la, depuis le nœud,
sur l'adresse du Service :

```bash
IP=$(kubectl get service vitrine-svc -n essai-douze -o jsonpath='{.spec.clusterIP}'); curl -s -m 5 -o /dev/null -w 'écriture : %{http_code}\n' -X POST -d essai "http://$IP/cache/cle"; curl -s -m 5 -w ' lecture : %{http_code}\n' "http://$IP/cache/cle"
```

```text
écriture : 200
{
  "code": 400,
  "message": "cache server is offline"
} lecture : 200
```

Les deux requêtes rendent 200, mais la lecture dit `cache server is offline`.
L'application est-elle déclarée prête ?

```bash
IP=$(kubectl get service vitrine-svc -n essai-douze -o jsonpath='{.spec.clusterIP}'); curl -s -m 5 "http://$IP/readyz"; echo; kubectl get pods -n essai-douze -l app=vitrine
```

```text
{
  "status": "OK"
}
NAME                       READY   STATUS        RESTARTS   AGE
vitrine-6bdfc6b45-68drb    1/1     Terminating   0          2s
vitrine-7bb897cb9d-7r788   1/1     Terminating   0          26s
vitrine-9d46bbc58-m4lkn    1/1     Running       0          1s
```

Oui : `/readyz` répond `OK`, et le nouveau Pod est `1/1`. La sonde de
podinfo ne vérifie pas son cache. Une ressource attachée injoignable ne se
voit donc ni dans l'état du Pod, ni dans ses conditions : il faut interroger
l'application elle-même. Corrigez le port :

```bash
kubectl patch configmap vitrine-config -n essai-douze --type merge -p '{"data":{"PODINFO_CACHE_SERVER":"tcp://cache:6379"}}'; kubectl rollout restart deployment/vitrine -n essai-douze; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap/vitrine-config patched
deployment.apps/vitrine restarted
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Écrivez de nouveau. Laissez dix secondes au nouveau Pod : sur cette machine,
une écriture lancée tout de suite après le redémarrage a expiré, et la même,
dix secondes plus tard, a réussi.

```bash
sleep 10; IP=$(kubectl get service vitrine-svc -n essai-douze -o jsonpath='{.spec.clusterIP}'); curl -s -m 5 -o /dev/null -w 'écriture : %{http_code}\n' -X POST -d essai "http://$IP/cache/cle"; curl -s -m 5 -w ' lecture : %{http_code}\n' "http://$IP/cache/cle"
```

```text
écriture : 202
essai lecture : 200
```

`202` à l'écriture, et la lecture rend la valeur `essai`.

## 📚 Exercice 4 : des clés qui ne ressemblent pas à des variables

Ajoutez à la ConfigMap deux clés au nom inhabituel : l'une contient un point,
l'autre commence par un chiffre.

```bash
kubectl patch configmap vitrine-config -n essai-douze --type merge -p '{"data":{"ui.couleur":"#ff6b00","1PODINFO_X":"oui"}}'; kubectl rollout restart deployment/vitrine -n essai-douze; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
configmap/vitrine-config patched
deployment.apps/vitrine restarted
Waiting for deployment spec update to be observed...
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

```bash
kubectl exec deploy/vitrine -n essai-douze -- env | grep -E 'couleur|PODINFO_X'; echo "grep : code $?"
```

```text
ui.couleur=#ff6b00
1PODINFO_X=oui
grep : code 0
```

Kubernetes 1.37 les transmet toutes les deux au conteneur. Mais un shell ne
sait pas les lire :

```bash
kubectl exec deploy/vitrine -n essai-douze -- sh -c 'echo "PODINFO_UI_MESSAGE=[$PODINFO_UI_MESSAGE]"; echo "ui.couleur=[$ui.couleur]"'
```

```text
PODINFO_UI_MESSAGE=[bonjour]
ui.couleur=[.couleur]
```

`$ui.couleur` se lit `$ui` (vide) suivi du texte `.couleur`. La variable
existe, mais un script en shell ne l'atteint pas. Pour une configuration lue
par n'importe quel programme, gardez des noms en majuscules, chiffres et
soulignés, qui ne commencent pas par un chiffre.

## 📚 Exercice 5 : un `preStop` plus long que le délai d'arrêt

Le crochet `preStop` retarde l'arrêt du conteneur, le temps de finir les
requêtes en cours. Demandez une pause de 20 secondes avec un délai d'arrêt
(`terminationGracePeriodSeconds`) de 5 secondes :

```bash
kubectl patch deployment vitrine -n essai-douze --type strategic -p '{"spec":{"template":{"spec":{"terminationGracePeriodSeconds":5,"containers":[{"name":"vitrine","lifecycle":{"preStop":{"sleep":{"seconds":20}}}}]}}}}'
```

```text
The Deployment "vitrine" is invalid: spec.template.spec.containers[0].lifecycle.preStop.sleep: Invalid value: 20: must be non-negative and less than terminationGracePeriodSeconds (5)
```

L'API refuse : la pause doit être plus courte que le délai d'arrêt, sinon le
conteneur serait tué au milieu de sa pause. Donnez 8 secondes de pause pour
10 de délai :

```bash
kubectl patch deployment vitrine -n essai-douze --type strategic -p '{"spec":{"template":{"spec":{"terminationGracePeriodSeconds":10,"containers":[{"name":"vitrine","lifecycle":{"preStop":{"sleep":{"seconds":8}}}}]}}}}'; kubectl rollout status deployment/vitrine -n essai-douze --timeout=120s
```

```text
deployment.apps/vitrine patched
Waiting for deployment spec update to be observed...
Waiting for deployment "vitrine" rollout to finish: 0 out of 1 new replicas have been updated...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "vitrine" rollout to finish: 1 old replicas are pending termination...
deployment "vitrine" successfully rolled out
```

Attendez que l'ancien Pod soit parti, puis chronométrez la suppression du
nouveau :

```bash
sleep 12; kubectl get pods -n essai-douze -l app=vitrine; P=$(kubectl get pod -n essai-douze -l app=vitrine -o name | head -1); debut=$(date +%s); kubectl delete $P -n essai-douze; echo "suppression : $(( $(date +%s) - debut )) s"
```

```text
NAME                       READY   STATUS    RESTARTS   AGE
vitrine-5fd85ff7c9-phh4d   1/1     Running   0          13s
pod "vitrine-5fd85ff7c9-phh4d" deleted from essai-douze namespace
suppression : 11 s
```

La suppression a pris le temps de la pause, plus l'arrêt de l'application.
C'est ce délai qui laisse le Service retirer le Pod de ses adresses avant que
le conteneur ne s'arrête.

## 📚 Exercice 6 : un Job d'administration qui échoue, puis qu'on modifie

Écrivez un Job qui lit la version de l'application. Il vise le port 9898,
celui du conteneur, alors que le Service écoute sur le port 80 :

```bash
cat > ~/essai-douze/version.yaml <<YAML
apiVersion: batch/v1
kind: Job
metadata:
  name: version-lue
  namespace: essai-douze
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: lire
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          command: ["sh", "-c", "wget -qO- -T 3 http://vitrine-svc:9898/version"]
YAML
kubectl apply -f ~/essai-douze/version.yaml; kubectl wait --for=condition=Failed job/version-lue -n essai-douze --timeout=120s
```

```text
apiVersion: batch/v1
kind: Job
metadata:
  name: version-lue
  namespace: essai-douze
spec:
  backoffLimit: 1
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: lire
          image: ghcr.io/stefanprodan/podinfo:6.17.0@sha256:fa2f27c1a8561097e5144bfc0853eba6054d743b68b03de4cad4675616ddefb0
          command: ["sh", "-c", "wget -qO- -T 3 http://vitrine-svc:9898/version"]
YAML
kubectl apply -f ~/essai-douze/version.yaml; kubectl wait --for=condition=Failed job/version-lue -n essai-douze --timeout=120s
job.batch/version-lue created
job.batch/version-lue condition met
```

```bash
kubectl get pods -n essai-douze -l job-name=version-lue; kubectl logs -n essai-douze -l job-name=version-lue --tail=1
```

```text
NAME                READY   STATUS   RESTARTS   AGE
version-lue-58vxn   0/1     Error    0          6s
version-lue-s6c97   0/1     Error    0          20s
wget: download timed out
wget: download timed out
```

Deux Pods en `Error` : la tentative de départ, plus la reprise que permet
`backoffLimit: 1`. Corrigez le port dans le fichier, puis réappliquez :

```bash
sed -i 's|vitrine-svc:9898|vitrine-svc|' ~/essai-douze/version.yaml; kubectl apply -f ~/essai-douze/version.yaml 2>&1 | tail -2 | cut -c1-120
```

```text
The Job "version-lue" is invalid: spec.template: Invalid value: {"labels":{"batch.kubernetes.io/controller-uid":"dba3def
```

L'API refuse : le gabarit d'un Job (`spec.template`) ne se modifie pas
(`field is immutable`). Un Job se supprime, puis se recrée :

```bash
kubectl delete job version-lue -n essai-douze; kubectl apply -f ~/essai-douze/version.yaml; kubectl wait --for=condition=Complete job/version-lue -n essai-douze --timeout=120s; kubectl logs job/version-lue -n essai-douze; echo
```

```text
job.batch "version-lue" deleted from essai-douze namespace
job.batch/version-lue created
job.batch/version-lue condition met
{
  "commit": "fd3a834ed8d14b80ea334cf8a2fddd4597924da6",
  "version": "6.17.0"
}
```

## 🧹 Nettoyage

Supprimez le namespace d'essai et le répertoire de travail :

```bash
kubectl delete namespace essai-douze; rm -rf ~/essai-douze
```

```text
namespace "essai-douze" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset k8s-rendre-une-application-conforme-12-facteurs
dsoxlab check k8s-rendre-une-application-conforme-12-facteurs
```

```text
╭─ Résultat : k8s-rendre-une-application-conforme-12-facteurs ─╮
│  0 / 100 pts                                                 │
│  ░░░░░░░░░░░░░░░░░░░░  0/4 tests                             │
╰──────────────────────────────────────────────────────────────╯
```

0 sur 4 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une application fautive à rendre conforme, facteur
par facteur, de sa configuration à sa tâche d'administration.

```bash
dsoxlab run k8s-rendre-une-application-conforme-12-facteurs
dsoxlab challenge k8s-rendre-une-application-conforme-12-facteurs
```
