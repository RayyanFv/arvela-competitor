const { spawnSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function shellQuote(arg) {
  if (arg === undefined || arg === null) return '""';
  const s = String(arg);
  if (!/[\s"']/g.test(s)) return s;
  return `"${s.replace(/"/g, '\\"')}"`;
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
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

function run(cmd, args, opts = {}) {
  const pretty = [cmd, ...args].join(' ');
  const command = [cmd, ...args.map(shellQuote)].join(' ');
  console.log(`\n$ ${opts.pretty || pretty}`);
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

function parseRepoFromRemote(remoteUrl) {
  if (!remoteUrl) return null;
  // https://github.com/owner/repo.git
  const httpsMatch = remoteUrl.match(/github\.com[/:]([^/]+)\/([^/]+?)(?:\.git)?$/i);
  if (httpsMatch) return `${httpsMatch[1]}/${httpsMatch[2]}`;
  return null;
}

async function createPullRequest({ token, repo, base, head, title, body }) {
  const url = `https://api.github.com/repos/${repo}/pulls`;
  const payload = { title, head, base, body };
  const resp = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: 'application/vnd.github+json',
      'Content-Type': 'application/json',
      'User-Agent': 'arvela-auto-safe-pipeline',
    },
    body: JSON.stringify(payload),
  });

  if (!resp.ok) {
    const msg = await resp.text();
    throw new Error(`Create PR failed: ${resp.status} ${msg}`);
  }
  return resp.json();
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
  loadEnvFile(path.resolve(process.cwd(), '.env'));
  loadEnvFile(path.resolve(process.cwd(), '.env.local'));

  const message = getArg('--message', 'chore: automated safe push');
  const branchArg = getArg('--branch', '');
  const baseBranch = getArg('--base', 'main');
  const openPr = getArg('--open-pr', 'false') === 'true';

  const gitEmail = process.env.GIT_AUTHOR_EMAIL || process.env.GITHUB_EMAIL || '';
  const gitName = process.env.GIT_AUTHOR_NAME || process.env.GITHUB_NAME || '';
  const githubToken = process.env.GITHUB_TOKEN || process.env.GH_TOKEN || '';

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

  if (gitEmail) {
    run('git', ['config', 'user.email', gitEmail]);
  }
  if (gitName) {
    run('git', ['config', 'user.name', gitName]);
  }

  run('git', ['add', '-A']);

  const staged = runCapture('git', ['diff', '--cached', '--name-only']);
  if (!staged) {
    console.log('No staged changes. Nothing to commit or push.');
    return;
  }

  run('git', ['commit', '-m', message]);

  const remoteUrl = runCapture('git', ['remote', 'get-url', 'origin']);
  const repoSlug = parseRepoFromRemote(remoteUrl);
  if (githubToken && repoSlug) {
    const secureRemote = `https://x-access-token:${githubToken}@github.com/${repoSlug}.git`;
    run('git', ['push', '-u', secureRemote, targetBranch], {
      pretty: `git push -u origin ${targetBranch}`,
    });
  } else {
    run('git', ['push', '-u', 'origin', targetBranch]);
  }

  if (openPr && githubToken && repoSlug) {
    const pr = await createPullRequest({
      token: githubToken,
      repo: repoSlug,
      base: baseBranch,
      head: targetBranch,
      title: message,
      body: 'Automated PR generated by auto-safe pipeline.',
    });
    console.log(`\nPR created: ${pr.html_url}`);
  }

  console.log('\nDone. Branch pushed successfully.');
})();
