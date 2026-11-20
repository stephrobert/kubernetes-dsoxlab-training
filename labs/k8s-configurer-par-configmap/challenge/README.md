# Challenge: Configure an application through ConfigMaps

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. The **`tarification`** namespace is empty.

## 🎯 What you must obtain

In the `tarification` namespace:

1. A ConfigMap **`tarifs-env`** carries `DEVISE=EUR` and `TAUX_TVA`. A
   Deployment **`tarifs`** (busybox 1.38.0, sleeping) receives these two keys
   as **environment variables**, and `DEVISE` can be read in the Pod.

2. A ConfigMap **`tarifs-grille`** carries a file **`grille.ini`**, mounted
   **as a directory** on **`/etc/tarifs`** in the container. After a change,
   this file contains the line **`remise=15`**, and the file read in the Pod
   is up to date.

3. `TAUX_TVA`, first set to `20`, moves to **`5.5`** in `tarifs-env`. The
   Deployment is then **restarted**, and the Pod sees `5.5`.

4. **No value** is written directly in the Deployment.

## 🧭 Useful landmarks

Create the ConfigMaps before the Deployment: `--from-literal` for values,
`--from-file` for a file, whose name becomes the key. Always check from the
container, with `kubectl exec deploy/tarifs --`: the spec says what is asked,
the container says what is seen.

After a change, not everything is updated the same way:

- an environment variable is read when the container starts, then stays
  frozen;
- a volume mounted as a directory updates by itself, with a delay;
- a `subPath` mount is never updated.

Restarting the Deployment replaces the Pods, which read everything again.

## ✅ How you will know it is right

The tests read the ConfigMaps and the Deployment, then what the container sees.

```bash
dsoxlab check k8s-configurer-par-configmap
```
