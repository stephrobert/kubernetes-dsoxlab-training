# Challenge: Apply and check your manifests, from a set of requirements

## 📍 The situation

The annuaire ("directory") team hands you the delivery of its application on
the kind cluster `lab`. It gives you no manifests: only its requirements, in
**`~/annuaire/cahier-des-charges.txt`** (in French, "specification"). They say
what the application must do, never which objects to write.

It wants two variants, **recette** (acceptance) and **production**, drawn from
one base, and a delivery it can replay without watching the screen.

## 🎯 What you must achieve

1. A Kustomize base in **`~/annuaire/base/`**, and two variants that start from
   it: **`~/annuaire/recette/`** and **`~/annuaire/production/`**. Each variant
   creates its namespace. **Blocking requirement.**

2. The **annuaire** application runs in both variants, as the requirements
   describe it.

3. The delay that the requirements set is put on the right API field, in both
   variants.

4. The production objects are applied **declaratively**.

5. Production then moves to the image
   `nginx:1.31.2@sha256:b5a9a3cfc86b81dd6f1458d53f2ad2b559cc255653d2efd6cacee5636bf2066f`,
   acceptance stays on 1.30.5. **Before** applying this change, you save what it
   will modify in **`~/annuaire/diff-production.txt`**.

6. A script **`~/annuaire/livrer.sh`** ("deliver") takes the name of a variant
   (`recette` or `production`), applies it declaratively, and **only hands back
   once the application is available**. **Blocking requirement.**

## ✅ How you will know it works

The tests build your two variants, read the cluster, then delete the
production namespace and run `livrer.sh production`: when it returns, the three
copies must already be available. The delay of the requirements is drawn at
random during preparation. The pass mark is 70 %, and both blocking
requirements must be met.

```bash
dsoxlab check k8s-challenge-appliquer-et-verifier-ses-manifests
```
