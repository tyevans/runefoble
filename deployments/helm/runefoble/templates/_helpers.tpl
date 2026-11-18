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
In-cluster JWKS endpoint. Services fetch signing keys here, because the browser-facing
host is not resolvable from a pod.
*/}}
{{- define "runefoble.zitadelJwksUrl" -}}
{{- printf "http://zitadel:%d/oauth/v2/keys" (int .Values.zitadel.port) -}}
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
Service-to-service credential (ADR-0015 e), read from the credentials Secret, key service-credential.
*/}}
{{- define "runefoble.serviceCredentialEnv" -}}
{{- include "runefoble.secretEnv" (dict "root" . "name" "RUNEFOBLE_SERVICE_CREDENTIAL" "key" "service-credential") -}}
{{- end -}}
