/**
 * App Shell Asset Forge permission state (TASK-0797). The campaign hub renders in a real
 * Chromium DOM. Only a campaign that reports `permissions.manage` shows the forge tab and
 * mounts the forge elements. Any other campaign shows the not-permitted notice.
 * Governing ADRs: ADR-0004, ADR-0013, ADR-0014.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { render } from 'lit';
import { renderCampaignHub } from '../src/views/campaign-hub-view.ts';
import type { RunefobleApp } from '../src/runefoble-app.ts';

function appWithPermissions(permissions: { manage?: boolean } | undefined): RunefobleApp {
  return {
    campaignId: 'camp-1',
    currentUserId: 'user-1',
    currentCampaign: { id: 'camp-1', title: 'The Sunken Vault', permissions },
  } as unknown as RunefobleApp;
}

let host: HTMLElement | undefined;

function renderForgeView(permissions: { manage?: boolean } | undefined): HTMLElement {
  host = document.createElement('div');
  document.body.append(host);
  render(renderCampaignHub(appWithPermissions(permissions), 'campaign-forge'), host);
  return host;
}

function hasForgeTab(root: HTMLElement): boolean {
  return [...root.querySelectorAll<HTMLAnchorElement>('a.nav-tab')].some(
    (tab) => tab.textContent?.trim() === 'Asset Forge',
  );
}

afterEach(() => {
  host?.remove();
  host = undefined;
});

describe('App Shell Asset Forge permission state', () => {
  it('shows the forge tab and mounts the forge elements when the campaign grants manage', () => {
    const root = renderForgeView({ manage: true });

    expect(hasForgeTab(root)).toBe(true);
    expect(root.querySelector('runefoble-asset-forge')).not.toBeNull();
    expect(root.querySelector('.forge-not-permitted')).toBeNull();
  });

  it('hides the forge tab and shows the not-permitted notice when manage is false', () => {
    const root = renderForgeView({ manage: false });

    expect(hasForgeTab(root)).toBe(false);
    expect(root.querySelector('runefoble-asset-forge')).toBeNull();
    expect(root.querySelector('.forge-not-permitted[role="alert"]')).not.toBeNull();
  });

  it('denies the forge when the campaign reports no permissions', () => {
    const root = renderForgeView(undefined);

    expect(hasForgeTab(root)).toBe(false);
    expect(root.querySelector('runefoble-asset-forge')).toBeNull();
    expect(root.querySelector('.forge-not-permitted')).not.toBeNull();
  });
});
