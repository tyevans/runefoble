import type { CaravanContractItem } from '../runefoble-caravan-types.ts';

export interface CaravanApiContext {
  apiBase: string;
  sharedWorldId: string;
  campaignId: string;
  partyName: string;
  userId?: string;
}

/** Outcome of a caravan request. A failed request never changes the contract. */
export type CaravanActionResult = { ok: true } | { ok: false; message: string };

export async function apiAcceptContract(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<void> {
  const res = await fetch(
    `${ctx.apiBase}/shared-worlds/${ctx.sharedWorldId}/caravans/contracts/${contract.contract_id}/accept`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(ctx.userId ? { 'x-user-id': ctx.userId } : {}),
      },
      body: JSON.stringify({
        contractor_campaign_id: ctx.campaignId,
        contractor_party_name: ctx.partyName,
      }),
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Authorization failed');
  }
  const data = await res.json();
  contract.status = data?.contract?.status || 'accepted';
  contract.contractor_party_name = data?.contract?.contractor_party_name || ctx.partyName;
}

/** Sends a POST to a caravan route and reports the result. Never throws. */
async function postCaravanAction(
  ctx: CaravanApiContext,
  path: string,
  body: Record<string, unknown>
): Promise<CaravanActionResult> {
  let res: Response;
  try {
    res = await fetch(`${ctx.apiBase}/shared-worlds/${ctx.sharedWorldId}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(ctx.userId ? { 'x-user-id': ctx.userId } : {}),
      },
      body: JSON.stringify(body),
    });
  } catch (err: unknown) {
    const reason = err instanceof Error ? err.message : String(err);
    return { ok: false, message: `Network error: ${reason}` };
  }
  if (!res.ok) {
    const payload = (await res.json().catch(() => undefined)) as { detail?: unknown } | undefined;
    const detail = typeof payload?.detail === 'string' ? payload.detail : '';
    return {
      ok: false,
      message: detail || `Request failed with status ${res.status}`,
    };
  }
  return { ok: true };
}

export async function apiDispatchCaravan(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<CaravanActionResult> {
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
): Promise<CaravanActionResult> {
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
