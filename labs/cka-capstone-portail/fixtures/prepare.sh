#!/usr/bin/env bash
# Pose la situation : un namespace livré par une équipe partie, avec trois
# défauts INDÉPENDANTS et aucune indication de ce qu'ils sont.
#
# Les trois défauts sont indépendants à dessein. Corriger l'un ne fait rien
# passer : le portail ne répondra qu'une fois les trois trouvés, et c'est
# précisément ce qu'un micro-lab ne peut pas enseigner, puisqu'il annonce son
# sujet dans son titre.
#
#   1. Le Deployment portail réserve 4 CPU par exemplaire. Les nœuds en ont 2.
#      Les Pods restent Pending, avec « Insufficient cpu » dans leurs events.
#   2. La réclamation portail-data demande une classe de stockage qui n'existe
#      pas, donc aucun volume ne la satisfait. Le Deployment archives, qui la
#      monte, reste Pending lui aussi, pour une tout autre raison.
#   3. Le Service portail-svc sélectionne app=portal quand les Pods portent
#      app=portail. Il n'a donc aucun endpoint, et il n'en aurait pas plus
#      si les Pods tournaient.
#
# Rien de tout cela n'est écrit dans le scénario : le trouver EST l'exercice.
set -euo pipefail
# La trace complète va dans un journal sur le nœud : dsoxlab ne montre que
# « non-zero return code » quand ce script échoue, et le validateur relit
# ce fichier pour dire pourquoi.
exec > >(tee /var/log/dsoxlab-prepare.log) 2>&1
set -x

if [[ "$(kubectl get namespace production -o jsonpath='{.status.phase}' 2>/dev/null)" == "Terminating" ]]; then
  kubectl wait --for=delete namespace/production --timeout=180s
fi
kubectl get namespace production >/dev/null 2>&1 || kubectl create namespace production

# Un passage précédent a pu laisser un volume et une classe de stockage créés
# par le candidat. Les retirer ici est indispensable : un PersistentVolume qui
# survit apparierait la réclamation dès le premier instant, et le lab
# rendrait 100 AVANT le travail.
for pv in $(kubectl get pv -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.spec.claimRef.namespace}{"\n"}{end}' | awk '$2=="production"{print $1}'); do
  kubectl delete pv "$pv" --ignore-not-found --wait=true --timeout=60s
done
kubectl delete storageclass rapide --ignore-not-found --wait=true --timeout=60s

kubectl -n production delete deployment portail archives --ignore-not-found --wait=true
kubectl -n production delete service portail-svc --ignore-not-found --wait=true
kubectl -n production delete pvc portail-data --ignore-not-found --wait=true --timeout=60s

kubectl apply -f - <<'YAML'
# Défaut 1 : 4 CPU réservés par exemplaire, sur des nœuds qui en ont 2.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: portail
  namespace: production
  labels:
    app: portail
spec:
  replicas: 2
  selector:
    matchLabels:
      app: portail
  template:
    metadata:
      labels:
        app: portail
    spec:
      containers:
        - name: portail
          image: nginx:1.27-alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: "4"
              memory: 64Mi
---
# Défaut 2 : une classe de stockage qui n'existe nulle part.
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: portail-data
  namespace: production
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: rapide
  resources:
    requests:
      storage: 1Gi
---
# Le service d'archives, qui monte la réclamation et attend donc indéfiniment.
apiVersion: apps/v1
kind: Deployment
metadata:
  name: archives
  namespace: production
  labels:
    app: archives
spec:
  replicas: 1
  selector:
    matchLabels:
      app: archives
  template:
    metadata:
      labels:
        app: archives
    spec:
      containers:
        - name: archives
          image: busybox:1.37
          command: ["sh", "-c", "sleep 86400"]
          volumeMounts:
            - name: data
              mountPath: /data
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: portail-data
---
# Défaut 3 : app=portal, alors que les Pods portent app=portail.
apiVersion: v1
kind: Service
metadata:
  name: portail-svc
  namespace: production
spec:
  type: ClusterIP
  selector:
    app: portal
  ports:
    - name: http
      protocol: TCP
      port: 80
      targetPort: 80
YAML

# On laisse le temps aux objets d'atteindre leur état bloqué, pour que le
# candidat trouve des events parlants dès sa première commande. Aucun `wait`
# ici : ce qui est attendu, c'est justement que rien ne démarre.
sleep 10
kubectl -n production get pods,pvc,svc -o wide || true

echo "Situation posée : le portail de production ne répond pas, et personne ne sait pourquoi."
