#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
set -euo pipefail

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"

# 0. L'état de départ, mesuré : rien n'est permis.
$K auth can-i list pods -n lab --as dev-user || true

# 1. Le Role : lire les Pods et leurs logs, sous-ressource pods/log.
$K create role pod-reader -n lab --verb=get,list,watch --resource=pods,pods/log

# 2. Le RoleBinding : ce Role, pour cette utilisatrice.
$K create rolebinding read-pods-binding -n lab --role=pod-reader --user=dev-user

# 3. La preuve, des deux côtés.
$K auth can-i list pods -n lab --as dev-user
$K auth can-i get pods/log -n lab --as dev-user
$K auth can-i create pods -n lab --as dev-user || true
$K auth can-i list pods -n default --as dev-user || true
$K --as dev-user -n lab logs journal --tail=1
echo "dev-user lit les Pods de lab et leurs logs, et rien de plus."
