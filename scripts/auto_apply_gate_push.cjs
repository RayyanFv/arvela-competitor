const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

function resolveCmd(cmd) {
  if (process.platform === 'win32' && cmd === 'pnpm') return 'pnpm.cmd';
  return cmd;
}

function run(cmd, args, opts = {}) {
  const execCmd = resolveCmd(cmd);
  const res = spawnSync(execCmd, args, {
    stdio: 'inherit',
    cwd: opts.cwd || process.cwd(),
    env: { ...process.env, ...(opts.env || {}) },
    shell: false,
  });
  if (res.status !== 0) {
    throw new Error(`Command failed: ${cmd} ${args.join(' ')}`);
  }
}

function runCapture(cmd, args, opts = {}) {
  const execCmd = resolveCmd(cmd);
  const res = spawnSync(execCmd, args, {
    encoding: 'utf-8',
    cwd: opts.cwd || process.cwd(),
    env: { ...process.env, ...(opts.env || {}) },
    shell: false,
  });
  if (res.status !== 0) {
    throw new Error(`Command failed: ${cmd} ${args.join(' ')}`);
  }
  return (res.stdout || '').trim();
}

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return;
  const lines = fs.readFileSync(filePath, 'utf-8').split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx <= 0) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    if (!(key in process.env)) process.env[key] = value;
  }
}

function getArg(name, fallback = '') {
  const idx = process.argv.indexOf(name);
  if (idx >= 0 && process.argv[idx + 1]) return process.argv[idx + 1];
  return fallback;
}

function hasScript(name) {
  try {
    const pkg = require('../package.json');
    return Boolean(pkg.scripts && pkg.scripts[name]);
  } catch {
    return false;
  }
}

function parseRepoFromRemote(remoteUrl) {
  if (!remoteUrl) return null;
  const httpsMatch = remoteUrl.match(/github\.com[/:]([^/]+)\/([^/]+?)(?:\.git)?$/i);
  if (httpsMatch) return `${httpsMatch[1]}/${httpsMatch[2]}`;
  return null;
}

function safeResolve(root, relPath) {
  if (!relPath || typeof relPath !== 'string') throw new Error('Invalid change path');
  if (path.isAbsolute(relPath)) throw new Error(`Absolute path not allowed: ${relPath}`);
  const normalized = relPath.replace(/\\/g, '/');
  const allowed = normalized === 'README.md' || normalized.startsWith('src/') || normalized.startsWith('public/');
  if (!allowed) throw new Error(`Path not allowed for autopilot write: ${relPath}`);

  const full = path.resolve(root, normalized);
  if (!full.startsWith(root)) throw new Error(`Path escapes repository: ${relPath}`);
  return full;
}

(function main() {
  const repoRoot = path.resolve(__dirname, '..');
  process.chdir(repoRoot);
  loadEnvFile(path.join(repoRoot, '.env'));
  loadEnvFile(path.join(repoRoot, '.env.local'));

  const changesFile = getArg('--changes-file');
  const message = getArg('--message', 'chore: autopilot update');
  const branch = getArg('--branch', runCapture('git', ['branch', '--show-current']) || 'main');

  if (!changesFile) throw new Error('--changes-file is required');
  if (!fs.existsSync(changesFile)) throw new Error(`Changes file not found: ${changesFile}`);

  const payload = JSON.parse(fs.readFileSync(changesFile, 'utf-8'));
  const changes = Array.isArray(payload.changes) ? payload.changes : [];
  if (!changes.length) throw new Error('No changes provided');

  console.log('== Coding Stage ==');
  for (const ch of changes) {
    const target = safeResolve(repoRoot, ch.path);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, String(ch.content ?? ''), 'utf-8');
    console.log(`written: ${ch.path}`);
  }

  console.log('\n== Review Gates ==');
  if (hasScript('lint')) {
    run('pnpm', ['lint']);
  } else {
    console.log('No lint script found, skipping lint');
  }

  if (hasScript('test')) {
    run('pnpm', ['test']);
  } else {
    console.log('No test script found, skipping test');
  }

  if (hasScript('build')) {
    const buildEnv = {
      NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://example.supabase.co',
      NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'local-dev-anon-key',
      SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY || 'local-dev-service-role-key',
    };
    run('pnpm', ['build'], { env: buildEnv });
  } else {
    throw new Error('Missing build script in package.json');
  }

  console.log('\n== Git Push ==');
  run('git', ['add', '-A']);
  const staged = runCapture('git', ['diff', '--cached', '--name-only']);
  if (!staged) {
    console.log('No staged changes. Nothing to commit or push.');
    return;
  }

  if (process.env.GITHUB_EMAIL) run('git', ['config', 'user.email', process.env.GITHUB_EMAIL]);
  if (process.env.GITHUB_NAME) run('git', ['config', 'user.name', process.env.GITHUB_NAME]);

  run('git', ['commit', '-m', message]);

  const remoteUrl = runCapture('git', ['remote', 'get-url', 'origin']);
  const repoSlug = parseRepoFromRemote(remoteUrl);
  if (process.env.GITHUB_TOKEN && repoSlug) {
    const secureRemote = `https://x-access-token:${process.env.GITHUB_TOKEN}@github.com/${repoSlug}.git`;
    run('git', ['push', '-u', secureRemote, branch]);
  } else {
    run('git', ['push', '-u', 'origin', branch]);
  }

  console.log('\nDone: coding -> gate -> commit -> push complete.');
})();
