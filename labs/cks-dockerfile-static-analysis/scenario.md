# Fix a Dockerfile static analysis rejects, without changing the application

## The situation

The **`inventaire`** application has its Dockerfile in `/root/inventaire/`. It
builds, the image runs, and that is all that was asked of it when it was
written.

The security team has just pointed **Trivy** at configuration files, and it
rejects this Dockerfile on **five counts**.

## What you must achieve

1. You have **run the analysis** and read what it holds against the file. Each
   finding carries a number and a section saying what to write.

2. The **five findings are gone**.

3. The image **still does the same thing**: it starts from a Node image and
   runs `server.js`. Fixing it by changing technology would answer beside the
   point.

4. The Dockerfile still exists. Deleting it would silence the analysis, which
   is not the same as satisfying it.

## Useful bearings

`trivy config <directory>` analyses the configuration files it finds there,
Dockerfile included. It is the same tool as for images, used upstream: there
you measure what an image **contains**, here what its recipe **promises**.

Each finding carries an identifier shaped `DS-0000`, a severity, a title, and
a `Resolution` section. Read it: it says exactly what to write, and saves you
guessing.

An Alpine image ships far fewer packages than a Debian-based one, and its
package manager is not the same. Changing base therefore also changes the
install line.

A `HEALTHCHECK` tells whoever runs the image how to know it is alive. It is
not a convenience: without it, an orchestrator can only observe that a process
exists.

## How you will know it works

The last test **reruns the analysis** and looks for the five findings by their
**number**. It does not count: Trivy adds rules with each version, and a test
demanding "zero findings" would go red on its own the day a new rule shipped,
without your Dockerfile changing a line.

```bash
dsoxlab check cks-dockerfile-static-analysis
```
