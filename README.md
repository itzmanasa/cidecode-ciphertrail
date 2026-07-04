# CideCode — Forensic Bank Statement Analyser

**Team:** CideCode (3 members) | **Hackathon:** CipherTrail

---

## What this does

Uploads any Indian bank statement (PDF, Excel, CSV, image), extracts every
transaction, runs forensic audit, and detects financial fraud patterns:

- **Reversal/failed transaction detection** — flags FAILED and REVERSED transactions,
  identifies debits in Account A with no matching credit in Account B
- **Round-trip detection** — finds money cycles (A->B->C->A) across multiple accounts
- **FIFO audit** — traces every rupee debited back to its credit source
- **Pre-credit balance audit** — detects running balance tampering
- **Mule account detection** — flags accounts that receive and immediately forward funds
- **Rs.10cr victim->accused tracing** — shows exactly how funds were dispersed (cash vs cheque)

---

## Supported bank formats (tested on real data)

| Bank | Format | Method |
|------|--------|--------|
| IDFC First Bank | PDF (text) | `pdf_idfc_first` |
| Punjab National Bank | PDF (CBS REP31) | `pdf_cbs_text` |
| Bank of India | PDF (CBS REP27) | `pdf_cbs_text` |
| IndusInd Bank | XLS | `xlsx_indusind` |
| State Bank of India | XLS/XLSX | `xlsx_sbi` |
| Any bank | PDF (generic table) | `pdf_text` |
| Any bank | CSV | `csv` |
| Any bank | Scanned PDF/Image | `pdf_ocr` (Tesseract) |

---

## Quick start (30 seconds)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the server
uvicorn app.main:app --port 8000

# 3. Open API docs
# Go to: http://localhost:8000/docs
```

**Upload a bank statement and get full analysis in one call:**
```bash
curl -X POST http://localhost:8000/api/upload \
     -F "file=@your_statement.pdf"
```

---

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/upload` | POST | Upload one file -> parse + clean + audit + save |
| `/api/upload-multi` | POST | Upload up to 10 files -> merged unified timeline |
| `/api/analyse` | POST | Cross-account reversal + round-trip detection |
| `/api/audit` | POST | FIFO + pre-credit balance audit |
| `/api/summary` | POST | Dashboard stats (total in/out, cash/cheque counts) |
| `/api/transactions` | POST | Cleaned transaction list with status flags |
| `/api/accounts` | GET | List all uploaded accounts |
| `/api/accounts/{acc}` | GET | Full statement for one account |
| `/api/all-transactions` | GET | All transactions across all accounts |
| `/api/cache/status` | GET | Check offline mode readiness |
| `/api/cache/{key}` | GET | Pre-cached demo data (offline fallback) |

Full interactive docs at `http://localhost:8000/docs`

---

## Response schema

Every upload returns:
```json
{
  "success": true,
  "statement": {
    "account_number": "17771917925",
    "bank_name": "IDFC First Bank",
    "owner_name": "PIONEER HOLDINGS",
    "period_from": "2025-05-07",
    "period_to": "2025-07-23",
    "transactions": [...]
  },
  "summary_stats": {
    "total_transactions": 178,
    "failed_count": 2,
    "total_debit": 14078460.13,
    "total_credit": 14078460.13,
    "cash_withdrawal_count": 3,
    "cash_withdrawal_total": 1000.0,
    "balance_audit_clean": true,
    "unsourced_debits": 0
  },
  "audit_results": {
    "pre_credit_audit": { "mismatch_count": 0, "is_clean": true },
    "fifo_audit": { "unsourced_count": 0, "is_clean": true }
  }
}
```

---

## Transaction status flags

Every transaction is classified at parse time:

| Status | Meaning | Impact on audit |
|--------|---------|-----------------|
| `SUCCESS` | Normal transaction | Included in all audits |
| `FAILED` | Payment failed (keyword-detected in narration) | **Excluded** from balance + FIFO audits |
| `REVERSAL` | Transaction reversed | **Excluded** from balance + FIFO audits |

> **Why exclusion matters:** Including FAILED transactions in balance audits produces
> absurd results — every failed debit looks like a balance discrepancy. The judges
> specifically flagged this as a critical requirement.

---

## How the reversal detection works

**Layer 1 — Explicit (single statement):**
Narration text scanned for keywords: `failed`, `reversed`, `returned`, `bounced`,
`NEFT RET`, `rejected`. Flagged at parse time.

**Layer 2 — Cross-account (the hard one):**
For every successful debit in Account A, searches all other uploaded accounts for
a matching credit (same amount ±Rs.50 or ±2%) within 3 days. If none found ->
`UNMATCHED_DEBIT` — money left A but never arrived anywhere visible.

**Round-trip:**
Within one account: debit followed by same-amount credit within 30 days.
Across accounts: NetworkX `simple_cycles()` on the transaction graph (P2's engine).

---

## How FIFO audit works

Matches each debit to the **earliest available unmatched credit** chronologically.
Answers: *"Where did this money come from?"*

Example — Rs.10cr victim->accused:
```
[2024-05-01] CREDIT  Rs.10,00,00,000  (RTGS from victim)     ← source
[2024-05-02] DEBIT   Rs.50,00,000     ATM CASH WITHDRAWAL    ← sourced from above
[2024-05-03] DEBIT   Rs.50,00,000     CHEQUE PAYMENT 001234  ← sourced from above
...
```
Every debit traced back to the Rs.10cr credit from the victim.

---

## Performance

| Dataset size | Processing time |
|-------------|----------------|
| 85 transactions (SBI) | < 0.1s |
| 228 transactions (BOI) | < 0.1s |
| 1,518 transactions (SBI large) | 0.3s |
| 3,000 transactions (stress test) | 0.14s |
| 10,000 transactions (stress test) | 1.25s |

---

## Offline mode (demo fallback)

If the server crashes during the demo, pre-cached responses are available:

```bash
GET /api/cache/status           # check what's cached
GET /api/cache/accounts         # cached account list
GET /api/cache/all_transactions # cached transaction data
GET /api/cache/analyse_demo     # cached anomaly detection results
GET /api/cache/summary_demo     # cached summary stats
```

The cache is rebuilt automatically on every server startup.

---

## Project structure

```
CIDECODE/
├── app/
│   ├── main.py                    # FastAPI app
│   ├── schemas.py                 # Shared data models
│   ├── parsers/
│   │   ├── registry.py            # Bank parser registry (9 parsers)
│   │   ├── dispatcher.py          # Smart format detection + routing
│   │   ├── pdf_parser.py          # IDFC First + CBS + generic PDF
│   │   ├── spreadsheet_parser.py  # IndusInd + SBI + generic XLS/CSV
│   │   ├── ocr_parser.py          # Scanned PDFs + images (Tesseract)
│   │   └── edge_cases.py          # Fuzzy headers, merged cells, etc.
│   ├── routes/
│   │   ├── upload.py              # POST /api/upload
│   │   ├── multi_upload.py        # POST /api/upload-multi
│   │   ├── transactions.py        # /api/audit + /api/summary + /api/clean
│   │   ├── accounts.py            # /api/accounts + /api/all-transactions
│   │   ├── analyse.py             # POST /api/analyse (reversal detection)
│   │   └── cache_routes.py        # /api/cache/* (offline fallback)
│   ├── utils/
│   │   ├── cleaner.py             # Dedup + FIFO + balance audit + stats
│   │   └── reversal_detector.py   # Cross-account reversal detection
│   └── db/
│       └── database.py            # SQLite persistence layer
├── offline_cache.py               # Cache builder
├── cache/                         # Pre-built cached responses (commit to git)
├── requirements.txt
├── forensic_audit.db              # SQLite database (auto-created)
└── test_*.py                      # Test suite (run before hackathon)
```

---



---


