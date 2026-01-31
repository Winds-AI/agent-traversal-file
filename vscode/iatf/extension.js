const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

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

/**
 * Find the LSP server executable
 */
function findLspServer() {
  const config = vscode.workspace.getConfiguration('iatf.lsp');
  
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
