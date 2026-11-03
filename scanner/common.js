// Shared helpers for the Hansard scanners.
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const RAW = path.join(ROOT, 'data', 'raw');
// Downloaded PDFs and DOCX files live outside the project. Set HANSARD_CACHE to choose where.
const CACHE = process.env.HANSARD_CACHE || path.join(ROOT, '.cache');
const WINDOW = { from: '2025-11-01', to: '2026-10-31' };
const UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36';

fs.mkdirSync(RAW, { recursive: true });
fs.mkdirSync(CACHE, { recursive: true });

// Matches "Auditor-General", "Auditor General", "Auditors-General", "Auditor- General" (line wraps) and dash variants.
const MENTION = /\bauditors?[\s ]*[-‐‑‒–—]?[\s ]*generals?\b/gi;
const countMentions = (s) => (String(s).match(MENTION) || []).length;
const hasMention = (s) => countMentions(s) > 0;

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function get(url, opts = {}) {
  const tries = opts.tries || 4;
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const res = await fetch(url, {
        method: opts.method || 'GET',
        body: opts.body,
        headers: { 'User-Agent': UA, Accept: '*/*', ...(opts.headers || {}) },
        redirect: 'follow',
        signal: AbortSignal.timeout(opts.timeout || 90000),
      });
      if (res.status === 404 && !opts.retry404) return null;
      // Respect rate limits: wait as long as the server asks, or a generous default.
      if (res.status === 429 && i < tries - 1) {
        const asked = Number(res.headers.get('retry-after'));
        await sleep(Math.max(asked ? asked * 1000 : 0, 45000 * (i + 1)));
        continue;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status} ${url}`);
      return opts.binary ? Buffer.from(await res.arrayBuffer()) : await res.text();
    } catch (e) {
      last = e;
      await sleep(1500 * (i + 1));
    }
  }
  throw last;
}

// Runs fn over items with a small worker pool, keeping request pressure polite.
async function pool(items, size, fn) {
  const out = new Array(items.length);
  let next = 0;
  await Promise.all(
    Array.from({ length: size }, async () => {
      while (next < items.length) {
        const i = next++;
        out[i] = await fn(items[i], i);
      }
    })
  );
  return out;
}

async function download(url, file) {
  if (fs.existsSync(file) && fs.statSync(file).size > 0) return file;
  const buf = await get(url, { binary: true, timeout: 180000 });
  if (!buf) return null;
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, buf);
  return file;
}

// Returns one string per PDF page. Form feeds separate pages in pdftotext output.
function pdfPages(file, { layout = false } = {}) {
  const args = ['-enc', 'UTF-8'];
  if (layout) args.push('-layout');
  args.push(file, '-');
  const text = execFileSync('pdftotext', args, { maxBuffer: 1024 * 1024 * 512 }).toString('utf8');
  return text.split('\f');
}

const clean = (s) => String(s).replace(/[ \s]+/g, ' ').trim();

function decodeEntities(s) {
  return String(s)
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCodePoint(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCodePoint(Number(d)))
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&rsquo;/g, '’')
    .replace(/&lsquo;/g, '‘')
    .replace(/&ldquo;/g, '“')
    .replace(/&rdquo;/g, '”')
    .replace(/&ndash;/g, '–')
    .replace(/&mdash;/g, '—')
    .replace(/&hellip;/g, '…');
}

// Block tags become spaces; inline tags vanish, so "Auditor-General<mark>'s</mark>" stays one word.
const stripTags = (s) => clean(decodeEntities(String(s).replace(/<\/?(?:p|div|br|li|tr|td|h\d|ul|ol|table|blockquote)\b[^>]*>/gi, ' ').replace(/<[^>]+>/g, '')));

// Pulls the sentences around each mention, joining overlapping windows, up to maxChars.
function excerpt(text, { before = 320, after = 420, maxChars = 1800 } = {}) {
  const t = clean(text);
  const spans = [];
  for (const m of t.matchAll(MENTION)) {
    let a = Math.max(0, m.index - before);
    let b = Math.min(t.length, m.index + m[0].length + after);
    // Snap to sentence edges where one is close.
    const left = t.slice(a, m.index);
    const ls = left.search(/[.?!:]\s+[A-Z(‘"]/);
    if (ls >= 0 && a > 0) a += ls + 2;
    const right = t.slice(m.index + m[0].length, b);
    const rs = [...right.matchAll(/[.?!]["’)]?(\s|$)/g)].pop();
    if (rs && b < t.length) b = m.index + m[0].length + rs.index + rs[0].trimEnd().length;
    const last = spans[spans.length - 1];
    if (last && a <= last[1] + 40) last[1] = Math.max(last[1], b);
    else spans.push([a, b]);
  }
  let out = '';
  for (const [a, b] of spans) {
    const piece = (a > 0 ? '… ' : '') + t.slice(a, b) + (b < t.length ? ' …' : '');
    if (out && out.length + piece.length > maxChars) break;
    out += (out ? ' ' : '') + piece;
  }
  return out.slice(0, maxChars + 400);
}

function save(name, data) {
  const file = path.join(RAW, name);
  fs.writeFileSync(file, JSON.stringify(data, null, 1));
  console.log(`wrote ${file} (${Array.isArray(data) ? data.length + ' records' : 'object'})`);
}

module.exports = { ROOT, RAW, CACHE, WINDOW, UA, MENTION, countMentions, hasMention, sleep, get, pool, download, pdfPages, clean, decodeEntities, stripTags, excerpt, save };
