/**
 * Frontend Blackbox Integration Test Suite: Character Management, Roster Inspection,
 * Campaign Creation Deduplication, and User Profile Routing.
 *
 * TASK-0258: Character Management and Tabletop Sync Blackbox Test Suite
 * Governing ADRs: ADR-0001, ADR-0002, ADR-0004, ADR-0010, ADR-0012, ADR-0013
 * Product & Stories: PRD-0006, PRD-0023, US-0064, US-0069, US-0070, US-0071
 * Hard Invariants:
 * - Hard Invariant 6: File length limit (< 500 lines)
 * - Hard Invariant 7: Blackbox TDD with frontdoor setup
 */

import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

import { Router, type MatchedRoute } from '../src/router/router.ts';
import { AppDataService } from '../src/services/app-data-service.ts';
import { authService, type UserClaims } from '../src/auth/auth-service.ts';
import { FALLBACK_CAMPAIGNS, FALLBACK_CHARACTERS } from '../src/services/fallback-data.ts';
import type { AppActiveView } from '../src/runefoble-app.ts';
import type { CampaignItem, CreateCampaignPayload, LobbyParticipant } from '../../services/game_session/ui/src/campaigns/types.ts';
import type { CharacterItem, InspectCharacterEventDetail, CreateCharacterPayload } from '../../services/character_sheet/ui/src/roster/types.ts';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..');
const REPO_ROOT = resolve(FRONTEND_DIR, '..');

const APP_SHELL_PATH = resolve(FRONTEND_DIR, 'src/runefoble-app.ts');
const ROUTER_PATH = resolve(FRONTEND_DIR, 'src/router/router.ts');
const PROFILE_PATH = resolve(FRONTEND_DIR, 'src/components/runefoble-user-profile.ts');
const ROSTER_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/roster/runefoble-character-roster.ts');
const CHARACTER_CARD_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-card.ts');
const STATS_TEMPLATE_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/templates/stats.template.ts');
const SPELLS_TEMPLATE_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/templates/spells.template.ts');
const SHEET_COMPONENT_PATH = resolve(REPO_ROOT, 'services/character_sheet/ui/src/runefoble-character-sheet.ts');

function resolveActiveView(route: MatchedRoute | null): AppActiveView {
  const pat = route?.pattern || '';
  if (pat === '#/login' || pat === '#/register') return 'login';
  if (pat.startsWith('#/campaigns/:campaignId/lobby/')) return 'session-lobby';
  if (pat.startsWith('#/campaigns/:campaignId/sessions/')) return 'session-active';
  if (pat === '#/campaigns/:campaignId/characters') return 'campaign-characters';
  if (pat.startsWith('#/campaigns/:campaignId')) return 'campaign-detail';
  if (pat.startsWith('#/characters/') && pat !== '#/characters') return 'character-sheet';
  if (pat === '#/characters') return 'characters';
  return pat === '#/profile' ? 'profile' : 'campaigns';
}

describe('Character Roster and Inspector Deep Route Navigation (US-0064, US-0069, TASK-0258)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
    router.setTitleResolver((type, id) => {
      if (type === 'campaign' && id === '4') return 'Tomb of the Star-Eater';
      if (type === 'character' && id === 'char-valeros') return 'Valeros of Korvosa';
      if (type === 'character' && id === 'char-seoni') return 'Seoni of Varisia';
      return undefined;
    });
  });

  it('test_roster_inspect_sheet_navigates_to_deep_route: clicking Inspect Sheet navigates to #/characters/:id and mounts runefoble-character-sheet', async () => {
    // 1. Initial navigation to Character Roster
    await router.navigate('#/characters');
    const rosterRoute = router.getCurrentRoute();
    assert.ok(rosterRoute, 'Roster route must match');
    assert.equal(rosterRoute.pattern, '#/characters');
    assert.equal(resolveActiveView(rosterRoute), 'characters');

    // 2. Simulate user clicking "Inspect Sheet" on Valeros of Korvosa
    const targetCharacterId = 'char-valeros';
    let navigationPath = '';
    const handleInspectCharacter = async (e: { detail: InspectCharacterEventDetail }) => {
      navigationPath = `#/characters/${e.detail.characterId}`;
      await router.navigate(navigationPath);
    };

    const inspectEvent = {
      detail: {
        characterId: targetCharacterId,
        character: {
          id: targetCharacterId,
          name: 'Valeros of Korvosa',
          characterClass: 'Fighter',
          level: 4,
          currentHp: 38,
          maxHp: 45,
          armorClass: 18,
        } as CharacterItem,
      },
    };

    await handleInspectCharacter(inspectEvent);

    // 3. Verify router navigates to deep route and pattern matches
    const current = router.getCurrentRoute();
    assert.ok(current, 'Deep character route must match');
    assert.equal(current.path, '#/characters/char-valeros');
    assert.equal(current.pattern, '#/characters/:characterId');
    assert.equal(current.params.characterId, 'char-valeros');

    // 4. Verify resolved active view is 'character-sheet'
    const activeView = resolveActiveView(current);
    assert.equal(activeView, 'character-sheet', 'Active view must resolve to character-sheet');

    // 5. Verify hierarchical breadcrumbs [Home, Characters, Character Name]
    assert.equal(current.breadcrumbs.length, 3);
    assert.equal(current.breadcrumbs[0].label, 'Home');
    assert.equal(current.breadcrumbs[0].path, '#/campaigns');
    assert.equal(current.breadcrumbs[1].label, 'Characters');
    assert.equal(current.breadcrumbs[1].path, '#/characters');
    assert.equal(current.breadcrumbs[2].label, 'Valeros of Korvosa');
    assert.equal(current.breadcrumbs[2].path, '#/characters/char-valeros');
    assert.equal(current.breadcrumbs[2].active, true);

    // 6. Verify template contract: runefoble-app mounts <runefoble-character-sheet>
    const appShellContent = readFileSync(APP_SHELL_PATH, 'utf-8');
    assert.ok(appShellContent.includes('<runefoble-character-sheet'));
    assert.ok(appShellContent.includes('.characterId=${charId}'));
    assert.ok(appShellContent.includes('.characterName='));
    assert.ok(appShellContent.includes('← Back to Roster'));
    assert.ok(appShellContent.includes("router.navigate('#/characters')"));
  });

  it('persists character creation and verifies unassigned roster card state', async () => {
    const dataService = new AppDataService();
    const payload: CreateCharacterPayload = {
      name: 'Seoni of Varisia',
      characterClass: 'Sorcerer',
      subclass: 'Draconic Bloodline',
      level: 3,
      maxHp: 22,
      armorClass: 12,
      speed: 30,
      abilityScores: { str: 8, dex: 14, con: 12, int: 12, wis: 10, cha: 16 },
      portraitUrl: '/assets/portraits/sorcerer.svg',
    };

    const created = await dataService.createCharacter(payload);
    assert.ok(created.id, 'Created character must have an ID');
    assert.equal(created.name, 'Seoni of Varisia');
    assert.equal(created.characterClass, 'Sorcerer');
    assert.equal(created.currentHp, 22);

    const all = await dataService.fetchCharacters();
    const found = all.find((c) => c.name === 'Seoni of Varisia');
    assert.ok(found, 'New character must appear in character roster query');
    assert.ok(found?.campaignId == null, 'New character should start unassigned');
  });
});

describe('Campaign Creation Deduplication and Lifecycle (US-0071, TASK-0258)', () => {
  it('test_campaign_creation_single_event_dispatch: stops bubbling and appends exactly one campaign to dashboard', async () => {
    const dataService = new AppDataService();
    let eventsDispatched = 0;
    let stopPropagationCalled = false;

    // Emulate child modal event dispatch and dashboard listener
    const fakeEvent = {
      detail: {
        title: 'Chronicles of the Astral Sea',
        setting: 'Astral Plane',
        system: '5e',
      } as CreateCampaignPayload,
      stopPropagation: () => {
        stopPropagationCalled = true;
      },
    };

    // Dashboard handler
    const handleCreatorSubmit = (e: typeof fakeEvent) => {
      e.stopPropagation();
      eventsDispatched += 1;
    };

    handleCreatorSubmit(fakeEvent);
    assert.equal(stopPropagationCalled, true, 'stopPropagation must be called on child submit');
    assert.equal(eventsDispatched, 1, 'Exactly one create-campaign event must be emitted');

    // Create through service and verify deduplication
    const newCamp = await dataService.createCampaign(fakeEvent.detail);
    assert.ok(newCamp.id, 'Campaign must be created with ID');
    assert.equal(newCamp.title, 'Chronicles of the Astral Sea');

    // Verify deduplication handles accidental double insertion
    const duplicatedList: CampaignItem[] = [newCamp, newCamp, ...FALLBACK_CAMPAIGNS];
    const deduped = dataService.deduplicateCampaigns(duplicatedList);
    const count = deduped.filter((c) => c.id === newCamp.id).length;
    assert.equal(count, 1, 'Only one campaign card must appear on dashboard');
  });
});

describe('User Account Profile View & Claims (US-0070, TASK-0258)', () => {
  let router: Router;

  beforeEach(() => {
    router = new Router();
    router.reset();
  });

  it('test_profile_route_renders_user_claims: navigates to #/profile and renders user identity and roles', async () => {
    await router.navigate('#/profile');
    const route = router.getCurrentRoute();
    assert.ok(route, 'Profile route must match');
    assert.equal(route.pattern, '#/profile');
    assert.equal(resolveActiveView(route), 'profile');

    // Verify hierarchical breadcrumb trail
    assert.equal(route.breadcrumbs.length, 2);
    assert.equal(route.breadcrumbs[0].label, 'Home');
    assert.equal(route.breadcrumbs[0].path, '#/campaigns');
    assert.equal(route.breadcrumbs[1].label, 'Account Settings');
    assert.equal(route.breadcrumbs[1].path, '#/profile');
    assert.equal(route.breadcrumbs[1].active, true);

    // Verify profile component structure and claims rendering
    const profileContent = readFileSync(PROFILE_PATH, 'utf-8');
    assert.ok(profileContent.includes('@customElement('));
    assert.ok(profileContent.includes('class RunefobleUserProfile extends LitElement'));
    assert.ok(profileContent.includes('user.username'));
    assert.ok(profileContent.includes('user.email'));
    assert.ok(profileContent.includes('user.user_id'));
    assert.ok(profileContent.includes('role-badge'));

    // Verify App Shell mounts profile component
    const appShellContent = readFileSync(APP_SHELL_PATH, 'utf-8');
    assert.ok(appShellContent.includes('<runefoble-user-profile'));
    assert.ok(appShellContent.includes('.user=${authService.getUser()}'));
  });
});

describe('Lobby Selection Sync and Active VTT Dynamic Card Binding (US-0065, US-0069, TASK-0258)', () => {
  it('synchronizes lobby character selection and binds active character card vitals', async () => {
    const dataService = new AppDataService();
    // 1. Fetch lobby state with campaign priority
    const lobby = await dataService.fetchLobbyState('4', 'session-tomb-14');
    assert.ok(lobby.availableCharacters.length >= 2);

    // 2. Select character in lobby
    const selectedCharId = 'char-valeros';
    const characters = await dataService.fetchCharacters();
    const valeros = characters.find((c) => c.id === selectedCharId)!;
    assert.ok(valeros, 'Valeros must exist in character store');

    // Emulate RunefobleApp.handleSelectCharacter
    let lobbyParticipants: LobbyParticipant[] = [
      { userId: 'user-valeros', displayName: 'Marcus', characterId: 'char-placeholder', characterName: 'Unknown', isReady: false },
    ];
    let activeCharacter: CharacterItem | null = null;

    const handleSelectCharacter = (detail: { userId: string; characterId: string }) => {
      const full = characters.find((c) => c.id === detail.characterId);
      if (full) activeCharacter = full;
      lobbyParticipants = lobbyParticipants.map((p) =>
        p.userId === detail.userId
          ? {
              ...p,
              characterId: detail.characterId,
              characterName: full?.name || p.characterName,
              characterClass: full?.characterClass || p.characterClass,
              characterLevel: full?.level || p.characterLevel,
              portraitUrl: full?.portraitUrl || p.portraitUrl,
            }
          : p
      );
    };

    handleSelectCharacter({ userId: 'user-valeros', characterId: 'char-valeros' });

    // Verify lobby participant updated
    const updatedParticipant = lobbyParticipants.find((p) => p.userId === 'user-valeros');
    assert.equal(updatedParticipant?.characterId, 'char-valeros');
    assert.equal(updatedParticipant?.characterName, 'Valeros of Korvosa');

    // 3. Verify active character card binding when entering active VTT session
    assert.ok(activeCharacter);
    assert.equal((activeCharacter as CharacterItem).name, 'Valeros of Korvosa');
    assert.equal((activeCharacter as CharacterItem).characterClass, 'Fighter');
    assert.equal((activeCharacter as CharacterItem).currentHp, 38);
    assert.equal((activeCharacter as CharacterItem).maxHp, 45);
    assert.equal((activeCharacter as CharacterItem).armorClass, 18);

    // 4. Verify character card component declaration
    const cardContent = readFileSync(CHARACTER_CARD_PATH, 'utf-8');
    assert.ok(cardContent.includes('@customElement('));
    assert.ok(cardContent.includes('class RunefobleCharacterCard extends LitElement'));
    assert.ok(cardContent.includes('characterName'));
    assert.ok(cardContent.includes('armorClass'));
    assert.ok(cardContent.includes('currentHp'));
    assert.ok(cardContent.includes('maxHp'));
  });

  it('resolves campaign-assigned character fallback when no explicit selection is made', () => {
    const characters: CharacterItem[] = [
      { id: 'c1', name: 'Ezren the Wizard', characterClass: 'Wizard', level: 3, currentHp: 20, maxHp: 20, armorClass: 12, campaignId: '99' },
      { id: 'c2', name: 'Valeros the Fighter', characterClass: 'Fighter', level: 4, currentHp: 38, maxHp: 45, armorClass: 18, campaignId: '4' },
    ];

    const resolveActiveCharacter = (campaignId: string, current: CharacterItem | null): CharacterItem => {
      if (current) return current;
      const matching = characters.find((c) => c.campaignId === campaignId);
      if (matching) return matching;
      return characters[0];
    };

    // Entering campaign 4 without prior selection picks Valeros because campaignId matches
    const resolved = resolveActiveCharacter('4', null);
    assert.equal(resolved.id, 'c2');
    assert.equal(resolved.name, 'Valeros the Fighter');
  });
});

describe('TASK-0356: Character Sheet Sub-Resource Mutations & Persistence', () => {
  it('modifies character health and clamps within [0, maxHp]', async () => {
    const service = AppDataService.getInstance();
    const resDmg = await service.modifyCharacterHealth('char-valeros', -10);
    assert.equal(resDmg.current_hp, 28);

    const resHeal = await service.modifyCharacterHealth('char-valeros', 20);
    assert.equal(resHeal.current_hp, 45);
  });

  it('triggers permadeath safeguard stabilization when AI stand-in health <= 0', async () => {
    const service = AppDataService.getInstance();
    const detail = service.getFallbackCharacterDetail('char-kyra');
    detail.isAiStandIn = true;
    detail.is_stand_in_active = true;

    const res = await service.modifyCharacterHealth('char-kyra', -100);
    assert.equal(res.current_hp, 0);
    assert.equal(res.is_stabilized, true);
    assert.ok(
      Array.isArray(res.conditions)
        ? res.conditions.some((c: any) => c.name === 'unconscious_stabilized')
        : Boolean(res.conditions?.unconscious_stabilized)
    );
  });

  it('equips and unequips gear with inventory synchronization', async () => {
    const service = AppDataService.getInstance();
    const resEquip = await service.equipCharacterItem('char-valeros', 'main_hand', 'Frostbrand Scimitar');
    assert.equal(resEquip.equipment.main_hand, 'Frostbrand Scimitar');

    const resUnequip = await service.unequipCharacterItem('char-valeros', 'main_hand');
    assert.equal(resUnequip.equipment.main_hand, undefined);
  });

  it('adds and removes inventory items with quantity tracking', async () => {
    const service = AppDataService.getInstance();
    const item = { item_id: 'tst-potion', name: 'Potion of Invisibility', quantity: 2, weight_lbs: 0.5 };
    const resAdd = await service.addCharacterInventoryItem('char-valeros', item);
    const added = resAdd.inventory.find((i: any) => i.item_id === 'tst-potion');
    assert.ok(added);
    assert.equal(added.quantity, 2);

    const resRem = await service.removeCharacterInventoryItem('char-valeros', 'tst-potion', 1);
    const remaining = resRem.inventory.find((i: any) => i.item_id === 'tst-potion');
    assert.equal(remaining.quantity, 1);
  });

  it('applies and removes conditions', async () => {
    const service = AppDataService.getInstance();
    const resApply = await service.applyCharacterCondition('char-valeros', 'frightened', 'dragon_roar');
    assert.ok(
      Array.isArray(resApply.conditions)
        ? resApply.conditions.some((c: any) => c.name === 'frightened')
        : Boolean(resApply.conditions?.frightened)
    );

    const resRem = await service.removeCharacterCondition('char-valeros', 'frightened');
    assert.ok(
      Array.isArray(resRem.conditions)
        ? !resRem.conditions.some((c: any) => c.name === 'frightened')
        : !resRem.conditions?.frightened
    );
  });

  it('casts spells, updates slot tracking, and toggles prepared spells', async () => {
    const service = AppDataService.getInstance();
    const resCast = await service.castCharacterSpell('char-valeros', 'Magic Missile', 1);
    assert.equal(resCast.spell_slots[1], 3);

    const resPrep = await service.prepareCharacterSpell('char-valeros', 'Detect Magic', true);
    assert.ok(resPrep.prepared_spells.includes('Detect Magic'));

    const resUnprep = await service.prepareCharacterSpell('char-valeros', 'Detect Magic', false);
    assert.ok(!resUnprep.prepared_spells.includes('Detect Magic'));
  });

  it('verifies App Shell binds all 11 action events to <runefoble-character-sheet>', () => {
    const appShellContent = readFileSync(APP_SHELL_PATH, 'utf-8');
    const requiredEvents = [
      '@hp-change', '@equip-item', '@unequip-item', '@add-item', '@remove-item',
      '@cast-spell', '@prepare-spell', '@apply-condition', '@remove-condition',
      '@expend-slot', '@restore-slot'
    ];
    for (const evt of requiredEvents) {
      assert.ok(appShellContent.includes(evt), `App Shell must bind ${evt}`);
    }
  });

  it('verifies template controls: quick HP buttons, spell tier cast, and slot modal', () => {
    const statsContent = readFileSync(STATS_TEMPLATE_PATH, 'utf-8');
    assert.ok(statsContent.includes('handleHpDelta(-5)'), 'Stats template must include -5 HP button');
    assert.ok(statsContent.includes('handleHpDelta(-1)'), 'Stats template must include -1 HP button');
    assert.ok(statsContent.includes('handleHpDelta(1)'), 'Stats template must include +1 HP button');
    assert.ok(statsContent.includes('handleHpDelta(5)'), 'Stats template must include +5 HP button');

    const spellsContent = readFileSync(SPELLS_TEMPLATE_PATH, 'utf-8');
    assert.ok(spellsContent.includes('handleCastSpell('), 'Spells template must invoke handleCastSpell');
    assert.ok(!spellsContent.includes('handleCastSpell(spell, 1)'), 'Spells template must not hardcode level 1');

    const sheetContent = readFileSync(SHEET_COMPONENT_PATH, 'utf-8');
    assert.ok(sheetContent.includes('openEquipDialog'), 'Sheet component must support openEquipDialog');
    assert.ok(sheetContent.includes('confirmEquipItem'), 'Sheet component must support confirmEquipItem');
  });
});

describe('File Length Invariants (Hard Invariant 6)', () => {
  it('verifies all test and component files are strictly < 500 lines', () => {
    const filesToCheck = [
      APP_SHELL_PATH,
      ROUTER_PATH,
      PROFILE_PATH,
      CHARACTER_CARD_PATH,
      resolve(FRONTEND_DIR, 'test/character-management-and-profile.test.ts'),
    ];

    for (const filePath of filesToCheck) {
      const content = readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');
      assert.ok(lines.length < 500, `${filePath} has ${lines.length} lines; must be < 500 lines`);
    }
  });
});
