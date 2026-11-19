/**
 * Caravan request client over the shared UI transport (TASK-0677, TASK-0812, TASK-0759).
 *
 * Every call goes through one POST over `postJson`. The bearer comes from the shared auth
 * source. No call sends a caller-asserted identity header. A failed call reports the text of
 * `actionFailureMessage` and never changes the contract.
 */

import { actionFailureMessage, postJson, type AuthSource } from '@runefoble/ui-core';
import type { CaravanContractItem } from '../runefoble-caravan-types.ts';

export interface CaravanApiContext {
  apiBase: string;
  sharedWorldId: string;
  campaignId: string;
  partyName: string;
  /** The shared auth source. The gateway reads identity from the bearer only. */
  auth: AuthSource;
}

/** The outcome of a caravan action. A failure carries the message that the player sees. */
export type CaravanResult<T = undefined> = { ok: true; data: T } | { ok: false; message: string };

interface AcceptContractResponse {
  contract?: { status?: CaravanContractItem['status']; contractor_party_name?: string };
}

/** Sends one POST to a caravan route of the shared world. Never throws. */
async function postCaravan<T>(
  ctx: CaravanApiContext,
  path: string,
  body: Record<string, unknown>,
): Promise<CaravanResult<T | undefined>> {
  try {
    const data = await postJson<T | undefined>(
      `/shared-worlds/${encodeURIComponent(ctx.sharedWorldId)}/caravans/contracts${path}`,
      body,
      { apiBase: ctx.apiBase, auth: ctx.auth },
    );
    return { ok: true, data };
  } catch (err) {
    return { ok: false, message: actionFailureMessage(err, 'caravan action') };
  }
}

function contractPath(contract: CaravanContractItem, action: string): string {
  return `/${encodeURIComponent(contract.contract_id)}/${action}`;
}

export async function apiAcceptContract(
  ctx: CaravanApiContext,
  contract: CaravanContractItem,
): Promise<CaravanResult> {
  const result = await postCaravan<AcceptContractResponse>(ctx, contractPath(contract, 'accept'), {
    contractor_campaign_id: ctx.campaignId,
    contractor_party_name: ctx.partyName,
  });
  if (!result.ok) return result;
  contract.status = result.data?.contract?.status || 'accepted';
  contract.contractor_party_name = result.data?.contract?.contractor_party_name || ctx.partyName;
  return { ok: true, data: undefined };
}

export async function apiDispatchCaravan(
  ctx: CaravanApiContext,
  contract: CaravanContractItem,
): Promise<CaravanResult> {
  const result = await postCaravan(ctx, contractPath(contract, 'dispatch'), {
    dispatched_by_campaign_id: ctx.campaignId,
  });
  if (!result.ok) return result;
  contract.status = 'in_transit';
  contract.current_stage = 1;
  return { ok: true, data: undefined };
}

export async function apiFulfillContract(
  ctx: CaravanApiContext,
  contract: CaravanContractItem,
): Promise<CaravanResult> {
  const result = await postCaravan(ctx, contractPath(contract, 'fulfill'), {});
  if (!result.ok) return result;
  contract.status = 'fulfilled';
  contract.current_stage = contract.transit_stages;
  return { ok: true, data: undefined };
}
