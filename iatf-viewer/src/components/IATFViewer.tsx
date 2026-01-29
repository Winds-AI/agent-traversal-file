import type { IATFDocument, IATFIndexEntry, IATFSection } from '../lib/iatfParser';
import './IATFViewer.css';

interface IATFViewerProps {
  doc: IATFDocument;
}

export function IATFViewer({ doc }: IATFViewerProps) {
  return (
    <div className="iatf-viewer">
      {/* Errors */}
      {doc.errors.length > 0 && (
        <div className="errors">
          <h3>Errors</h3>
          <ul>
            {doc.errors.map((error, i) => (
              <li key={i}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Header/Metadata */}
      <div className="doc-header">
        {doc.metadata.title && <h1 className="doc-title">{doc.metadata.title}</h1>}
        <div className="doc-meta">
          <span className="meta-item">
            <strong>Format:</strong> IATF{doc.metadata.version ? ` v${doc.metadata.version}` : ''}
          </span>
          {doc.indexGenerated && (
            <span className="meta-item">
              <strong>Generated:</strong> {formatDate(doc.indexGenerated)}
            </span>
          )}
          {doc.contentHash && (
            <span className="meta-item">
              <strong>Hash:</strong> <code>{doc.contentHash}</code>
            </span>
          )}
        </div>
      </div>

      {/* Table of Contents */}
      {doc.indexEntries.length > 0 && (
        <nav className="toc">
          <h2>Table of Contents</h2>
          <ul className="toc-list">
            {doc.indexEntries.map((entry) => (
              <TOCEntry key={entry.id} entry={entry} />
            ))}
          </ul>
        </nav>
      )}

      {/* Content Sections */}
      <div className="content-sections">
        {doc.sections.map((section) => {
          const indexEntry = doc.indexEntries.find((e) => e.id === section.id);
          return (
            <SectionBlock key={section.id} section={section} indexEntry={indexEntry} />
          );
        })}
      </div>
    </div>
  );
}

function TOCEntry({ entry }: { entry: IATFIndexEntry }) {
  return (
    <li className={`toc-item level-${entry.level}`}>
      <a href={`#section-${entry.id}`} className="toc-link">
        <span className="toc-title">{entry.title}</span>
        <span className="toc-meta">
          <span className="toc-words">{entry.words}w</span>
        </span>
      </a>
      {entry.summary && <p className="toc-summary">{entry.summary}</p>}
    </li>
  );
}

function SectionBlock({
  section,
  indexEntry,
}: {
  section: IATFSection;
  indexEntry?: IATFIndexEntry;
}) {
  return (
    <section id={`section-${section.id}`} className="content-section">
      <div className="section-header">
        <span className="section-id">#{section.id}</span>
        {indexEntry && (
          <div className="section-meta">
            <span className="meta-lines">
              Lines {indexEntry.lineStart}-{indexEntry.lineEnd}
            </span>
            <span className="meta-words">{indexEntry.words} words</span>
            {indexEntry.modified && (
              <span className="meta-modified">Modified: {indexEntry.modified}</span>
            )}
          </div>
        )}
      </div>

      {section.summary && (
        <div className="section-summary">
          <em>{section.summary}</em>
        </div>
      )}

      <div className="section-content">
        <MarkdownContent content={section.content} />
      </div>
    </section>
  );
}

function MarkdownContent({ content }: { content: string }) {
  // Simple markdown rendering (basic formatting)
  const html = simpleMarkdown(content);
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />;
}

function simpleMarkdown(text: string): string {
  const lines = text.split('\n');
  const result: string[] = [];
  let inCodeBlock = false;
  let codeBlockStartLine = -1;
  let codeContent: string[] = [];
  let inList = false;
  let listItems: string[] = [];
  let inTable = false;
  let tableRows: string[][] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      result.push('<ul>' + listItems.map((li) => `<li>${li}</li>`).join('') + '</ul>');
      listItems = [];
      inList = false;
    }
  };

  const flushTable = () => {
    if (tableRows.length > 0) {
      const [header, ...body] = tableRows;
      let html = '<table><thead><tr>';
      header.forEach((cell) => {
        html += `<th>${escapeHtml(cell.trim())}</th>`;
      });
      html += '</tr></thead><tbody>';
      // Skip separator row if it exists
      const dataRows = body.filter((row) => !row.every((cell) => /^[-:|]+$/.test(cell.trim())));
      dataRows.forEach((row) => {
        html += '<tr>';
        row.forEach((cell) => {
          html += `<td>${escapeHtml(cell.trim())}</td>`;
        });
        html += '</tr>';
      });
      html += '</tbody></table>';
      result.push(html);
      tableRows = [];
      inTable = false;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        result.push('<pre><code>' + escapeHtml(codeContent.join('\n')) + '</code></pre>');
        codeContent = [];
        inCodeBlock = false;
        codeBlockStartLine = -1;
      } else {
        flushList();
        flushTable();
        inCodeBlock = true;
        codeBlockStartLine = i;
      }
      continue;
    }

    if (inCodeBlock) {
      codeContent.push(line);
      continue;
    }

    // Table rows
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      flushList();
      inTable = true;
      const cells = line
        .trim()
        .slice(1, -1)
        .split('|')
        .map((c) => c.trim());
      tableRows.push(cells);
      continue;
    } else if (inTable) {
      flushTable();
    }

    // Headers
    const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headerMatch) {
      flushList();
      const level = headerMatch[1].length;
      result.push(`<h${level}>${escapeHtml(headerMatch[2])}</h${level}>`);
      continue;
    }

    // List items
    if (line.match(/^[\s]*[-*]\s+/)) {
      const listText = line.replace(/^[\s]*[-*]\s+/, '');
      inList = true;
      listItems.push(formatInline(listText));
      continue;
    } else if (inList) {
      flushList();
    }

    // Empty line - skip it (spacing handled by paragraph margins)
    if (line.trim() === '') {
      continue;
    }

    // Regular paragraph
    result.push(`<p>${formatInline(line)}</p>`);
  }

  flushList();
  flushTable();

  // Check for unclosed code block
  if (inCodeBlock) {
    result.push(
      '<div class="warning-box">' +
      '<strong>⚠️ Warning:</strong> Unclosed code block detected (started at line ' + (codeBlockStartLine + 1) + ')' +
      '</div>'
    );
    result.push('<pre><code>' + escapeHtml(codeContent.join('\n')) + '</code></pre>');
  }

  return result.join('\n');
}

function formatInline(text: string): string {
  let result = escapeHtml(text);

  // Process in order to avoid nested issues:
  // 1. Inline code first (to protect code from other formatting)
  result = result.replace(/`([^`]+)`/g, '<code>$1</code>');

  // 2. Bold + Italic (***text***)
  result = result.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>');

  // 3. Bold (**text**)
  result = result.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');

  // 4. Italic (*text*)
  result = result.replace(/\*(.+?)\*/g, '<em>$1</em>');

  // 5. Links
  result = result.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

  // 6. Section references {@section-id}
  result = result.replace(
    /\{@([\w-]+)\}/g,
    '<a href="#section-$1" class="section-ref">@$1</a>'
  );

  return result;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function formatDate(dateStr: string): string {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}
