#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le capstone est FAISABLE et que ses tests passent quand le travail est
# fait.
#
# Elle est écrite dans l'ordre des cinq exigences du scénario, et non dans
# l'ordre où un candidat les découvrirait.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# --- 1. Le cluster refuse lui-même ce qui ne doit pas entrer. -------------
#
# Trois labels, et non un seul. `enforce` refuse, `warn` prévient celui qui
# applique, `audit` laisse une trace dans le journal d'audit. Un espace qui
# n'aurait qu'`enforce` refuserait sans que personne ne sache pourquoi.
$K label namespace enclave \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted --overwrite

# --- 2. Une identité propre, dont le jeton ne se monte pas. ---------------
#
# Le champ se pose sur le ServiceAccount lui-même : il vaut alors pour tout
# Pod qui l'emploie sans avoir à le répéter dans chaque manifeste.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: ServiceAccount
metadata:
  name: coffre
  namespace: enclave
automountServiceAccountToken: false
YAML

# --- 3. Cette identité ne peut que lister les charges de son espace. ------
#
# Un Role, et non un ClusterRole : le second vaudrait pour TOUT le cluster,
# et l'exigence parle de son propre espace.
cat <<'YAML' | $K apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: coffre-lecture
  namespace: enclave
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: coffre-lecture
  namespace: enclave
subjects:
  - kind: ServiceAccount
    name: coffre
    namespace: enclave
roleRef:
  kind: Role
  name: coffre-lecture
  apiGroup: rbac.authorization.k8s.io
YAML

# --- 4. La charge, conforme au niveau exigé. ------------------------------
#
# Les quatre champs que `restricted` impose sont tous là. En manquer un seul
# fait refuser le Pod à la création, avec un message qui nomme le champ.
# L'image écoute sur 8080 : une image qui écouterait sur 80 aurait besoin
# d'une capacité que `restricted` interdit.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: coffre
  namespace: enclave
  labels:
    app: coffre
spec:
  serviceAccountName: coffre
  securityContext:
    runAsNonRoot: true
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: web
      image: nginxinc/nginx-unprivileged:1.27-alpine
      ports:
        - containerPort: 8080
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop: [ALL]
---
apiVersion: v1
kind: Service
metadata:
  name: coffre
  namespace: enclave
spec:
  selector:
    app: coffre
  ports:
    - port: 80
      targetPort: 8080
YAML

$K -n enclave wait --for=condition=ready pod/coffre --timeout=240s

# --- 5. Rien n'atteint le coffre hors de l'enclave. -----------------------
#
# Une politique d'ENTRÉE seulement : fermer la sortie n'était pas demandé, et
# couperait le DNS des Pods de l'enclave par surcroît.
#
# Le podSelector désigne ce qui est PROTÉGÉ, le from désigne ce qui est
# ADMIS. Les deux sélecteurs du from sont dans la MÊME entrée de liste :
# écrits comme deux entrées, ils voudraient dire « tout Pod de l'enclave, OU
# tout Pod portant role=appelant dans n'importe quel espace », ce qui ouvrirait
# la porte que l'on ferme.
cat <<'YAML' | $K apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coffre-entree
  namespace: enclave
spec:
  podSelector:
    matchLabels:
      app: coffre
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              kubernetes.io/metadata.name: enclave
          podSelector:
            matchLabels:
              role: appelant
YAML

# Calico programme la règle après avoir été notifié : elle n'agit pas à la
# seconde où l'API accepte l'objet.
sleep 10

# --- La preuve, dans les deux sens. ---------------------------------------
echo -n "appelant déclaré -> coffre : "
$K -n enclave exec autorise -- wget -qO- -T 5 http://coffre.enclave.svc.cluster.local/ >/dev/null 2>&1 \
  && echo "passe" || echo "BLOQUÉ, anormal"
echo -n "intrus hors enclave -> coffre : "
$K -n dehors exec intrus -- wget -qO- -T 5 http://coffre.enclave.svc.cluster.local/ >/dev/null 2>&1 \
  && echo "PASSE, anormal" || echo "bloqué"
echo -n "une charge privilégiée est-elle admise ? "
$K -n enclave run essai --image=busybox:1.37 --restart=Never \
  --overrides='{"spec":{"containers":[{"name":"x","image":"busybox:1.37","securityContext":{"privileged":true}}]}}' \
  >/dev/null 2>&1 && { echo "OUI, anormal"; $K -n enclave delete pod essai --ignore-not-found >/dev/null; } \
  || echo "non, refusée"
