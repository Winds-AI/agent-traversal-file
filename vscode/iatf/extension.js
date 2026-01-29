const vscode = require('vscode');

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

function activate(context) {
  if (vscode.window.activeTextEditor) {
    updateDecorations(vscode.window.activeTextEditor);
  }

  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      updateDecorations(editor);
    })
  );

  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => {
      const editor = vscode.window.activeTextEditor;
      if (!editor || event.document !== editor.document) {
        return;
      }
      updateDecorations(editor);
    })
  );
}

function deactivate() {
  for (const decorationType of decorationTypes) {
    decorationType.dispose();
  }
}

module.exports = {
  activate,
  deactivate
};
