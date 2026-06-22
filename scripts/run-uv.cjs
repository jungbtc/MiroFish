const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');

const rootDir = path.resolve(__dirname, '..');
const backendDir = path.join(rootDir, 'backend');
const localUv = process.platform === 'win32'
  ? path.join(rootDir, '.uv-tool', 'Scripts', 'uv.exe')
  : path.join(rootDir, '.uv-tool', 'bin', 'uv');
const uvCommand = fs.existsSync(localUv) ? localUv : 'uv';

const env = {
  ...process.env,
  UV_CACHE_DIR: path.join(rootDir, '.uv-cache'),
};

const result = spawnSync(uvCommand, process.argv.slice(2), {
  cwd: backendDir,
  env,
  stdio: 'inherit',
  shell: process.platform === 'win32' && !fs.existsSync(localUv),
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}

process.exit(result.status ?? 0);
