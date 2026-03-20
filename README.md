This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://github.com/vercel/next.js/tree/canary/packages/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.js`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

## Auto Safe Pipeline (Analyze -> Build -> Test -> Push)

This repository includes automation helpers for a guarded push flow:

1. Analyze repository structure and generate report:

```bash
pnpm insight
```

Report output:

- `reports/repo-insight.md`

2. Run guarded automation (analyze + build + optional test + commit + push):

```bash
pnpm safe:push -- --message "feat: your change summary" --branch feature/your-branch
```

3. Non-interactive mode with email + token (VPS/CI friendly):

Create env file first in the repository root:

```bash
cp .env.example .env
```

Then fill `GITHUB_EMAIL`, `GITHUB_NAME`, and `GITHUB_TOKEN` in `.env`.

```bash
export GITHUB_EMAIL="you@example.com"
export GITHUB_NAME="Your Name"
export GITHUB_TOKEN="ghp_xxx"

pnpm safe:push -- --message "feat: your change summary" --branch feature/your-branch --base main --open-pr true
```

PowerShell equivalent:

```powershell
$env:GITHUB_EMAIL="you@example.com"
$env:GITHUB_NAME="Your Name"
$env:GITHUB_TOKEN="ghp_xxx"
pnpm safe:push -- --message "feat: your change summary" --branch feature/your-branch --base main --open-pr true
```

Notes:

- `pnpm build` is mandatory and must pass.
- `pnpm test` runs if a test script exists; otherwise skipped.
- Push happens only if there are staged/changed files after quality gates pass.
- If `GITHUB_TOKEN` is set, push uses token-based HTTPS auth without interactive login.
- If `--open-pr true` and `GITHUB_TOKEN` are set, a PR will be created automatically.
- CI guardrail is defined in `.github/workflows/guardrail-ci.yml`.

## Autopilot Branch Flow (Write Code -> Gate -> Push, No PR)

For super-admin automation where code changes are provided as a change-set JSON:

```bash
node scripts/auto_apply_gate_push.cjs --changes-file .automation/changes.json --message "feat: autopilot update" --branch feature/owner-tech-workflow
```

`changes.json` format:

```json
{
	"changes": [
		{
			"path": "src/app/example/page.jsx",
			"content": "export default function Page(){ return <div>Hello</div> }"
		}
	]
}
```

Safety constraints:

- Only writes to `src/**`, `public/**`, or `README.md`.
- Runs lint/test/build gates before commit/push.
- Pushes to branch only (no PR creation in this flow).
