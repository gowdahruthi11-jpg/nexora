# Verity — AI-Assisted Digital Evidence Verification & Tamper Detection

**Problem Statement PR-ASCEND · NEXORA 2026 Innovation Hackathon**

Screenshots, payment receipts, documents, and images can be manipulated in seconds — yet they're trusted as evidence every day. Verity analyzes a file's cryptographic fingerprint, hidden metadata, and pixel-level compression patterns to generate an **explainable Trust Score** and a **verification record containing the file's cryptographic fingerprint, analysis findings, and Trust Score**.
## 🚀 Live Demo

**Live Application:** https://verity-4tgo.onrender.com
---

## What it does

Verity runs three independent forensic checks on every uploaded image or PDF, then combines them into a single 0–100 Trust Score with a plain-English explanation of every finding — never a black-box verdict.

| Check | What it catches |
|---|---|
| **SHA-256 Fingerprinting** | Proves whether a file has changed since it was first analyzed |
| **Metadata Forensics** | Reads EXIF data (images) and document metadata (PDFs) for editing-software signatures and mismatched creation/modification dates |
| **Error Level Analysis (ELA)** | Re-compresses the image and diffs it against the original, exposing localized edits as compression "hotspots" invisible to the naked eye |
| **OCR Text Check** | Extracts visible text and flags regions where compression variation is abnormally concentrated, catching altered numbers, names, or amounts |

### Additional features

- **Large-image handling** — automatically downscales very large uploads before forensic processing, improving reliability and performance on mobile devices
- **Side-by-side comparison mode** — upload an original and a suspected-edited file to get a direct visual diff, highlighting exactly what changed and by how much
- **PDF/document support** — not just images; receipts and documents are analyzed too
- **Verification Certificate** — download a formatted PDF report with a case reference number, trust score, and full findings — a tamper-evident evidence record for every analysis

---

## Screenshots

<img width="937" height="430" alt="image" src="https://github.com/user-attachments/assets/f6b26297-cf7e-4e32-ae86-1d95004884a5" />
<img width="938" height="412" alt="image" src="https://github.com/user-attachments/assets/431bfd2f-7e1e-43ac-89c0-ea4aab5aec55" />
<img width="937" height="434" alt="image" src="https://github.com/user-attachments/assets/caccb993-4c5e-4020-8397-1a9fb3b58054" />
<img width="922" height="397" alt="image" src="https://github.com/user-attachments/assets/4db59ed7-0452-4af6-8539-bec4d4ba9c8e" />
<img width="941" height="434" alt="image" src="https://github.com/user-attachments/assets/65970f16-ef74-46e0-9231-4c92fe964f32" />
<img width="713" height="391" alt="image" src="https://github.com/user-attachments/assets/860df7fe-641c-4c50-a39d-90c814df7980" />




---

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **Image processing:** Pillow, NumPy
- **Document parsing:** pypdf
- **OCR:** Tesseract OCR + pytesseract
- **PDF report generation:** ReportLab
- **Frontend:** Vanilla HTML/CSS/JS (single-page, no framework dependency)

---

## How it works

1. A file is uploaded and hashed (SHA-256) — this fingerprint becomes the file's tamper-evident anchor.
2. Metadata is inspected — EXIF fields for images, producer/creation/modification dates for PDFs.
3. For images, Error Level Analysis re-compresses the file and measures pixel-level deviation from the original, flagging both widespread inconsistency and small localized "hotspots."
4. OCR extracts any visible text and cross-checks each text region against the ELA data — a word sitting in a region with abnormally high compression variation suggests it was edited independently of the rest of the file.
5. All findings are combined into a single Trust Score (starting at 100, deducted per finding) with a verdict: **Likely Authentic**, **Some Concerns — Review Recommended**, or **High Risk — Likely Tampered**.
6. Users can generate a downloadable PDF certificate summarizing the full analysis, or run a direct comparison between two file versions.

---

## Getting Started

### Prerequisites

- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed (for the OCR text-tampering check)

### Installation

```bash
# Clone the repository
git clone https://github.com/<your-username>/<your-repo-name>.git
cd <your-repo-name>

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS/Linux

# Install dependencies
pip install fastapi uvicorn python-multipart Pillow numpy pypdf pytesseract reportlab
```

### Running the app

```bash
uvicorn main:app --reload --port 8080
```

Then open **http://127.0.0.1:8080** in your browser.

> **Note:** Port `8000` may be blocked by some antivirus/firewall software on Windows — this project defaults to port `8080` to avoid that issue.

---

## Scope

Verity detects **manipulation of real evidence** — edits made to a genuine photo or document after it was created. It does not attempt to classify whether an image is fully AI-generated from scratch, which is a separate problem requiring a different (trained classifier) approach.

---
## ⚠️ Known Limitations

- ELA works best with original digital image files.
- Photos taken of screens, screenshots photographed by a camera, or repeatedly compressed images may show higher ELA variation because of recompression, lighting, and screen-pattern artifacts.
- ELA is treated as one forensic signal and should be interpreted together with metadata, hashing, and OCR findings rather than as standalone proof of tampering.
- Verity focuses on detecting manipulation of existing digital evidence; it does not determine whether an image was completely AI-generated.

## Team

Data smasher 

Hruthik Gowda <br>
Kartik Gupta <br>
Tanvi Chilap <br>
Vaibhav Sharma <br>

---

## Built for

**NEXORA 2026 Innovation Hackathon** — Department of Information Technology, Vivek College of Commerce (Autonomous)
Problem Statement: **PR-ASCEND** — AI-Assisted Digital Evidence Verification & Tamper Detection
