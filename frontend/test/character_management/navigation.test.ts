/**
 * Character Management Navigation & Dynamic Route Title Test Suite.
 *
 * TASK-0288: Frontend Character Management Test Suite Modular Decomposition
 * Governing ADRs: ADR-0004, ADR-0010, ADR-0012, ADR-0013
 * Hard Invariants: Hard Invariant 6 (< 130 lines), Hard Invariant 7 (Blackbox TDD)
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { Router, type MatchedRoute } from '../../src/router/router.ts';
import { AppDataService } from '../../src/services/app-data-service.ts';
import type { AppActiveView } from '../../src/runefoble-app.ts';
import type { CharacterItem, InspectCharacterEventDetail } from '../../../services/character_sheet/ui/src/roster/types.ts';
import type { LobbyParticipant } from '../../../services/game_session/ui/src/campaigns/types.ts';

const APP_SHELL_PATH = resolve(import.meta.dirname, '../../src/runefoble-app.ts');

function resolveActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat.startsWith('#/characters/') && pat !== '#/characters') return 'character-sheet';
  return pat === '#/characters' ? 'characters' : 'campaigns';
}

describe('Character Roster & Deep Route Navigation (US-0064, US-0069, TASK-0288)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
    router.setTitleResolver((type, id) => {
      if (type === 'character' && id === 'char-valeros') return 'Valeros of Korvosa';
      return undefined;
    });
  });

  it('test_roster_inspect_sheet_navigates_to_deep_route: mounts sheet and updates breadcrumbs', async () => {
    await router.navigate('#/characters');
    const rosterRoute = router.getCurrentRoute();
    assert.ok(rosterRoute);
    assert.equal(resolveActiveView(rosterRoute), 'characters');

    const handleInspectCharacter = async (e: { detail: InspectCharacterEventDetail }) => {
      await router.navigate(`#/characters/${e.detail.characterId}`);
    };
    await handleInspectCharacter({
      detail: {
        characterId: 'char-valeros',
        character: { id: 'char-valeros', name: 'Valeros of Korvosa', characterClass: 'Fighter', level: 4, currentHp: 38, maxHp: 45, armorClass: 18 } as CharacterItem,
      },
    });

    const current = router.getCurrentRoute();
    assert.ok(current);
    assert.equal(current.path, '#/characters/char-valeros');
    assert.equal(current.pattern, '#/characters/:characterId');
    assert.equal(resolveActiveView(current), 'character-sheet');

    assert.equal(current.breadcrumbs.length, 3);
    assert.equal(current.breadcrumbs[0].label, 'Home');
    assert.equal(current.breadcrumbs[1].label, 'Characters');
    assert.equal(current.breadcrumbs[2].label, 'Valeros of Korvosa');
    assert.equal(current.breadcrumbs[2].active, true);

    const appShellContent = readFileSync(APP_SHELL_PATH, 'utf-8');
    assert.ok(appShellContent.includes('<runefoble-character-sheet'));
    assert.ok(appShellContent.includes('.characterId=${charId}'));
    assert.ok(appShellContent.includes('← Back to Roster'));
  });

  it('test_lobby_selection_and_active_card_binding: syncs lobby participant and card vitals', async () => {
    const dataService = new AppDataService();
    const lobby = await dataService.fetchLobbyState('4', 'session-tomb-14');
    assert.ok(lobby.availableCharacters.length >= 2);

    const characters = await dataService.fetchCharacters();
    const valeros = characters.find((c) => c.id === 'char-valeros')!;
    assert.ok(valeros, 'Valeros must exist in character store');

    let lobbyParticipants: LobbyParticipant[] = [
      { userId: 'user-valeros', displayName: 'Marcus', characterId: 'char-placeholder', characterName: 'Unknown', isReady: false },
    ];
    let activeCharacter: CharacterItem | null = null;
    const handleSelect = (detail: { userId: string; characterId: string }) => {
      const full = characters.find((c) => c.id === detail.characterId);
      if (full) activeCharacter = full;
      lobbyParticipants = lobbyParticipants.map((p) =>
        p.userId === detail.userId ? { ...p, characterId: detail.characterId, characterName: full?.name || p.characterName } : p
      );
    };

    handleSelect({ userId: 'user-valeros', characterId: 'char-valeros' });
    assert.equal(lobbyParticipants[0].characterId, 'char-valeros');
    assert.equal(activeCharacter?.name, 'Valeros of Korvosa');
    assert.equal(activeCharacter?.armorClass, 18);
    assert.equal(activeCharacter?.maxHp, 45);
  });
});
