import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-caravan-board.ts';
import type { CaravanContractItem } from './runefoble-caravan-board.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleCaravanBoard',
  component: 'runefoble-caravan-board',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleContracts: CaravanContractItem[] = [
  {
    contract_id: 'contract-ironford-01',
    origin_outpost: 'Bastion Cross',
    destination_outpost: 'Ironford',
    cargo: { iron_ingots: 40, timber: 20 },
    cargo_value: 300,
    route_risk_level: 'medium',
    transit_stages: 3,
    current_stage: 1,
    escort_collateral: 50,
    reward_gold: 150,
    reward_reputation: 15,
    status: 'open',
  },
  {
    contract_id: 'contract-shadowfen-02',
    origin_outpost: 'Ironford',
    destination_outpost: 'Shadowfen',
    cargo: { medicinal_herbs: 30, alchemical_salts: 15 },
    cargo_value: 500,
    route_risk_level: 'high',
    transit_stages: 3,
    current_stage: 2,
    escort_collateral: 100,
    reward_gold: 350,
    reward_reputation: 30,
    status: 'in_transit',
    contractor_party_name: 'The Sunken Wolves',
    ambush_history: [
      {
        stage_index: 1,
        ambush_type: 'Goblin Archers',
        danger_level: 2,
        outcome: 'repelled',
        cargo_loss_percentage: 0,
        notes: 'Bandits routed at the river crossing.',
      },
    ],
  },
  {
    contract_id: 'contract-highland-03',
    origin_outpost: 'Shadowfen',
    destination_outpost: 'Highland Keep',
    cargo: { adamantine_ore: 10, refined_reagents: 25 },
    cargo_value: 1200,
    route_risk_level: 'deadly',
    transit_stages: 4,
    current_stage: 3,
    escort_collateral: 250,
    reward_gold: 800,
    reward_reputation: 75,
    status: 'in_transit',
    contractor_party_name: 'The Dawn Vanguard',
    ambush_history: [
      {
        stage_index: 2,
        ambush_type: 'Mountain Trolls',
        danger_level: 4,
        outcome: 'cargo_damaged',
        cargo_loss_percentage: 0.15,
        notes: 'Supply wagon wagon damaged during rockslide attack.',
      },
    ],
  },
  {
    contract_id: 'contract-bastion-04',
    origin_outpost: 'Highland Keep',
    destination_outpost: 'Bastion Cross',
    cargo: { star_metal: 5, ancient_runestones: 2 },
    cargo_value: 1800,
    route_risk_level: 'deadly',
    transit_stages: 4,
    current_stage: 4,
    escort_collateral: 300,
    reward_gold: 1100,
    reward_reputation: 100,
    status: 'fulfilled',
    contractor_party_name: 'The Dawn Vanguard',
  },
];

export const DefaultNoticeBoard: Story = {
  render: () => html`
    <runefoble-caravan-board
      shared-world-id="world-sunken-marches"
      campaign-id="camp-amber-vanguard"
      party-name="The Amber Vanguard"
      user-role="player"
      .contracts=${sampleContracts}
      selectedContractId="contract-ironford-01"
    ></runefoble-caravan-board>
  `,
};

export const ActiveCaravanTransit: Story = {
  render: () => html`
    <runefoble-caravan-board
      shared-world-id="world-sunken-marches"
      campaign-id="camp-amber-vanguard"
      party-name="The Sunken Wolves"
      user-role="player"
      .contracts=${sampleContracts}
      selectedContractId="contract-shadowfen-02"
    ></runefoble-caravan-board>
  `,
};

export const AmbushWarningAlert: Story = {
  render: () => html`
    <runefoble-caravan-board
      shared-world-id="world-sunken-marches"
      campaign-id="camp-dawn-vanguard"
      party-name="The Dawn Vanguard"
      user-role="player"
      .contracts=${sampleContracts}
      selectedContractId="contract-highland-03"
    ></runefoble-caravan-board>
  `,
};

export const CaravanManifestModalOpen: Story = {
  render: () => html`
    <runefoble-caravan-board
      shared-world-id="world-sunken-marches"
      campaign-id="camp-amber-vanguard"
      party-name="The Amber Vanguard"
      user-role="player"
      .contracts=${sampleContracts}
      selectedContractId="contract-highland-03"
      is-modal-open
    ></runefoble-caravan-board>
  `,
};

export const GuildOfficerManagement: Story = {
  render: () => html`
    <runefoble-caravan-board
      shared-world-id="world-sunken-marches"
      campaign-id="camp-guild-command"
      party-name="Frontier Trade Guild"
      user-role="guild_officer"
      .contracts=${sampleContracts}
      selectedContractId="contract-ironford-01"
    ></runefoble-caravan-board>
  `,
};

export const ContractPayoutFulfilled: Story = {
  render: () => html`
    <runefoble-caravan-board
      shared-world-id="world-sunken-marches"
      campaign-id="camp-dawn-vanguard"
      party-name="The Dawn Vanguard"
      user-role="player"
      .contracts=${sampleContracts}
      selectedContractId="contract-bastion-04"
      is-modal-open
    ></runefoble-caravan-board>
  `,
};
