const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const srcRoot = path.join(root, 'src');
const reportDir = path.join(root, 'reports');
const reportPath = path.join(reportDir, 'repo-insight.md');

function walk(dir, out = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (['node_modules', '.next', '.git'].includes(entry.name)) continue;
      walk(full, out);
    } else {
      out.push(full);
    }
  }
  return out;
}

function topFolders(files) {
  const map = new Map();
  for (const f of files) {
    const rel = path.relative(srcRoot, f);
    const first = rel.split(path.sep)[0] || 'root';
    map.set(first, (map.get(first) || 0) + 1);
  }
  return [...map.entries()].sort((a, b) => b[1] - a[1]);
}

if (!fs.existsSync(srcRoot)) {
  console.error('src directory not found');
  process.exit(1);
}

const files = walk(srcRoot);
const jsLike = files.filter((f) => /\.(js|jsx|ts|tsx)$/.test(f));
const folders = topFolders(files);

fs.mkdirSync(reportDir, { recursive: true });
const lines = [];
lines.push('# Repo Insight');
lines.push('');
lines.push(`Generated at: ${new Date().toISOString()}`);
lines.push('');
lines.push(`- Total files under src: ${files.length}`);
lines.push(`- Code files (js/jsx/ts/tsx): ${jsLike.length}`);
lines.push('');
lines.push('## Top Folders by File Count');
lines.push('');
for (const [name, count] of folders.slice(0, 12)) {
  lines.push(`- ${name}: ${count}`);
}
lines.push('');
lines.push('## Suggested Focus');
lines.push('');
lines.push('- Prioritize changes inside src/app/dashboard and src/lib/actions for workflow automation features.');
lines.push('- Keep schema untouched; focus on UI flow, server actions, and guardrail pipelines.');

fs.writeFileSync(reportPath, lines.join('\n'), 'utf-8');
console.log(`Insight report written: ${reportPath}`);
