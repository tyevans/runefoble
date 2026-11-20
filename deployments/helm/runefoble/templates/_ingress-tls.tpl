{{- /*
Ingress TLS helpers (TASK-0956). The keys are read with `dig`, so an absent key takes the local
default: no TLS and no HTTPS redirect. `values.yaml` does not list these keys.
Docs: docs/reference/ports-and-endpoints.md and docs/reference/hosted-profile.md.
*/ -}}

{{- define "runefoble.ingress.tlsMode" -}}
{{- $mode := dig "tls" "mode" "none" .Values.ingress | toString -}}
{{- if not (has $mode (list "none" "certManager" "existingSecret")) -}}
{{- fail (printf "ingress.tls.mode must be none, certManager, or existingSecret. Found: %s" $mode) -}}
{{- end -}}
{{- $mode -}}
{{- end -}}

{{- define "runefoble.ingress.httpsRedirect" -}}
{{- if eq (toString (.Values.ingress.httpsRedirect | default false)) "true" -}}true{{- else -}}false{{- end -}}
{{- end -}}

{{- define "runefoble.ingress.clusterIssuer" -}}
{{- dig "tls" "clusterIssuer" "" .Values.ingress | toString -}}
{{- end -}}

{{- define "runefoble.ingress.tlsSecretName" -}}
{{- if eq (include "runefoble.ingress.tlsMode" .) "certManager" -}}
{{- printf "%s-tls" .Release.Name -}}
{{- else -}}
{{- dig "tls" "secretName" "" .Values.ingress | toString -}}
{{- end -}}
{{- end -}}

{{- define "runefoble.ingress.validateTls" -}}
{{- $mode := include "runefoble.ingress.tlsMode" . -}}
{{- $redirect := include "runefoble.ingress.httpsRedirect" . -}}
{{- if and (eq $redirect "true") (eq $mode "none") -}}
{{- fail "ingress.httpsRedirect is true but ingress.tls.mode is none. The redirect needs a TLS source (certManager or existingSecret)." -}}
{{- end -}}
{{- if and (eq $mode "certManager") (empty (include "runefoble.ingress.clusterIssuer" .)) -}}
{{- fail "ingress.tls.clusterIssuer must name a ClusterIssuer when ingress.tls.mode is certManager." -}}
{{- end -}}
{{- if and (eq $mode "existingSecret") (empty (include "runefoble.ingress.tlsSecretName" .)) -}}
{{- fail "ingress.tls.secretName must name a kubernetes.io/tls Secret when ingress.tls.mode is existingSecret." -}}
{{- end -}}
{{- end -}}
