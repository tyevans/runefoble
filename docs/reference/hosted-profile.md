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
| `zitadel.bootstrap.closedRegistration` | `true` | Fails unless `true`. The bootstrap Job turns off local self-registration (ADR-0023 a). Source: `templates/hosted-guard-identity.yaml`. |
| `zitadel.smtp.host` | `REPLACE-ME` | Required. Fails when empty, on `REPLACE-ME`, `localhost`, or a `.local` suffix. The SMTP provider host. |
| `zitadel.smtp.port` | `587` | No guard. The SMTP port of the provider. |
| `zitadel.smtp.tls` | `true` | Fails unless `true`. STARTTLS or implicit TLS, as the provider requires. |
| `zitadel.smtp.user` | `REPLACE-ME` | Fails on `REPLACE-ME`. The SMTP login name. An empty value passes. |
| `zitadel.smtp.fromAddress` | `noreply@REPLACE-ME` | Required. Fails on `REPLACE-ME` or a `.local` suffix. The sender address. |
| `zitadel.smtp.fromName` | `Runefoble` | No guard. The sender name. |
| `zitadel.smtp.passwordSecretKey` | `smtp-password` (default) | No guard. The key of the password in the credentials Secret. See [`hosted-secrets.md`](hosted-secrets.md). |
| `mailpit.enabled` | `false` | Fails when `true`. Mailpit is a development mail capture. |
| `swaggerUI.enabled` | `false` | No guard on the key. A Swagger UI path fails the render (see [Development routes](#development-routes-and-the-analytics-decision-d6)). |
| `openpanel.enabled` | `false` | No guard on the key. An OpenPanel path fails the render (see [Development routes](#development-routes-and-the-analytics-decision-d6)). |
| `ingress.hosts[].paths[]` | No `/mail`, `/mailpit`, `/docs`, `/swagger-ui` or `/analytics` path | Fails on those prefixes. Fails on a path whose service is `mailpit`, `swagger-ui` or `openpanel` when that workload is off. |
| `ingress.tls.mode` | `certManager` | Fails unless `certManager` or `existingSecret`. `none` serves HTTP only. |
| `ingress.tls.clusterIssuer` | `REPLACE-ME` | Required with `certManager`. Fails on `REPLACE-ME`. Name of a ClusterIssuer that you install. |
| `ingress.tls.secretName` | `""` | Required with `existingSecret`. Fails on `REPLACE-ME`. Name of a `kubernetes.io/tls` Secret that you create. |
| `networkPolicy.ingressController.namespace` | `REPLACE-ME` | Fails on `REPLACE-ME`. The namespace of the ingress controller (decision D2d). |
| `networkPolicy.kubeApi[].cidr` | `REPLACE-ME/32` | Fails on `REPLACE-ME` or on a block wider than one address. |
| `networkPolicy.external[].cidr` | `REPLACE-ME/32` | Fails on `REPLACE-ME` or on a block wider than one address. |
| `networkPolicy.external[].host` | `REPLACE-ME` | Fails on `REPLACE-ME`. Name of the endpoint that the address belongs to. |
| `services.*.resources`, and each `resources` key of a workload | Anchors in the example | Fails when `requests.memory` or `limits.memory` is empty or holds `REPLACE-ME`. |
| `ingress.httpsRedirect` | `true` | Fails unless `true`. Plain HTTP answers 301 to HTTPS. See [TLS and HTTP redirect rules](ports-and-endpoints.md#tls-and-http-redirect-rules-hosted). |
| `backup.enabled` | `true` | Fails unless `true`. A hosted release needs the daily backup. Source: `templates/hosted-guard-backup.yaml`. |
| `backup.endpoint` | `https://REPLACE-ME` | Fails unless it starts with `https://`. Fails on `REPLACE-ME`, `localhost`, or a `svc.cluster.local` host. The bucket must sit outside the cluster. |
| `backup.bucket` | `REPLACE-ME` | Fails on `REPLACE-ME`. |
| `backup.credentialsSecret` | `runefoble-backup-credentials` | Fails on `REPLACE-ME`. The Secret holds `access-key` and `secret-key`. See [`hosted-secrets.md`](hosted-secrets.md). |
| `backup.image` | Chainguard MinIO client, pinned by digest | Fails on `REPLACE-ME`. The client copies the dumps. It needs no shell. |
| `restore.objectPrefix` | `""` | Fails on `REPLACE-ME` when `restore.enabled` is `true`. Required when restore is on. |

## PostgreSQL backup and restore (TASK-0961)

The chart runs one backup CronJob, `postgres-backup`, when `backup.enabled` is `true`. The default
is `false`, so the local render holds no backup object. The hosted example turns it on.

| Value | Default | Meaning |
|---|---|---|
| `backup.schedule` | `17 2 * * *` | Cron schedule, in UTC. The Job runs once a day. |
| `backup.endpoint` | none | HTTPS endpoint of an S3-compatible store outside the cluster. |
| `backup.bucket` | none | Bucket. The dumps go under `postgres/<UTC date>/`. |
| `backup.credentialsSecret` | none | Secret with `access-key` and `secret-key`. Add `encryption-passphrase` when encryption is on. |
| `backup.image` | none | S3 client image, pinned by digest. |
| `backup.encryption.enabled` | `false` | When `true`, each dump is encrypted with AES-256-CBC (PBKDF2). The key is `encryption-passphrase`. |
| `backup.retentionDays` | `30` in the example | Documentation only. The bucket lifecycle rule enforces the period. The chart never deletes an object. |

Each run makes one custom-format `pg_dump` for each database that accepts connections. The dump
reads the `postgres` service and the `postgres-password` key. The Job ends by it logging
`backup-object postgres/<date>`. That prefix names the run. The `concurrencyPolicy` is `Forbid`.

Start a run on demand with `kubectl create job --from=cronjob/postgres-backup <name>`.

### Restore

The restore Job `postgres-restore` renders only when `restore.enabled` is `true`. It is a
post-install hook, so it runs once, for a fresh install. It never runs on upgrade.

1. Set `restore.enabled: true` and `restore.objectPrefix` to the logged prefix, for example `postgres/2026-11-18`.
2. Install the release into an empty namespace, with the same credentials Secret and the same backup values.
3. The Job downloads the prefix. It waits for PostgreSQL, decrypts any `.enc` file, and runs `pg_restore --clean --if-exists` for each dump. The dump name is the database name.
4. Restart the services after the Job completes, so each service reads the restored rows.

A restore replaces the objects of every dumped database. Run it only into a fresh release. The
runbook (TASK-0965) holds the operator steps and the lifecycle rule.

### Lifecycle rule (operator)

Configure a bucket lifecycle rule that expires objects under `postgres/` after `backup.retentionDays`.
The chart does not delete dumps.

## Account creation (D12)

The hosted profile closes self-registration. Zitadel does not show a sign-up page to visitors.
Two paths create an account:

- A campaign invite. The invite link creates the account (ADR-0023 b to e, TASK-0967).
- The Zitadel admin console. The first admin signs in with `zitadel.adminEmail`. The admin creates each other account. Zitadel sends the setup e-mail through the SMTP provider.

The bootstrap Job sets the closed policy with `zitadel.bootstrap.closedRegistration`. See
[Authenticate with Zitadel OIDC](../how-to/authenticate-with-zitadel-oidc.md#closed-registration).

## Development routes and the analytics decision (D6)

The guard in `templates/hosted-guard-dev-routes.yaml` fails a staging or production render when:

- an Ingress path equals or sits below `/mail`, `/mailpit`, `/docs`, `/swagger-ui` or `/analytics`; or
- an Ingress path targets `mailpit`, `swagger-ui` or `openpanel`, and that workload is off.

The hosted example serves no development route. Each development workload is off there. A hosted render has no Mailpit, no Swagger UI page and no OpenPanel. Each service still serves `/openapi.json` inside the cluster (AGENTS.md, Hard Invariant 5). A removed route returns 404. The chart adds no substitute page.

Decision D6 (analytics): off by default. OpenPanel is not public and no service needs it. The OpenPanel client (`libs/runefoble_platform/src/runefoble_platform/analytics/client.py`) has no call site in a service. A failed send logs a warning and does not raise, so an off workload cannot block a player action. To turn analytics on for a hosted site, first add authentication in front of the OpenPanel UI, then change the example and the guard in one record.

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

## Workload resources

Every container of every Deployment, StatefulSet, and Job needs `requests.memory` and
`limits.memory`. The hosted guard (`templates/hosted-guard-hardening.yaml`) fails the render and
names the first key that lacks one. CPU limits are optional. The chart sets no CPU limit, so a
workload can use idle CPU. Requests set the scheduling share for each container.

The sizes sit in the hosted example. Each `resources` key uses a YAML anchor (`*small`, `*medium`,
`*large`). The example sizes are starting estimates. They are not measured. The measured load run
(decision D11) sets the final values.

Every workload runs one replica. The hosted render has no HorizontalPodAutoscaler and no
PodDisruptionBudget. PRD-0025 sets no autoscaling. `gateway-mcp` keeps state in memory, so it
must stay at one replica.

## Network policies

A hosted render (`staging` or `production`) renders the policies in
`templates/network-policies.yaml`. The local render has none. The model is default deny. One
policy selects every release pod for ingress and egress. Each allow rule names one path that the
platform uses today:

| Path | Rule source | Policies |
|---|---|---|
| Ingress controller to each routed service | `ingress.hosts[].paths` and `networkPolicy.ingressController` | `allow-ingress-<service>` |
| Consumer to the service it calls | `services.*.urlEnv` and `consumers` | `allow-into-<service>`, `allow-egress-<consumer>` |
| Any pod to the OTel collector | Every release pod (ports 4317 and 4318) | `allow-into-otel-collector`, `allow-egress-to-otel-collector` |
| Application service to PostgreSQL, SpiceDB, Zitadel, Redis, and Silo | Platform env in `_helpers.tpl` and `services.yaml` | `allow-into-postgres` and the other `allow-into-*` platform policies |
| Platform pods to their own dependencies | SpiceDB, Zitadel, OpenPanel, and the backup and restore Jobs to PostgreSQL, the schema Job to SpiceDB, the Silo Job to Silo, the collector and Grafana to Loki | `allow-egress-<pod>` |
| Every pod to cluster DNS | UDP and TCP 53 in `networkPolicy.dnsNamespace` (default `kube-system`) | `allow-dns-egress` |
| External endpoint (model, embedding, speech-to-text, SMTP, backup bucket) | `networkPolicy.external` | `allow-egress-external-<n>` |
| Zitadel pod and bootstrap Job to the Kubernetes API | `networkPolicy.kubeApi` | `allow-egress-kube-api-<n>` |

Rules for the external and API entries:

- Standard NetworkPolicy matches an IP address. It cannot match a host name. Each entry names one
  address as a `/32` block. The guard fails on a wider block or on a placeholder. Resolve each host
  name to its address before you render. When the address changes, the render must change too.
- Each entry names the service that calls it (`from`), the host (`host`), the address (`cidr`), and
  the port. A pod with no entry has no external egress.

`gateway-mcp` is a ClusterIP endpoint with no ingress path. No consumers list names it, so no pod
may reach it. The hosted render tests check this.

Kubelet health probes come from the node, not from a pod. Confirm that the probes pass under the
chosen network plugin in the 0964 smoke job.

### Enforcement

Policies take effect only when the cluster network plugin enforces them. Kind uses kindnet by
default. Kindnet does not enforce NetworkPolicy. A live check that depends on enforcement must run
on a cluster with a policy-enforcing plugin (for example Calico). The 0964 smoke job names the
plugin that it uses.

### Network policy checks

- A hosted render names the first key that lacks the ingress namespace (`networkPolicy.ingressController.namespace`)
  or that holds a wide or placeholder address.
- The blackbox tests in `tests/test_blackbox_helm_hosted_hardening.py` check each consumers pair
  in both directions, each platform path, the ingress controller paths, and the single-address
  external entries.

## Pod security

A hosted render sets these rules. The local render does not change.

- Every pod runs with the `RuntimeDefault` seccomp profile.
- Every container blocks privilege escalation (`allowPrivilegeEscalation: false`).
- Every application container (the Python services, `gateway-mcp`, `inference-worker`, the
  `pat-publisher` sidecar, and the Zitadel bootstrap Job) drops all capabilities, runs as a
  numeric non-root UID, and mounts a read-only root filesystem with an `emptyDir` at `/tmp`.
  The UID is the one in the image Dockerfile: `10001` for the Python images (see
  `deployments/docker/python-service.Dockerfile`), and `1000` for `audience-studio` (its image
  runs as `node`). The numeric value is required. A user name in the image cannot prove non-root.
- The `HOME` variable of each application container is `/tmp` in a hosted render.
- A service that writes to disk outside `/tmp` needs a volume for that path before its
  `readOnlyRootFilesystem` can stay true. The audit of the Python sources found no such write.
  The voice agent writes its model files to its model cache volume.

## Security exceptions

Third-party images choose their own users. Some start as root and switch users at run time. This
list names each container that the hosted render does not restrict further. Each container keeps
`allowPrivilegeEscalation: false` and the `RuntimeDefault` seccomp profile. For each container,
the table names the reason. Enable the stricter settings only after you test the image.

| Container | Workload | Reason |
|---|---|---|
| `postgres` | StatefulSet `postgres` | The image entrypoint runs as root, sets data ownership, and switches to the `postgres` user. |
| `redis` | StatefulSet `runefoble-redis` | The image entrypoint runs as root and switches to the `redis` user. |
| `silo` | StatefulSet `silo` | Third-party object store. Its UID and write paths are not verified in this chart. |
| `zitadel` | Deployment `zitadel` | Third-party identity server. Its UID and write paths are not verified in this chart. |
| `spicedb-migrate` | Deployment `spicedb` (init container) | Third-party authorization server image. Its UID is not verified in this chart. |
| `spicedb` | Deployment `spicedb` | Third-party authorization server image. Its UID is not verified in this chart. |
| `otel-collector` | Deployment `otel-collector` | Third-party collector image. Its UID is not verified in this chart. |
| `loki` | Deployment `loki` | Third-party log store. Its UID and write paths are not verified in this chart. |
| `grafana` | Deployment `grafana` | Third-party dashboard image. Its UID and write paths are not verified in this chart. |
| `frontend` | Deployment `frontend` | The `nginx:alpine` image runs as root and listens on port 80. A non-root image on port 8080 is a follow-up. |
| `render-runtime-config` | Deployment `frontend` (init container) | Same image as `frontend`. |
| `dump` | CronJob `postgres-backup` (init container) | The `postgres` image. `pg_dump` runs under its entrypoint. |
| `upload` | CronJob `postgres-backup` | Third-party MinIO client image. Its UID is not verified in this chart. |
| `download` | Job `postgres-restore` (init container) | Third-party MinIO client image. Its UID is not verified in this chart. |
| `restore` | Job `postgres-restore` | The `postgres` image. `psql` runs under its entrypoint. |
| `create-buckets` | Job `silo-buckets` | Third-party MinIO client image. It writes its client configuration under `/tmp/mc`. |
| `schema-writer` | Job `spicedb-schema-migration` | Third-party `zed` image. Its UID is not verified in this chart. |

OpenPanel and Swagger UI are off in the hosted profile (TASK-0957). When you turn one on, add its container to this table.

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
