# CipherTrail — Karnataka CID Financial Forensic Investigation Platform

Production-ready React 19 + TypeScript + Vite frontend for an AI-powered financial
forensic investigation platform. Consumes a pre-built backend at `http://localhost:8001`.

## Stack
React 19 · Vite · TypeScript · Tailwind CSS · React Router · TanStack Query · Axios ·
Framer Motion · React Flow · Recharts · React Hook Form · Lucide Icons · jsPDF · html2canvas

## Getting started
```bash
npm install
npm run dev
```
The app expects the backend running at `http://localhost:8001` exposing:
- `POST /upload` (multipart `file`)
- `GET /analyse/{case_id}`
- `GET /transactions/{case_id}`
- `GET /cases`
- `POST /api/clean` (optional, response shape: `{ success, statement, audit_results, summary_stats }`)

## Folder structure
```
src/
  api/         axios client + endpoint functions
  components/  componentized UI grouped by feature (dashboard, moneyflow, roundtrip, ...)
  pages/       route-level pages
  hooks/       React Query hooks
  layouts/     AppLayout (sidebar + top nav shell)
  context/     active case (case_id) context, persisted to localStorage
  services/    PDF evidence-report generator
  utils/       formatting + class-merge helpers
  types/       TypeScript types mirroring the backend contract
```

## Pages
Upload (landing) · Dashboard · Money Flow (React Flow graph) · Round Tripping ·
Investigation Findings · Transactions · Evidence Report (jsPDF) · Uploaded Cases · Settings

## Notes
- No backend logic, mock endpoints, or API contract changes were introduced.
- The active case is tracked via `CaseProvider` and persisted in `localStorage`, so refreshing
  any page keeps the investigator on the same case.
- `/api/clean` response handling follows the documented nested shape — fields are always
  read from `data.statement`, `data.summary_stats`, and `data.audit_results`.
