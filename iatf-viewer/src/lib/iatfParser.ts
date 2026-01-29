export interface IATFMetadata {
  title?: string;
  version?: string;
  [key: string]: string | undefined;
}

export interface IATFIndexEntry {
  id: string;
  title: string;
  level: number;
  words: number;
  summary?: string;
  lineStart: number;
  lineEnd: number;
  modified?: string;
}

export interface IATFSection {
  id: string;
  content: string;
  summary?: string;
}

export interface IATFDocument {
  isValid: boolean;
  errors: string[];
  metadata: IATFMetadata;
  indexGenerated?: string;
  contentHash?: string;
  indexEntries: IATFIndexEntry[];
  sections: IATFSection[];
}

export function parseIATF(input: string): IATFDocument {
  const doc: IATFDocument = {
    isValid: true,
    errors: [],
    metadata: {},
    indexEntries: [],
    sections: [],
  };

  const lines = input.split('\n');

  // Check for IATF header
  if (!lines[0]?.trim().startsWith(':::IATF')) {
    doc.errors.push('Missing IATF header (:::IATF)');
    doc.isValid = false;
  } else {
    // Optional version after IATF (e.g., :::IATF/1.0)
    const versionMatch = lines[0].match(/:::IATF(?:\/(.+))?/);
    if (versionMatch && versionMatch[1]) {
      doc.metadata.version = versionMatch[1].trim();
    }
  }

  // Find section markers
  const indexStart = lines.findIndex(line => line.trim() === '===INDEX===');
  const contentStart = lines.findIndex(line => line.trim() === '===CONTENT===');

  // Parse metadata (between header and INDEX)
  if (indexStart > 0) {
    for (let i = 1; i < indexStart; i++) {
      const line = lines[i].trim();
      if (line.startsWith('@')) {
        const match = line.match(/^@(\w+):\s*(.+)$/);
        if (match) {
          const [, key, value] = match;
          doc.metadata[key] = value.trim();
        }
      }
    }
  }

  // Parse INDEX section
  if (indexStart !== -1 && contentStart !== -1) {
    parseIndexSection(lines.slice(indexStart + 1, contentStart), doc);
  } else if (indexStart === -1) {
    doc.errors.push('Missing INDEX section');
  }

  // Parse CONTENT section
  if (contentStart !== -1) {
    parseContentSection(lines.slice(contentStart + 1), doc);
  } else {
    doc.errors.push('Missing CONTENT section');
  }

  if (doc.errors.length > 0) {
    doc.isValid = false;
  }

  return doc;
}

function parseIndexSection(lines: string[], doc: IATFDocument): void {
  let currentEntry: Partial<IATFIndexEntry> | null = null;
  let summaryLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip comments
    if (trimmed.startsWith('<!--')) {
      // Extract special metadata from comments
      if (trimmed.includes('Generated:')) {
        const match = trimmed.match(/Generated:\s*(\S+)/);
        if (match) doc.indexGenerated = match[1];
      }
      if (trimmed.includes('Content-Hash:')) {
        const match = trimmed.match(/Content-Hash:\s*(\S+)/);
        if (match) doc.contentHash = match[1];
      }
      continue;
    }

    // Skip empty lines
    if (trimmed === '') {
      if (currentEntry && summaryLines.length > 0) {
        currentEntry.summary = summaryLines.join(' ').trim();
        summaryLines = [];
      }
      continue;
    }

    // Parse header with metadata
    const headerMatch = trimmed.match(/^(#{1,6})\s+(.+?)\s+\{#([\w-]+)\s*\|\s*lines:(\d+)-(\d+)\s*\|\s*words:(\d+)(?:\s*\|\s*modified:(\S+))?\}/);
    if (headerMatch) {
      // Save previous entry
      if (currentEntry && currentEntry.id) {
        doc.indexEntries.push(currentEntry as IATFIndexEntry);
      }

      const [, hashes, title, id, lineStart, lineEnd, words, modified] = headerMatch;
      currentEntry = {
        id,
        title,
        level: hashes.length,
        lineStart: parseInt(lineStart, 10),
        lineEnd: parseInt(lineEnd, 10),
        words: parseInt(words, 10),
        modified,
      };
      summaryLines = [];
      continue;
    }

    // Parse summary line (starts with >)
    if (trimmed.startsWith('>')) {
      summaryLines.push(trimmed.slice(1).trim());
      continue;
    }
  }

  // Save last entry
  if (currentEntry && currentEntry.id) {
    if (summaryLines.length > 0) {
      currentEntry.summary = summaryLines.join(' ').trim();
    }
    doc.indexEntries.push(currentEntry as IATFIndexEntry);
  }
}

function parseContentSection(lines: string[], doc: IATFDocument): void {
  let currentSection: Partial<IATFSection> | null = null;
  let contentLines: string[] = [];

  for (const line of lines) {
    const trimmed = line.trim();

    // Section start tag
    const startMatch = trimmed.match(/^\{#([\w-]+)\}$/);
    if (startMatch) {
      // Save previous section
      if (currentSection && currentSection.id) {
        currentSection.content = contentLines.join('\n').trim();
        doc.sections.push(currentSection as IATFSection);
      }

      currentSection = {
        id: startMatch[1],
      };
      contentLines = [];
      continue;
    }

    // Section end tag
    const endMatch = trimmed.match(/^\{\/[\w-]+\}$/);
    if (endMatch) {
      if (currentSection && currentSection.id) {
        currentSection.content = contentLines.join('\n').trim();
        doc.sections.push(currentSection as IATFSection);
      }
      currentSection = null;
      contentLines = [];
      continue;
    }

    // Summary annotation
    if (trimmed.startsWith('@summary:')) {
      if (currentSection) {
        currentSection.summary = trimmed.slice(9).trim();
      }
      continue;
    }

    // Regular content line
    if (currentSection) {
      contentLines.push(line);
    }
  }

  // Save last section if not closed
  if (currentSection && currentSection.id) {
    currentSection.content = contentLines.join('\n').trim();
    doc.sections.push(currentSection as IATFSection);
  }
}
