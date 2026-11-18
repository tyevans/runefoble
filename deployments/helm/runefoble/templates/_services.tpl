{{/*
Cross-service URL env vars for one consumer. Call with (dict "root" $ "consumer" "game-session")
and pipe through trim and nindent. Each entry of .Values.services that sets urlEnv adds one
variable for every name in its consumers list. The value is http://<kebab-name>:<port>.
*/}}
{{- define "runefoble.serviceUrlEnv" -}}
{{- range $key, $svc := .root.Values.services }}
{{- if and $svc.urlEnv (has $.consumer (default (list) $svc.consumers)) }}
- name: {{ $svc.urlEnv }}
  value: {{ printf "http://%s:%v" (kebabcase $key) $svc.port | quote }}
{{- end }}
{{- end }}
{{- end -}}
