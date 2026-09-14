#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
# Un lab dont la solution échoue est un lab cassé.
#
# Transposée de K8sExamLab, où elle portait le commentaire « CoreDNS is
# already running in a fresh cluster, no fix needed » : elle ne réparait rien,
# alors que le setup éteint CoreDNS. Celle-ci répare.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 1. Le diagnostic : le Service kube-dns est là, mais personne ne se tient
#    derrière lui, parce que le Deployment coredns est à zéro replica.
$K -n kube-system get service kube-dns
$K -n kube-system get endpointslices -l kubernetes.io/service-name=kube-dns
$K -n kube-system get deployment coredns

# 2. La réparation : rendre à CoreDNS le nombre de replicas que kubeadm pose.
$K -n kube-system scale deployment coredns --replicas=2
$K -n kube-system rollout status deployment/coredns --timeout=180s

# 3. La preuve, depuis le Pod client. Les premières requêtes peuvent partir
#    avant que les nouveaux Pods soient joignables : on insiste un peu.
for essai in $(seq 1 15); do
  if $K -n app exec client -- nslookup web-svc.app.svc.cluster.local >/dev/null 2>&1; then
    break
  fi
  sleep 3
done
$K -n app exec client -- nslookup web-svc.app.svc.cluster.local
$K -n app exec client -- wget -q -O /dev/null --timeout=5 http://web-svc.app.svc.cluster.local
echo "Le client résout et joint web-svc : le DNS du cluster est de retour."
