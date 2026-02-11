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

function parseIatfForPreview(text) {
  const lines = text.split(/\r?\n/);
  const indexById = new Map();
  const indexOrder = [];
  const contentById = new Map();

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

    const entryMatch = line.match(/^(#{1,6})\s+(.+?)\s+\{#([A-Za-z][\w-]{0,63})\b/);
    if (entryMatch) {
      const title = entryMatch[2].trim();
      const id = entryMatch[3];
      if (!indexById.has(id)) {
        indexOrder.push(id);
      }
      indexById.set(id, { title, summary: '' });
      currentIndexId = id;
      continue;
    }

    const summaryMatch = line.match(/^>\s+(.*)$/);
    if (summaryMatch && currentIndexId && indexById.has(currentIndexId)) {
      const existing = indexById.get(currentIndexId);
      existing.summary = summaryMatch[1].trim();
      indexById.set(currentIndexId, existing);
    }
  }

  let inContent = false;
  let currentBlockId = null;
  let currentBlockLines = [];
  for (const line of lines) {
    if (!inContent) {
      if (line.trim() === '===CONTENT===') {
        inContent = true;
      }
      continue;
    }

    const startMatch = line.match(/^\{#([A-Za-z][\w-]{0,63})\}$/);
    if (startMatch) {
      currentBlockId = startMatch[1];
      currentBlockLines = [];
      continue;
    }

    const endMatch = line.match(/^\{\/([A-Za-z][\w-]{0,63})\}$/);
    if (endMatch && currentBlockId && endMatch[1] === currentBlockId) {
      let contentSummary = '';
      for (const blockLine of currentBlockLines) {
        const summaryMatch = blockLine.match(/^@summary\s*:\s*(.*)$/i);
        if (summaryMatch) {
          contentSummary = summaryMatch[1].trim();
          break;
        }
      }

      const filteredLines = cleanupContentLines(currentBlockLines);
      let titleFromContent = '';
      if (filteredLines.length > 0) {
        const headingMatch = filteredLines[0].match(/^#{1,6}\s+(.*)$/);
        if (headingMatch) {
          titleFromContent = headingMatch[1].trim();
          filteredLines.shift();
        }
      }

      contentById.set(currentBlockId, {
        titleFromContent,
        contentSummary,
        contentLines: cleanupContentLines(filteredLines)
      });
      currentBlockId = null;
      currentBlockLines = [];
      continue;
    }

    if (currentBlockId) {
      currentBlockLines.push(line);
    }
  }

  const allIds = [];
  const seen = new Set();
  for (const id of indexOrder) {
    seen.add(id);
    allIds.push(id);
  }
  for (const id of contentById.keys()) {
    if (!seen.has(id)) {
      allIds.push(id);
    }
  }

  return allIds.map((id) => {
    const indexEntry = indexById.get(id) || {};
    const contentEntry = contentById.get(id) || {};
    const title = indexEntry.title || contentEntry.titleFromContent || id;
    const summary = indexEntry.summary || contentEntry.contentSummary || '';
    const contentLines = contentEntry.contentLines || [];
    return { id, title, summary, contentLines };
  });
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
  const knownSectionIds = new Set(sections.map((section) => section.id));
  const tocHtml = sections
    .map((section) => {
      return `<li><a class="toc-link" href="#${sectionAnchorId(section.id)}">${escapeHtml(section.title)}</a></li>`;
    })
    .join('\n');

  const sectionHtml = sections
    .map((section) => {
      const summaryHtml = section.summary
        ? `<p class="summary">${escapeHtml(section.summary)}</p>`
        : '';
      const contentHtml = section.contentLines.length > 0
        ? `<div class="content">${formatContentForPreview(section.contentLines, knownSectionIds)}</div>`
        : '<div class="content empty">No content in this section.</div>';
      return `<article id="${sectionAnchorId(section.id)}" class="section"><h2>${escapeHtml(section.title)}</h2>${summaryHtml}${contentHtml}</article>`;
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
      margin: 0 0 10px 0;
      color: var(--vscode-foreground);
      font-size: 0.85rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .toc-list {
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 6px;
    }
    .toc-link {
      color: var(--vscode-textLink-foreground);
      text-decoration: none;
      border-radius: 4px;
      padding: 2px 4px;
      display: inline-block;
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
      padding: 0 0 18px 0;
      border-bottom: 1px solid var(--vscode-editorWidget-border);
      scroll-margin-top: 12px;
    }
    .section h2 {
      margin: 0 0 8px 0;
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
  ${tocHtml ? `<nav class="toc"><h3 class="toc-title">Contents</h3><ul class="toc-list">${tocHtml}</ul></nav>` : ''}
  ${body}
  <script>
    (() => {
      const tocLinks = Array.from(document.querySelectorAll('.toc-link'));
      const sectionNodes = Array.from(document.querySelectorAll('.section[id]'));
      const linkByTarget = new Map(
        tocLinks.map((link) => [link.getAttribute('href')?.slice(1), link])
      );

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
