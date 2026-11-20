{{/*
Browser-facing Zitadel issuer. Zitadel writes this value into the token `iss` claim,
so every service must set RUNEFOBLE_ZITADEL_ISSUER to exactly this value.
*/}}
{{- define "runefoble.zitadelIssuer" -}}
{{- $secure := .Values.zitadel.externalSecure | default false -}}
{{- $scheme := ternary "https" "http" $secure -}}
{{- $defaultPort := ternary 443 80 $secure -}}
{{- $port := int .Values.zitadel.externalPort -}}
{{- if eq $port $defaultPort -}}
{{- printf "%s://%s" $scheme .Values.zitadel.externalDomain -}}
{{- else -}}
{{- printf "%s://%s:%d" $scheme .Values.zitadel.externalDomain $port -}}
{{- end -}}
{{- end -}}

{{/*
In-cluster Zitadel origin. Services and the bootstrap Job send discovery and JWKS requests here.
Zitadel serves only its external host, so each request also carries Host set to the issuer host.
*/}}
{{- define "runefoble.zitadelInternalUrl" -}}
{{- printf "http://zitadel:%d" (int .Values.zitadel.port) -}}
{{- end -}}

{{/*
Name of the Secret that the bootstrap Job writes. It holds the generated project ID and client ID.
*/}}
{{- define "runefoble.zitadelClientSecretName" -}}
{{- .Values.zitadel.client.secretName -}}
{{- end -}}

{{/*
Zitadel verification env for a service container. Call with $ and pipe to nindent.
The audience is the project ID that the bootstrap Job wrote, because the App Shell requests
the project audience scope.
*/}}
{{- define "runefoble.zitadelServiceEnv" -}}
- name: RUNEFOBLE_ZITADEL_ISSUER
  value: {{ include "runefoble.zitadelIssuer" . | quote }}
- name: RUNEFOBLE_ZITADEL_INTERNAL_URL
  value: {{ include "runefoble.zitadelInternalUrl" . | quote }}
- name: RUNEFOBLE_ZITADEL_AUDIENCE
  valueFrom:
    secretKeyRef:
      name: {{ include "runefoble.zitadelClientSecretName" . }}
      key: project-id
{{- end -}}

{{/*
Zitadel service token and organization for account provisioning (ADR-0023 c). Call with the
root context. An empty zitadel.provisioner.secretName renders the token only in the local
environment, where it reads the bootstrap admin token (DEV-ONLY, Kind only). Hosted
environments must name their own Secret, or the service refuses to start.
*/}}
{{- define "runefoble.zitadelProvisionerEnv" -}}
{{- $secret := .Values.zitadel.provisioner.secretName | default (ternary "zitadel-admin" "" (eq .Values.global.environment "local")) -}}
{{- if $secret }}
- name: RUNEFOBLE_ZITADEL_SERVICE_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ $secret }}
      key: {{ .Values.zitadel.provisioner.secretKey | quote }}
{{- end }}
{{- with .Values.zitadel.provisioner.orgId }}
- name: RUNEFOBLE_ZITADEL_ORG_ID
  value: {{ . | quote }}
{{- end }}
{{- end -}}

{{/*
Name of the Secret that holds chart credentials. credentials.existingSecret replaces the
Secret that this chart renders.
*/}}
{{- define "runefoble.credentialsSecret" -}}
{{- .Values.credentials.existingSecret | default "runefoble-credentials" -}}
{{- end -}}

{{/*
One container env entry that reads a key from the credentials Secret.
Call with (dict "root" $ "name" "ENV_NAME" "key" "secret-key") and pipe to nindent.
*/}}
{{- define "runefoble.secretEnv" -}}
- name: {{ .name }}
  valueFrom:
    secretKeyRef:
      name: {{ include "runefoble.credentialsSecret" .root }}
      key: {{ .key }}
{{- end -}}

{{/*
Data claim template for a stateful workload. The claim is named `data`. Call with
(dict "persistence" .Values.<service>.persistence) and pipe to nindent 2 under volumeClaimTemplates.
storageClassName is rendered only when the value is set. An empty value uses the cluster default.
*/}}
{{- define "runefoble.dataClaimTemplate" -}}
- metadata:
    name: data
  spec:
    accessModes:
      - ReadWriteOnce
    {{- if .persistence.storageClass }}
    storageClassName: {{ .persistence.storageClass | quote }}
    {{- end }}
    resources:
      requests:
        storage: {{ .persistence.size | quote }}
{{- end -}}

{{/*
Service-to-service credential (ADR-0015 e), read from the credentials Secret, key service-credential.
*/}}
{{- define "runefoble.serviceCredentialEnv" -}}
{{- include "runefoble.secretEnv" (dict "root" . "name" "RUNEFOBLE_SERVICE_CREDENTIAL" "key" "service-credential") -}}
{{- end -}}

{{/*
One container env entry with a plain value. Call with (dict "name" "ENV_NAME" "value" <any>) and
pipe to nindent. The value is quoted, so a boolean or a number renders as a string.
*/}}
{{- define "runefoble.plainEnv" -}}
- name: {{ .name }}
  value: {{ .value | quote }}
{{- end -}}

{{/*
PostgreSQL URL for a service container. The password is not in the URL. The container reads
POSTGRES_PASSWORD from its env, so Kubernetes expands $(POSTGRES_PASSWORD) at start. POSTGRES_PASSWORD
must come before this variable in the env list. Call with (dict "root" $ "driver" "postgresql+asyncpg")
and pipe to quote. The scheme is the driver: each service sets the scheme its driver reads.
*/}}
{{- define "runefoble.databaseUrl" -}}
{{- $pg := .root.Values.postgres -}}
{{- printf "%s://%s:$(POSTGRES_PASSWORD)@postgres:%d/%s" .driver $pg.username (int $pg.port) $pg.database -}}
{{- end -}}

{{/*
Redis URL for the event bus. Call with $ and pipe to quote. The chart renders the Redis
StatefulSet only when redis.enabled is true, and the URL points at that Service.
*/}}
{{- define "runefoble.redisUrl" -}}
{{- printf "redis://runefoble-redis:%d/0" (int .Values.redis.port) -}}
{{- end -}}

{{/*
Platform env for one service container: PostgreSQL, SpiceDB, Redis, OpenTelemetry, and the
Zitadel verification settings. The Redis URL is rendered only when redis.enabled is true.
Call with (dict "root" $ "svc" <services entry>) and pipe to trim, then nindent.
The values that differ per service come from the services entry: databaseDriver.
*/}}
{{- define "runefoble.platformEnv" -}}
{{- $root := .root -}}
{{- $svc := .svc -}}
{{- include "runefoble.secretEnv" (dict "root" $root "name" "POSTGRES_PASSWORD" "key" "postgres-password") | nindent 0 }}
{{- include "runefoble.secretEnv" (dict "root" $root "name" "RUNEFOBLE_SPICEDB_PRESHARED_KEY" "key" "spicedb-preshared-key") | nindent 0 }}
{{- include "runefoble.plainEnv" (dict "name" "RUNEFOBLE_DATABASE_URL" "value" (include "runefoble.databaseUrl" (dict "root" $root "driver" ($svc.databaseDriver | default "postgresql+asyncpg")))) | nindent 0 }}
{{- include "runefoble.plainEnv" (dict "name" "RUNEFOBLE_SPICEDB_ENDPOINT" "value" (printf "spicedb:%v" $root.Values.spicedb.grpcPort)) | nindent 0 }}
{{- if $root.Values.redis.enabled }}
{{- include "runefoble.plainEnv" (dict "name" "RUNEFOBLE_REDIS_URL" "value" (include "runefoble.redisUrl" $root)) | nindent 0 }}
{{- end }}
{{- include "runefoble.plainEnv" (dict "name" "RUNEFOBLE_OTEL_ENABLED" "value" $root.Values.observability.enabled) | nindent 0 }}
{{- include "runefoble.plainEnv" (dict "name" "RUNEFOBLE_OTEL_EXPORTER_OTLP_ENDPOINT" "value" (printf "http://otel-collector:%v" $root.Values.observability.otelCollector.grpcPort)) | nindent 0 }}
{{- include "runefoble.zitadelServiceEnv" $root | nindent 0 }}
{{- end -}}

{{/*
Container probes of one app service (TASK-0930, TASK-0933). Call with the service entry of
.Values.services and pipe to nindent. Every app container gets three probes:
- startupProbe: GET /healthz, every startupPeriodSeconds (default 5) for startupFailureThreshold
  tries (default 36). The budget is 180 s. The kubelet holds the other two probes until it passes.
- readinessProbe: path readinessPath (default /readyz) and time limit readinessTimeoutSeconds
  (default 3, longer than the 2.5 s limit of one dependency check).
- livenessProbe: only when livenessPath is set.
*/}}
{{- define "runefoble.probes" -}}
startupProbe:
  httpGet:
    path: /healthz
    port: {{ .port }}
  periodSeconds: {{ .startupPeriodSeconds | default 5 }}
  failureThreshold: {{ .startupFailureThreshold | default 36 }}
readinessProbe:
  httpGet:
    path: {{ .readinessPath | default "/readyz" }}
    port: {{ .port }}
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: {{ .readinessTimeoutSeconds | default 3 }}
{{- with .livenessPath }}
livenessProbe:
  httpGet:
    path: {{ . }}
    port: {{ $.port }}
  initialDelaySeconds: 5
  periodSeconds: 10
{{- end }}
{{- end -}}

{{- /*
Pull Secrets for every pod spec (TASK-0960). Renders nothing when global.imagePullSecrets is
empty. Put it on its own line under a pod spec `spec:` (the pod spec keys sit at six spaces):
  spec:
    {{- include "runefoble.imagePullSecrets" $ }}
    containers:
*/ -}}
{{- define "runefoble.imagePullSecrets" -}}
{{- with default (list) .Values.global.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
{{- end }}
{{- end -}}
