#  CipherTrail — Graph & Intelligence Engine (P2)

> **"From 3 days to 3 minutes."**  
> The brain behind CipherTrail's fraud detection — built for Karnataka CID.

---

##  What This Module Does

Given bank statements from multiple accounts, this engine:

-  **Detects round-trip fraud** — money that leaves an account and secretly returns through mule chains
-  **Flags mule accounts** — accounts with suspicious velocity (80%+ of funds moved within 2 hours)
-  **Traces every rupee** — FIFO audit trail showing exactly where credited money went
-  **Generates AI briefs** — formal police report style investigation summary via Groq (Llama 3.3)
-  **Issues Section 65B certificates** — court-admissible electronic evidence under Bharatiya Sakshya Adhiniyam 2023
-  **Packages evidence** — one-click ZIP with hashed files, audit log, and 65B certificate

---

##  Setup

**1. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Create a `.env` file:**
GROQ_API_KEY=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

Get a free key at [console.groq.com](https://console.groq.com)

**3. Run the API:**
```bash
python main.py
```
API starts at `http://localhost:8001`  
Interactive docs at `http://localhost:8001/docs`

---

##  API Endpoints

| Method | Endpoint | What it does |
|--------|----------|-------------|
| `POST` | `/upload` | Upload a bank statement PDF/CSV |
| `GET` | `/analyse/{case_id}` | Full fraud analysis — round trips, graph, AI brief |
| `GET` | `/transactions/{case_id}` | Raw transaction table |
| `GET` | `/certificate/{case_id}` | Section 65B certificate |
| `GET` | `/evidence-package/{case_id}` | Download complete evidence ZIP |
| `GET` | `/cases` | List all uploaded cases |
| `GET` | `/` | Health check |

---

##  File Structure
p2-graph/
├── main.py                # FastAPI — 7 endpoints on port 8001
├── graph_engine.py        # Round-trip detection, mule flagging (NetworkX)
├── fifo_trail.py          # FIFO money trail tracker
├── analytics.py           # Cash / cheque / UPI breakdown
├── ai_brief.py            # Groq AI investigation brief generator
├── findings.py            # Master function — ties everything together
├── database.py            # SQLite DB + SHA-256 chain of custody
├── adapter.py             # Converts P1's BankStatement → engine format
├── section_65b.py         # Section 65B certificate auto-generator
├── evidence_package.py    # One-click evidence ZIP package
├── validate_engine.py     # Validation against ground truth dataset
├── generate_test_data.py  # 2000 transaction synthetic stress test
├── test_data.py           # Mock transaction data for unit testing
└── requirements.txt       # Python dependencies
---

##  How the Fraud Detection Works
Upload PDF
↓
P1 Parser extracts transactions
↓
Adapter converts to engine format
↓
Reversals / failed txns excluded ← CRITICAL STEP
↓
NetworkX graph built (nodes = accounts, edges = transactions)
↓
DFS cycle detection → Round trips found
↓
Velocity analysis → Mule accounts flagged
↓
FIFO trail → Every rupee traced to destination
↓
Groq AI → Formal investigation brief drafted
↓
Section 65B certificate generated
↓
Evidence ZIP packaged and ready for court


---

##  Performance

| Dataset | Transactions | Time |
|---------|-------------|------|
| Small | 5 | < 2s |
| Medium | 2,000 | 0.20s |
| Large | 10,000 | < 5s |

---

##  Validation Results

Tested against P1's synthetic ground truth dataset (1,843 transactions, 16 accounts):

-  **Round trips** — Found 50 cycles (ground truth: 3 minimum)
-  **Reversals** — 0 detected, 0 expected 
-  **Mule accounts** — All 5 ground truth mules correctly identified 

---

##  Legal Compliance

This module auto-generates a **Section 65B certificate** under the  
**Bharatiya Sakshya Adhiniyam (BSA) 2023**, making all digital evidence  
court-admissible with:

- SHA-256 file hash verification
- System metadata capture (OS, hostname, timestamp)
- Full chain of custody audit log
- Officer certification fields

---

*Built for CIDECODE 2026 — Karnataka CID Hackathon*  
*Team CipherTrail | P2 — Graph & Intelligence Engine*
