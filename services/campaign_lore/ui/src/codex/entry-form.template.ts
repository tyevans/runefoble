import { html, type TemplateResult } from 'lit';

export type CodexPrivacy = 'private' | 'party_shared' | 'public';

export interface CodexEntryDraft {
  title: string;
  content: string;
  privacy: CodexPrivacy;
}

export const EMPTY_ENTRY_DRAFT: CodexEntryDraft = { title: '', content: '', privacy: 'party_shared' };

/** Returns the entry to publish, or null when the title or the content is blank. */
export function buildEntryDetail(draft: CodexEntryDraft): CodexEntryDraft | null {
  const title = draft.title.trim();
  const content = draft.content.trim();
  if (!title || !content) return null;
  return { title, content, privacy: draft.privacy };
}

export interface EntryFormProps {
  draft: CodexEntryDraft;
  onChange: (patch: Partial<CodexEntryDraft>) => void;
  onSubmit: (e: SubmitEvent) => void;
}

/** The form that publishes a new codex entry. */
export function renderEntryForm(props: EntryFormProps): TemplateResult {
  const { draft, onChange } = props;
  return html`<form class="entry-form" aria-label="New codex entry" @submit=${props.onSubmit}>
    <label for="entry-title">Entry title</label>
    <input id="entry-title" name="title" type="text" required .value=${draft.title}
      @input=${(e: Event) => onChange({ title: (e.target as HTMLInputElement).value })} />
    <label for="entry-content">Entry text</label>
    <textarea id="entry-content" name="content" required .value=${draft.content}
      @input=${(e: Event) => onChange({ content: (e.target as HTMLTextAreaElement).value })}></textarea>
    <label for="entry-privacy">Visibility</label>
    <select id="entry-privacy" name="privacy"
      @change=${(e: Event) => onChange({ privacy: (e.target as HTMLSelectElement).value as CodexPrivacy })}>
      <option value="party_shared" ?selected=${draft.privacy === 'party_shared'}>Party shared</option>
      <option value="private" ?selected=${draft.privacy === 'private'}>Private</option>
      <option value="public" ?selected=${draft.privacy === 'public'}>Public</option>
    </select>
    <button type="submit" class="search-btn">Publish entry</button>
  </form>`;
}

/** The refusal message of the last entry write. Renders nothing when there is no error. */
export function renderEntryError(message: string): TemplateResult | string {
  return message ? html`<div class="entry-error" role="alert">${message}</div>` : '';
}
