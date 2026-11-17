/**
 * PostgreSQL event store for Audience Studio (ADR-0015 decision f).
 * Table `audience_studio_events` holds one row per event. The primary key
 * (stream_id, version) enforces optimistic concurrency.
 */

import pg from 'pg';
import {
  ConcurrencyConflictError,
  type AppendChange,
  type EventStore,
  type StoredEvent,
} from './types.js';

const TABLE = 'audience_studio_events';

interface EventRow {
  stream_id: string;
  version: number;
  event_type: string;
  payload: Record<string, unknown>;
  occurred_at: Date;
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
          await client.query(
            `INSERT INTO ${TABLE} (stream_id, version, event_type, payload, occurred_at)
             VALUES ($1, $2, $3, $4, $5)`,
            [
              change.streamId,
              change.expectedVersion + index + 1,
              event.type,
              JSON.stringify(event.data),
              event.occurredAt,
            ]
          );
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

  async close(): Promise<void> {
    await this.pool.end();
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
