import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { standInGuardrailsStyles } from './runefoble-stand-in-guardrails.styles.ts';
import {
  renderActionsBar,
  renderAllyProtectionTags,
  renderCustomPriorityChips,
  renderHeader,
  renderPostureSelector,
  renderSpellSlotPreservation,
} from './runefoble-stand-in-guardrails.templates.ts';

@customElement('runefoble-stand-in-guardrails')
export class RunefobleStandInGuardrails extends LitElement {
  static styles = [standInGuardrailsStyles];

  @property({ type: String }) characterId = '';
  @property({ type: String }) characterName = '';
  @property({ type: Object }) preserveSpellSlots: Record<number, number> = { 3: 1 };
  @property({ type: Array }) protectAllies: string[] = ['Marcus'];
  @property({ type: Number }) protectAllyHpThreshold = 0.3;
  @property({ type: String }) riskThreshold: 'cautious' | 'balanced' | 'reckless' = 'cautious';
  @property({ type: Boolean }) avoidMelee = true;
  @property({ type: Boolean }) permadeathSafeguard = true;
  @property({ type: Array }) customPriorities: string[] = [
    'Save Level 3 slots for Revivify',
    'Prioritize healing Marcus if under 30% HP',
    'Avoid frontline melee',
  ];

  @state() newAllyInput = '';
  @state() newPriorityInput = '';
  @state() saveStatus = '';

  addAlly() {
    if (this.newAllyInput.trim()) {
      this.protectAllies = [...this.protectAllies, this.newAllyInput.trim()];
      this.newAllyInput = '';
    }
  }

  removeAlly(index: number) {
    this.protectAllies = this.protectAllies.filter((_, i) => i !== index);
  }

  addPriority() {
    if (this.newPriorityInput.trim()) {
      this.customPriorities = [...this.customPriorities, this.newPriorityInput.trim()];
      this.newPriorityInput = '';
    }
  }

  removePriority(index: number) {
    this.customPriorities = this.customPriorities.filter((_, i) => i !== index);
  }

  handleSave() {
    const detail = {
      characterId: this.characterId,
      preserve_spell_slots: this.preserveSpellSlots,
      protect_allies: this.protectAllies,
      protect_ally_hp_threshold: this.protectAllyHpThreshold,
      risk_threshold: this.riskThreshold,
      avoid_melee: this.avoidMelee,
      permadeath_safeguard: this.permadeathSafeguard,
      custom_priorities: this.customPriorities,
    };
    this.dispatchEvent(
      new CustomEvent('guardrails-saved', { detail, bubbles: true, composed: true })
    );
    this.dispatchEvent(
      new CustomEvent('guardrails-updated', { detail, bubbles: true, composed: true })
    );
    this.saveStatus = 'Tactical Guardrails Saved!';
    setTimeout(() => {
      this.saveStatus = '';
    }, 3000);
  }

  handleHotSwap() {
    const detail = { characterId: this.characterId };
    this.dispatchEvent(
      new CustomEvent('hot-swap-requested', { detail, bubbles: true, composed: true })
    );
    this.dispatchEvent(
      new CustomEvent('request-hot-swap', { detail, bubbles: true, composed: true })
    );
  }

  render() {
    return html`
      ${renderHeader(this)}
      ${renderSpellSlotPreservation(this)}
      ${renderAllyProtectionTags(this)}
      ${renderPostureSelector(this)}
      ${renderCustomPriorityChips(this)}
      ${renderActionsBar(this)}
    `;
  }
}

declare global {
  interface HTMLElementTagNameMap {
    'runefoble-stand-in-guardrails': RunefobleStandInGuardrails;
  }
}
