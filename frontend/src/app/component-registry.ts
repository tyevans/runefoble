/**
 * App Shell Component Registry (TASK-0640b).
 *
 * Loads the shell chrome elements at startup. Each microfrontend bundle loads by route,
 * through a dynamic import, the first time a view needs it. Each import registers its elements once.
 */

import '../components/runefoble-header.ts';
import '../components/runefoble-settings-modal.ts';
import '../components/runefoble-auth-modal.ts';
import '../components/runefoble-session-list.ts';
import '../components/runefoble-party-vitals-page.ts';
import '../components/plugins/runefoble-plugin-slot.ts';
import '../components/runefoble-user-profile.ts';
import '../components/state/runefoble-data-error.ts';
import type { AppActiveView } from '../router/view-resolver.ts';

type BundleLoader = () => Promise<unknown>;

const BUNDLES = {
  gameSession: () => import('@runefoble/game-session-ui'),
  characterSheet: () => import('@runefoble/character-sheet-ui'),
  boardState: () => import('@runefoble/board-state-ui'),
  theWatcher: () => import('@runefoble/the-watcher-ui'),
  voiceAgent: () => import('@runefoble/voice-agent-ui'),
  soundscape: () => import('@runefoble/soundscape-ui'),
  campaignLore: () => import('@runefoble/campaign-lore-ui'),
  campaignAnalytics: () => import('@runefoble/campaign-analytics-ui'),
  assetForge: () => import('@runefoble/asset-forge-ui'),
  rulesCompendium: () => import('@runefoble/rules-compendium-ui'),
} satisfies Record<string, BundleLoader>;

type BundleName = keyof typeof BUNDLES;

const SESSION_BUNDLES: BundleName[] = ['gameSession', 'characterSheet', 'boardState', 'theWatcher', 'voiceAgent', 'soundscape'];

/** The microfrontend bundles that each view mounts. */
export const VIEW_BUNDLES: Record<AppActiveView, BundleName[]> = {
  'login': [],
  'campaign-join': ['gameSession'],
  'campaigns': ['gameSession'],
  'campaign-detail': ['gameSession'],
  'campaign-characters': ['gameSession', 'characterSheet'],
  'campaign-codex': ['gameSession', 'campaignLore'],
  'campaign-analytics': ['gameSession', 'campaignAnalytics'],
  'campaign-forge': ['gameSession', 'assetForge'],
  'campaign-rules': ['gameSession', 'rulesCompendium'],
  'characters': ['characterSheet'],
  'character-sheet': ['characterSheet'],
  'session-lobby': SESSION_BUNDLES,
  'session-active': SESSION_BUNDLES,
  'profile': [],
  'rules': ['rulesCompendium'],
  'caravan-board': ['gameSession'],
  'party-vitals-overlay': ['gameSession'],
};

/** Loads the bundles for a view. A failed import rejects so that the caller reports it. */
export async function loadViewBundles(view: AppActiveView): Promise<void> {
  await Promise.all(VIEW_BUNDLES[view].map((name) => BUNDLES[name]()));
}
