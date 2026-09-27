import type { Meta, StoryObj } from '@storybook/web-components';
import { html } from 'lit';
import './runefoble-faction-espionage.ts';
import type { EspionageAlert, InterceptedDispatch, RegionalAlert } from './runefoble-faction-espionage.ts';

const meta: Meta = {
  title: 'TTRPG/RunefobleFactionEspionage',
  component: 'runefoble-faction-espionage',
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj;

const sampleAlerts: EspionageAlert[] = [
  {
    id: 'alt-01',
    faction_id: 'ironfang_syndicate',
    faction_name: 'Ironfang Syndicate',
    severity: 'critical',
    title: 'Smuggling Network Mobilization',
    summary: 'Black-market weapons convoy departed the eastern docks under cover of magical fog.',
    region: 'Oakhaven Docks',
    timestamp: '14:22 UTC',
  },
  {
    id: 'alt-02',
    faction_id: 'arcane_order',
    faction_name: 'Arcane Order',
    severity: 'high',
    title: 'Reliquary Infiltration Detected',
    summary: 'Runic surveillance wards breached on the third sub-level of the High Spire vault.',
    region: 'High Spire Towers',
    timestamp: '15:05 UTC',
  },
  {
    id: 'alt-03',
    faction_id: 'silver_flame',
    faction_name: 'Silver Flame Knights',
    severity: 'medium',
    title: 'Sentry Reassignment Order',
    summary: 'Two dozen veteran paladins shifted to outer wall barricades following unrest rumors.',
    region: 'Upper Citadel',
    timestamp: '16:10 UTC',
  },
];

const sampleIntercepts: InterceptedDispatch[] = [
  {
    id: 'dsp-01',
    sender_faction: 'Ironfang Syndicate',
    target_recipient: 'Corrupt Harbor Master',
    region: 'Oakhaven Docks',
    intercept_status: 'compromised',
    message_snippet: 'Shipment 7 arrived. Ensure night watch looks away when red lantern is lit.',
    timestamp: '13:45 UTC',
  },
  {
    id: 'dsp-02',
    sender_faction: 'Shadow Cabal',
    target_recipient: 'Under-Crypt Emissary',
    region: 'Sunken Catacombs',
    intercept_status: 'decrypted',
    message_snippet: 'The ritual seal weakens. Delay the adventurers until blood moon ascendance.',
    timestamp: '14:50 UTC',
  },
];

const sampleRegions: RegionalAlert[] = [
  { region_id: 'reg-01', region_name: 'Oakhaven Docks', alert_level: 'lockdown', unrest_score: 82 },
  { region_id: 'reg-02', region_name: 'High Spire Towers', alert_level: 'high', unrest_score: 65 },
  { region_id: 'reg-03', region_name: 'Upper Citadel', alert_level: 'elevated', unrest_score: 42 },
];

export const Default: Story = {
  render: () => html`
    <runefoble-faction-espionage
      campaignId="camp-101"
      .alerts=${sampleAlerts}
      .intercepts=${sampleIntercepts}
      .regionalAlerts=${sampleRegions}
    ></runefoble-faction-espionage>
  `,
};

export const HighUrgencyAlerts: Story = {
  render: () => html`
    <runefoble-faction-espionage
      campaignId="camp-101"
      filterSeverity="critical"
      .alerts=${sampleAlerts}
      .regionalAlerts=${sampleRegions}
    ></runefoble-faction-espionage>
  `,
};

export const InterceptedDispatches: Story = {
  render: () => html`
    <runefoble-faction-espionage
      campaignId="camp-101"
      selectedId="dsp-01"
      .intercepts=${sampleIntercepts}
    ></runefoble-faction-espionage>
  `,
};

export const EmptyState: Story = {
  render: () => html`
    <runefoble-faction-espionage campaignId="camp-empty"></runefoble-faction-espionage>
  `,
};

export const DMPrivateBriefing: Story = {
  render: () => html`
    <runefoble-faction-espionage
      campaignId="camp-101"
      isDm
      selectedId="alt-01"
      .alerts=${sampleAlerts}
      .intercepts=${sampleIntercepts}
      .regionalAlerts=${sampleRegions}
    ></runefoble-faction-espionage>
  `,
};
