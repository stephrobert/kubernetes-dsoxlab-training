# Replace an image riddled with flaws, and prove it with a second scan

## The situation

In the **`chaine-appro`** namespace, the **`web`** Deployment runs two
replicas on the **`nginx:1.21`** image, published in 2021. It serves the same
pages as a recent image, nobody complains, and nothing in the cluster flags
what it carries.

**Trivy** is installed on the node, and its vulnerability database is already
downloaded.

## What you must achieve

1. You have **scanned** the production image and measured what it carries.

2. The `web` Deployment runs another **version of nginx**, carrying
   **strictly fewer** critical findings. The choice is yours, but it must be
   justified by a scan, not by a publication date.

3. **Both replicas run** after the change. A more recent image may change its
   listening port or its default user.

4. You do not change application: it is nginx that must be updated.

## Useful bearings

`trivy image <image>` scans an image and sorts what it finds by severity. The
`--severity` option narrows the output, `--quiet` removes the progress bar,
and `--format json` gives you something to count.

Scan **before** deploying. Deploying then scanning is scanning in production,
which is exactly what supply chain security exists to avoid.

A more recent image is not always the one carrying least. Alpine-based
variants ship far fewer packages than Debian-based ones, and every absent
package is one flaw fewer.

No tool says an image is "safe". It says what it **knows** at the moment it
looks, with the database of the day.

## How you will know it works

The last test scans **both** images, the original and yours, at the same
moment and with the same database, then requires strictly fewer critical
findings in the second. A fixed threshold would be wrong within a week: the
database grows daily, and an image beyond reproach today counts flaws tomorrow
without having changed a byte.

```bash
dsoxlab check cks-image-scanning-trivy
```
