/**
 * Lit Web Component: <runefoble-chronicle-timeline>
 * Governed by ADR-0004, ADR-0007, ADR-0011, and ADR-0013.
 */

import { LitElement, html } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { chronicleTimelineStyles } from './runefoble-chronicle-timeline.styles.ts';
import type { CampaignTimelineResponse, TimelineMilestone } from './types.ts';

@customElement('runefoble-chronicle-timeline')
export class RunefobleChronicleTimeline extends LitElement {
  static styles = [chronicleTimelineStyles];

  @property({ type: Object }) timelineData: CampaignTimelineResponse | null = null;
  @property({ type: Number }) activeIndex = 0;

  @state() private playingAudioId: string | null = null;
  @state() private isAutoScrubbing = false;
  private autoScrubInterval: number | null = null;

  disconnectedCallback() {
    super.disconnectedCallback();
    this.stopAutoScrub();
  }

  private get milestones(): TimelineMilestone[] {
    return this.timelineData?.milestones || [];
  }

  private selectMilestone(index: number) {
    if (index < 0 || index >= this.milestones.length) return;
    this.activeIndex = index;
    const milestone = this.milestones[index];
    this.dispatchEvent(
      new CustomEvent('milestone-selected', {
        detail: { index, milestone },
        bubbles: true,
        composed: true,
      })
    );
  }

  private handleSliderChange(e: Event) {
    const target = e.target as HTMLInputElement;
    const index = parseInt(target.value, 10);
    this.selectMilestone(index);
  }

  private handlePrev() {
    if (this.activeIndex > 0) {
      this.selectMilestone(this.activeIndex - 1);
    }
  }

  private handleNext() {
    if (this.activeIndex < this.milestones.length - 1) {
      this.selectMilestone(this.activeIndex + 1);
    }
  }

  private toggleAutoScrub() {
    if (this.isAutoScrubbing) {
      this.stopAutoScrub();
    } else {
      this.startAutoScrub();
    }
  }

  private startAutoScrub() {
    this.isAutoScrubbing = true;
    this.autoScrubInterval = window.setInterval(() => {
      if (this.activeIndex < this.milestones.length - 1) {
        this.selectMilestone(this.activeIndex + 1);
      } else {
        this.stopAutoScrub();
      }
    }, 1800);
  }

  private stopAutoScrub() {
    this.isAutoScrubbing = false;
    if (this.autoScrubInterval !== null) {
      clearInterval(this.autoScrubInterval);
      this.autoScrubInterval = null;
    }
  }

  private handlePlayAudio(milestone: TimelineMilestone, e: Event) {
    e.stopPropagation();
    if (this.playingAudioId === milestone.id) {
      this.playingAudioId = null;
    } else {
      this.playingAudioId = milestone.id;
      this.dispatchEvent(
        new CustomEvent('play-audio-recap', {
          detail: {
            milestoneId: milestone.id,
            title: milestone.title,
            audioUrl: milestone.metadata?.audio_url || null,
          },
          bubbles: true,
          composed: true,
        })
      );
    }
  }

  render() {
    const list = this.milestones;
    const total = list.length;
    const current = list[this.activeIndex] || null;
    const currentRound = current?.metadata?.round ?? this.activeIndex + 1;

    return html`
      <div class="timeline-header">
        <div class="timeline-title">
          <span>Living Chronicle Timeline</span>
        </div>
      </div>

      <div class="scrubber-panel">
        <div class="scrubber-controls">
          <button
            class="scrub-btn"
            @click=${this.handlePrev}
            ?disabled=${this.activeIndex <= 0}
            title="Previous milestone"
          >
            ◀
          </button>
          <button
            class="scrub-btn"
            @click=${this.toggleAutoScrub}
            title=${this.isAutoScrubbing ? 'Pause timeline' : 'Auto-scrub timeline'}
          >
            ${this.isAutoScrubbing ? '⏸ Pause' : '▶ Play'}
          </button>
          <button
            class="scrub-btn"
            @click=${this.handleNext}
            ?disabled=${this.activeIndex >= total - 1}
            title="Next milestone"
          >
            ▶
          </button>
          <input
            type="range"
            class="scrubber-slider"
            min="0"
            max="${Math.max(total - 1, 0)}"
            .value="${String(this.activeIndex)}"
            @input=${this.handleSliderChange}
            ?disabled=${total === 0}
          />
        </div>
        <div class="scrubber-info">
          <span>Index: ${total > 0 ? this.activeIndex + 1 : 0} of ${total}</span>
          <span>${current ? `Round: ${currentRound} | ${current.title}` : 'No milestones'}</span>
        </div>
      </div>

      <div class="milestones-container">
        ${list.length === 0
          ? html`<div style="font-size: 0.85rem; color: #777;">No chronicle milestones recorded yet.</div>`
          : list.map(
              (m, idx) => html`
                <div
                  class="milestone-card ${idx === this.activeIndex ? 'selected' : ''}"
                  @click=${() => this.selectMilestone(idx)}
                >
                  <div class="milestone-top">
                    <span class="badge-category ${m.type}">${m.type.replace('_', ' ')}</span>
                    <span class="badge-timestamp">${m.timestamp}</span>
                  </div>
                  <div class="milestone-title">${m.title}</div>
                  <div class="milestone-desc">${m.description}</div>
                  <div class="audio-action-row">
                    <button
                      class="audio-btn ${this.playingAudioId === m.id ? 'playing' : ''}"
                      @click=${(e: Event) => this.handlePlayAudio(m, e)}
                    >
                      ${this.playingAudioId === m.id
                        ? html`
                            <span class="audio-waves">
                              <span class="audio-bar"></span>
                              <span class="audio-bar"></span>
                              <span class="audio-bar"></span>
                            </span>
                            Stop
                          `
                        : html`▶ Audio Recap`}
                    </button>
                  </div>
                </div>
              `
            )}
      </div>
    `;
  }
}
