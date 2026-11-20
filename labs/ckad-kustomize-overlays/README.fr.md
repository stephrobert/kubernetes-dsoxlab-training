# Une base Kustomize et deux overlays

Une même application tourne souvent dans plusieurs environnements : test,
démonstration, production. Recopier ses manifestes pour chacun finit toujours
par des copies qui divergent. **Kustomize**, intégré à kubectl, part d'une
**base** commune et lui applique des **overlays** : de petits fichiers qui ne
décrivent que les différences. La leçon montre comment les écrire. Ce cours
part d'une base toute prête et s'arrête sur ce qui piège : un label ajouté
après coup que le cluster refuse, un patch qui ne vise qu'un environnement,
et un patch mal nommé qui ne dit rien.

Vous travaillez avec une application `site` et deux environnements d'essai,
`essai-qualif` et `essai-demo`. Le challenge vous demandera une autre
application, dans deux autres environnements : vous le ferez seul, à la fin.

Page associée : [Kustomize](https://www.stephane-robert.info/docs/conteneurs/orchestrateurs/outils/kustomize/).

## 🔧 Avant de commencer

Lancez le lab :

```bash
dsoxlab run ckad-kustomize-overlays
```

Vous êtes maintenant connecté à `k8s-cp.lab`, le nœud qui pilote le cluster
kubeadm (le control plane). Votre kubectl le vise déjà.

Les sorties montrées dans ce cours ont été relevées sur cette machine le
20 novembre 2026, avec Kubernetes v1.37.2 et la version de Kustomize intégrée à
kubectl, v5.8.1.

## 📚 Exercice 1 : une base toute prête

Créez les deux namespaces d'essai, l'arborescence de travail et la base : un
Deployment, un Service et un `kustomization.yaml` qui les liste et génère une
ConfigMap `site-config`. La leçon détaille chacun de ces fichiers :

```bash
kubectl create namespace essai-qualif; kubectl create namespace essai-demo; mkdir -p ~/essai-kustomize/base ~/essai-kustomize/overlays/qualif ~/essai-kustomize/overlays/demo
cat > ~/essai-kustomize/base/deployment.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 1
  selector:
    matchLabels:
      app: site
  template:
    metadata:
      labels:
        app: site
    spec:
      containers:
        - name: nginx
          image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
          ports:
            - containerPort: 80
          envFrom:
            - configMapRef:
                name: site-config
YAML
cat > ~/essai-kustomize/base/service.yaml <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: site-svc
spec:
  selector:
    app: site
  ports:
    - port: 80
      targetPort: 80
YAML
cat > ~/essai-kustomize/base/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
configMapGenerator:
  - name: site-config
    literals:
      - COULEUR=bleu
YAML
```

```text
namespace/essai-qualif created
namespace/essai-demo created
```

`kubectl kustomize` affiche ce que Kustomize produit, sans rien appliquer.
`grep` ne garde que le type et le nom de chaque objet :

```bash
kubectl kustomize ~/essai-kustomize/base | grep -E '^kind:|^  name:|name: site-config'
```

```text
kind: ConfigMap
  name: site-config-mgm6hf9htk
kind: Service
  name: site-svc
kind: Deployment
  name: site
            name: site-config-mgm6hf9htk
```

La ConfigMap porte l'empreinte de son contenu, et Kustomize a réécrit ce nom
dans l'`envFrom` du Deployment.

## 📚 Exercice 2 : un label ajouté après coup

Écrivez l'overlay `qualif` **sans label** : un namespace, un préfixe et 2
réplicas. Appliquez-le, et regardez les adresses du Service :

```bash
cat > ~/essai-kustomize/overlays/qualif/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-qualif
namePrefix: qualif-
replicas:
  - name: site
    count: 2
YAML
kubectl apply -k ~/essai-kustomize/overlays/qualif; kubectl rollout status deployment/qualif-site -n essai-qualif --timeout=120s | tail -1
kubectl get endpointslices -n essai-qualif -l kubernetes.io/service-name=qualif-site-svc
```

```text
configmap/qualif-site-config-mgm6hf9htk created
service/qualif-site-svc created
deployment.apps/qualif-site created
deployment "qualif-site" successfully rolled out
NAME                    ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
qualif-site-svc-dx6kk   IPv4          80      10.244.38.108,10.244.163.46   0s
```

Le Service trouve les deux Pods. Ajoutez maintenant le label `env: qualif`,
avec `includeSelectors: true`, pour qu'il entre aussi dans les sélecteurs.
Regardez d'abord le sélecteur que produirait l'overlay :

```bash
cat >> ~/essai-kustomize/overlays/qualif/kustomization.yaml <<'YAML'
labels:
  - pairs:
      env: qualif
    includeSelectors: true
YAML
kubectl kustomize ~/essai-kustomize/overlays/qualif | sed -n '/^kind: Service/,/^---/p' | grep -A3 'selector:'
```

```text
  selector:
    app: site
    env: qualif
---
```

C'est bien ce qu'on veut. Appliquez :

```bash
kubectl apply -k ~/essai-kustomize/overlays/qualif; echo "code $?"
```

```text
configmap/qualif-site-config-mgm6hf9htk configured
service/qualif-site-svc configured
The Deployment "qualif-site" is invalid: spec.selector: Invalid value: {"matchLabels":{"app":"site","env":"qualif"}}: field is immutable
code 1
```

Le sélecteur d'un Deployment ne se modifie plus après sa création : `field is
immutable`. Le Deployment est refusé, mais le Service, lui, a été modifié.
Regardez où cela mène :

```bash
sleep 3; kubectl get service qualif-site-svc -n essai-qualif -o jsonpath='{.spec.selector}{"\n"}'; kubectl get pods -n essai-qualif --show-labels
kubectl get endpointslices -n essai-qualif -l kubernetes.io/service-name=qualif-site-svc
```

```text
{"app":"site","env":"qualif"}
NAME                           READY   STATUS    RESTARTS   AGE   LABELS
qualif-site-858dd798db-h46rq   1/1     Running   0          4s    app=site,pod-template-hash=858dd798db
qualif-site-858dd798db-l8fps   1/1     Running   0          4s    app=site,pod-template-hash=858dd798db
NAME                    ADDRESSTYPE   PORTS     ENDPOINTS   AGE
qualif-site-svc-dx6kk   IPv4          <unset>   <unset>     4s
```

Le Service cherche maintenant `env=qualif`, que les Pods n'ont pas : il n'a
plus aucune adresse. Les Pods tournent, mais l'application ne répond plus par
son Service. Pour changer le sélecteur, il faut recréer le Deployment.
Supprimez-le, puis réappliquez :

```bash
kubectl delete deployment qualif-site -n essai-qualif; kubectl apply -k ~/essai-kustomize/overlays/qualif; kubectl rollout status deployment/qualif-site -n essai-qualif --timeout=120s | tail -1
sleep 3; kubectl get endpointslices -n essai-qualif -l kubernetes.io/service-name=qualif-site-svc
```

```text
deployment.apps "qualif-site" deleted from essai-qualif namespace
configmap/qualif-site-config-mgm6hf9htk unchanged
service/qualif-site-svc unchanged
deployment.apps/qualif-site created
deployment "qualif-site" successfully rolled out
NAME                    ADDRESSTYPE   PORTS   ENDPOINTS                     AGE
qualif-site-svc-dx6kk   IPv4          80      10.244.38.114,10.244.163.47   8s
```

Le Service retrouve deux Pods. Entre la suppression et la fin du déploiement,
l'application n'avait plus de Pod : décidez des labels d'un environnement
**avant** son premier déploiement.

## 📚 Exercice 3 : un overlay qui change l'image

L'overlay `demo` porte cette fois son label dès le départ, 2 réplicas, et
passe l'image en version 1.30.6 par un bloc `images`. Celui-ci vise les images
nommées `nginx` et leur donne un nouveau tag et un nouveau digest :

```bash
cat > ~/essai-kustomize/overlays/demo/kustomization.yaml <<'YAML'
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namespace: essai-demo
namePrefix: demo-
labels:
  - pairs:
      env: demo
    includeSelectors: true
replicas:
  - name: site
    count: 2
images:
  - name: nginx
    newTag: 1.30.6
    digest: sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
YAML
kubectl kustomize ~/essai-kustomize/overlays/demo | grep -E 'image:|replicas:'
kubectl kustomize ~/essai-kustomize/base | grep -E 'image:|replicas:'
```

```text
  replicas: 2
        image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
  replicas: 1
        image: nginx:1.30.5@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb
```

`demo` passe en 1.30.6 avec 2 réplicas, et la base reste en 1.30.5 avec 1
réplica.

## 📚 Exercice 4 : un patch pour un seul environnement

`namespace`, `replicas` ou `images` couvrent les changements courants. Pour
tout autre champ, un overlay applique un **patch** : un morceau de manifeste
qui ne contient que ce qui change, et que Kustomize fusionne avec l'objet de la
base. Ajoutez à `demo` des réservations et des limites de ressources, avec un
patch dans le champ `patches`. Le patch désigne le Deployment par son nom dans
la base, `site`, et le conteneur par son nom, `nginx` :

```bash
cat > ~/essai-kustomize/overlays/demo/limites.yaml <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  template:
    spec:
      containers:
        - name: nginx
          resources:
            requests:
              cpu: 50m
              memory: 32Mi
            limits:
              cpu: 200m
              memory: 64Mi
YAML
cat >> ~/essai-kustomize/overlays/demo/kustomization.yaml <<'YAML'
patches:
  - path: limites.yaml
YAML
kubectl kustomize ~/essai-kustomize/overlays/demo | sed -n '/^kind: Deployment/,$p' | grep -A7 'resources:'
kubectl kustomize ~/essai-kustomize/overlays/qualif | grep -c 'resources:'
```

```text
        resources:
          limits:
            cpu: 200m
            memory: 64Mi
          requests:
            cpu: 50m
            memory: 32Mi
0
```

`demo` reçoit les ressources, `qualif` n'en a aucune : le patch ne touche que
l'overlay qui le cite. Que se passe-t-il si le patch nomme mal le conteneur ?
Essayez avec une copie qui l'appelle `web` :

```bash
sed 's/name: nginx$/name: web/' ~/essai-kustomize/overlays/demo/limites.yaml > ~/essai-kustomize/overlays/demo/limites-faux.yaml
sed -i 's/path: limites.yaml/path: limites-faux.yaml/' ~/essai-kustomize/overlays/demo/kustomization.yaml; kubectl kustomize ~/essai-kustomize/overlays/demo | sed -n '/^kind: Deployment/,$p' | grep -A12 'containers:'
```

```text
      containers:
      - name: web
        resources:
          limits:
            cpu: 200m
            memory: 64Mi
          requests:
            cpu: 50m
            memory: 32Mi
      - envFrom:
        - configMapRef:
            name: demo-site-config-mgm6hf9htk
        image: nginx:1.30.6@sha256:42c68eab6f7e22611786a9fe1d1c019e275c50185bd54b8f75dc2b9184322703
```

Aucune erreur. Kustomize n'a trouvé aucun conteneur `web`, alors il en a
**ajouté** un, sans image, à côté de `nginx`, qui n'a pas reçu ses ressources.
Un patch fusionne par nom : un nom faux crée un objet au lieu d'en modifier
un. Relisez toujours la sortie de `kubectl kustomize`. Remettez le bon patch :

```bash
sed -i 's/path: limites-faux.yaml/path: limites.yaml/' ~/essai-kustomize/overlays/demo/kustomization.yaml; rm ~/essai-kustomize/overlays/demo/limites-faux.yaml
```

## 📚 Exercice 5 : appliquer et comparer

Appliquez `demo`, vérifiez les ressources du conteneur, puis comparez chaque
overlay au cluster :

```bash
kubectl apply -k ~/essai-kustomize/overlays/demo; kubectl rollout status deployment/demo-site -n essai-demo --timeout=120s | tail -1
kubectl get deployment demo-site -n essai-demo -o jsonpath='{.spec.template.spec.containers[0].resources}{"\n"}'
kubectl diff -k ~/essai-kustomize/overlays/demo; echo "demo : code $?"; kubectl diff -k ~/essai-kustomize/overlays/qualif; echo "qualif : code $?"
```

```text
configmap/demo-site-config-mgm6hf9htk created
service/demo-site-svc created
deployment.apps/demo-site created
deployment "demo-site" successfully rolled out
{"limits":{"cpu":"200m","memory":"64Mi"},"requests":{"cpu":"50m","memory":"32Mi"}}
demo : code 0
qualif : code 0
```

Code 0 pour les deux : le cluster correspond exactement au dossier.

## 🧹 Nettoyage

Supprimez les deux namespaces d'essai et le dossier de travail :

```bash
kubectl delete namespace essai-qualif essai-demo; rm -rf ~/essai-kustomize
```

```text
namespace "essai-qualif" deleted
namespace "essai-demo" deleted
```

Quittez ensuite la machine et remettez le lab à zéro. `dsoxlab reset` rejoue
le nettoyage puis la préparation du lab : vous retrouvez exactement l'état de
départ du challenge. Il vous demande de confirmer : répondez `y`.

```bash
exit
dsoxlab reset ckad-kustomize-overlays
dsoxlab check ckad-kustomize-overlays
```

```text
╭─ Résultat : ckad-kustomize-overlays ─╮
│  0 / 100 pts                         │
│  ░░░░░░░░░░░░░░░░░░░░  0/9 tests     │
╰──────────────────────────────────────╯
```

0 sur 9 : c'est le résultat attendu. Le challenge vous attend, intact.

## 🎯 Le challenge

À vous, seul cette fois : une autre application, une base et deux overlays,
`recette` et `production`, dont un seul passe en version 2, et une
configuration fusionnée en production.

```bash
dsoxlab run ckad-kustomize-overlays
dsoxlab challenge ckad-kustomize-overlays
```
