import {
  HttpError, postJson, requestFailureMessage, type ActionResult,
} from '@runefoble/ui-core';
import type { CaravanContractItem } from '../runefoble-caravan-types.ts';

/** Resolves the headers that carry the caller's bearer. Empty when nobody is signed in. */
export type AuthHeaders = () => Promise<Record<string, string>>;

export interface CaravanApiContext {
  apiBase: string;
  sharedWorldId: string;
  campaignId: string;
  partyName: string;
  /** The shared auth source (TASK-0812). The gateway reads identity from the bearer only. */
  authHeaders: AuthHeaders;
}

/** A sign-in or permission message for a refused caravan request. Undefined for other statuses. */
function authFailureMessage(status: number): string | undefined {
  if (status === 401) return 'Sign in to continue with this caravan action.';
  if (status === 403) return 'Your account does not have permission for this caravan action.';
  return undefined;
}

interface AcceptContractResponse {
  contract?: { status?: CaravanContractItem['status']; contractor_party_name?: string };
}

/** The message a player sees for a failed caravan request. Sign-in and permission wording wins. */
function caravanFailureMessage(err: unknown): string {
  if (err instanceof HttpError) return authFailureMessage(err.status) ?? err.detail;
  return requestFailureMessage(err);
}

function caravanUrl(ctx: CaravanApiContext, path: string): string {
  return `${ctx.apiBase}/shared-worlds/${ctx.sharedWorldId}${path}`;
}

export async function apiAcceptContract(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<void> {
  let data: AcceptContractResponse | undefined;
  try {
    data = await postJson<AcceptContractResponse | undefined>(
      caravanUrl(ctx, `/caravans/contracts/${contract.contract_id}/accept`),
      {
        contractor_campaign_id: ctx.campaignId,
        contractor_party_name: ctx.partyName,
      },
      { headers: await ctx.authHeaders() }
    );
  } catch (err) {
    throw new Error(caravanFailureMessage(err));
  }
  contract.status = data?.contract?.status || 'accepted';
  contract.contractor_party_name = data?.contract?.contractor_party_name || ctx.partyName;
}

/** Sends a POST to a caravan route and reports the result. Never throws. */
async function postCaravanAction(
  ctx: CaravanApiContext,
  path: string,
  body: Record<string, unknown>
): Promise<ActionResult> {
  try {
    await postJson(caravanUrl(ctx, path), body, { headers: await ctx.authHeaders() });
    return { ok: true };
  } catch (err) {
    return { ok: false, message: caravanFailureMessage(err) };
  }
}
export async function apiDispatchCaravan(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<ActionResult> {
  const result = await postCaravanAction(
    ctx,
    `/caravans/contracts/${contract.contract_id}/dispatch`,
    { dispatched_by_campaign_id: ctx.campaignId }
  );
  if (!result.ok) return result;
  contract.status = 'in_transit';
  contract.current_stage = 1;
  return result;
}

export async function apiFulfillContract(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<ActionResult> {
  const result = await postCaravanAction(
    ctx,
    `/caravans/contracts/${contract.contract_id}/fulfill`,
    {}
  );
  if (!result.ok) return result;
  contract.status = 'fulfilled';
  contract.current_stage = contract.transit_stages;
  return result;
}
