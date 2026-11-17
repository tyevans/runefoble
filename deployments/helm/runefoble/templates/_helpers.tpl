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
