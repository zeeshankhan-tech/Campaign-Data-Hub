# Campaign Data Hub — Frontend

React + TypeScript (Vite) dashboard for campaign metrics and delivery data health.

## Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

App: http://localhost:5173  
API base URL: `VITE_API_BASE_URL` (default `http://localhost:8000`)

## Views

- **Campaign metrics** — sortable spend/CTR table, platform + date filters, filter-aware totals
- **Data health** — delivery list with health badges and quality-report drill-down

## Build

```bash
npm run build
```

Requires the backend running for live data.
