import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-autonomous-dm.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleAutonomousDM',
  component: 'runefoble-autonomous-dm',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

export const CryptAmbush: Story = {
  render: () => html`
    <runefoble-autonomous-dm
      locationName="Crypt of the Restless Kings"
      lighting="pale cold luminescence from weeping wall moss"
      mood="suspenseful"
      description="Ancient stone sarcophagi line the moss-covered walls. A bone-chilling draft stirs dry funerary shrouds, accompanied by the faint scraping of granite against granite."
      ambientAudioPrompt="eerie crypt silence, faint mournful wind, scratching behind stone tombs"
      encounterName="Crypt Guardian Vanguard"
      threatLevel="hard"
      tacticalObjective="Defeat the Bugbear Chieftain before the archers pin the frontline down."
      .monsters=${[
        { id: 'c-1', name: 'Bugbear Chieftain', cr: '3', hp: 65, max_hp: 65, ac: 17, role: 'bruiser' },
        { id: 'c-2', name: 'Skeleton Archer Alpha', cr: '1/4', hp: 13, max_hp: 13, ac: 13, role: 'ranged' },
        { id: 'c-3', name: 'Skeleton Archer Beta', cr: '1/4', hp: 13, max_hp: 13, ac: 13, role: 'ranged' },
      ]}
      .lastAction=${{
        actor_name: 'Bugbear Chieftain',
        action_type: 'charge_attack',
        target_name: 'Valeros',
        narrative: 'Bugbear Chieftain breaks from cover in an aggressive charge, slamming their morningstar toward Valeros for 6 damage!',
        hp_impact: -6,
      }}
    ></runefoble-autonomous-dm>
  `,
};

export const SuspensefulTavern: Story = {
  render: () => html`
    <runefoble-autonomous-dm
      locationName="The Wayward Drake Inn"
      lighting="warm hearth glow interspersed with flickering tallow candles"
      mood="suspenseful"
      description="Heavy oak beams creak overhead as roasted meat scents mingle with uneasy murmurs among cloaked patrons keeping one hand on their hilts."
      ambientAudioPrompt="busy medieval tavern background noise, clinking flagons, muffled hearth fire crackle"
      encounterName="Tavern Brawl Skirmish"
      threatLevel="medium"
      tacticalObjective="Disarm the instigators without causing collateral tavern damage."
      .monsters=${[
        { id: 't-1', name: 'Ruffian Leader', cr: '1', hp: 25, max_hp: 25, ac: 14, role: 'boss' },
        { id: 't-2', name: 'Drunken Brawler', cr: '1/2', hp: 16, max_hp: 16, ac: 11, role: 'skirmisher' },
      ]}
    ></runefoble-autonomous-dm>
  `,
};

export const DragonLair: Story = {
  render: () => html`
    <runefoble-autonomous-dm
      locationName="Scorched Crag of the Wyrm"
      lighting="smoldering magma fissures casting an intense crimson gleam"
      mood="deadly"
      description="Charred dragon scales and calcified bones crunch underfoot. The acrid stench of sulfur hangs thick, punctuated by the cavernous exhalations of a slumbering terror."
      ambientAudioPrompt="volcanic cave rumble, magma bubbling, distant low reptile breathing, crackling ember heat"
      encounterName="Infernal Drake Reckoning"
      threatLevel="deadly"
      tacticalObjective="Sever the drake's fire breath rhythm by disrupting its grounding stance."
      .monsters=${[
        { id: 'd-1', name: 'Young Red Dragon', cr: '10', hp: 178, max_hp: 178, ac: 18, role: 'boss' },
        { id: 'd-2', name: 'Fire Cultist Zealot', cr: '2', hp: 45, max_hp: 45, ac: 15, role: 'caster' },
      ]}
      .lastAction=${{
        actor_name: 'Fire Cultist Zealot',
        action_type: 'cast_spell',
        target_name: 'Kyra',
        narrative: 'Fire Cultist Zealot channels forbidden incantations, unleashing Fire Bolt directly into Kyra for 8 fire damage!',
        hp_impact: -8,
      }}
    ></runefoble-autonomous-dm>
  `,
};
