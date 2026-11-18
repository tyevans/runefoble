/**
 * GET requests that send an explicit Host header. Node's fetch ignores a Host header, so the
 * verifier uses node:http for requests that go to the in-cluster Zitadel origin (ADR-0015 c).
 */

import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';

/** Fetches `url` and sends `host` as the Host header. Resolves with the HTTP response. */
export function getWithHost(url: string, host: string, timeoutMs: number): Promise<Response> {
  const target = new URL(url);
  const send = target.protocol === 'https:' ? httpsRequest : httpRequest;
  return new Promise<Response>((resolve, reject) => {
    const req = send(
      target,
      { method: 'GET', headers: { Host: host, Accept: 'application/json' }, timeout: timeoutMs },
      (res) => {
        const chunks: Buffer[] = [];
        res.on('data', (chunk: Buffer) => chunks.push(chunk));
        res.on('error', reject);
        res.on('end', () => {
          const contentType = res.headers['content-type'] ?? 'application/json';
          resolve(
            new Response(Buffer.concat(chunks), {
              status: res.statusCode ?? 0,
              headers: { 'content-type': contentType },
            })
          );
        });
      }
    );
    req.on('timeout', () => req.destroy(new Error(`GET ${url} timed out after ${timeoutMs} ms`)));
    req.on('error', reject);
    req.end();
  });
}
