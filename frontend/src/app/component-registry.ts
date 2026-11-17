/**
 * App Shell Component Registry (TASK-0640b).
 *
 * Loads the custom elements and microfrontend bundles that the App Shell mounts.
 * Each import registers its elements once, before the shell renders.
 */

import '../components/runefoble-header.ts';
import '../components/runefoble-settings-modal.ts';
import '../components/runefoble-auth-modal.ts';
import '../components/runefoble-session-list.ts';
import '../components/plugins/runefoble-plugin-slot.ts';
import '../components/runefoble-user-profile.ts';
import '../components/state/runefoble-data-error.ts';
import '@runefoble/board-state-ui';
import '@runefoble/campaign-analytics-ui';
import '@runefoble/campaign-lore-ui';
import '@runefoble/character-sheet-ui';
import '@runefoble/game-session-ui';
import '@runefoble/soundscape-ui';
import '@runefoble/the-watcher-ui';
import '@runefoble/voice-agent-ui';
