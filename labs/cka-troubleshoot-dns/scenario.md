# Troubleshoot DNS Resolution

<!-- A_COMPLETER : ce scénario vient de K8sExamLab et il est EN ANGLAIS.
     À réécrire en français, et à confronter à Kubernetes 1.37 : ce lab visait
     la 1.34. -->

## La situation

Pods in the cluster can no longer resolve service names. Diagnose and
fix the CoreDNS issue so that DNS resolution works again.

## Ce que vous devez obtenir

A namespace 'app' contains a web server pod 'web' and a Service
'web-svc'. A client pod 'client' should be able to reach the web
server via DNS (web-svc.app.svc.cluster.local), but DNS is broken.

1. Confirm that DNS resolution fails from the 'client' pod by
   attempting to resolve the service hostname.

2. Investigate the CoreDNS component in the kube-system namespace
   to identify why DNS resolution is not functioning.

3. Restore CoreDNS to a healthy state so that DNS queries are
   answered again.

4. Verify that the 'client' pod can successfully resolve the service
   hostname and reach 'web-svc' via HTTP.

## Comment vous saurez que c'est bon

Les tests lisent l'état du cluster, pas les commandes tapées.

```bash
dsoxlab check troubleshoot-dns
```
