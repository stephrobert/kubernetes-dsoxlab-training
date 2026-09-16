#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
NS=secure-ns

# 1. Le standard, dans ses trois modes. Ce sont des labels sur le namespace :
#    Pod Security Admission est intégré à l'API server, il n'y a aucun
#    composant à installer ni aucun objet de politique à créer.
#
#    Les trois modes sont indépendants : enforce REFUSE, warn répond un
#    avertissement à l'appelant, audit inscrit une annotation dans le journal
#    d'audit. On les met tous les trois sur restricted, comme demandé.
$K label namespace "$NS" \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted \
  pod-security.kubernetes.io/audit=restricted \
  --overwrite

# 2. Le Pod conforme. Les quatre exigences du standard restricted, et elles se
#    déclarent à deux niveaux différents : l'identité au niveau du Pod ou du
#    conteneur, le reste au niveau du conteneur seulement.
cat <<'YAML' | $K apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: conforme
  namespace: secure-ns
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: outil
      image: busybox:1.37
      command: ["sh", "-c", "sleep 86400"]
      securityContext:
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
YAML
$K -n "$NS" wait --for=condition=ready pod/conforme --timeout=180s

# 3. La preuve, dans les deux sens, et sans rien créer.
#
#    --dry-run=server envoie l'objet à l'API server, qui le fait passer par
#    toute la chaîne d'admission puis ne l'écrit pas. C'est ce qui permet de
#    montrer un REFUS sans laisser de trace dans le cluster.
echo -n "Pod interdit : "
if cat <<'YAML' | $K apply --dry-run=server -f - >/dev/null 2>&1
apiVersion: v1
kind: Pod
metadata:
  name: interdit
  namespace: secure-ns
spec:
  hostPID: true
  containers:
    - name: outil
      image: busybox:1.37
      securityContext:
        runAsUser: 0
YAML
then
  echo "ACCEPTÉ, anormal"
else
  echo "refusé à l'admission, comme prévu"
fi

echo -n "Pod conforme : "
$K -n "$NS" get pod conforme -o jsonpath='{.status.phase}'; echo

# 4. Et laxiste, créé AVANT l'activation, tourne toujours : l'admission ne
#    s'applique qu'aux demandes, jamais rétroactivement.
echo -n "laxiste, créé avant le standard : "
$K -n "$NS" get pod laxiste -o jsonpath='{.status.phase}'; echo
echo "secure-ns applique restricted, refuse ce qui viole, et n'a expulsé personne."
