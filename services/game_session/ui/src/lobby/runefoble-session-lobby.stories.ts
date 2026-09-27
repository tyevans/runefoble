import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-session-lobby.ts';
import type { LobbyParticipant, LobbyCharacterOption } from './types.ts';

const meta: Meta = {
  title: 'GameSession/SessionLobby',
  component: 'runefoble-session-lobby',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleCharacters: LobbyCharacterOption[] = [
  {
    id: 'char-valeros-1',
    name: 'Valeros of Korvosa',
    characterClass: 'Fighter',
    level: 4,
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    id: 'char-ezren-2',
    name: 'Ezren the Gray',
    characterClass: 'Wizard',
    level: 5,
    portraitUrl: '/assets/portraits/wizard.svg',
  },
];

const sampleParticipants: LobbyParticipant[] = [
  {
    userId: 'usr-evelyn',
    username: 'Evelyn (GM)',
    role: 'owner',
    onlineStatus: 'online',
    isReady: true,
    isAbsent: false,
    characterName: 'Dungeon Master',
    characterClass: 'Storyteller',
  },
  {
    userId: 'usr-marcus',
    username: 'Marcus Vance',
    role: 'player',
    onlineStatus: 'online',
    isReady: true,
    isAbsent: false,
    characterId: 'char-valeros-1',
    characterName: 'Valeros of Korvosa',
    characterClass: 'Fighter',
    characterLevel: 4,
    portraitUrl: '/assets/portraits/fighter.svg',
  },
  {
    userId: 'usr-lyra',
    username: 'Lyra Moonshadow',
    role: 'player',
    onlineStatus: 'online',
    isReady: true,
    isAbsent: false,
    characterId: 'char-lyra-1',
    characterName: 'Aeloria',
    characterClass: 'Elf Wizard',
    characterLevel: 4,
    portraitUrl: '/assets/portraits/wizard.svg',
  },
];

const participantsWithAbsentee: LobbyParticipant[] = [
  sampleParticipants[0], // Evelyn (GM)
  sampleParticipants[1], // Marcus (Ready)
  {
    userId: 'usr-sarah',
    username: 'Sarah Chen',
    role: 'player',
    onlineStatus: 'offline',
    isReady: false,
    isAbsent: true, // Marked for AI Stand-in
    characterId: 'char-kyra-1',
    characterName: 'Kyra the Cleric',
    characterClass: 'Cleric',
    characterLevel: 4,
    portraitUrl: '/assets/portraits/cleric.svg',
  },
];

const participantsUnready: LobbyParticipant[] = [
  sampleParticipants[0], // Evelyn (GM)
  {
    userId: 'usr-marcus',
    username: 'Marcus Vance',
    role: 'player',
    onlineStatus: 'online',
    isReady: false,
    isAbsent: false,
    characterId: null,
    characterName: null,
  },
  {
    userId: 'usr-lyra',
    username: 'Lyra Moonshadow',
    role: 'player',
    onlineStatus: 'idle',
    isReady: false,
    isAbsent: false,
    characterId: 'char-lyra-1',
    characterName: 'Aeloria',
    characterClass: 'Elf Wizard',
    characterLevel: 4,
  },
];

export const DmViewAllReady: Story = {
  render: () => html`
    <runefoble-session-lobby
      session-id="sess-star-eater-15"
      campaign-id="camp-star-eater"
      session-title="Session 15: Descent into the Sunken Vaults"
      current-user-id="usr-evelyn"
      .isDm=${true}
      .canLaunch=${true}
      .participants=${sampleParticipants}
      .availableCharacters=${sampleCharacters}
    ></runefoble-session-lobby>
  `,
};

export const DmViewWithAbsentStandIn: Story = {
  render: () => html`
    <runefoble-session-lobby
      session-id="sess-star-eater-15"
      campaign-id="camp-star-eater"
      session-title="Session 15: Descent into the Sunken Vaults"
      current-user-id="usr-evelyn"
      .isDm=${true}
      .canLaunch=${true}
      .participants=${participantsWithAbsentee}
      .availableCharacters=${sampleCharacters}
    ></runefoble-session-lobby>
  `,
};

export const PlayerViewUnready: Story = {
  render: () => html`
    <runefoble-session-lobby
      session-id="sess-star-eater-15"
      campaign-id="camp-star-eater"
      session-title="Session 15: Descent into the Sunken Vaults"
      current-user-id="usr-marcus"
      .isDm=${false}
      .canLaunch=${false}
      .participants=${participantsUnready}
      .availableCharacters=${sampleCharacters}
    ></runefoble-session-lobby>
  `,
};

export const PlayerViewReady: Story = {
  render: () => html`
    <runefoble-session-lobby
      session-id="sess-star-eater-15"
      campaign-id="camp-star-eater"
      session-title="Session 15: Descent into the Sunken Vaults"
      current-user-id="usr-marcus"
      .isDm=${false}
      .canLaunch=${false}
      .participants=${sampleParticipants}
      .availableCharacters=${sampleCharacters}
    ></runefoble-session-lobby>
  `,
};

export const EmptyLobby: Story = {
  render: () => html`
    <runefoble-session-lobby
      session-id="sess-new-lobby-1"
      campaign-id="camp-frontier"
      session-title="Frontier Staging Area"
      current-user-id="usr-evelyn"
      .isDm=${true}
      .canLaunch=${true}
      .participants=${[]}
      .availableCharacters=${sampleCharacters}
    ></runefoble-session-lobby>
  `,
};
