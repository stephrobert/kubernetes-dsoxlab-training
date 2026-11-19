# Basculer le trafic d'une version à l'autre

Un **Service** donne un nom et une adresse fixes à un groupe de Pods. Il ne
choisit pas ses Pods par leur nom, mais par leurs **labels** : c'est son
**sélecteur** (en anglais, *selector*). Changer ce sélecteur change, en
quelques secondes, les Pods qui reçoivent le trafic. C'est tout le principe
d'une livraison **blue-green** : deux versions tournent en même temps, et le
Service décide laquelle répond. Dans ce cours, vous faites tourner deux
versions, vous mélangez puis séparez leur trafic, vous basculez, puis vous
revenez en arrière.

Vous travaillez dans un namespace d'essai, `essai-bascule`, avec une
application `boutique` en deux versions, `v1` et `v2`. Le challenge vous
demandera le même travail sur une autre application : vous le ferez seul, à la
fin.

Page associée : [Services Kubernetes](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/kubernetes/services/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-blue-green-deployment
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
19 novembre 2026, avec Kubernetes v1.37.2.

## 📚 Exercice 1 : faire tourner deux versions en même temps

Créez le namespace d'essai :

```bash
kubectl create namespace essai-bascule
```

```text
namespace/essai-bascule created
```

Chaque version est un Deployment de deux Pods. Leur conteneur écrit le nom de
sa version dans une page web, puis la sert avec le petit serveur `httpd` de
busybox, sur le port 8080. Les Pods portent deux labels : `app=boutique`,
commun aux deux versions, et `version`, qui les distingue. Créez la `v1` :

```bash
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boutique-v1
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boutique
      version: v1
  template:
    metadata:
      labels:
        app: boutique
        version: v1
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo v1 > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - containerPort: 8080
YAML
```

```text
deployment.apps/boutique-v1 created
```

Puis la `v2`, identique à ces trois détails près : son nom, son label
`version` et le texte qu'elle répond.

```bash
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: boutique-v2
spec:
  replicas: 2
  selector:
    matchLabels:
      app: boutique
      version: v2
  template:
    metadata:
      labels:
        app: boutique
        version: v2
    spec:
      containers:
        - name: web
          image: busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4
          command: ["sh", "-c", "echo v2 > /tmp/index.html && httpd -f -p 8080 -h /tmp"]
          ports:
            - containerPort: 8080
YAML
```

```text
deployment.apps/boutique-v2 created
```

Attendez que les deux soient prêtes, puis affichez les Pods avec leurs labels
en colonnes (`-L`) :

```bash
kubectl rollout status deployment/boutique-v1 -n essai-bascule --timeout=120s | tail -1
kubectl rollout status deployment/boutique-v2 -n essai-bascule --timeout=120s | tail -1
kubectl get pods -n essai-bascule -L app,version
```

```text
deployment "boutique-v1" successfully rolled out
deployment "boutique-v2" successfully rolled out
NAME                           READY   STATUS    RESTARTS   AGE   APP        VERSION
boutique-v1-86cc57db9f-vf7ps   1/1     Running   0          4s    boutique   v1
boutique-v1-86cc57db9f-z95c6   1/1     Running   0          4s    boutique   v1
boutique-v2-869bb4f44c-7vxms   1/1     Running   0          4s    boutique   v2
boutique-v2-869bb4f44c-mpqcm   1/1     Running   0          4s    boutique   v2
```

Quatre Pods, tous `app=boutique`, deux en `v1` et deux en `v2`.

## 📚 Exercice 2 : un Service qui choisit ses Pods par leurs labels

Pour interroger le Service depuis l'intérieur du cluster, il faut un Pod. Créez
un Pod `sonde` qui ne fait que dormir :

```bash
kubectl run sonde --image=busybox:1.38.0@sha256:a46257e06c82ad85242d0d38077d0a52d9896389ca60a1a59d3463db586e5fa4 --restart=Never -n essai-bascule -- sleep 3600
```

```text
pod/sonde created
```

Créez maintenant le Service `boutique`. Son sélecteur ne demande que
`app=boutique` : il choisit donc les Pods des deux versions.

```bash
cat <<'YAML' | kubectl apply -n essai-bascule -f -
apiVersion: v1
kind: Service
metadata:
  name: boutique
spec:
  selector:
    app: boutique
  ports:
    - port: 8080
      targetPort: 8080
YAML
```

```text
service/boutique created
```

Attendez que la sonde soit prête, puis envoyez huit requêtes au Service, par
son nom, depuis la sonde :

```bash
kubectl wait --for=condition=Ready pod/sonde -n essai-bascule --timeout=60s
for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
pod/sonde condition met
v2
v1
v2
v1
v2
v1
v1
v1
```

Les réponses se mélangent : le Service répartit les requêtes entre les quatre
Pods. Les adresses des Pods qu'il a choisis s'appellent ses **endpoints**.
Elles se lisent dans un objet `EndpointSlice` :

```bash
kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique
```

```text
NAME             ADDRESSTYPE   PORTS   ENDPOINTS                                              AGE
boutique-2llhn   IPv4          8080    10.244.38.99,10.244.163.34,10.244.38.100 + 1 more...   2s
```

Quatre adresses : trois affichées, et « 1 more », la quatrième.

## 📚 Exercice 3 : ne garder qu'une version

`kubectl set selector` remplace le sélecteur d'un Service. Ajoutez-y
`version=v1` :

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
kubectl get service boutique -n essai-bascule -o jsonpath='{.spec.selector}{"\n"}'
```

```text
service/boutique selector updated
{"app":"boutique","version":"v1"}
```

Le Service ne choisit plus que les Pods qui ont **les deux** labels. Laissez-lui
trois secondes pour mettre à jour ses endpoints, puis relancez les huit
requêtes :

```bash
sleep 3; for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
v1
v1
v1
v1
v1
v1
v1
v1
```

Huit réponses sur huit viennent de la `v1`. La `v2` tourne toujours, mais ne
reçoit plus rien.

## 📚 Exercice 4 : la bascule

Passer en production la `v2`, c'est changer une seule valeur du sélecteur :

```bash
kubectl set selector service boutique 'app=boutique,version=v2' -n essai-bascule
sleep 3; for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
service/boutique selector updated
v2
v2
v2
v2
v2
v2
v2
v2
```

Tout le trafic est passé d'un coup sur la `v2`. Aucun Pod n'a été créé ni
supprimé : les quatre tournent toujours.

```bash
kubectl get pods -n essai-bascule -l app=boutique -L version
```

```text
NAME                           READY   STATUS    RESTARTS   AGE   VERSION
boutique-v1-86cc57db9f-vf7ps   1/1     Running   0          13s   v1
boutique-v1-86cc57db9f-z95c6   1/1     Running   0          13s   v1
boutique-v2-869bb4f44c-7vxms   1/1     Running   0          13s   v2
boutique-v2-869bb4f44c-mpqcm   1/1     Running   0          13s   v2
```

C'est ce qui rend le blue-green sûr : l'ancienne version reste prête à
reprendre la main.

## 📚 Exercice 5 : le retour arrière

La `v2` pose un problème ? Revenir en arrière, c'est la même commande, avec
l'ancienne valeur :

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
sleep 3; for i in 1 2 3 4 5 6 7 8; do kubectl exec sonde -n essai-bascule -- wget -qO- -T 2 'http://boutique:8080'; done
```

```text
service/boutique selector updated
v1
v1
v1
v1
v1
v1
v1
v1
```

Le retour arrière est immédiat, parce que les Pods de la `v1` n'ont jamais
cessé de tourner. Si vous aviez supprimé la `v1` après la bascule, il faudrait
attendre que de nouveaux Pods démarrent.

## 📚 Exercice 6 : un sélecteur qui ne choisit personne

Une faute de frappe dans le sélecteur, et le Service ne trouve plus aucun Pod.
Essayez avec une version qui n'existe pas, `v3` :

```bash
kubectl set selector service boutique 'app=boutique,version=v3' -n essai-bascule
sleep 3; kubectl get endpointslices -n essai-bascule -l kubernetes.io/service-name=boutique
```

```text
service/boutique selector updated
NAME             ADDRESSTYPE   PORTS     ENDPOINTS   AGE
boutique-2llhn   IPv4          <unset>   <unset>     16s
```

Plus aucun endpoint. Une requête est alors refusée :

```bash
kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique:8080
```

```text
wget: can't connect to remote host (10.100.228.214): Connection refused
command terminated with exit code 1
```

Le Service existe toujours, avec son adresse (`10.100.228.214`), mais il n'a
personne à qui transmettre la requête. Pour trouver la cause, cherchez les Pods
avec le même sélecteur :

```bash
kubectl get pods -n essai-bascule -l 'app=boutique,version=v3'
```

```text
No resources found in essai-bascule namespace.
```

Aucun Pod ne porte ces labels : c'est le sélecteur qui est faux. Corrigez-le :

```bash
kubectl set selector service boutique 'app=boutique,version=v1' -n essai-bascule
sleep 3; kubectl exec sonde -n essai-bascule -- wget -qO- -T 3 http://boutique:8080
```

```text
service/boutique selector updated
v1
```

## 🧹 Nettoyage

Supprimez le namespace d'essai, avec tout ce qu'il contient :

```bash
kubectl delete namespace essai-bascule
```

```text
namespace "essai-bascule" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-blue-green-deployment
dsoxlab check ckad-blue-green-deployment
```

```text
╭─ Résultat : ckad-blue-green-deployment ─╮
│  0 / 100 pts                            │
│  ░░░░░░░░░░░░░░░░░░░░  0/10 tests       │
╰─────────────────────────────────────────╯
```

0 sur 10 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : faire tourner deux versions d'une application, puis
basculer son Service de l'une à l'autre, sans arrêter l'ancienne.

```bash
dsoxlab run ckad-blue-green-deployment
dsoxlab challenge ckad-blue-green-deployment
```
