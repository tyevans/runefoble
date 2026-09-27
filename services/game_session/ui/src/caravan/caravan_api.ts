import type { CaravanContractItem } from '../runefoble-caravan-types.ts';

export interface CaravanApiContext {
  apiBase: string;
  sharedWorldId: string;
  campaignId: string;
  partyName: string;
  userId?: string;
}

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

export async function apiDispatchCaravan(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<void> {
  try {
    await fetch(
      `${ctx.apiBase}/shared-worlds/${ctx.sharedWorldId}/caravans/contracts/${contract.contract_id}/dispatch`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(ctx.userId ? { 'x-user-id': ctx.userId } : {}),
        },
        body: JSON.stringify({ dispatched_by_campaign_id: ctx.campaignId }),
      }
    );
  } catch {
    /* offline fallback */
  }
  contract.status = 'in_transit';
  contract.current_stage = 1;
}

export async function apiFulfillContract(
  ctx: CaravanApiContext,
  contract: CaravanContractItem
): Promise<void> {
  try {
    await fetch(
      `${ctx.apiBase}/shared-worlds/${ctx.sharedWorldId}/caravans/contracts/${contract.contract_id}/fulfill`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(ctx.userId ? { 'x-user-id': ctx.userId } : {}),
        },
        body: JSON.stringify({}),
      }
    );
  } catch {
    /* offline fallback */
  }
  contract.status = 'fulfilled';
  contract.current_stage = contract.transit_stages;
}
