/**
 * Bridge between client tabletop 3D visualizer, backend physics engine,
 * and real-time board WebSocket notifications.
 *
 * TASK-0758: the physics routes go through the shared transport in `@runefoble/ui-core`.
 * The host gives the API base and the bearer source. A refused call throws `HttpError`.
 */

import { postJson, type AuthSource, type FetchLike } from '@runefoble/ui-core';
import type { TabletopPhysicsVisualizer } from './tabletop_canvas.ts';

export interface PhysicsBridgeHost {
  tokens?: Array<{ id: string; x: number; y: number; [key: string]: any }>;
  /** API base for the physics routes. Empty or absent means the page origin. */
  apiBaseUrl?: string;
  dispatchEvent(event: Event): boolean;
}

export class PhysicsBridge {
  private host: PhysicsBridgeHost;
  private visualizer: TabletopPhysicsVisualizer | null = null;
  private auth: AuthSource | undefined;
  private fetchImpl: FetchLike | undefined;

  constructor(
    host: PhysicsBridgeHost,
    visualizer?: TabletopPhysicsVisualizer | null,
    auth?: AuthSource,
    fetchImpl?: FetchLike,
  ) {
    this.host = host;
    this.visualizer = visualizer ?? null;
    this.auth = auth;
    this.fetchImpl = fetchImpl;
  }

  /** Posts to a board physics route under the host API base, with the bearer. */
  private postPhysics(boardId: string, route: string, body: Record<string, unknown>): Promise<any> {
    const path = `/api/v1/boards/${encodeURIComponent(boardId)}/physics/${route}`;
    return postJson(path, body, { apiBase: this.host.apiBaseUrl, auth: this.auth, fetchImpl: this.fetchImpl });
  }

  public setVisualizer(v: TabletopPhysicsVisualizer | null): void {
    this.visualizer = v;
  }

  public handleWebSocketMessage(data: any): boolean {
    if (!data) return false;
    const type = data.type || data.action;

    if (type === 'dice_settled' || type === 'simulate_throw') {
      const dice = data.dice || data;
      if (dice?.settled_cell && dice?.face_value !== undefined) {
        this.visualizer?.rollDice({
          diceId: dice.dice_id,
          diceType: dice.dice_type,
          faceValue: dice.face_value,
          settledCell: dice.settled_cell,
          trajectory: dice.trajectory,
        });
        this.host.dispatchEvent(new CustomEvent('dice-settled', {
          detail: dice, bubbles: true, composed: true,
        }));
        return true;
      }
    }

    if (type === 'token_knockback' || type === 'knockback') {
      const kb = data.knockback || data;
      if (kb?.token_id && kb.to_x !== undefined) {
        this.visualizer?.knockbackToken({
          tokenId: kb.token_id,
          fromX: kb.from_x ?? 0,
          fromY: kb.from_y ?? 0,
          toX: kb.to_x,
          toY: kb.to_y,
          collided: kb.collided,
          collisionType: kb.collision_type,
          impactEnergy: kb.impact_energy,
        });
        if (this.host.tokens) {
          this.host.tokens = this.host.tokens.map((t) => (t.id === kb.token_id ? { ...t, x: kb.to_x, y: kb.to_y } : t));
        }
        this.host.dispatchEvent(new CustomEvent('token-knockback', {
          detail: kb, bubbles: true, composed: true,
        }));
        return true;
      }
    }

    if (type === 'physics_collision') {
      this.host.dispatchEvent(new CustomEvent('physics-collision', {
        detail: data, bubbles: true, composed: true,
      }));
      return true;
    }
    return false;
  }

  public async triggerSimulateThrow(boardId: string, options?: { diceType?: string; velocityX?: number; velocityY?: number; seed?: number }): Promise<any> {
    const data = await this.postPhysics(boardId, 'simulate-throw', {
      dice_type: options?.diceType ?? 'd20',
      velocity_x: options?.velocityX ?? 4.0,
      velocity_y: options?.velocityY ?? 4.0,
      seed: options?.seed,
    });
    this.handleWebSocketMessage({ type: 'dice_settled', dice: data });
    return data;
  }

  public async triggerKnockback(boardId: string, tokenId: string, directionX: number, directionY: number, distanceFt = 10.0, mass = 1.0): Promise<any> {
    const data = await this.postPhysics(boardId, 'knockback', {
      token_id: tokenId,
      direction_x: directionX,
      direction_y: directionY,
      distance_ft: distanceFt,
      mass,
    });
    this.handleWebSocketMessage({ type: 'token_knockback', knockback: data });
    return data;
  }
}
