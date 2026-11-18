# Reference: Browser Asset Reads

This page sets the rule for browser reads of protected media assets. It covers the helper in `libs/runefoble_ui` (`@runefoble/ui-core`). It applies to every microfrontend that shows an asset URL.

## Rule

Asset reads need a verified bearer token and the `forged_asset.view` permission. `GET /api/v1/assets/{asset_id}`, `/stream`, and `/download` return `401` without a bearer and `403` without the permission.

A browser `<img src>` or `<a href>` cannot send an `Authorization` header. A microfrontend must not put a protected asset URL in `src` or `href`.

## Approach

The microfrontend fetches the asset with the shared bearer. It turns the bytes into a blob URL. It shows the blob URL.

Signed URLs were not chosen. A signed URL needs a new server secret and a new issuing route. The fetch approach needs neither.

## Helper

| Export | Contents |
|---|---|
| `fetchAssetObjectUrl(url, authHeaders, fetchImpl?)` | Sends `GET url` with the headers from `authHeaders()`. Returns a blob URL. Rejects with the HTTP status when the response is not OK. |
| `revokeAssetObjectUrl(url)` | Releases a `blob:` URL. Other URLs pass through unchanged. |
| `AssetFetchLike` | The type of the optional `fetchImpl` argument. |

Pass `() => this.auth.authHeaders()` as `authHeaders`. The `AuthConsumerController` supplies the App Shell token.

The helper never returns a substitute URL. A refused read produces an error. The caller shows the error.

## Lifetime

A blob URL exists only in the current document. Do not store it, send it to a server, or put it in a persisted record. Revoke it with `revokeAssetObjectUrl` when the view no longer needs it.

## Current callers

| Caller | Source of the URL | Treatment |
|---|---|---|
| `runefoble-map-dropzone` (`services/board_state/ui`) | `download_url` in the `POST /api/v1/assets/upload` response, `/api/v1/assets/{id}?stream=true` | Fetched with the bearer. The blob URL goes to `upload-success`. |
| `runefoble-map-uploader` (`services/board_state/ui`) | The blob URL from the dropzone | Revoked on `resetMap`. |

## URLs that are not asset routes

Some forge responses return a Silo object URL (`http://<silo>/<bucket>/<key>?expires=3600`). Examples are `download_url` in the print forge, and `image_url` in the battlemap, token, and wardrobe responses. These URLs do not point at `/api/v1/assets`. The helper does not apply to them. A `<img src>` or `<a href>` can use them directly.

## Failure

| Condition | Result |
|---|---|
| No bearer, or an invalid token | The server returns `401`. The helper rejects. |
| Bearer without `forged_asset.view` | The server returns `403`. The helper rejects. |
| Upload response without `download_url` | The dropzone raises an error and emits `upload-error`. |
