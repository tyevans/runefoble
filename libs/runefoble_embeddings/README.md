# runefoble-embeddings

Builds `redstring` embedding providers from Runefoble settings. Services call
`build_embedding_provider` in their composition root. Services never import an
adapter class directly.

See `docs/reference/embedding-providers.md`.
