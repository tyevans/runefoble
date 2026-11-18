/**
 * The authorization port that Audience Studio depends on. Governed by ADR-0001.
 *
 * Production wires the SpiceDB gRPC client (spicedbClient.ts). Tests wire a fake at this
 * boundary. Object types, relations, and permissions are the names in
 * libs/runefoble_auth/schema/runefoble.zed. The service never writes the schema.
 */

export interface ObjectRef {
  objectType: string;
  objectId: string;
}

export interface PermissionQuery {
  resource: ObjectRef;
  permission: string;
  subject: ObjectRef;
}

export interface RelationshipWrite {
  resource: ObjectRef;
  relation: string;
  subject: ObjectRef;
}

export interface SpiceDbPort {
  /** True only when SpiceDB reports HAS_PERMISSION at full consistency. */
  checkPermission(query: PermissionQuery): Promise<boolean>;
  /** Creates or refreshes one relationship (OPERATION_TOUCH). */
  writeRelationship(write: RelationshipWrite): Promise<void>;
}
