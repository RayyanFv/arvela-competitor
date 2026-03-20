const { spawnSync } = require('child_process');
const fs = require('fs');

function shellQuote(arg) {
  if (arg === undefined || arg === null) return '""';
  const s = String(arg);
  if (!/[\s"']/g.test(s)) return s;
  return `"${s.replace(/"/g, '\\"')}"`;
}

function run(cmd, args, opts = {}) {
  const pretty = [cmd, ...args].join(' ');
  const command = [cmd, ...args.map(shellQuote)].join(' ');
  console.log(`\n$ ${pretty}`);
  const res = spawnSync(command, {
    stdio: 'inherit',
    shell: true,
    env: { ...process.env, ...(opts.env || {}) },
  });
  if (res.status !== 0) {
    throw new Error(`Command failed: ${pretty}`);
  }
}

function runCapture(cmd, args) {
  const command = [cmd, ...args.map(shellQuote)].join(' ');
  const res = spawnSync(command, {
    encoding: 'utf-8',
    shell: true,
  });
  if (res.status !== 0) {
    throw new Error(`Command failed: ${cmd} ${args.join(' ')}`);
  }
  return (res.stdout || '').trim();
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

(async function main() {
  const message = getArg('--message', 'chore: automated safe push');
  const branchArg = getArg('--branch', '');

  console.log('== Auto Safe Pipeline ==');
  run('node', ['scripts/repo_insight.cjs']);

  const hasNodeModules = fs.existsSync('node_modules');
  if (!hasNodeModules) {
    console.log('\n== Dependencies ==');
    run('pnpm', ['install', '--frozen-lockfile']);
  }

  console.log('\n== Quality Gates ==');
  const buildEnv = {
    NEXT_PUBLIC_SUPABASE_URL:
      process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://example.supabase.co',
    NEXT_PUBLIC_SUPABASE_ANON_KEY:
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'local-dev-anon-key',
    SUPABASE_SERVICE_ROLE_KEY:
      process.env.SUPABASE_SERVICE_ROLE_KEY || 'local-dev-service-role-key',
  };

  if (hasScript('build')) {
    run('pnpm', ['build'], { env: buildEnv });
  } else {
    throw new Error('Missing build script in package.json');
  }

  if (hasScript('test')) {
    run('pnpm', ['test']);
  } else {
    console.log('No test script found, skipping pnpm test');
  }

  console.log('\n== Git Commit + Push ==');
  const currentBranch = runCapture('git', ['branch', '--show-current']);
  const targetBranch = branchArg || currentBranch;
  if (!targetBranch) throw new Error('Cannot determine target branch');

  run('git', ['add', '-A']);

  const staged = runCapture('git', ['diff', '--cached', '--name-only']);
  if (!staged) {
    console.log('No staged changes. Nothing to commit or push.');
    return;
  }

  run('git', ['commit', '-m', message]);
  run('git', ['push', '-u', 'origin', targetBranch]);

  console.log('\nDone. Branch pushed successfully.');
})();
