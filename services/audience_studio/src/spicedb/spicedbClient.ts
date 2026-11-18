/**
 * SpiceDB gRPC client for Audience Studio. Governed by ADR-0001 and ADR-0015 decision (f).
 *
 * Endpoint forms (RUNEFOBLE_SPICEDB_ENDPOINT):
 * - `host:port`: gRPC without TLS. This is the in-cluster form, for example `spicedb:50051`.
 * - `grpc://host:port`: gRPC without TLS, explicit.
 * - `https://host:port`: gRPC over TLS.
 * Any other scheme is refused at start-up.
 *
 * The preshared key is sent as the bearer token on every call. Unreachable SpiceDB and deadline
 * overruns surface as DependencyUnavailableError (503). Other gRPC failures surface as errors (500).
 */

import { deadlineInterceptor, v1 } from '@authzed/authzed-node';
import { DependencyUnavailableError } from '../errors.js';
import type { PermissionQuery, RelationshipWrite, SpiceDbPort } from './spicedbPort.js';

/** gRPC status codes that mean SpiceDB cannot answer now. */
const UNAVAILABLE = 14;
const DEADLINE_EXCEEDED = 4;

export const DEFAULT_SPICEDB_DEADLINE_MS = 3000;

export interface SpiceDbClientSettings {
  endpoint: string;
  presharedKey: string;
  deadlineMs?: number;
}

export interface ParsedEndpoint {
  address: string;
  security: v1.ClientSecurity;
}

/** Splits the endpoint setting into a gRPC address and a transport security mode. */
export function parseSpiceDbEndpoint(endpoint: string): ParsedEndpoint {
  if (endpoint.startsWith('https://')) {
    return { address: endpoint.slice('https://'.length), security: v1.ClientSecurity.SECURE };
  }
  if (endpoint.startsWith('grpc://')) {
    return { address: endpoint.slice('grpc://'.length), security: v1.ClientSecurity.INSECURE_PLAINTEXT_CREDENTIALS };
  }
  if (endpoint.includes('://')) {
    throw new Error(`RUNEFOBLE_SPICEDB_ENDPOINT uses an unsupported scheme: '${endpoint}'. Use host:port, grpc://, or https://.`);
  }
  if (!endpoint.includes(':')) {
    throw new Error(`RUNEFOBLE_SPICEDB_ENDPOINT must be host:port, grpc://host:port, or https://host:port. Got '${endpoint}'.`);
  }
  return { address: endpoint, security: v1.ClientSecurity.INSECURE_PLAINTEXT_CREDENTIALS };
}

function isGrpcStatus(err: unknown, code: number): boolean {
  return typeof err === 'object' && err !== null && (err as { code?: unknown }).code === code;
}

function asDependencyError(err: unknown): unknown {
  if (isGrpcStatus(err, UNAVAILABLE) || isGrpcStatus(err, DEADLINE_EXCEEDED)) {
    return new DependencyUnavailableError('SpiceDB is unavailable', { cause: err });
  }
  return err;
}

export function createSpiceDbClient(settings: SpiceDbClientSettings): SpiceDbPort {
  const { address, security } = parseSpiceDbEndpoint(settings.endpoint);
  // Every call gets a deadline, so a hung SpiceDB cannot hold a request open.
  const client: v1.ZedClientInterface = v1.NewClient(
    settings.presharedKey,
    address,
    security,
    undefined,
    { interceptors: [deadlineInterceptor(settings.deadlineMs ?? DEFAULT_SPICEDB_DEADLINE_MS)] }
  );

  return {
    async checkPermission(query: PermissionQuery): Promise<boolean> {
      try {
        const response = await client.promises.checkPermission(
          {
            consistency: v1.Consistency.create({ requirement: { oneofKind: 'fullyConsistent', fullyConsistent: true } }),
            resource: query.resource,
            permission: query.permission,
            subject: { object: query.subject, optionalRelation: '' },
            context: undefined,
            withTracing: false,
          },
        );
        return response.permissionship === v1.CheckPermissionResponse_Permissionship.HAS_PERMISSION;
      } catch (err: unknown) {
        throw asDependencyError(err);
      }
    },

    async writeRelationship(write: RelationshipWrite): Promise<void> {
      try {
        await client.promises.writeRelationships(
          {
            updates: [
              {
                operation: v1.RelationshipUpdate_Operation.TOUCH,
                relationship: {
                  resource: write.resource,
                  relation: write.relation,
                  subject: { object: write.subject, optionalRelation: '' },
                  optionalCaveat: undefined,
                  optionalExpiresAt: undefined,
                },
              },
            ],
            optionalPreconditions: [],
          }
        );
      } catch (err: unknown) {
        throw asDependencyError(err);
      }
    },
  };
}
