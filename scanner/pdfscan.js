// Turns the text of a daily Hansard PDF into speaker-and-topic attributed mention records.
const { clean, excerpt, countMentions, hasMention, MENTION } = require('./common');

const norm = (s) => String(s).toUpperCase().replace(/[^A-Z0-9]/g, '');

// Speaker turn openers, e.g. "Mr BLEIJIE:", "Ms PUGH (Mount Ommaney—ALP) (3.57 pm):", "Hon. RM BATES (...) (2.23 pm):",
// "MS BERRY(Ginninderra—Deputy Chief Minister) (11.12):", "Madam DEPUTY SPEAKER (Mrs Gerber):", "Mr BURGOYNE (Lands)(in reply):".
const SPEAKER = /^((?:Hon\.?\s+)?(?:Mr|Ms|Mrs|Miss|Dr|MR|MS|MRS|MISS|DR|Madam|MADAM|Mister|THE|The)\.?\s+(?:[A-Z]{1,4}\s+)?(?:(?:de|van|von|di|del)\s+)?(?:Mc|Mac)?[A-Z][A-Z'\u2019\-]+(?:\s+(?:Mc|Mac)?[A-Z][A-Z'\u2019\-]+){0,3}|Hon\.?\s+(?:[A-Z]{1,4}\s+)?(?:(?:de|van|von|di|del)\s+)?(?:Mc|Mac)?[A-Z][A-Z'\u2019\-]+|[A-Z]\s+[A-Z][A-Z'\u2019\-]{2,})\s*((?:\([^()]*(?:\([^()]*\)[^()]*)*\)\s*)*):(?=\s|$)/;

function parseSpeaker(line) {
  const m = line.match(SPEAKER);
  if (!m) return null;
  const name = clean(m[1]);
  const paren = (m[2] || '').match(/\(([^()]*)\)/);
  let electorate = null;
  let party = null;
  if (paren) {
    const inner = clean(paren[1]);
    if (!/^\d/.test(inner)) {
      const dash = inner.split(/[—–]|\s-\s/);
      electorate = dash[0] || null;
      if (dash[1] && /^[A-Z]{2,5}$/.test(dash[1].trim())) party = dash[1].trim();
    }
  }
  return { name, electorate, party };
}

// Standardises "MS BERRY" and "Ms BERRY" so a member's turns group together.
const speakerKey = (name) => norm(String(name).replace(/^(Hon\.?\s+)/i, '').replace(/^(Mr|Ms|Mrs|Miss|Dr|Madam|Mister)\.?\s+/i, '').replace(/^[A-Z]{1,4}\s+(?=[A-Z]{2})/, ''));

function titleCaseName(name) {
  // "MS CASTLEY" -> "Ms Castley"; "Hon. RM BATES" -> "Hon. RM Bates"; keeps short initial groups as they are.
  return clean(name)
    .split(' ')
    .map((w, i, all) => {
      if (/^(Hon\.?|Mr|Ms|Mrs|Miss|Dr)$/i.test(w)) return w[0].toUpperCase() + w.slice(1).toLowerCase();
      if (/^(de|van|von|di|del)$/.test(w)) return w;
      if (/^[A-Z]{1,3}$/.test(w) && i < all.length - 1 && !/^(MR|MS|DR)$/.test(w)) return w;
      return w.toLowerCase().replace(/(^|[-'’])([a-z])/g, (_, a, b) => a + b.toUpperCase()).replace(/^Mc([a-z])/, (_, c) => 'Mc' + c.toUpperCase());
    })
    .join(' ');
}

// Title-cases SHOUTING headings, keeping short joining words in lower case.
function nicerHeading(s) {
  const t = clean(s);
  if (/[a-z]/.test(t)) return t;
  const small = new Set(['and', 'of', 'the', 'in', 'on', 'for', 'to', 'a', 'an', 'at', 'by', 'or', 'with', 'from']);
  return t
    .toLowerCase()
    .split(' ')
    .map((w, i) => (i > 0 && small.has(w) ? w : w.replace(/(^|[-(—–/])([a-z])/g, (_, a, b) => a + b.toUpperCase())))
    .join(' ');
}

// Parses dot-leader contents entries: "Hospital Funding ....... 3160" (possibly several on a line).
function parseContents(text) {
  const out = [];
  const re = /([^.\n][^\n]*?)\s*\.{3,}\s*P?(\d{1,5})\b/g;
  for (const m of clean(text).matchAll(/(.{2,300}?)\s*\.{3,}\s*P?(\d{1,5})(?=\s|$)/g)) {
    out.push({ title: clean(m[1]), page: Number(m[2]) });
  }
  return out;
}

// Finds heading lines in order; falls back to the first line of the contents page when a heading can't be matched.
function alignContents(lines, entries, firstLineOfPrinted, startLine = 0) {
  const normLines = lines.map(norm);
  const marks = [];
  let at = startLine;
  for (const e of entries) {
    const h = norm(e.match || e.title);
    if (h.length < 4) continue;
    let found = -1;
    const pageStart = firstLineOfPrinted ? firstLineOfPrinted(e.page) : null;
    const from = Math.max(at, pageStart != null ? pageStart - 2 : at);
    const to = Math.min(lines.length, from + 2500);
    for (let i = from; i < to; i++) {
      const l = normLines[i];
      if (!l || l.length > h.length + 12) continue;
      const joined = l + (normLines[i + 1] || '');
      if (l === h || joined === h || (joined + (normLines[i + 2] || '')) === h || (h.length > 30 && l.length >= 24 && h.startsWith(l))) {
        found = i;
        break;
      }
    }
    if (found < 0 && pageStart != null) found = Math.max(at, pageStart);
    if (found >= 0) {
      marks.push({ line: found, entry: e, exact: normLines[found] && (normLines[found] === h || h.startsWith(normLines[found])) });
      at = found;
    }
  }
  return marks;
}

/*
 * Walks the lines of a transcript and returns mention groups.
 * opts: skipLine(line) => running headers to ignore; topicAt(lineIndex) => {title, proceeding}
 */
function extract(lines, linePage, opts) {
  const groups = new Map();
  const readSpeaker = opts.parseSpeaker || parseSpeaker;
  const showName = opts.speakerName || titleCaseName;
  let speaker = null;
  let turnStart = 0;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim() || (opts.skipLine && opts.skipLine(line, i))) continue;
    // A new heading ends the previous speaker's turn, so a mention in the heading isn't pinned on them.
    if (opts.headingLines && opts.headingLines.has(i)) {
      speaker = null;
      turnStart = i;
    }
    const sp = readSpeaker(line.trim());
    if (sp) {
      speaker = sp;
      turnStart = i;
    }
    const wrapped = /auditors?[\s-]*$/i.test(line.trim()) && /^\s*-?\s*generals?\b/i.test(lines[i + 1] || '');
    const count = countMentions(line) + (wrapped ? 1 : 0);
    if (!count) continue;
    const topic = opts.topicAt(i);
    const key = `${topic.title}|${speaker ? speakerKey(speaker.name) : ''}`;
    if (!groups.has(key)) {
      groups.set(key, {
        title: topic.title,
        proceeding: topic.proceeding || null,
        speaker: speaker ? showName(speaker.name) : null,
        electorate: speaker ? speaker.electorate : null,
        party: speaker ? speaker.party : null,
        page: linePage[i],
        printed: opts.printedAt ? opts.printedAt(i) : null,
        mentions: 0,
        parts: [],
      });
    }
    const g = groups.get(key);
    if (!g.electorate && speaker && speaker.electorate) g.electorate = speaker.electorate;
    if (!g.party && speaker && speaker.party) g.party = speaker.party;
    g.mentions += count;
    const ctx = [];
    for (let k = Math.max(turnStart, i - 1); k <= Math.min(lines.length - 1, i + 1); k++) {
      if (!lines[k].trim() || (opts.skipLine && opts.skipLine(lines[k], k))) continue;
      if (k > i && readSpeaker(lines[k].trim())) break;
      ctx.push(lines[k]);
    }
    g.parts.push(ctx.join(' '));
  }
  return [...groups.values()].map((g) => {
    const seen = new Set();
    const text = clean(g.parts.filter((p) => !seen.has(p) && seen.add(p)).join(' '));
    const { parts, ...rest } = g;
    return { ...rest, passage: excerpt(text) };
  });
}

module.exports = { norm, SPEAKER, parseSpeaker, speakerKey, titleCaseName, nicerHeading, parseContents, alignContents, extract };
