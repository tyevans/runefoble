/**
 * PostgreSQL event store for Audience Studio (ADR-0015 decision f).
 * Table `audience_studio_events` holds one row per event. The primary key
 * (stream_id, version) enforces optimistic concurrency. Table `audience_studio_outbox`
 * holds one unsent marker per event, written in the same transaction as the event.
 */

import pg from 'pg';
import {
  ConcurrencyConflictError,
  type AppendChange,
  type EventStore,
  type NewEvent,
  type StoredEvent,
} from './types.js';

const TABLE = 'audience_studio_events';
const OUTBOX = 'audience_studio_outbox';
/** PostgreSQL names the primary key of a new table `<table>_pkey`. */
const EVENTS_PRIMARY_KEY = `${TABLE}_pkey`;
const UNIQUE_VIOLATION = '23505';

interface EventRow {
  stream_id: string;
  version: number;
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: Date;
}

function isEventVersionViolation(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    (err as { code?: unknown }).code === UNIQUE_VIOLATION &&
    (err as { constraint?: unknown }).constraint === EVENTS_PRIMARY_KEY
  );
}

export class PostgresEventStore implements EventStore {
  readonly kind = 'postgresql' as const;
  private readonly pool: pg.Pool;

  constructor(connectionString: string) {
    this.pool = new pg.Pool({
      connectionString,
      max: 10,
      connectionTimeoutMillis: 3000,
    });
  }

  async init(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS ${TABLE} (
        stream_id   text        NOT NULL,
        version     integer     NOT NULL,
        event_type  text        NOT NULL,
        payload     jsonb       NOT NULL,
        occurred_at timestamptz NOT NULL,
        PRIMARY KEY (stream_id, version)
      )`);
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS ${OUTBOX} (
        seq          bigserial   PRIMARY KEY,
        stream_id   text        NOT NULL,
        version     integer     NOT NULL,
        published_at timestamptz,
        FOREIGN KEY (stream_id, version) REFERENCES ${TABLE} (stream_id, version)
      )`);
    await this.pool.query(`
      CREATE INDEX IF NOT EXISTS ${OUTBOX}_unsent ON ${OUTBOX} (seq) WHERE published_at IS NULL`);
  }

  async ping(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }

  async load(streamId: string): Promise<StoredEvent[]> {
    const res = await this.pool.query<EventRow>(
      `SELECT stream_id, version, event_type, payload, occurred_at
         FROM ${TABLE} WHERE stream_id = $1 ORDER BY version`,
      [streamId]
    );
    return res.rows.map(toStoredEvent);
  }

  async loadPrefix(prefix: string): Promise<StoredEvent[]> {
    const res = await this.pool.query<EventRow>(
      `SELECT stream_id, version, event_type, payload, occurred_at
         FROM ${TABLE}
        WHERE left(stream_id, length($1)) = $1
        ORDER BY stream_id, version`,
      [prefix]
    );
    return res.rows.map(toStoredEvent);
  }

  async appendAll(changes: AppendChange[]): Promise<void> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      for (const change of changes) {
        const { rows } = await client.query<{ latest: number }>(
          `SELECT COALESCE(MAX(version), 0) AS latest FROM ${TABLE} WHERE stream_id = $1`,
          [change.streamId]
        );
        if (Number(rows[0].latest) !== change.expectedVersion) {
          throw new ConcurrencyConflictError(change.streamId, change.expectedVersion);
        }
        for (const [index, event] of change.events.entries()) {
          const version = change.expectedVersion + index + 1;
          await insertEvent(client, change, version, event);
          await client.query(`INSERT INTO ${OUTBOX} (stream_id, version) VALUES ($1, $2)`, [change.streamId, version]);
        }
      }
      await client.query('COMMIT');
    } catch (err) {
      await client.query('ROLLBACK').catch(() => {});
      throw err;
    } finally {
      client.release();
    }
  }

  async drainOutbox(limit: number, publish: (event: StoredEvent) => Promise<void>): Promise<number> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      // SKIP LOCKED lets two relays drain different batches. Each row is sent by one relay at a time.
      const { rows } = await client.query<EventRow>(
        `SELECT e.stream_id, e.version, e.event_type, e.payload, e.occurred_at
           FROM ${OUTBOX} o
           JOIN ${TABLE} e ON e.stream_id = o.stream_id AND e.version = o.version
          WHERE o.published_at IS NULL
          ORDER BY o.seq
          LIMIT $1
            FOR UPDATE OF o SKIP LOCKED`,
        [limit]
      );
      for (const row of rows) {
        await publish(toStoredEvent(row));
        await client.query(
          `UPDATE ${OUTBOX} SET published_at = now() WHERE stream_id = $1 AND version = $2`,
          [row.stream_id, row.version]
        );
      }
      await client.query('COMMIT');
      return rows.length;
    } catch (err) {
      await client.query('ROLLBACK').catch(() => {});
      throw err;
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }
}

/** A version key violation means another writer appended first. It maps to a conflict, not a 500. */
async function insertEvent(
  client: pg.PoolClient,
  change: AppendChange,
  version: number,
  event: NewEvent
): Promise<void> {
  try {
    await client.query(
      `INSERT INTO ${TABLE} (stream_id, version, event_type, payload, occurred_at)
       VALUES ($1, $2, $3, $4, $5)`,
      [change.streamId, version, event.type, JSON.stringify(event.data), event.occurredAt]
    );
  } catch (err) {
    if (isEventVersionViolation(err)) {
      throw new ConcurrencyConflictError(change.streamId, change.expectedVersion);
    }
    throw err;
  }
}

function toStoredEvent(row: EventRow): StoredEvent {
  return {
    streamId: row.stream_id,
    version: Number(row.version),
    type: row.event_type,
    data: row.payload,
    occurredAt: row.occurred_at.toISOString(),
  };
}
