<div align="center">

# 📄 Resume Parser

> AI-powered resume extraction using custom-trained spaCy NER

[![Python](https://img.shields.io/badge/Python-3.10+-blue)](https://python.org) [![spaCy](https://img.shields.io/badge/spaCy-v3-09A3D5)](https://spacy.io) [![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B)](https://streamlit.io) [![License](https://img.shields.io/badge/License-MIT-green)](#)

```bash
git clone https://github.com/BilalAamir4/resume-parser.git && cd resume-parser && pip install -r requirements.txt
```

| 📊 220 Training Resumes | 🏷️ 9 Entity Types | 🎯 91.95% Best F1 (Name) |
|:-:|:-:|:-:|

</div>

---

## Overview

Resume Parser is an end-to-end AI-powered resume analysis tool that takes a PDF, DOCX, DOC, or plain text resume as input and automatically extracts structured information from it — no templates, no fixed formats.

The core extraction engine is a custom spaCy v3 Named Entity Recognition model trained from scratch on 220 annotated resumes. A hybrid regex layer runs in parallel to catch deterministic fields (email, phone, URLs, graduation years) that rule-based patterns handle better than neural models. Both results are merged intelligently with field-level priority logic.

The project ships with a Streamlit web app featuring a premium dark-mode UI, skills gap analysis against any job description, batch processing for multiple resumes, and JSON/CSV export.

---

## Features

### Core Extraction
- Name, Designation, Email, Phone
- LinkedIn and GitHub URLs (including PDF annotation layer extraction)
- Skills — matched against a 120+ keyword library
- Education: College, Degree, Graduation Year
- Work Experience: Companies, Roles
- Location
- Confidence score for every extracted field

### Skills Gap Analysis
- Paste any job description and compare against the resume's skills
- See matched skills, missing skills, and bonus skills at a glance
- Match percentage with a visual progress indicator
- Export full gap analysis as JSON

### Batch Processing
- Upload multiple resumes at once
- Process all in parallel with a live progress bar
- Download results as CSV (one row per resume) or JSON array
- Summary stats: average skills, LinkedIn presence

### UI
- Full dark mode — premium design system with custom CSS
- 4-tab layout: Upload File, Paste Text, Skills Gap, Batch
- Entity cards with colored left-border accents and radial glows
- Skill pills sorted by confidence score
- Sidebar with per-label F1 scores and mini progress bars
- JSON preview and one-click download

---

## Project Structure

```
resume_parser/
├── app.py                        # Streamlit web app (4 tabs)
├── assets/
│   └── style.css                 # Dark mode design system
├── parser/
│   ├── __init__.py
│   ├── extractor.py              # ResumeExtractor class
│   ├── regex_patterns.py         # Compiled regex + skill keywords
│   └── gap_analyzer.py           # SkillsGapAnalyzer class
├── scripts/
│   ├── convert_data.py           # JSON → spaCy DocBin
│   ├── train_model.py            # spaCy v3 training + evaluation
│   └── test_pipeline.py          # CLI test for a single resume
├── data/
│   ├── raw/
│   │   └── Entity_Recognition_in_Resumes.json
│   └── processed/
│       ├── train.spacy
│       └── dev.spacy
├── training/
│   ├── config.cfg                # spaCy training config
│   ├── eval_results.json         # Per-label F1/P/R scores
│   └── output/
│       └── model-best/           # Trained NER model
├── requirements.txt
└── test_resume.txt               # Sample resume for testing
```

---

## Tech Stack

| Library | Purpose |
|---|---|
| **spaCy v3** | Custom NER model training, inference, evaluation |
| **PyMuPDF (fitz)** | PDF text + annotation/hyperlink layer extraction |
| **python-docx** | DOCX file text and table extraction |
| **Streamlit** | Web UI — 4-tab dark mode app |
| **pandas** | Batch processing DataFrame and CSV export |
| **re (regex)** | Email, phone, URL, year, skill keyword matching |
| **Python 3.10+** | Core language |

---

## Installation & Setup

```bash
# 1. Clone
git clone https://github.com/your-username/resume-parser.git
cd resume-parser

# 2. Install
pip install -r requirements.txt

# 3. Prepare dataset — place Entity_Recognition_in_Resumes.json in data/raw/ then:
python scripts/convert_data.py

# 4. Train the NER model (~5–10 min on CPU)
python scripts/train_model.py

# 5. Run the app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Usage

### Web App
- **Tab 1 — Upload File:** drag and drop a PDF, DOCX, DOC, or TXT resume
- **Tab 2 — Paste Text:** paste raw resume text and click *Parse Resume*
- **Tab 3 — Skills Gap Analysis:** upload or use an already-parsed resume, paste a job description, click *Analyze*
- **Tab 4 — Batch Processing:** upload multiple resumes, click *Process All*, download CSV or JSON

### Command Line

```bash
python scripts/test_pipeline.py path/to/resume.pdf
```

### Python API

```python
from parser.extractor import ResumeExtractor

extractor = ResumeExtractor(model_path='training/output/model-best')

result = extractor.parse('resume.pdf')                  # from file
result = extractor.parse_from_text(resume_text)         # from raw text

flat = extractor.get_flat_result(result)
print(flat['skills'])   # ['Python', 'Flutter', 'PyTorch', ...]
```

---

## Model Performance

Trained for 30 epochs on 80% of the dataset. Evaluated on the held-out 20% dev set.

| Entity Label | Precision | Recall | F1 Score |
|---|:-:|:-:|:-:|
| Name | 97.56% | 86.96% | **91.95%** |
| Email Address | 79.49% | 83.78% | **81.58%** |
| Degree | 72.73% | 76.92% | **74.77%** |
| College Name | 57.41% | 48.44% | **52.54%** |
| Location | 62.75% | 43.84% | **51.61%** |
| Designation | 57.53% | 43.30% | **49.41%** |
| Companies worked at | 49.18% | 41.96% | **45.28%** |
| Graduation Year | 46.34% | 33.33% | **38.78%** |
| Skills | 27.27% | 16.36% | **20.45%** |

> **Note:** Skills and Graduation Year low F1 scores are by design — regex is the primary strategy for those fields.

---

## How It Works — Pipeline

Input → text extraction (PyMuPDF / python-docx / plain text) → spaCy NER model → regex layer runs in parallel → `_merge_results()` combines both (regex wins for skills & years; NER wins for name, designation, companies, location) → final `{text, score}` dict → `get_flat_result()` for flat string output.

---

## Dataset

| Field | Details |
|---|---|
| **Source** | Kaggle — Entity Recognition in Resumes |
| **Format** | JSONL — one JSON object per line |
| **Size** | 220 annotated resumes |
| **Annotation** | Character-level span annotations (start, end, text, label) |
| **Labels** | Name, Designation, Companies worked at, College Name, Degree, Graduation Year, Skills, Email Address, Location |
| **Split** | 80% train (176 records) / 20% dev (44 records), random seed 42 |

---

## Configuration

### Training hyperparameters (`training/config.cfg`)

| Parameter | Value |
|---|---|
| `max_epochs` | 30 |
| `eval_frequency` | 200 steps |
| `patience` | 5 (early stopping) |
| `optimizer` | Adam (spaCy default) |
| `pipeline` | tok2vec + ner |

### Custom model path

```python
extractor = ResumeExtractor(model_path='path/to/your/model')
```

---

## Known Limitations

- **Skills NER F1 is low (20%)** — compensated by the 120-keyword regex library. Add niche skills to `SKILLS_KEYWORDS` in `parser/regex_patterns.py`
- **Scanned PDFs:** PyMuPDF cannot extract text from image-only PDFs — OCR (pytesseract) is a planned enhancement
- **Non-English resumes:** model is trained on English data only
- **Company duration:** identifies company names but not employment date ranges

---

## Roadmap

- [ ] OCR support for scanned PDF resumes (pytesseract)
- [ ] Employment duration parsing — extract date ranges per company
- [ ] HuggingFace transformer-based NER for higher accuracy
- [ ] REST API wrapper (FastAPI)
- [ ] Resume scoring against a job description (beyond skills gap)
- [ ] Docker containerization
- [ ] Active learning loop — flag low-confidence extractions for re-annotation

---

## Author

**Bilal Aamir**

---

<div align="center">

**Resume Parser** · Custom spaCy NER · 220 training resumes · Built with Streamlit

</div>
