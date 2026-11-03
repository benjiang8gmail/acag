// Small local receiver: pages open in the browser POST scraped JSON here, and it lands in data/raw/.
// Needed for WA and SA, whose Hansard sites only answer a real browser.
// Usage: node scanner/receiver.js [port]
const http = require('http');
const fs = require('fs');
const path = require('path');

const port = Number(process.argv[2] || 8765);
const outDir = path.join(__dirname, '..', 'data', 'raw');
fs.mkdirSync(outDir, { recursive: true });

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
  'Access-Control-Allow-Private-Network': 'true',
};

http.createServer((req, res) => {
  if (req.method === 'OPTIONS') {
    res.writeHead(204, cors);
    return res.end();
  }
  if (req.method === 'GET' && req.url.startsWith('/relay')) {
    // A public page can't reach localhost directly, but it can postMessage to this tab, which can.
    res.writeHead(200, { ...cors, 'Content-Type': 'text/html' });
    return res.end(`<!doctype html><title>relay</title><pre id=log>relay ready</pre><script>
      addEventListener('message', async (e) => {
        const { name, body } = e.data || {};
        if (!name) return;
        const r = await fetch('/' + encodeURIComponent(name), { method: 'POST', body });
        document.getElementById('log').textContent += '\\n' + name + ' ' + body.length + ' ' + r.status;
        e.source && e.source.postMessage({ saved: name, status: r.status }, '*');
      });
    </script>`);
  }
  if (req.method === 'GET') {
    res.writeHead(200, { ...cors, 'Content-Type': 'text/plain' });
    return res.end('ok');
  }
  const name = decodeURIComponent(new URL(req.url, 'http://x').pathname.slice(1)).replace(/[^\w.-]/g, '_');
  const chunks = [];
  req.on('data', (c) => chunks.push(c));
  req.on('end', () => {
    let body = Buffer.concat(chunks);
    // Form posts (top-level navigations from the Hansard site) carry the JSON in a "payload" field.
    if ((req.headers['content-type'] || '').includes('x-www-form-urlencoded')) {
      body = Buffer.from(new URLSearchParams(body.toString('utf8')).get('payload') || '', 'utf8');
    }
    fs.writeFileSync(path.join(outDir, name), body);
    console.log(`${new Date().toISOString()} saved ${name} ${body.length} bytes`);
    res.writeHead(200, { ...cors, 'Content-Type': 'text/plain' });
    res.end(`saved ${name} ${body.length} bytes`);
  });
}).listen(port, '127.0.0.1', () => console.log(`receiver listening on ${port}, writing to ${outDir}`));
