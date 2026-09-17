#!/usr/bin/env bash
# Solution du formateur. Rejouée sur la cible après `dsoxlab run`, elle prouve
# que le lab est FAISABLE et que ses tests passent quand le travail est fait.
#
# Tout `ssh` porte `-n` : la solution est lue par `bash -s` depuis l'entrée
# standard, et un ssh sans `-n` avalerait le reste du script comme entrée.
# Rien après lui ne s'exécuterait, et le lab rendrait 0.
set -eu

K="sudo kubectl --kubeconfig /etc/kubernetes/admin.conf"
CIBLE=v1.37.0
PAQUET=1.37.0-1.1
WORKER=k8s-w1.lab

# 1. Constater l'état de départ.
echo "avant :"
$K get nodes -o custom-columns=NOM:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion --no-headers

# ---------------------------------------------------------------------------
# 2. LE PLAN DE CONTRÔLE, d'abord. Un worker ne peut pas dépasser son plan de
#    contrôle : l'ordre n'est pas une préférence.
# ---------------------------------------------------------------------------

# kubeadm d'abord, et lui seul : c'est lui qui conduit la montée, et il doit
# déjà être à la version visée pour savoir ce qu'elle attend. Les paquets sont
# figés par le socle, il faut les défiger pour les changer.
sudo apt-mark unhold kubeadm
sudo apt-get update -qq
sudo apt-get install -y -qq "kubeadm=$PAQUET"
sudo apt-mark hold kubeadm

# `upgrade plan` dit ce qui est possible sans rien changer. On le joue pour la
# trace, puis on applique.
sudo kubeadm upgrade plan "$CIBLE" 2>&1 | tail -5 || true
sudo kubeadm upgrade apply "$CIBLE" --yes

# Le kubelet n'est PAS monté par `upgrade apply` : il se remplace à la main,
# nœud par nœud, et se redémarre. C'est l'oubli le plus fréquent, et il laisse
# un nœud qui annonce toujours l'ancienne version.
sudo apt-mark unhold kubelet kubectl
sudo apt-get install -y -qq "kubelet=$PAQUET" "kubectl=$PAQUET"
sudo apt-mark hold kubelet kubectl
sudo systemctl daemon-reload
sudo systemctl restart kubelet

# L'API server est redémarré par la montée, et il ne revient pas d'un coup :
# `upgrade apply` remplace les manifestes statiques du plan de contrôle, et le
# kubelet recrée ces Pods par vagues. L'API répond, retombe, puis revient.
#
# On exige donc PLUSIEURS réponses de suite, espacées, avant de la croire
# revenue : un contrôle ponctuel tombe dans une accalmie et laisse la commande
# suivante échouer sur « connection refused », ce qui ressemble à une panne
# alors que c'est une transition.
echo -n "retour de l'API server : "
stable=0
for _ in $(seq 120); do
  if $K get --raw /readyz >/dev/null 2>&1; then
    stable=$((stable + 1))
    [ "$stable" -ge 5 ] && break
  else
    stable=0
  fi
  sleep 3
done
echo "stable"
$K wait --for=condition=Ready nodes --all --timeout=300s >/dev/null

# ---------------------------------------------------------------------------
# 3. LE WORKER. On le vide avant de le toucher, pour que ses Pods aillent
#    ailleurs plutôt que de disparaître avec lui.
# ---------------------------------------------------------------------------
#
# Le drain est long, et il peut traverser une bascule du plan de contrôle même
# lancé sur une API stable. On le réessaie plutôt que d'abandonner : il est
# idempotent, un nœud déjà vidé se vide en une seconde.
for essai in 1 2 3; do
  if $K drain "$WORKER" --ignore-daemonsets --delete-emptydir-data --timeout=300s; then
    break
  fi
  echo "  drain interrompu, essai $essai, on laisse l'API revenir"
  sleep 20
done

ssh -n "$WORKER" "sudo apt-mark unhold kubeadm && sudo apt-get update -qq && sudo apt-get install -y -qq kubeadm=$PAQUET && sudo apt-mark hold kubeadm"
# `upgrade node` et non `upgrade apply` : seul le plan de contrôle applique une
# version au cluster, un worker se contente de mettre sa configuration à jour.
ssh -n "$WORKER" "sudo kubeadm upgrade node"
ssh -n "$WORKER" "sudo apt-mark unhold kubelet kubectl && sudo apt-get install -y -qq kubelet=$PAQUET kubectl=$PAQUET && sudo apt-mark hold kubelet kubectl"
ssh -n "$WORKER" "sudo systemctl daemon-reload && sudo systemctl restart kubelet"

# Un nœud vidé reste INORDONNANÇABLE tant qu'on ne l'a pas rendu : l'oublier
# laisse le cluster avec un nœud en moins, sans que rien ne le signale.
$K uncordon "$WORKER"

$K wait --for=condition=Ready nodes --all --timeout=600s
$K -n supervision rollout status deployment/sonde --timeout=300s

# 4. La preuve.
echo "après :"
$K get nodes -o custom-columns=NOM:.metadata.name,VERSION:.status.nodeInfo.kubeletVersion,ORDONNANCABLE:.spec.unschedulable --no-headers
echo -n "exemplaires prêts : "
$K -n supervision get deployment sonde -o jsonpath='{.status.readyReplicas}'; echo
