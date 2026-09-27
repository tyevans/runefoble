// --- Runefoble Project Content Visualizer: Markdown Renderer ---
(function() {
  window.visualizer = window.visualizer || {};

  function escapeHtml(str) {
    return (str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatInline(text) {
    if (!text) return '';

    // 1. Preserve and protect inline code tokens before processing inline typography
    const codeTokens = [];
    text = text.replace(/`([^`]+)`/g, (_, code) => {
      const idx = codeTokens.length;
      codeTokens.push(
        `<code class="px-1.5 py-0.5 rounded bg-slate-800 text-indigo-300 font-mono text-[11px] border border-slate-700">${code}</code>`
      );
      return `%%CODE${idx}%%`;
    });

    // 2. Links: [text](url)
    text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, label, url) => {
      const cleanUrl = url.trim();
      return `<a href="${cleanUrl}" target="_blank" rel="noopener noreferrer" class="text-indigo-400 hover:text-indigo-300 underline font-medium">${label}</a>`;
    });

    // 3. Autolinks: http:// or https://
    text = text.replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g, (_, prefix, url) => {
      return `${prefix}<a href="${url}" target="_blank" rel="noopener noreferrer" class="text-indigo-400 hover:text-indigo-300 underline font-medium">${url}</a>`;
    });

    // 4. Bold + Italic: ***text*** or ___text___
    text = text.replace(/(\*\*\*|___)(.*?)\1/g, '<strong class="font-bold text-white"><em>$2</em></strong>');

    // 5. Bold: **text** or __text__
    text = text.replace(/(\*\*|__)(.*?)\1/g, '<strong class="font-semibold text-white">$2</strong>');

    // 6. Italic: *text* or _text_
    text = text.replace(/(^|[^*_])(\*|_)([^*_]+?)\2(?=[^*_]|$)/g, '$1<em class="italic text-slate-200">$3</em>');

    // 7. Strikethrough: ~~text~~
    text = text.replace(/~~(.*?)~~/g, '<del class="line-through text-slate-500">$1</del>');

    // 8. Restore protected inline code tokens
    codeTokens.forEach((token, idx) => {
      text = text.replace(`%%CODE${idx}%%`, token);
    });

    return text;
  }

  function renderMarkdown(rawMd) {
    if (!rawMd) return '';

    const lines = rawMd.split(/\r?\n/);
    const blocks = [];
    let i = 0;

    while (i < lines.length) {
      const rawLine = lines[i];

      // Skip empty lines
      if (!rawLine.trim()) {
        i++;
        continue;
      }

      // Fenced code block (```lang ... ```)
      if (rawLine.trim().startsWith('```')) {
        const langMatch = rawLine.trim().match(/^```(\w+)?/);
        const lang = langMatch && langMatch[1] ? langMatch[1] : '';
        const codeLines = [];
        i++;
        while (i < lines.length && !lines[i].trim().startsWith('```')) {
          codeLines.push(escapeHtml(lines[i]));
          i++;
        }
        i++; // skip closing ```
        const langBadge = lang
          ? `<div class="text-[10px] font-mono text-muted uppercase tracking-wider mb-1.5 pb-1 border-b border-slate-800">${lang}</div>`
          : '';
        blocks.push(
          `<pre class="bg-black/50 border border-slate-700/60 p-3 rounded-xl overflow-x-auto text-[11px] font-mono text-emerald-400 my-2.5">${langBadge}<code>${codeLines.join('\n')}</code></pre>`
        );
        continue;
      }

      // Horizontal rule (---, ***, ___)
      if (rawLine.trim().match(/^(\*{3,}|-{3,}|_{3,})$/)) {
        blocks.push('<hr class="border-subtle my-3">');
        i++;
        continue;
      }

      // Headings (# Heading ... ###### Heading)
      const headingMatch = rawLine.match(/^(#{1,6})\s+(.*)$/);
      if (headingMatch) {
        const level = headingMatch[1].length;
        const text = formatInline(escapeHtml(headingMatch[2].trim()));
        const hClass = level <= 3
          ? 'text-sm font-bold text-white mt-3.5 mb-1.5'
          : 'text-xs font-bold text-slate-200 uppercase tracking-wider mt-3 mb-1';
        const tag = `h${Math.min(level + 2, 6)}`;
        blocks.push(`<${tag} class="${hClass}">${text}</${tag}>`);
        i++;
        continue;
      }

      // Blockquote (> line ...)
      if (rawLine.trim().startsWith('>')) {
        const quoteLines = [];
        while (i < lines.length && lines[i].trim().startsWith('>')) {
          quoteLines.push(escapeHtml(lines[i].trim().replace(/^>\s*/, '')));
          i++;
        }
        blocks.push(
          `<blockquote class="border-l-4 border-indigo-500/60 bg-[var(--bg-elevated)] p-3 rounded-r-xl my-2.5 text-xs text-slate-300 italic">${formatInline(quoteLines.join(' '))}</blockquote>`
        );
        continue;
      }

      // Markdown Table (| col | col | ... |---|---|...)
      if (
        rawLine.trim().startsWith('|') &&
        rawLine.trim().endsWith('|') &&
        i + 1 < lines.length &&
        lines[i + 1].trim().match(/^\|(\s*:?-+:?\s*\|)+$/)
      ) {
        const headerCells = rawLine
          .split('|')
          .slice(1, -1)
          .map(c => formatInline(escapeHtml(c.trim())));
        i += 2; // Skip header and separator rows

        const rowList = [];
        while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
          const cells = lines[i]
            .split('|')
            .slice(1, -1)
            .map(c => formatInline(escapeHtml(c.trim())));
          rowList.push(cells);
          i++;
        }

        let tableHtml = '<div class="overflow-x-auto my-3"><table class="min-w-full text-xs text-left border border-subtle rounded-lg overflow-hidden">';
        tableHtml += '<thead class="bg-[var(--bg-elevated)] text-white font-semibold border-b border-subtle"><tr>';
        headerCells.forEach(hc => {
          tableHtml += `<th class="px-3 py-2 border-r border-subtle last:border-r-0">${hc}</th>`;
        });
        tableHtml += '</tr></thead><tbody class="divide-y divide-subtle">';
        rowList.forEach(row => {
          tableHtml += '<tr class="hover:bg-[var(--bg-elevated)]/50 transition">';
          row.forEach(rc => {
            tableHtml += `<td class="px-3 py-2 border-r border-subtle last:border-r-0 text-slate-300">${rc}</td>`;
          });
          tableHtml += '</tr>';
        });
        tableHtml += '</tbody></table></div>';
        blocks.push(tableHtml);
        continue;
      }

      // List Items (Ordered: 1. ... or Unordered: - ... / * ...)
      const listMatch = rawLine.match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
      if (listMatch) {
        const listItems = [];
        while (i < lines.length) {
          const curLine = lines[i];
          if (!curLine.trim()) {
            // Check lookahead: is the subsequent line a list item?
            if (i + 1 < lines.length && lines[i + 1].match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/)) {
              i++;
              continue;
            }
            break;
          }
          const m = curLine.match(/^(\s*)([-*+]|\d+\.)\s+(.*)$/);
          if (m) {
            const indent = m[1].replace(/\t/g, '  ').length;
            const isOrdered = /^\d+\./.test(m[2]);
            let itemText = m[3];

            // Interactive-styled read-only checkboxes: [ ] or [x]
            if (itemText.startsWith('[ ] ')) {
              itemText = '<input type="checkbox" disabled class="mr-1.5 rounded opacity-60"> ' + itemText.slice(4);
            } else if (itemText.startsWith('[x] ') || itemText.startsWith('[X] ')) {
              itemText = '<input type="checkbox" checked disabled class="mr-1.5 rounded text-emerald-400"> ' + itemText.slice(4);
            }

            listItems.push({ indent, isOrdered, text: itemText });
            i++;
          } else if (curLine.match(/^\s{2,}/) && listItems.length > 0) {
            // Multi-line continuation of preceding item
            listItems[listItems.length - 1].text += ' ' + curLine.trim();
            i++;
          } else {
            break;
          }
        }

        // Recursive tree builder for nested lists
        function renderListTree(items, startIndex, baseIndent) {
          let res = '';
          let j = startIndex;
          const currentType = items[j].isOrdered ? 'ol' : 'ul';
          const listTag = currentType;
          const listClass = currentType === 'ol'
            ? 'list-decimal list-outside pl-5 space-y-1.5 my-2.5 text-xs text-slate-300'
            : 'list-disc list-outside pl-5 space-y-1.5 my-2.5 text-xs text-slate-300';

          res += `<${listTag} class="${listClass}">`;
          while (j < items.length) {
            const item = items[j];
            if (item.indent < baseIndent) {
              break;
            }
            if (item.indent > baseIndent) {
              break;
            }

            let itemHtml = formatInline(escapeHtml(item.text));
            j++;

            // If next item has greater indentation, render as nested sublist
            if (j < items.length && items[j].indent > baseIndent) {
              const childIndent = items[j].indent;
              const sublistHtml = renderListTree(items, j, childIndent);
              itemHtml += sublistHtml.html;
              j = sublistHtml.nextIndex;
            }

            res += `<li class="leading-relaxed">${itemHtml}</li>`;
          }
          res += `</${listTag}>`;
          return { html: res, nextIndex: j };
        }

        const listResult = renderListTree(listItems, 0, listItems[0].indent);
        blocks.push(listResult.html);
        continue;
      }

      // Paragraph (group consecutive non-block lines)
      const paraLines = [];
      while (
        i < lines.length &&
        lines[i].trim() &&
        !lines[i].match(/^(#{1,6}\s+|```|>|\||(\*{3,}|-{3,}|_{3,})$|(\s*)([-*+]|\d+\.)\s+)/)
      ) {
        paraLines.push(lines[i].trim());
        i++;
      }
      if (paraLines.length > 0) {
        blocks.push(`<p class="my-2.5 leading-relaxed text-xs text-slate-300">${formatInline(escapeHtml(paraLines.join(' ')))}</p>`);
      }
    }

    return blocks.join('\n');
  }

  function renderInlineMarkdown(rawText) {
    if (!rawText) return '';
    const normalized = rawText.replace(/\r?\n+/g, ' ').trim();
    return formatInline(escapeHtml(normalized));
  }

  window.visualizer.renderMarkdown = renderMarkdown;
  window.visualizer.renderInlineMarkdown = renderInlineMarkdown;
  window.visualizer.formatInline = formatInline;
})();
