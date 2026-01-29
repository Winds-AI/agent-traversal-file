import { useState, useMemo, useEffect, useRef } from 'react'
import { parseIATF } from './lib/iatfParser'
import type { IATFDocument } from './lib/iatfParser'
import { IATFViewer } from './components/IATFViewer'
import { useDebounce } from './hooks/useDebounce'
import './App.css'

// Theme toggle button component
function ThemeToggle({ theme, toggleTheme }: { theme: 'light' | 'dark'; toggleTheme: () => void }) {
  return (
    <button
      onClick={toggleTheme}
      className="theme-toggle"
      aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
      title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
    >
      {theme === 'light' ? (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      ) : (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
      )}
    </button>
  );
}

const SAMPLE_IATF = `:::IATF
@title: Sample Document
@purpose: Quick introduction to IATF format

===INDEX===
<!-- AUTO-GENERATED - DO NOT EDIT MANUALLY -->
<!-- Generated: 2026-01-28T10:00:00Z -->
<!-- Content-Hash: sha256:abc1234 -->

# Introduction {#intro | lines:17-25 | words:35}
> Getting started with IATF format
  Created: 2026-01-28 | Modified: 2026-01-28
  Hash: abc1234

# Features {#features | lines:27-40 | words:50}
> Key features of the format
  Created: 2026-01-28 | Modified: 2026-01-28
  Hash: def5678

===CONTENT===

{#intro}
@summary: Getting started with IATF format
# Introduction

IATF (Indexed Agent Traversable File) makes large documents navigable for AI agents.
Paste your own IATF content on the left to see it formatted!

Try clicking the links in the Table of Contents to navigate to sections.
{/intro}

{#features}
@summary: Key features of the format
# Features

- **Token efficient**: Load only what you need
- **Self-indexing**: INDEX auto-generated from CONTENT
- **Human readable**: Plain text format
- **Line-addressable**: Direct access to any section

See {@intro} for more information.
{/features}
`;

function App() {
  const [input, setInput] = useState(SAMPLE_IATF);
  const [isParsing, setIsParsing] = useState(false);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [scrollTop, setScrollTop] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lineNumbersRef = useRef<HTMLDivElement>(null);
  const lineCount = useMemo(() => (input ? input.split('\n').length : 0), [input]);
  const charCount = input.length;

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const savedTheme = localStorage.getItem('iatf-theme') as 'light' | 'dark' | null;
    if (savedTheme) {
      setTheme(savedTheme);
    } else if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark');
    }
  }, []);

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('iatf-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Debounce input to prevent lag during typing
  const debouncedInput = useDebounce(input, 300);

  const parsedDoc: IATFDocument | null = useMemo(() => {
    if (!debouncedInput.trim()) return null;
    setIsParsing(true);
    try {
      const doc = parseIATF(debouncedInput);
      setIsParsing(false);
      return doc;
    } catch (error) {
      setIsParsing(false);
      // Return a document with errors
      return {
        isValid: false,
        errors: [`Parse error: ${error instanceof Error ? error.message : 'Unknown error'}`],
        metadata: {},
        indexEntries: [],
        sections: [],
      };
    }
  }, [debouncedInput]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <div className="brand-mark">IATF</div>
          <div className="brand-copy">
            <h1>Indexed Viewer</h1>
            <p>Preview, navigate, and validate IATF without leaving your editor.</p>
          </div>
        </div>
        <div className="header-meta">
          <ThemeToggle theme={theme} toggleTheme={toggleTheme} />
        </div>
      </header>

      <main className="split-panel">
        <div className="panel input-panel">
          <div className="panel-header">
            <div className="panel-title">
              <h2>IATF Input</h2>
            </div>
            <div className="panel-actions">
              <button onClick={() => setInput('')} className="btn-secondary">
                Clear
              </button>
              <button onClick={() => setInput(SAMPLE_IATF)} className="btn-secondary">
                Load Sample
              </button>
            </div>
          </div>
          <div className="input-wrapper">
            <div
              ref={lineNumbersRef}
              className="line-numbers"
              style={{ transform: `translateY(-${scrollTop}px)` }}
            >
              {Array.from({ length: lineCount }, (_, i) => (
                <div key={i} className="line-number">{i + 1}</div>
              ))}
            </div>
            <div
              className="notebook-lines"
              style={{ transform: `translateY(-${scrollTop}px)` }}
            />
            <textarea
              ref={textareaRef}
              className="iatf-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onScroll={(e) => setScrollTop(e.currentTarget.scrollTop)}
              placeholder="Paste your IATF content here..."
              spellCheck={false}
            />
          </div>
          <div className="panel-footer">
            <span className="footer-chip">{lineCount} lines</span>
            <span className="footer-chip">{charCount} chars</span>
            <span className="footer-muted">Auto-indexed sections appear on the right.</span>
          </div>
        </div>

        <div className="panel output-panel">
          <div className="panel-header">
            <div className="panel-title">
              <h2>Formatted View</h2>
            </div>
            {isParsing ? (
              <div className="status">
                <span className="status-pill status-parsing">Parsing…</span>
              </div>
            ) : parsedDoc ? (
              <div className="status">
                {parsedDoc.isValid ? (
                  <span className="status-pill status-valid">Valid</span>
                ) : (
                  <span className="status-pill status-invalid">Invalid</span>
                )}
                <span className="section-count">
                  {parsedDoc.sections.length} section{parsedDoc.sections.length !== 1 ? 's' : ''}
                </span>
              </div>
            ) : null}
          </div>
          <div className="iatf-output">
            {isParsing ? (
              <div className="loading-state">
                <div className="spinner"></div>
                <p>Parsing document...</p>
              </div>
            ) : parsedDoc ? (
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
