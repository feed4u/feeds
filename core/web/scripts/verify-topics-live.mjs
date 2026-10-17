// Run: node core/web/scripts/verify-topics-live.mjs
// Builds 4u, reads the live digest, and checks the rendered labels after reload.
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { preview } from 'vite';
import { chromium } from 'playwright';

const root = fileURLToPath(new URL('../', import.meta.url));
const result = spawnSync('npm', ['run', 'build'], {
  cwd: root, env: { ...process.env, VITE_VERTICAL: '4u' }, stdio: 'inherit',
});
assert.equal(result.status, 0, 'production build');
const response = await fetch('https://4u.ai/data/4u/archive/news/topics/topics_latest.json', {
  signal: AbortSignal.timeout(30_000),
});
assert.equal(response.status, 200, 'live digest response');
const payload = await response.json();
const directory = `${root}dist/data/4u/archive/news/topics`;
await mkdir(directory, { recursive: true });
await writeFile(`${directory}/topics_latest.json`, JSON.stringify(payload));
const covered = new Intl.DateTimeFormat('en-US', {
  weekday: 'long', month: 'long', day: 'numeric', timeZone: 'UTC',
}).format(new Date(`${payload.date}T00:00:00Z`));
const heading = `Topics for ${covered}`;
const server = await preview({ root, preview: { host: '127.0.0.1', port: 4179, strictPort: true } });
let browser;
try {
  browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ timezoneId: 'Pacific/Kiritimati' });
  for (let visit = 0; visit < 2; visit++) {
    if (visit === 0) await page.goto('http://127.0.0.1:4179/topics');
    else await page.reload();
    await page.getByRole('heading', { name: heading, exact: true }).waitFor();
    await page.waitForFunction(expected => document.title === expected, `${heading} — 4u.ai — AI & ML News Feed`);
    assert.equal(await page.locator('h1').innerText(), heading);
  }
  await page.screenshot({ path: '/tmp/news-topics-live.png', fullPage: true });
  console.log(JSON.stringify({ date: payload.date, generated_at: payload.generated_at,
    heading, title: await page.title(), reload: 'passed', screenshot: '/tmp/news-topics-live.png' }));
} finally {
  await browser?.close();
  await new Promise(resolve => server.httpServer.close(resolve));
}
