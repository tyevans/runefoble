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
