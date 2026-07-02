\# CipherTrail — P2 Graph \& Intelligence Engine



\## What this does

\- Detects round-trip fraud patterns (money laundering cycles)

\- Flags mule accounts using velocity anomaly detection

\- Traces money flow using FIFO audit trail

\- Generates AI investigation brief using Groq (Llama 3.3)

\- Auto-generates Section 65B court-admissible certificate

\- Creates one-click evidence ZIP package



\## Setup

```bash

pip install -r requirements.txt

```



Create a `.env` file with:

GROQ\_API\_KEY=gsk\_4FmfiY0Tk7DbSIxicNIkWGdyb3FY4mv7v8SOYvbw4ecSV5MncuQN



\## Run

```bash

python main.py

```

API runs on `http://localhost:8001`



\## Endpoints

| Endpoint | Description |

|----------|-------------|

| `POST /upload` | Upload bank statement |

| `GET /analyse/{case\_id}` | Full fraud analysis |

| `GET /transactions/{case\_id}` | Transaction table |

| `GET /certificate/{case\_id}` | Section 65B certificate |

| `GET /evidence-package/{case\_id}` | Download evidence ZIP |

| `GET /cases` | List all cases |



\## Files

| File | Purpose |

|------|---------|

| `graph\_engine.py` | Round-trip detection, mule flagging |

| `fifo\_trail.py` | FIFO money trail |

| `analytics.py` | Cash/cheque/UPI breakdown |

| `ai\_brief.py` | Groq AI investigation brief |

| `findings.py` | Master function — ties everything |

| `database.py` | SQLite + chain of custody |

| `adapter.py` | Converts P1's format to engine format |

| `section\_65b.py` | Section 65B certificate generator |

| `evidence\_package.py` | Evidence ZIP package |

| `main.py` | FastAPI — 7 endpoints on port 8001 |



