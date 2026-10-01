import { copyFile, mkdir, readFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';

// Explicit manifest keeps desktop tools and CI credentials outside the public site.
const files = ['index.html', 'styles.css', 'main.js', 'beta.html', 'beta.css', 'beta.js', 'beta-form.js'];
const root = new URL('../', import.meta.url);
const contents = new Map(await Promise.all(files.map(async file => [file, await readFile(new URL(file, root))])));
for (const file of files.filter(file => file.endsWith('.js'))) {
  execFileSync(process.execPath, ['--check', new URL(file, root).pathname.replace(/^\/([A-Z]:)/, '$1')]);
}
assert.match(contents.get('beta.html').toString(), /noindex,\s*nofollow/);
assert.doesNotMatch(contents.get('index.html').toString(), /href=["']\/?beta(?:["'#/])/i);

if (process.argv[2] === 'verify') {
  const base = process.argv[3];
  assert.ok(base && new URL(base).protocol === 'https:', 'HTTPS deployment URL required');
  let lastError;
  for (let attempt = 0; attempt < 12; attempt++) {
    try {
      for (const file of files) {
        const path = file === 'index.html' ? '/' : file === 'beta.html' ? '/beta' : `/${file}`;
        const response = await fetch(new URL(path, base), { signal: AbortSignal.timeout(15000), cache: 'no-store' });
        assert.equal(response.status, 200, path);
        assert.deepEqual(Buffer.from(await response.arrayBuffer()), contents.get(file), `Published bytes differ: ${path}`);
      }
      console.log(`Verified ${files.length} published assets and /beta at ${base}`);
      process.exit(0);
    } catch (error) {
      lastError = error;
      if (attempt < 11) await new Promise(resolve => setTimeout(resolve, 10000));
    }
  }
  throw lastError;
} else {
  await mkdir(new URL('dist/site/', root), { recursive: true });
  for (const file of files) await copyFile(new URL(file, root), new URL(`dist/site/${file}`, root));
  console.log(`Site validated and staged: ${files.length} assets`);
}
