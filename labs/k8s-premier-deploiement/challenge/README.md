# Challenge: Deploy, expose and scale a first application

## 📍 The situation

The kind cluster **`boutique`** is running on the machine, and your kubectl
already targets it. The **`demo-app`** namespace does not exist yet. The
**`~/demo-app/`** directory is empty: it waits for your application's answer.

## 🎯 What you must obtain

1. In the **`demo-app`** namespace, a Deployment **`nginx`** that runs the
   lesson's image:
   `nginx:1.30@sha256:9bf97bd7714f5e24c1ccd545ecb9eb5435cb6d109c97cebb15e7e455e0239edb`.

2. The `nginx` Deployment was first created with **a single Pod**, then moved
   to **three available Pods**.

3. A ClusterIP Service **`nginx`**, on port **80**, that finds **the three
   Pods**.

4. A **`~/demo-app/reponse.html`** file that holds the page returned by
   `http://nginx`, asked from a Pod of the `demo-app` namespace.

## 🧭 Useful landmarks

Create the namespace first. Then add `-n demo-app` to every command: without
this option, your objects go to the `default` namespace.

A Service gives no warning when it finds no Pod. If the application does not
answer, compare the Service's `Selector` with the Pods' labels, and look at its
endpoints after moving to three Pods.

A Service's name, `nginx`, only exists inside the cluster. To reach it, start a
temporary Pod with an image that can make a web request. Its answer is written
to a file with `>`, as for any command.

## ✅ How you will know it works

The tests look at the Deployment, the Service and its endpoints. Then they
compare your file with the page nginx really serves.

```bash
dsoxlab check k8s-premier-deploiement
```
