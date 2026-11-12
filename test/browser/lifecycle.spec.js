// A real navigation must release its old transport. Chromium 149+ can cache
// a page with an open socket; frozen JavaScript cannot consume its patches.
const { test, expect, chromium } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const { once } = require('node:events');
const { wsServer: WebSocketServer } = require(path.join(
  path.dirname(require.resolve('playwright-core')), 'lib/utilsBundle.js'));
const client = fs.readFileSync(process.env.LIVE_CLIENT_SOURCE ||
  path.join(__dirname, '../../priv/lib/live/client.js'), 'utf8');

test('a cached page releases its socket and resynchronizes without losing private input', async () => {
  const connections = new Set();
  const upgrades = [];
  const sessions = new Set();
  let revision = 0;
  const markup = () => `<output id="version">${revision}</output><input id="draft">`;
  const server = http.createServer((request, response) => {
    if (request.url === '/client.js') {
      response.writeHead(200, { 'Content-Type': 'text/javascript' });
      response.end(client);
      return;
    }
    response.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    response.end(`<!doctype html><html><body><main id="live-root">${markup()}</main>
      <script src="/client.js"></script><script>
      window.lifecycle=[];addEventListener('pageshow',e=>lifecycle.push({type:e.type,persisted:e.persisted}));
      Live.connect({root:document.getElementById('live-root'),url:'ws://'+location.host+'/ws'+location.pathname,heartbeatMs:0});
      </script></body></html>`);
  });
  const sockets = new WebSocketServer({ server });
  sockets.on('connection', (socket, request) => {
    const url = new URL(request.url, 'http://localhost');
    const sid = url.searchParams.get('live-sid');
    connections.add(socket);
    upgrades.push({ sid, path: url.pathname, mounted: url.searchParams.get('live-mounted') });
    socket.on('close', () => connections.delete(socket));
    // The same session may request a fresh mount: unseen patches can race
    // page freezing, so its cached DOM cannot be assumed to match the server.
    if (!sessions.has(sid) || url.searchParams.get('live-mounted') === '0') {
      socket.send(JSON.stringify(['mount', markup(), { 'input-ack': true }]));
    }
    sessions.add(sid);
  });
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await chromium.launch({
    headless: true,
    executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH,
    // Playwright disables bfcache by default. Exercise the real browser mode
    // used by normal users and native recordings, rather than hiding the leak.
    ignoreDefaultArgs: ['--disable-back-forward-cache'],
  });
  try {
    const page = await browser.newPage();
    await page.goto(origin + '/one');
    await page.waitForFunction(() => document.documentElement.dataset.mounted === '1');
    await page.locator('#draft').fill('Private words · كلمات');
    const first = await page.evaluate(() => {
      window.originalInput = document.getElementById('draft');
      return { origin: performance.timeOrigin, url: Live.ws.url };
    });
    await page.goto(origin + '/two');
    await page.waitForFunction(() => document.documentElement.dataset.mounted === '1');
    await expect.poll(() => connections.size, { timeout: 1500 }).toBe(1);
    revision = 1;
    await page.goBack({ waitUntil: 'commit' });
    await page.waitForFunction(() => Live.ws.readyState === WebSocket.OPEN);
    expect(await page.evaluate(() => lifecycle.some(e => e.persisted))).toBe(true);
    expect(await page.evaluate(() => performance.timeOrigin)).toBe(first.origin);
    await expect(page.locator('#version')).toHaveText('1');
    await expect(page.locator('#draft')).toHaveValue('Private words · كلمات');
    expect(await page.evaluate(() => new URL(Live.ws.url).searchParams.get('live-sid')))
      .toBe(new URL(first.url).searchParams.get('live-sid'));
    await expect.poll(() => connections.size).toBe(1);
    expect(upgrades.at(-1).mounted).toBe('0');
  } finally {
    await browser.close();
    for (const socket of connections) socket.terminate();
    await new Promise(resolve => sockets.close(resolve));
    await new Promise(resolve => server.close(resolve));
  }
});
