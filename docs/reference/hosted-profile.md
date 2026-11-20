# Hosted values profile

This page lists the hosted keys, the check that guards each key, and the placeholder marker.
The profile is a values file. It is not a second chart. Source: `deployments/helm/runefoble/values.hosted.example.yaml`
and `deployments/helm/runefoble/templates/hosted-guard.yaml`.

## Use the profile

1. Copy `deployments/helm/runefoble/values.hosted.example.yaml` to a file outside the repository.
2. Replace every `REPLACE-ME` with your value.
3. Create the Secret named in `credentials.existingSecret`. It holds every key in [`hosted-secrets.md`](hosted-secrets.md).
4. Render the chart. Deploy only when the render succeeds:

```sh
helm template runefoble deployments/helm/runefoble -f <your-hosted-values.yaml>
```

`make helm-deploy` is the Kind developer path. It adds `values.local.yaml`. Do not use it for a hosted release.

## Render guard

The guard runs when `global.environment` is `staging` or `production`. It renders no object.
It fails the render on the first key that holds a placeholder or a development default. The
failure message names the key path and the value. The guard does not run for `local`, so the
Kind render does not change.

An unset key that the guard reads also fails the render. The guard never takes a development value for a missing key.

## Hosted keys

| Key | Hosted value in the example | Check |
|---|---|---|
| `global.environment` | `production` | Selects the guard. Use `staging` or `production`. |
| `global.domain` | `REPLACE-ME` | Fails on `REPLACE-ME`, `localhost`, or a `.local` suffix. |
| `credentials.existingSecret` | `runefoble-hosted-credentials` | `templates/secret.yaml` fails when it is empty. The chart then renders no credential Secret, so no `DEV-ONLY` value reaches the output. The Secret keys are in [`hosted-secrets.md`](hosted-secrets.md). |
| `services.campaignLore.embeddingApiKeySecret` | `campaign-lore-embedding` | Fails when it is empty or holds `REPLACE-ME`. The chart renders no Secret with this name in a hosted render. The operator creates it with the key `api-key`. |
| `ingress.hosts[].host` | `REPLACE-ME` and `auth.REPLACE-ME` | Fails on `REPLACE-ME`, `localhost`, or a `.local` suffix. |
| `zitadel.externalDomain` | `auth.REPLACE-ME` | Fails on `REPLACE-ME`, `localhost`, or a `.local` suffix. |
| `global.imagePullSecrets` | `[]` | Names of pull Secrets for the registry. No guard. The chart adds them to every pod spec. |
| `values.images.yaml` (file, passed with `-f`) | Not in the example. Full image references with digests. | Guard on every `image` key: registry host, `@sha256:`, no `REPLACE-ME`, `localhost`, or `.local/`. See [Image references](#image-references). |
| `zitadel.externalPort` | `443` | No guard. Must match the public port. |
| `zitadel.externalSecure` | `true` | Fails when `false`. |
| `zitadel.adminEmail` | `admin@REPLACE-ME` | Fails on `REPLACE-ME` or the `@runefoble.local` suffix. |
| `zitadel.bootstrap.patExpirationDate` | `2027-01-01T00:00:00Z` | Fails on `REPLACE-ME` or a `2099` date. Set a short date for your policy. |
| `zitadel.bootstrap.redirectUris` | `https://REPLACE-ME/auth/callback` | Fails on `REPLACE-ME`, `localhost`, `http://`, or a `.local/` path. |
| `zitadel.bootstrap.postLogoutRedirectUris` | `https://REPLACE-ME/` | Same check as `redirectUris`. |
| `zitadel.bootstrap.devMode` | `false` | Fails when `true`. |
| `mailpit.enabled` | `false` | Fails when `true`. Mailpit is a development mail capture. |
| `ingress.tls.mode` | `certManager` | Fails unless `certManager` or `existingSecret`. `none` serves HTTP only. |
| `ingress.tls.clusterIssuer` | `REPLACE-ME` | Required with `certManager`. Fails on `REPLACE-ME`. Name of a ClusterIssuer that you install. |
| `ingress.tls.secretName` | `""` | Required with `existingSecret`. Fails on `REPLACE-ME`. Name of a `kubernetes.io/tls` Secret that you create. |
| `ingress.httpsRedirect` | `true` | Fails unless `true`. Plain HTTP answers 301 to HTTPS. See [TLS and HTTP redirect rules](ports-and-endpoints.md#tls-and-http-redirect-rules-hosted). |

## Image references

A hosted render pulls images from a registry. It does not use the local Kind cache. Pass the image
file after the hosted values file:

```sh
helm template runefoble deployments/helm/runefoble -f <your-hosted-values.yaml> -f deployments/helm/runefoble/values.images.yaml
```

`values.images.yaml` holds one full reference for each image. The Runefoble lines are written by
`make images-push IMAGE_REGISTRY=<host>/<path>`. The file holds `REPLACE-ME` until the push runs.
Third-party images carry the digest of their tag. The chart keeps the local tags in `values.yaml`.
The local render does not read the image file.

The guard checks every `image` key in a hosted render (`templates/hosted-guard-images.yaml`). It
fails the render when an image:

- has no registry host (the first path segment must contain a dot or a colon),
- has no digest (`@sha256:`),
- holds `REPLACE-ME`, `localhost`, or a `.local/` path.

The failure message names the key path, for example `services.gatewayApi.image`.

## Pull Secrets

`global.imagePullSecrets` is a list of Secret names (`kubernetes.io/dockerconfigjson`). The chart
adds the list to every Deployment, StatefulSet, and Job pod spec. When the list is empty, the chart
renders no `imagePullSecrets` key. The chart does not create the Secret. The operator creates it
(D2b, with the credential stored through [`hosted-secrets.md`](hosted-secrets.md)).

## Placeholder marker

`REPLACE-ME` marks every value that an operator must set. The guard fails on it in every
hosted key that the table lists. Do not keep the marker in a rendered file.

## Development defaults

`deployments/helm/runefoble/values.yaml` marks the credential defaults as `DEV-ONLY`. Do not
use these values in a hosted render. In a hosted render, the chart does not render them, because
`credentials.existingSecret` names a Secret that you manage.

## Secret decisions

- D5 (Secret source): the operator chooses. A hand-applied Secret or an external-secret operator
  both work. The chart reads only the names. The choice is not a chart decision.
- D5b (narrow the `create` grant): Option A. The chart keeps the namespace-wide `create` grant on
  Secrets, because RBAC cannot limit `create` by name. The residual risk is in
  [`hosted-secrets.md`](hosted-secrets.md), section 5.
