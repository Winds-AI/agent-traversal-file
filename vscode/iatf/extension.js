const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
let LanguageClient = null;
let TransportKind = null;

const START_RE = /^\{#([A-Za-z][\w-]{0,63})\}$/;
const END_RE = /^\{\/([A-Za-z][\w-]{0,63})\}$/;

const PALETTE = [
  '#e06c75',
  '#61afef',
  '#98c379',
  '#e5c07b',
  '#c678dd',
  '#56b6c2',
  '#d19a66',
  '#7f848e'
];

const decorationTypes = PALETTE.map((color) =>
  vscode.window.createTextEditorDecorationType({
    color,
    fontWeight: 'bold'
  })
);

let client = null;
const previewPanels = new Map();

function hashId(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i += 1) {
    hash = (hash * 31 + id.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function updateDecorations(editor) {
  if (!editor || editor.document.languageId !== 'iatf') {
    return;
  }

  const rangesByColor = PALETTE.map(() => []);
  const idToColor = new Map();
  let lastAssignedColor = -1;
  const lines = editor.document.getText().split(/\r?\n/);

  for (let lineIndex = 0; lineIndex < lines.length; lineIndex += 1) {
    const line = lines[lineIndex];
    let match = START_RE.exec(line);
    if (!match) {
      match = END_RE.exec(line);
    }
    if (!match) {
      continue;
    }

    const id = match[1];
    let colorIndex = idToColor.get(id);
    if (colorIndex === undefined) {
      colorIndex = hashId(id) % PALETTE.length;
      if (PALETTE.length > 1 && colorIndex === lastAssignedColor) {
        colorIndex = (colorIndex + 1) % PALETTE.length;
      }
      idToColor.set(id, colorIndex);
      lastAssignedColor = colorIndex;
    }
    const range = new vscode.Range(lineIndex, 0, lineIndex, line.length);
    rangesByColor[colorIndex].push(range);
  }

  for (let i = 0; i < decorationTypes.length; i += 1) {
    editor.setDecorations(decorationTypes[i], rangesByColor[i]);
  }
}

function escapeHtml(input) {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function sectionAnchorId(sectionId) {
  return `iatf-sec-${sectionId}`;
}

function cleanupContentLines(lines) {
  const technicalLine = /^\s*(?:@(?:summary|created|modified|hash)\s*:|Hash\s*:|Created\s*:|Modified\s*:)/i;
  const cleaned = lines.filter((line) => !technicalLine.test(line));

  while (cleaned.length > 0 && cleaned[0].trim() === '') {
    cleaned.shift();
  }
  while (cleaned.length > 0 && cleaned[cleaned.length - 1].trim() === '') {
    cleaned.pop();
  }
  return cleaned;
}

function parseIndexMetadataRange(metaRangeText) {
  if (!metaRangeText) {
    return '';
  }
  const compact = metaRangeText.replace(/\s+/g, ' ').trim();
  return compact;
}

function parseIatfForPreview(text) {
  const lines = text.split(/\r?\n/);
  const indexById = new Map();
  const indexOrder = [];
  const contentById = new Map();
  const contentOrder = [];

  let inIndex = false;
  let currentIndexId = null;
  for (const line of lines) {
    if (line.trim() === '===INDEX===') {
      inIndex = true;
      currentIndexId = null;
      continue;
    }
    if (line.trim() === '===CONTENT===') {
      break;
    }
    if (!inIndex) {
      continue;
    }

    const entryMatch = line.match(/^\s*-\s+([A-Za-z][\w-]{0,63})\b(?:\s+\{([^}]*)\})?/);
    if (entryMatch) {
      const id = entryMatch[1];
      if (!indexById.has(id)) {
        indexOrder.push(id);
      }
      indexById.set(id, {
        summary: '',
        rangeMeta: parseIndexMetadataRange(entryMatch[2] || '')
      });
      currentIndexId = id;
      continue;
    }

    if (!currentIndexId || !indexById.has(currentIndexId)) {
      continue;
    }

    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    if (/^(Created|Modified|Hash)\s*:/i.test(trimmed)) {
      continue;
    }

    const existing = indexById.get(currentIndexId);
    if (!existing.summary) {
      existing.summary = trimmed;
      indexById.set(currentIndexId, existing);
    }
  }

  let inContent = false;
  const sectionStack = [];

  function ensureContentSection(sectionId, parentId, depth) {
    if (!contentById.has(sectionId)) {
      contentById.set(sectionId, {
        id: sectionId,
        parentId,
        depth,
        titleFromContent: '',
        contentSummary: '',
        contentLines: [],
        rawLines: []
      });
      contentOrder.push(sectionId);
      return contentById.get(sectionId);
    }

    const existing = contentById.get(sectionId);
    existing.parentId = existing.parentId || parentId || null;
    existing.depth = Math.min(existing.depth, depth);
    return existing;
  }

  for (const line of lines) {
    if (!inContent) {
      if (line.trim() === '===CONTENT===') {
        inContent = true;
      }
      continue;
    }

    const startMatch = line.match(/^\{#([A-Za-z][\w-]{0,63})\}$/);
    if (startMatch) {
      const id = startMatch[1];
      const parent = sectionStack.length > 0 ? sectionStack[sectionStack.length - 1] : null;
      const section = ensureContentSection(id, parent ? parent.id : null, sectionStack.length);
      sectionStack.push(section);
      continue;
    }

    const endMatch = line.match(/^\{\/([A-Za-z][\w-]{0,63})\}$/);
    if (endMatch) {
      const expectedId = endMatch[1];
      if (sectionStack.length > 0 && sectionStack[sectionStack.length - 1].id === expectedId) {
        const section = sectionStack.pop();
        const filteredLines = cleanupContentLines(section.rawLines);

        let contentSummary = '';
        for (const blockLine of section.rawLines) {
          const summaryMatch = blockLine.match(/^@summary\s*:\s*(.*)$/i);
          if (summaryMatch) {
            contentSummary = summaryMatch[1].trim();
            break;
          }
        }
        section.contentSummary = contentSummary;

        let titleFromContent = '';
        if (filteredLines.length > 0) {
          const headingMatch = filteredLines[0].match(/^#{1,6}\s+(.*)$/);
          if (headingMatch) {
            titleFromContent = headingMatch[1].trim();
            filteredLines.shift();
          }
        }
        section.titleFromContent = titleFromContent;
        section.contentLines = cleanupContentLines(filteredLines);
      }
      continue;
    }

    if (sectionStack.length > 0) {
      const activeSection = sectionStack[sectionStack.length - 1];
      activeSection.rawLines.push(line);
    }
  }

  const allIds = [];
  const seen = new Set();
  for (const id of indexOrder) {
    seen.add(id);
    allIds.push(id);
  }
  for (const id of contentOrder) {
    if (!seen.has(id)) {
      allIds.push(id);
    }
  }

  return allIds.map((id) => {
    const indexEntry = indexById.get(id) || {};
    const contentEntry = contentById.get(id) || {};
    const title = contentEntry.titleFromContent || id;
    const summary = indexEntry.summary || contentEntry.contentSummary || '';
    const contentLines = contentEntry.contentLines || [];
    return {
      id,
      title,
      summary,
      contentLines,
      depth: Number.isInteger(contentEntry.depth) ? contentEntry.depth : 0,
      parentId: contentEntry.parentId || null,
      rangeMeta: indexEntry.rangeMeta || ''
    };
  });
}

function buildSectionTree(sections) {
  const order = new Map(sections.map((section, index) => [section.id, index]));
  const byId = new Map(
    sections.map((section) => [section.id, { ...section, children: [] }])
  );
  const roots = [];

  for (const section of byId.values()) {
    if (section.parentId && byId.has(section.parentId)) {
      byId.get(section.parentId).children.push(section);
    } else {
      roots.push(section);
    }
  }

  const sortBySourceOrder = (a, b) => (order.get(a.id) || 0) - (order.get(b.id) || 0);
  const sortTree = (nodes) => {
    nodes.sort(sortBySourceOrder);
    for (const node of nodes) {
      sortTree(node.children);
    }
  };

  sortTree(roots);
  return roots;
}

function flattenSectionTree(roots) {
  const flattened = [];
  const visit = (node, topRootId) => {
    flattened.push({ ...node, topRootId });
    for (const child of node.children) {
      visit(child, topRootId);
    }
  };

  for (const root of roots) {
    visit(root, root.id);
  }
  return flattened;
}

function createTocHtml(roots) {
  const renderNodes = (nodes, topRootId = '') => {
    if (!nodes.length) {
      return '';
    }
    return `<ul class="toc-list">${nodes
      .map((node) => {
        const resolvedTopRootId = topRootId || node.id;
        const parentHint = node.parentId ? ` data-parent="${escapeHtml(node.parentId)}"` : '';
        return `<li class="toc-item depth-${Math.min(node.depth, 6)}" data-top-root="${escapeHtml(resolvedTopRootId)}" data-depth="${node.depth}"${parentHint}>
          <a class="toc-link" href="#${sectionAnchorId(node.id)}">
            <span class="toc-label">${escapeHtml(node.title)}</span>
            <code class="toc-id">${escapeHtml(node.id)}</code>
          </a>
          ${renderNodes(node.children, resolvedTopRootId)}
        </li>`;
      })
      .join('')}</ul>`;
  };

  return renderNodes(roots);
}

function formatContentForPreview(lines, knownSectionIds) {
  const text = escapeHtml(lines.join('\n'));
  return text
    .replace(/\{@([A-Za-z][\w-]{0,63})\}/g, (_, refId) => {
      if (knownSectionIds.has(refId)) {
        return `<a class="ref" href="#${sectionAnchorId(refId)}">@${refId}</a>`;
      }
      return `<span class="ref ref-missing" title="Reference target not found">@${refId}</span>`;
    })
    .replace(/\n/g, '<br/>');
}

function createPreviewHtml(document) {
  const sections = parseIatfForPreview(document.getText());
  const sectionRoots = buildSectionTree(sections);
  const orderedSections = flattenSectionTree(sectionRoots);
  const knownSectionIds = new Set(sections.map((section) => section.id));
  const tocHtml = createTocHtml(sectionRoots);

  const sectionHtml = orderedSections
    .map((section) => {
      const summaryHtml = section.summary
        ? `<p class="summary">${escapeHtml(section.summary)}</p>`
        : '';
      const contentHtml = section.contentLines.length > 0
        ? `<div class="content">${formatContentForPreview(section.contentLines, knownSectionIds)}</div>`
        : '<div class="content empty">No content in this section.</div>';
      const level = section.depth + 1;
      const parentHtml = section.parentId
        ? `<span class="meta-pill parent">in ${escapeHtml(section.parentId)}</span>`
        : '<span class="meta-pill root">top-level</span>';
      const rangeHtml = section.rangeMeta
        ? `<span class="meta-pill range">${escapeHtml(section.rangeMeta)}</span>`
        : '';
      const collapseButtonHtml = section.depth === 0 && section.children.length > 0
        ? `<button class="subtree-toggle" type="button" data-root-id="${escapeHtml(section.id)}" aria-expanded="true">Collapse Subsections</button>`
        : '';
      return `<article id="${sectionAnchorId(section.id)}" class="section depth-${Math.min(section.depth, 6)}" data-top-root="${escapeHtml(section.topRootId)}" data-depth="${section.depth}">
        <div class="section-meta">
          <span class="meta-pill level">L${level}</span>
          <code class="section-id">${escapeHtml(section.id)}</code>
          ${parentHtml}
          ${rangeHtml}
          ${collapseButtonHtml}
        </div>
        <h2>${escapeHtml(section.title)}</h2>
        ${summaryHtml}
        ${contentHtml}
      </article>`;
    })
    .join('\n');

  const body = sectionHtml || '<p class="empty">No sections found to preview.</p>';
  const fileName = escapeHtml(path.basename(document.fileName));
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>IATF Preview</title>
  <style>
    :root {
      color-scheme: light dark;
    }
    body {
      margin: 0;
      padding: 20px 24px 36px;
      background: var(--vscode-editor-background);
      color: var(--vscode-editor-foreground);
      font-family: var(--vscode-font-family);
      line-height: 1.55;
    }
    .header {
      margin-bottom: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--vscode-editorWidget-border);
      color: var(--vscode-descriptionForeground);
      font-size: 0.95rem;
    }
    .toc {
      margin: 0 0 20px 0;
      padding: 12px 14px;
      border: 1px solid var(--vscode-editorWidget-border);
      border-radius: 8px;
      background: var(--vscode-sideBar-background);
    }
    .toc-title {
      margin: 0;
      color: var(--vscode-foreground);
      font-size: 0.85rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .toc-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin: 0 0 10px 0;
      flex-wrap: wrap;
    }
    .toc-actions {
      display: inline-flex;
      gap: 6px;
    }
    .toc-action-btn {
      border: 1px solid var(--vscode-button-border, var(--vscode-editorWidget-border));
      border-radius: 6px;
      padding: 2px 8px;
      cursor: pointer;
      color: var(--vscode-button-foreground);
      background: var(--vscode-button-secondaryBackground, var(--vscode-button-background));
      font: inherit;
      font-size: 0.72rem;
      font-weight: 600;
    }
    .toc-action-btn:hover {
      background: var(--vscode-button-secondaryHoverBackground, var(--vscode-button-hoverBackground));
    }
    .toc-list {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .toc-item {
      margin: 6px 0 0 0;
    }
    .toc-item:first-child {
      margin-top: 0;
    }
    .toc-item .toc-list {
      margin-top: 4px;
      border-left: 1px dashed var(--vscode-editorWidget-border);
      padding-left: 12px;
      margin-left: 10px;
    }
    .toc-link {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--vscode-textLink-foreground);
      text-decoration: none;
      border-radius: 4px;
      padding: 3px 6px;
      width: fit-content;
      max-width: 100%;
      box-sizing: border-box;
    }
    .toc-label {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .toc-id {
      color: var(--vscode-descriptionForeground);
      font-size: 0.78rem;
      padding: 1px 4px;
      border-radius: 4px;
      background: var(--vscode-editorWidget-background, var(--vscode-editor-selectionBackground));
    }
    .toc-link:hover {
      text-decoration: underline;
    }
    .toc-link.active {
      background: var(--vscode-editor-selectionBackground);
      color: var(--vscode-textLink-activeForeground);
    }
    .section {
      margin: 0 0 22px 0;
      padding: 12px 14px 16px;
      border: 1px solid var(--vscode-editorWidget-border);
      border-left-width: 3px;
      border-radius: 8px;
      background: color-mix(in srgb, var(--vscode-editor-background) 88%, var(--vscode-sideBar-background) 12%);
      scroll-margin-top: 12px;
    }
    .section.depth-0 {
      border-left-color: var(--vscode-terminal-ansiBlue, var(--vscode-textLink-foreground));
    }
    .section.depth-1 {
      margin-left: 18px;
      border-left-color: var(--vscode-terminal-ansiGreen, var(--vscode-textLink-foreground));
      background: color-mix(in srgb, var(--vscode-editor-background) 84%, var(--vscode-sideBar-background) 16%);
    }
    .section.depth-2, .section.depth-3, .section.depth-4, .section.depth-5, .section.depth-6 {
      margin-left: 30px;
      border-left-color: var(--vscode-terminal-ansiYellow, var(--vscode-textLink-foreground));
      background: color-mix(in srgb, var(--vscode-editor-background) 80%, var(--vscode-sideBar-background) 20%);
    }
    .section-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      margin: 0 0 8px 0;
    }
    .meta-pill {
      font-size: 0.74rem;
      font-weight: 600;
      border-radius: 999px;
      padding: 1px 8px;
      border: 1px solid var(--vscode-editorWidget-border);
      color: var(--vscode-descriptionForeground);
      background: var(--vscode-editorWidget-background, var(--vscode-editor-selectionBackground));
    }
    .meta-pill.level {
      color: var(--vscode-textLink-foreground);
    }
    .meta-pill.root {
      color: var(--vscode-terminal-ansiBlue, var(--vscode-descriptionForeground));
    }
    .meta-pill.parent {
      color: var(--vscode-terminal-ansiGreen, var(--vscode-descriptionForeground));
    }
    .section-id {
      font-size: 0.78rem;
      border-radius: 6px;
      padding: 1px 7px;
      border: 1px solid var(--vscode-editorWidget-border);
      background: var(--vscode-editorWidget-background, var(--vscode-editor-selectionBackground));
      color: var(--vscode-foreground);
    }
    .subtree-toggle {
      margin-left: auto;
      border: 1px solid var(--vscode-button-border, var(--vscode-editorWidget-border));
      border-radius: 6px;
      padding: 3px 10px;
      cursor: pointer;
      color: var(--vscode-button-foreground);
      background: var(--vscode-button-background);
      font: inherit;
      font-size: 0.76rem;
      font-weight: 600;
    }
    .subtree-toggle:hover {
      background: var(--vscode-button-hoverBackground);
    }
    .subtree-hidden {
      display: none;
    }
    .section h2 {
      margin: 0 0 10px 0;
      color: var(--vscode-textLink-foreground);
      font-size: 1.2rem;
    }
    .summary {
      margin: 0 0 12px 0;
      color: var(--vscode-foreground);
      font-weight: 600;
    }
    .content {
      color: var(--vscode-editor-foreground);
      white-space: normal;
      word-break: break-word;
    }
    .empty {
      color: var(--vscode-descriptionForeground);
      font-style: italic;
    }
    .ref {
      color: var(--vscode-symbolIcon-referenceForeground, var(--vscode-textLink-foreground));
      background: var(--vscode-editor-selectionBackground);
      border-radius: 4px;
      padding: 0 4px;
      text-decoration: none;
    }
    .ref:hover {
      text-decoration: underline;
    }
    .ref-missing {
      color: var(--vscode-errorForeground);
      text-decoration: dotted underline;
    }
    .target-flash {
      animation: iatf-flash 1.1s ease;
    }
    @keyframes iatf-flash {
      0% { background: transparent; }
      25% { background: var(--vscode-editor-selectionHighlightBackground); }
      100% { background: transparent; }
    }
  </style>
</head>
<body>
  <div class="header">Preview: ${fileName}</div>
  ${tocHtml ? `<nav class="toc"><div class="toc-header"><h3 class="toc-title">Contents</h3><div class="toc-actions"><button id="iatf-collapse-all" class="toc-action-btn" type="button">Collapse All</button><button id="iatf-expand-all" class="toc-action-btn" type="button">Expand All</button></div></div>${tocHtml}</nav>` : ''}
  ${body}
  <script>
    (() => {
      const tocLinks = Array.from(document.querySelectorAll('.toc-link'));
      const sectionNodes = Array.from(document.querySelectorAll('.section[id]'));
      const subtreeToggleButtons = Array.from(document.querySelectorAll('.subtree-toggle[data-root-id]'));
      const collapseAllButton = document.getElementById('iatf-collapse-all');
      const expandAllButton = document.getElementById('iatf-expand-all');
      const linkByTarget = new Map(
        tocLinks.map((link) => [link.getAttribute('href')?.slice(1), link])
      );
      const rootSubtreeCollapsed = new Map();

      const setSubtreeVisibility = (rootId, collapsed) => {
        rootSubtreeCollapsed.set(rootId, collapsed);
        const subtreeSections = Array.from(document.querySelectorAll('.section'));
        for (const section of subtreeSections) {
          const sectionId = section.id.replace(/^iatf-sec-/, '');
          const isRoot = sectionId === rootId;
          const isDescendant = section.getAttribute('data-top-root') === rootId && section.getAttribute('data-depth') !== '0';
          if (!isRoot && isDescendant) {
            section.classList.toggle('subtree-hidden', collapsed);
          }
        }

        const tocItems = Array.from(document.querySelectorAll('.toc-item'));
        for (const item of tocItems) {
          const isDescendant = item.getAttribute('data-top-root') === rootId && item.getAttribute('data-depth') !== '0';
          if (isDescendant) {
            item.classList.toggle('subtree-hidden', collapsed);
          }
        }

        const button = subtreeToggleButtons.find((node) => node.getAttribute('data-root-id') === rootId);
        if (button) {
          button.setAttribute('aria-expanded', String(!collapsed));
          button.textContent = collapsed ? 'Expand Subsections' : 'Collapse Subsections';
        }
      };

      const ensureSectionVisible = (sectionNode) => {
        if (!sectionNode) {
          return;
        }
        const topRootId = sectionNode.getAttribute('data-top-root');
        const depth = sectionNode.getAttribute('data-depth');
        if (!topRootId || depth === '0') {
          return;
        }
        if (rootSubtreeCollapsed.get(topRootId)) {
          setSubtreeVisibility(topRootId, false);
        }
      };

      for (const button of subtreeToggleButtons) {
        const rootId = button.getAttribute('data-root-id');
        if (!rootId) {
          continue;
        }
        rootSubtreeCollapsed.set(rootId, false);
        button.addEventListener('click', () => {
          const current = rootSubtreeCollapsed.get(rootId) || false;
          setSubtreeVisibility(rootId, !current);
        });
      }

      if (collapseAllButton) {
        collapseAllButton.addEventListener('click', () => {
          for (const [rootId] of rootSubtreeCollapsed.entries()) {
            setSubtreeVisibility(rootId, true);
          }
        });
      }

      if (expandAllButton) {
        expandAllButton.addEventListener('click', () => {
          for (const [rootId] of rootSubtreeCollapsed.entries()) {
            setSubtreeVisibility(rootId, false);
          }
        });
      }

      if (subtreeToggleButtons.length === 0) {
        if (collapseAllButton) {
          collapseAllButton.disabled = true;
          collapseAllButton.title = 'No subsections to collapse';
        }
        if (expandAllButton) {
          expandAllButton.disabled = true;
          expandAllButton.title = 'No subsections to expand';
        }
      }

      const flashTarget = (node) => {
        node.classList.remove('target-flash');
        void node.offsetWidth;
        node.classList.add('target-flash');
        setTimeout(() => node.classList.remove('target-flash'), 1200);
      };

      const jumpToHash = (hash) => {
        if (!hash || !hash.startsWith('#')) {
          return;
        }
        const target = document.querySelector(hash);
        if (!target) {
          return;
        }
        ensureSectionVisible(target);
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        flashTarget(target);
      };

      document.addEventListener('click', (event) => {
        const link = event.target.closest('a[href^="#"]');
        if (!link) {
          return;
        }
        const hash = link.getAttribute('href');
        if (!hash) {
          return;
        }
        const target = document.querySelector(hash);
        if (!target) {
          return;
        }
        event.preventDefault();
        history.replaceState(null, '', hash);
        jumpToHash(hash);
      });

      if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(
          (entries) => {
            let activeId = null;
            for (const entry of entries) {
              if (entry.isIntersecting) {
                activeId = entry.target.id;
                break;
              }
            }
            if (!activeId) {
              return;
            }
            for (const link of tocLinks) {
              link.classList.remove('active');
            }
            const activeLink = linkByTarget.get(activeId);
            if (activeLink) {
              activeLink.classList.add('active');
            }
          },
          {
            rootMargin: '-20% 0px -70% 0px',
            threshold: [0, 1]
          }
        );

        for (const node of sectionNodes) {
          observer.observe(node);
        }
      }

      if (location.hash) {
        jumpToHash(location.hash);
      }
    })();
  </script>
</body>
</html>`;
}

function openPreviewForActiveEditor() {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'iatf') {
    vscode.window.showInformationMessage('Open an .iatf file to use IATF Preview.');
    return;
  }

  const document = editor.document;
  const key = document.uri.toString();
  const existing = previewPanels.get(key);
  if (existing) {
    existing.reveal(vscode.ViewColumn.Active);
    existing.webview.html = createPreviewHtml(document);
    return;
  }

  const panel = vscode.window.createWebviewPanel(
    'iatfPreview',
    `IATF Preview: ${path.basename(document.fileName)}`,
    vscode.ViewColumn.Active,
    {
      enableFindWidget: true,
      retainContextWhenHidden: true
    }
  );

  panel.webview.html = createPreviewHtml(document);
  previewPanels.set(key, panel);

  const changeSub = vscode.workspace.onDidChangeTextDocument((event) => {
    if (event.document.uri.toString() === key) {
      panel.webview.html = createPreviewHtml(event.document);
    }
  });

  const closeDocSub = vscode.workspace.onDidCloseTextDocument((closedDoc) => {
    if (closedDoc.uri.toString() === key) {
      panel.dispose();
    }
  });

  panel.onDidDispose(() => {
    previewPanels.delete(key);
    changeSub.dispose();
    closeDocSub.dispose();
  });
}

/**
 * Find the LSP server executable
 */
function findLspServer() {
  const config = vscode.workspace.getConfiguration('iatf.lsp');
  const completionConfig = vscode.workspace.getConfiguration('iatf.completion');
  
  // Check user-configured path
  const configPath = config.get('path');
  if (configPath && fs.existsSync(configPath)) {
    return configPath;
  }

  // Check common installation locations
  const possiblePaths = [];
  
  // Extension bundled binary
  const extensionPath = path.join(__dirname, 'bin', 'iatf-lsp');
  possiblePaths.push(extensionPath);
  possiblePaths.push(extensionPath + '.exe'); // Windows

  // GOPATH/bin
  const gopath = process.env.GOPATH || path.join(require('os').homedir(), 'go');
  possiblePaths.push(path.join(gopath, 'bin', 'iatf-lsp'));
  possiblePaths.push(path.join(gopath, 'bin', 'iatf-lsp.exe'));

  // Check if iatf-lsp is in PATH
  const pathDirs = (process.env.PATH || '').split(path.delimiter);
  for (const dir of pathDirs) {
    possiblePaths.push(path.join(dir, 'iatf-lsp'));
    possiblePaths.push(path.join(dir, 'iatf-lsp.exe'));
  }

  // Look for the LSP in the project's lsp/bin directory (development)
  const projectLspPath = path.join(__dirname, '..', '..', 'lsp', 'bin', 'iatf-lsp');
  possiblePaths.push(projectLspPath);
  possiblePaths.push(projectLspPath + '.exe');

  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }

  return null;
}

/**
 * Start the LSP client
 */
async function startLspClient(context) {
  if (!LanguageClient || !TransportKind) {
    try {
      ({ LanguageClient, TransportKind } = require('vscode-languageclient/node'));
    } catch (error) {
      console.log('vscode-languageclient is unavailable; LSP features disabled.');
      return;
    }
  }

  const config = vscode.workspace.getConfiguration('iatf.lsp');
  
  if (!config.get('enabled', true)) {
    console.log('IATF LSP is disabled by configuration');
    return;
  }

  const serverPath = findLspServer();
  
  if (!serverPath) {
    console.log('IATF LSP server not found. Language features disabled.');
    console.log('Install with: go install github.com/Winds-AI/agent-traversal-file/lsp@latest');
    return;
  }

  console.log('Starting IATF LSP server:', serverPath);

  const serverOptions = {
    run: {
      command: serverPath,
      transport: TransportKind.stdio
    },
    debug: {
      command: serverPath,
      transport: TransportKind.stdio
    }
  };

  const clientOptions = {
    documentSelector: [{ scheme: 'file', language: 'iatf' }],
    synchronize: {
      fileEvents: vscode.workspace.createFileSystemWatcher('**/*.iatf')
    },
    initializationOptions: {
      completionMode: completionConfig.get('mode', 'context'),
      includeTitles: completionConfig.get('includeTitles', true),
      smartInsert: completionConfig.get('smartInsert', true)
    }
  };

  client = new LanguageClient(
    'iatf-lsp',
    'IATF Language Server',
    serverOptions,
    clientOptions
  );

  try {
    await client.start();
    console.log('IATF LSP server started successfully');
  } catch (error) {
    console.error('Failed to start IATF LSP server:', error);
    vscode.window.showWarningMessage(
      'IATF Language Server failed to start. Some features may be unavailable.'
    );
  }
}

function activate(context) {
  // Apply decorations to current editor
  if (vscode.window.activeTextEditor) {
    updateDecorations(vscode.window.activeTextEditor);
  }

  // Update decorations when editor changes
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      updateDecorations(editor);
    })
  );

  // Update decorations on text changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || event.document !== editor.document) {
        return;
      }
      updateDecorations(editor);
    })
  );

  // Start the LSP client
  startLspClient(context);

  context.subscriptions.push(
    vscode.commands.registerCommand('iatf.openPreview', openPreviewForActiveEditor)
  );
}

async function deactivate() {
  // Dispose decorations
  for (const decorationType of decorationTypes) {
    decorationType.dispose();
  }

  // Stop LSP client
  if (client) {
    try {
      await client.stop();
    } catch (error) {
      console.error('Error stopping LSP client:', error);
    }
  }
}

module.exports = {
  activate,
  deactivate
};
