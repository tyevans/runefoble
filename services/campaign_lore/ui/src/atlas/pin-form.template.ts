import { html, type TemplateResult } from 'lit';

export interface PinFormProps {
  title: string;
  onInput: (value: string) => void;
  onSubmit: (e: SubmitEvent) => void;
  onCancel: () => void;
}

/** The new-pin form that opens after a click on an empty canvas location. */
export function renderPinForm(props: PinFormProps): TemplateResult {
  return html`<form class="pin-form" aria-label="New milestone pin" @submit=${props.onSubmit}>
    <label for="pin-title">Pin title</label>
    <input id="pin-title" name="title" type="text" required .value=${props.title}
      @input=${(e: Event) => props.onInput((e.target as HTMLInputElement).value)} />
    <button type="submit" class="btn">Place pin</button>
    <button type="button" class="btn" @click=${props.onCancel}>Cancel</button>
  </form>`;
}

/** The refusal message of the last pin write. Renders nothing when there is no error. */
export function renderPinError(message: string): TemplateResult | string {
  return message ? html`<div class="pin-error" role="alert">${message}</div>` : '';
}
