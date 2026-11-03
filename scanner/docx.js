// Minimal DOCX reader: unzips word/document.xml and returns its paragraphs. No dependencies.
const zlib = require('zlib');
const { decodeEntities } = require('./common');

function readZipEntry(buf, wanted) {
  let eocd = -1;
  for (let i = buf.length - 22; i >= Math.max(0, buf.length - 66000); i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error('not a zip file');
  const count = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16);
  for (let n = 0; n < count; n++) {
    const method = buf.readUInt16LE(p + 10);
    const size = buf.readUInt32LE(p + 20);
    const nameLen = buf.readUInt16LE(p + 28);
    const extra = buf.readUInt16LE(p + 30);
    const comment = buf.readUInt16LE(p + 32);
    const local = buf.readUInt32LE(p + 42);
    const name = buf.toString('utf8', p + 46, p + 46 + nameLen);
    if (name === wanted) {
      const lName = buf.readUInt16LE(local + 26);
      const lExtra = buf.readUInt16LE(local + 28);
      const start = local + 30 + lName + lExtra;
      const data = buf.subarray(start, start + size);
      return method === 8 ? zlib.inflateRawSync(data) : data;
    }
    p += 46 + nameLen + extra + comment;
  }
  return null;
}

// Each paragraph: { style, text, bold } where bold is the leading run of bold text, used to spot speaker names.
function paragraphs(buf) {
  const xml = readZipEntry(buf, 'word/document.xml').toString('utf8');
  const out = [];
  for (const m of xml.matchAll(/<w:p[ >][\s\S]*?<\/w:p>/g)) {
    const p = m[0];
    const style = (p.match(/<w:pStyle w:val="([^"]+)"/) || [])[1] || '';
    let text = '';
    let bold = '';
    let inLead = true;
    for (const r of p.matchAll(/<w:r[ >][\s\S]*?<\/w:r>/g)) {
      // Word stores non-breaking hyphens as their own element: "Auditor<w:noBreakHyphen/>General".
      const t = [...r[0].matchAll(/<w:t(?: [^>]*)?>([^<]*)<\/w:t>|<w:tab\/>|<w:br\/>|<w:noBreakHyphen\/>|<w:softHyphen\/>/g)]
        .map((x) => (x[1] !== undefined ? x[1] : x[0].includes('noBreak') ? '-' : x[0].includes('soft') ? '' : ' '))
        .join('');
      const isBold = /<w:b\/>|<w:b w:val="(?:1|true)"\/>/.test(r[0]);
      text += t;
      if (inLead && isBold) bold += t;
      else if (t.trim()) inLead = false;
    }
    text = decodeEntities(text).replace(/\s+/g, ' ').trim();
    if (text) out.push({ style, text, bold: decodeEntities(bold).trim() });
  }
  return out;
}

module.exports = { paragraphs };
