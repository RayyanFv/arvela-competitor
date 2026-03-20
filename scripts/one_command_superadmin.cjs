#!/usr/bin/env node
/*
 One-command flow:
 1) Trigger orchestrator tech delivery pipeline
 2) Apply code changes from JSON changeset
 3) Run lint/test/build gate
 4) Auto commit + push to target branch
*/

const fs = require('fs')
const path = require('path')
const { spawnSync } = require('child_process')

const ROOT = process.cwd()

function loadEnvFile(filePath) {
  if (!fs.existsSync(filePath)) return
  const lines = fs.readFileSync(filePath, 'utf8').split(/\r?\n/)
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const eq = trimmed.indexOf('=')
    if (eq <= 0) continue
    const key = trimmed.slice(0, eq).trim()
    const value = trimmed.slice(eq + 1).trim()
    if (!process.env[key]) process.env[key] = value
  }
}

function parseArgs(argv) {
  const out = {
    objective: '',
    company: process.env.ORCHESTRATOR_COMPANY_ID || 'arvela',
    base: process.env.ORCHESTRATOR_API_BASE || process.env.NEXT_PUBLIC_ORCHESTRATOR_API_BASE || 'http://127.0.0.1:8013',
    changesFile: '',
    branch: 'feature/owner-tech-workflow',
    message: 'feat: super admin dashboard update via one-command flow',
  }

  for (let i = 2; i < argv.length; i += 1) {
    const a = argv[i]
    if (a === '--objective') out.objective = argv[++i] || out.objective
    else if (a === '--company') out.company = argv[++i] || out.company
    else if (a === '--base') out.base = argv[++i] || out.base
    else if (a === '--changes-file') out.changesFile = argv[++i] || out.changesFile
    else if (a === '--branch') out.branch = argv[++i] || out.branch
    else if (a === '--message') out.message = argv[++i] || out.message
  }
  return out
}

async function run() {
  loadEnvFile(path.join(ROOT, '.env'))
  loadEnvFile(path.join(ROOT, '.env.local'))

  const args = parseArgs(process.argv)

  if (!args.objective.trim()) {
    throw new Error('Missing --objective')
  }
  if (!args.changesFile.trim()) {
    throw new Error('Missing --changes-file')
  }

  const absoluteChanges = path.isAbsolute(args.changesFile)
    ? args.changesFile
    : path.join(ROOT, args.changesFile)

  if (!fs.existsSync(absoluteChanges)) {
    throw new Error(`changes file not found: ${absoluteChanges}`)
  }

  console.log('[1/2] Trigger orchestration plan...')
  const runUrl = `${args.base}/api/v1/${args.company}/pipelines/tech_delivery/run`
  const planResp = await fetch(runUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective: args.objective }),
  })

  if (!planResp.ok) {
    const text = await planResp.text()
    throw new Error(`orchestrator failed (${planResp.status}): ${text}`)
  }

  const planData = await planResp.json()
  console.log(`Orchestration run OK: ${planData.run_id || 'run-id-unavailable'}`)

  console.log('[2/2] Apply + gate + commit + push...')
  const autoArgs = [
    'scripts/auto_apply_gate_push.cjs',
    '--changes-file',
    absoluteChanges,
    '--message',
    args.message,
    '--branch',
    args.branch,
  ]

  const child = spawnSync(process.execPath, autoArgs, {
    cwd: ROOT,
    stdio: 'inherit',
    env: process.env,
  })

  if (child.status !== 0) {
    throw new Error('auto apply/gate/push failed')
  }

  console.log('One-command flow completed successfully.')
}

run().catch((err) => {
  console.error(err.message || err)
  process.exit(1)
})
