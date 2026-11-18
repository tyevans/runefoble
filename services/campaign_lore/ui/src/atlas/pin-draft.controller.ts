import { html, type ReactiveController, type ReactiveControllerHost, type TemplateResult } from 'lit';
import { renderPinError, renderPinForm } from './pin-form.template.ts';

export interface PinDraft {
  title: string;
  coordinates: { x: number; y: number };
}

/**
 * Holds the new-pin draft that opens after a click on an empty canvas location.
 * Submitting hands the draft to `onSubmit` and closes the form. A refused write is shown by
 * the host through `render(error)`.
 */
export class PinDraftController implements ReactiveController {
  private draft: PinDraft | null = null;

  private readonly host: ReactiveControllerHost;
  private readonly onSubmit: (draft: PinDraft) => void;

  constructor(host: ReactiveControllerHost, onSubmit: (draft: PinDraft) => void) {
    this.host = host;
    this.onSubmit = onSubmit;
    host.addController(this);
  }

  hostDisconnected(): void {
    this.draft = null;
  }

  open(coordinates: { x: number; y: number }): void {
    this.draft = { title: '', coordinates };
    this.host.requestUpdate();
  }

  render(error: string): TemplateResult {
    const draft = this.draft;
    return html`${renderPinError(error)}${draft
      ? renderPinForm({
        title: draft.title,
        onInput: (title) => this.setTitle(title),
        onSubmit: (e) => this.submit(e),
        onCancel: () => this.close(),
      })
      : ''}`;
  }

  private setTitle(title: string): void {
    if (this.draft) this.draft = { ...this.draft, title };
  }

  private submit(e: SubmitEvent): void {
    e.preventDefault();
    const title = this.draft?.title.trim();
    if (!this.draft || !title) return;
    const submitted: PinDraft = { title, coordinates: this.draft.coordinates };
    this.close();
    this.onSubmit(submitted);
  }

  private close(): void {
    this.draft = null;
    this.host.requestUpdate();
  }
}
