# mRNA Vaccine Misinformation Pipeline

**Paper:** *A multi-agent pipeline integrating ICD-11 and narrative taxonomy for mRNA vaccine misinformation surveillance on social media*  
**Authors:** Vu Thinh Doan, Trong Phuc Nguyen, Jitendra Jonnagaddala, Hong-Jie Dai  
**Journal:**  npj | Digital Public Health (under review)

---

## Overview

A five-stage multi-agent pipeline integrating a thematic misinformation taxonomy with ICD-11 clinical coding for structured surveillance of mRNA vaccine discourse on Reddit. The pipeline processes raw Reddit posts through sequential agents for summarization, disease extraction, ICD-11 coding, and narrative classification.

---

## Requirements

```bash
pip install pandas numpy openai spacy chromadb sentence-transformers
python -m spacy download en_core_web_sm
```

All LLM calls use the **OpenAI-compatible API format**, run locally via [Ollama](https://ollama.com) and [LMStudio](https://lmstudio.ai). No external API costs required.

**Models used:**
- SummaryCouncil: `llama3.3:70b`
- DiseaseCouncil: `llama3.1:8b`
- NarrativeCouncil: `gemma3:27b`

Configure your local endpoint in `config.py` before running.

---

## Pipeline Execution

The pipeline is divided into four groups. **Groups 1–3 run once** to prepare resources. **Group 4 runs per post batch.**

---

### GROUP 1 — UMLS Preparation (run once, ~8h total)

> ⚠️ **Skip this group** by downloading pre-processed files from Google Drive (recommended).

```bash
python umls_to_sqlite.py          # Step 1  → umls_simple.sqlite
python export_lexicon.py          # Step 2  → lexicon_from_mrconso.json (~2 GB, ~2h)
python build_alias_map_full.py    # Step 3  → alias_map_full.pkl
python build_cui_sty_map.py       # Step 4  → cui_to_stys.json
python build_cui_icd11_map.py     # Step 5  → cui_has_icd11.sqlite
python cui_sql_2_json.py          # Step 6  → cui_has_icd11.json
python build_reduced_lexicon.py   # Step 7  → lexicon_reduced.json
```

---

### GROUP 2 — Post Preparation (run once, >24h for n-gram step)

> ⚠️ **`extract_top_ngrams.py` takes >24 hours.** Download `top_ngrams.txt` from Google Drive instead.

```bash
python csv_split.py               # Step 8  → datasets/csv/{post_id}.csv
python remove_content_mty.py      # Step 9  → removes empty/deleted posts
python extract_top_ngrams.py      # Step 10 → top_ngrams.txt (>24h)
python map_ngrams_to_uMLS.py      # Step 11 → mapped_candidates.jsonl
```

---

### GROUP 3 — Build ICD-11 Index (run once, ~30min)

```bash
python index_icd.py               # Step 12 → ChromaDB collection (SapBERT embeddings)
```

---

### GROUP 4 — Main Pipeline (run per post batch)

```bash
python main_v1.py
# Input:  datasets/csv/{post_id}.csv
# Output: results/{post_id}.txt + final_results.csv
```

**Pipeline flow per post batch:**

```
for each post_id.csv:
│
├── rawblock_processor.py
│     → Parses CSV into IDENTIFIER_BLOCK + CONTENT_BLOCK
│
├── DiseaseCouncil.py
│     → Extracts disease/symptom mentions
│     → Uses spaCy NER + UMLS alias matching + LLM filter
│
├── ICD11Council.py
│     → Maps diseases to ICD-11 codes
│     → Uses SapBERT + ChromaDB retrieval + LLM verification
│     → Calls QualifiersICD11.py for post-coordination
│
└── for each post in batch:
      │
      ├── RawtextSummaryl.py  (SummaryCouncil)
      │     → Distills post into one professional sentence
      │
      └── NarrativeCouncil.py
            → Stage 1: Binary pre-screening (YES/NO)
            → Stage 2: Taxonomy classification
                       (Subtopic, Narrative, FLICC,
                        Stigma Target, Real-World Trigger)
            → Stage 3–5: Validation guards + FP correction

Output: {post_id}.txt report + row in final_results.csv
```

---

## Pre-processed Resource Files (Google Drive)

Download these files to skip Groups 1–2. Place in `datasets/UMLS_2024AA/`.

| File | Description | Link |
|------|-------------|------|
| `vaccine_to_diseases.json` | Vaccine-disease mapping | [Download](https://drive.google.com/open?id=1z4NCpcq6nNteN613RA1GqaKIHq9n5vIh&usp=drive_copy) |
| `umls_simple.sqlite` | Simplified UMLS SQLite database | [Download](https://drive.google.com/open?id=1Hr0IDZJUV9K3USQWnnN6aybm9VIW8GYQ&usp=drive_copy) |
| `cui_has_icd11.sqlite` | CUI-to-ICD-11 mapping (SQLite) | [Download](https://drive.google.com/open?id=1FoBlsH2scByBllxtQT78ecFBIEa_EJjS&usp=drive_copy) |
| `cui_to_stys.json` | CUI semantic type mapping | [Download](https://drive.google.com/open?id=1qaZ8TmsiyuhzFJmNXrjZdNqeSAiUy5vJ&usp=drive_copy) |
| `lexicon_from_mrconso.json` | Full alias map from MRCONSO (~2 GB) | [Download](https://drive.google.com/open?id=1dc0pnQJxjOC34SH1mDpKrOdlHMXBzcUh&usp=drive_copy) |
| `top_ngrams.txt` | Top 20,000 corpus n-grams (>24h to rebuild) | [Download](https://drive.google.com/open?id=1rKogcfATUpIA-c2yg1Fs4Lb7encBmb_i&usp=drive_copy) |
| `cui_has_icd11.json` | CUI-to-ICD-11 mapping (JSON) | [Download](https://drive.google.com/open?id=1ObYF3zUfE9fvVmZ3YYOIm8g_V33jACq5&usp=drive_copy) |
| `alias_map_full.pkl` | Full alias map (pickle) | [Download](https://drive.google.com/open?id=1WXN5w6yT2K8u4-SOGG6U8bCgmfYK1Hr5&usp=drive_copy) |
| `mapped_candidates.jsonl` | Pre-mapped ICD-11 candidate entities | [Download](https://drive.google.com/open?id=1PeFHpdTm_8toneuCpMtQyAQZ-XOsWQms&usp=drive_copy) |

**Raw UMLS 2024AA** (required for Group 1 only):
1. Register for a free UMLS license: https://uts.nlm.nih.gov/uts/signup-login
2. Download UMLS 2024AA Full Release: https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html

---

## Repository Structure

```
├── pipeline/
│   ├── main_v1.py                  # Main pipeline entry point
│   ├── config.py                   # LLM endpoint configuration
│   ├── rawblock_processor.py       # Post parser
│   ├── RawtextSummaryl.py          # SummaryCouncil (Stage 1)
│   ├── DiseaseCouncil.py           # Disease extraction (Stage 2)
│   ├── NarrativeCouncil.py         # Narrative classification (Stage 3)
│   ├── ICD11Council.py             # ICD-11 coding (Stage 4)
│   ├── QualifiersICD11.py          # ICD-11 post-coordination
│   ├── vaccine_filter.py           # Vaccine relevance pre-filter
│   ├── umls_to_sqlite.py           # Group 1, Step 1
│   ├── export_lexicon.py           # Group 1, Step 2
│   ├── build_alias_map_full.py     # Group 1, Step 3
│   ├── build_cui_sty_map.py        # Group 1, Step 4
│   ├── build_cui_icd11_map.py      # Group 1, Step 5
│   ├── cui_sql_2_json.py           # Group 1, Step 6
│   ├── build_reduced_lexicon.py    # Group 1, Step 7
│   ├── csv_split.py                # Group 2, Step 8
│   ├── remove_content_mty.py       # Group 2, Step 9
│   ├── extract_top_ngrams.py       # Group 2, Step 10 (>24h)
│   ├── map_ngrams_to_uMLS.py       # Group 2, Step 11
│   └── index_icd.py                # Group 3, Step 12
│
├── datasets/
│   ├── taxonomy.json               # 11-narrative misinformation taxonomy
│   ├── posts.csv                   # Reddit post IDs
│   ├── csv/                        # Individual post CSV files
│   └── UMLS_2024AA/                # Pre-processed UMLS files (see Drive)
│
├── evaluation/
│   ├── evaluate_batch.py
│   ├── keyword_classifier.py
│   ├── ablation_study.py
│   └── consensus_GT_expert_detailed.csv
│
├── results/
│   └── results_alltxt.csv          # Full corpus results (3,054 posts)
│
└── README.md
```

---

## Taxonomy

**11 narratives** across **3 subtopics**:

| Subtopic | Narratives |
|----------|------------|
| Safety & Bodily Integrity | Acute Injuries, Chronic Disease (Turbo Cancer), Reproductive Harm, Microchips & Tracking, Genomic Alteration, Ingredient Safety Concerns, Suppression of Data |
| Efficacy & Necessity | Zero Protection Claims, Alternative Cures, Vaccine Safety and Efficacy |
| Ethics & Liberties | Coercion Narratives |

---

## Evaluation

```bash
# Reproduce evaluation results
python evaluation/evaluate_batch.py \
    --results results/results_alltxt.csv \
    --gt evaluation/consensus_GT_expert_detailed.csv

# Run ablation study (4 conditions)
python evaluation/ablation_study.py --condition all
```

---

## Citation

```bibtex
@article{doan2026vaccine,
  author  = {Doan, Vu Thinh and Nguyen, Trong Phuc and
             Jonnagaddala, Jitendra and Dai, Hong-Jie},
  title   = {A multi-agent pipeline integrating ICD-11 and narrative taxonomy for 
            {mRNA} vaccine misinformation surveillance on social media},
  journal = { npj | Digital Public Health},
  note    = {under review}
  year    = {2026}
}
```

---

## License

Code: MIT License  
Dataset: CC BY 4.0  
UMLS-derived files: Subject to [UMLS License Agreement](https://uts.nlm.nih.gov/uts/assets/LicenseAgreement.pdf)
