import { useState, useMemo } from 'react'
import { parseIATF } from './lib/iatfParser'
import type { IATFDocument } from './lib/iatfParser'
import { IATFViewer } from './components/IATFViewer'
import './App.css'

const SAMPLE_IATF = `:::IATF/1.0
@title: Sample Document

===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
<!-- Generated: 2026-01-28T10:00:00Z -->
<!-- Content-Hash: sha256:abc1234 -->

# Introduction {#intro | lines:15-22 | words:25}
> Getting started with IATF format

# Features {#features | lines:24-35 | words:40}
> Key features of the format

===CONTENT===

{#intro}
@summary: Getting started with IATF format
# Introduction

IATF (Indexed Agent Traversable File) makes large documents navigable for AI agents.
Paste your own IATF content on the left to see it formatted!
{/intro}

{#features}
@summary: Key features of the format
# Features

- **Token efficient**: Load only what you need
- **Self-indexing**: INDEX auto-generated from CONTENT
- **Human readable**: Plain text format
- **Line-addressable**: Direct access to any section
{/features}
`;

function App() {
  const [input, setInput] = useState(SAMPLE_IATF);
  
  const parsedDoc: IATFDocument | null = useMemo(() => {
    if (!input.trim()) return null;
    try {
      return parseIATF(input);
    } catch {
      return null;
    }
  }, [input]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>IATF Viewer</h1>
        <p>Paste IATF content on the left, see formatted output on the right</p>
      </header>
      
      <main className="split-panel">
        <div className="panel input-panel">
          <div className="panel-header">
            <h2>IATF Input</h2>
            <div className="panel-actions">
              <button onClick={() => setInput('')} className="btn-secondary">
                Clear
              </button>
              <button onClick={() => setInput(SAMPLE_IATF)} className="btn-secondary">
                Load Sample
              </button>
            </div>
          </div>
          <textarea
            className="iatf-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste your IATF content here..."
            spellCheck={false}
          />
        </div>
        
        <div className="panel output-panel">
          <div className="panel-header">
            <h2>Formatted View</h2>
            {parsedDoc && (
              <div className="status">
                {parsedDoc.isValid ? (
                  <span className="status-valid">Valid</span>
                ) : (
                  <span className="status-invalid">Invalid</span>
                )}
                <span className="section-count">
                  {parsedDoc.sections.length} section{parsedDoc.sections.length !== 1 ? 's' : ''}
                </span>
              </div>
            )}
          </div>
          <div className="iatf-output">
            {parsedDoc ? (
              <IATFViewer doc={parsedDoc} />
            ) : (
              <div className="empty-state">
                <p>Enter valid IATF content to see the formatted view</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
