"""
BƯỚC 0: Vaccine filter  ← MỚI, chạy TRƯỚC
BƯỚC 1: DiseaseCouncil  ← chỉ chạy khi có vaccine posts
BƯỚC 2: ICD mapping     ← chỉ chạy khi có vaccine posts
BƯỚC 3: Xử lý từng post ← chỉ lặp qua vaccine_posts, không phải data_dict
"""


import os, sys, json, time, warnings
import pandas as pd
from utils.rawblock_processor import RawDataProcessor
from utils.DiseaseCouncil import DiseaseCouncil
from utils.RawtextSummaryl import SummaryCouncil
from utils.NarrativeCouncil import NarrativeCouncil
from utils.ICD11Council import ICD11Council
from utils.QualifiersICD11 import ICD11Qualifiers
from utils.DiseaseCouncil import validate_icd_codes
from utils.vaccine_filter import should_process_post, is_vaccine_related_rule

# --- 1. CẤU HÌNH ĐƯỜNG DẪN ---
INPUT_DIR       = r"C:\Users\VU\Documents\NLP\Demo2\datasets\individual_posts"
JSON_PATH       = r"C:\Users\VU\Documents\NLP\Demo2\datasets\taxonomy.json"
OUTPUT_CSV      = r"C:\Users\VU\Documents\NLP\Demo2\datasets\final_results.csv"
OUTPUT_TXT_DIR  = r"C:\Users\VU\Documents\NLP\Demo2\datasets\raw_reports_txt"
NON_VACCINE_LOG = r"C:\Users\VU\Documents\NLP\Demo2\datasets\non_vaccine_posts.txt"
TREE_11_JSON    = r"C:\Users\VU\Documents\NLP\datasets\ICD-11-MMS.tree.json"
CHROMA_11_DB_PATH = r"C:\Users\VU\Documents\NLP\datasets\chroma_icd11"

if not os.path.exists(OUTPUT_TXT_DIR):
    os.makedirs(OUTPUT_TXT_DIR)

# --- 2. KHỞI TẠO LLM CONFIG ---
sys.path.insert(0, r"C:\Users\VU\Documents\NLP\llm-council\backend")
try:
    import config
    from config import client, ModelManager
    print("✅ Config & ModelManager loaded.")
except ImportError as e:
    print(f"❌ Error loading config: {e}")
    sys.exit(1)

warnings.filterwarnings("ignore")

# --- 3. HÀM HỖ TRỢ ---
def read_taxonomy(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_to_txt(row_data, target_dir):
    """Lưu mỗi post thành file Markdown .txt"""
    file_path = os.path.join(target_dir, f"{row_data['Post ID']}.txt")
    content = f"""# REPORT ID: {row_data['Post ID']}
---
                    
## IDENTIFIERS
- **Source**: {row_data['Source']}
- **Date**: {row_data['Date']}
- **Language**: {row_data['Language']}
                    
---
                    
## MEDICAL ANALYSIS
- **Disease**: {row_data['Disease']}
- **ICD-11 Code Tag(s)**: {row_data['ICD-11 Code Tag(s)']}
                    
---
                    
## NARRATIVE CLASSIFICATION
- **Category ID**: {row_data.get('Category ID', 'NA')}
- **Category Name**: {row_data.get('Category Name', 'NA')}
- **Topic**: {row_data.get('Topic', 'NA')}
- **Subtopic**: {row_data.get('Subtopic', 'NA')}
- **Specific Narrative**: {row_data.get('Specific Narrative', 'NA')}
- **Cognitive Tactic (FLICC)**: {row_data.get('Cognitive Tactic (FLICC)', 'NA')}
- **Stigma Target**: {row_data.get('Stigma Target', 'NA')}
- **Real-World Trigger**: {row_data.get('Real-World Trigger', 'NA')}
                    
---
                    
## AI SUMMARY
{row_data['Raw Text / Summary']}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def log_non_vaccine(post_id: str, title: str, body: str, log_path: str):
    """Ghi post không liên quan vaccine vào file log để đối chiếu sau."""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{'='*60}\n")
        f.write(f"POST ID : {post_id}\n")
        f.write(f"TITLE   : {title}\n")
        f.write(f"CONTENT : {body[:300]}{'...' if len(body) > 300 else ''}\n")
        f.write(f"{'='*60}\n\n")

def filter_vaccine_posts(data_dict, log_path):
    """
    Chạy vaccine filter trên toàn bộ data_dict TRƯỚC khi gọi bất kỳ Council nào.
    Trả về vaccine_posts (dict đã lọc) và số posts bị skip.
    """
    vaccine_posts = {}
    skipped = 0

    for post_id, blocks in data_dict.items():
        content_block = blocks.get('CONTENT_BLOCK', {})
        title = content_block.get('post_title', '') or ''
        body  = content_block.get('post_content', '') or ''

        is_related, confidence = is_vaccine_related_rule(title, body)

        if confidence == 'high':
            vaccine_posts[post_id] = blocks

        elif confidence == 'uncertain':
            # LLM adjudication cho borderline cases
            is_related = should_process_post(
                client, ModelManager, title, body,
                use_llm_fallback=True
            )
            if is_related:
                vaccine_posts[post_id] = blocks
            else:
                log_non_vaccine(post_id, title, body, log_path)
                print(f"  ⏭️  Skipped (LLM: non-vaccine): {post_id}")
                skipped += 1

        else:  # low confidence → out-of-scope
            log_non_vaccine(post_id, title, body, log_path)
            print(f"  ⏭️  Skipped (non-vaccine): {post_id}")
            skipped += 1

    return vaccine_posts, skipped

# --- 4. CHƯƠNG TRÌNH CHÍNH ---
if __name__ == "__main__":
    print("🚀 Khởi tạo hệ thống Hội đồng chuyên gia...")

    taxonomy_data   = read_taxonomy(JSON_PATH)
    qualifier_engine = ICD11Qualifiers()

    icd11_council = ICD11Council(
        client, ModelManager,
        TREE_11_JSON, CHROMA_11_DB_PATH,
        qualifier_engine
    )
    summary_council   = SummaryCouncil(client, ModelManager)
    narrative_council = NarrativeCouncil(client, ModelManager, taxonomy_data)

    all_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".csv")]
    results_table = []

    print(f"\n📊 Bắt đầu xử lý {len(all_files)} files...")

    for file_name in all_files:
        file_path = os.path.join(INPUT_DIR, file_name)
        if not os.path.exists(file_path):
            print(f"⚠️ File không tồn tại: {file_name}")
            continue

        try:
            processor = RawDataProcessor(file_path)
            data_dict = processor.process_all_posts()

            # Bỏ qua file nếu tất cả posts đã có .txt
            all_txt_exist = all(
                os.path.exists(os.path.join(OUTPUT_TXT_DIR, f"{pid}.txt"))
                for pid in data_dict.keys()
            )
            if all_txt_exist:
                print(f"⏩ Skipping {file_name} (all posts already exported)")
                continue

            # ── BƯỚC 0: VACCINE FILTER ─────────────────────────────────────
            # Chạy TRƯỚC DiseaseCouncil và ICD mapping để tránh lãng phí API
            vaccine_posts, n_skipped = filter_vaccine_posts(data_dict, NON_VACCINE_LOG)

            if not vaccine_posts:
                print(f"⏩ Skipping {file_name} (no vaccine-related posts)")
                continue

            if n_skipped > 0:
                print(f"  📋 {file_name}: {len(vaccine_posts)} vaccine posts, {n_skipped} skipped")
            # ───────────────────────────────────────────────────────────────

            # ── BƯỚC 1: DISEASE EXTRACTION ─────────────────────────────────
            # Chỉ chạy trên file gốc — DiseaseCouncil đọc file CSV trực tiếp
            disease_results = DiseaseCouncil(file_path)
            diseases_all = []
            for ds in disease_results.values():
                diseases_all.extend(ds or [])
            diseases_all = [d for d in diseases_all if d and d.upper() != "NA"]
            diseases_all = list(dict.fromkeys(diseases_all))

            # ── BƯỚC 2: ICD-11 MAPPING ─────────────────────────────────────
            icd_map_per_file = []
            if diseases_all:
                icd_codes_list = icd11_council.get_icd11_code(
                    "; ".join(diseases_all), ""
                )
                icd_codes_list = validate_icd_codes(diseases_all, icd_codes_list)
                for i, d in enumerate(diseases_all):
                    code = icd_codes_list[i] if i < len(icd_codes_list) else "NA"
                    icd_map_per_file.append((d, code))
                    print(f"  [ICD][{file_name}] {d} → {code}")

            # ── BƯỚC 3: XỬ LÝ TỪNG POST (chỉ vaccine posts) ───────────────
            for post_id, blocks in vaccine_posts.items():

                txt_filename = os.path.join(OUTPUT_TXT_DIR, f"{post_id}.txt")
                if os.path.exists(txt_filename):
                    print(f"  ⏩ Skipping {post_id} (already exists)")
                    continue

                ident_data    = blocks.get('IDENTIFIER_BLOCK', {})
                content_block = blocks.get('CONTENT_BLOCK', {})

                summary_val      = summary_council.process_summary(post_id, content_block)
                narrative_results = narrative_council.process_narrative(post_id, summary_val)

                disease_str = "; ".join(diseases_all) if diseases_all else "NA"
                icd11_val   = "; ".join(
                    [code for _, code in icd_map_per_file]
                ) if icd_map_per_file else "NA"

                row_data = {
                    "Post ID":            post_id,
                    "Source":             ident_data.get("Source", "Reddit"),
                    "Date":               ident_data.get("Date", "NA"),
                    "Language":           ident_data.get("Language", "English"),
                    "Country":            "NA",
                    "Disease":            disease_str,
                    "Raw Text / Summary": summary_val,
                    **narrative_results,
                    "ICD-11 Code Tag(s)": icd11_val
                }

                results_table.append(row_data)
                save_to_txt(row_data, OUTPUT_TXT_DIR)
                print(f"  ✔️ {post_id} | {disease_str[:25]}.. | {icd11_val[:25]}..")
                time.sleep(1.3)

        except Exception as e:
            print(f"❌ Lỗi tại file {file_name}: {str(e)}")

    # --- 5. XUẤT CSV ---
    if results_table:
        final_df = pd.DataFrame(results_table)
        column_order = [
            "Post ID", "Source", "Date", "Language", "Country", "Disease",
            "Raw Text / Summary", "Category ID", "Category Name", "Topic",
            "Subtopic", "Specific Narrative", "Cognitive Tactic (FLICC)",
            "Stigma Target", "Real-World Trigger", "ICD-11 Code Tag(s)"
        ]
        final_df = final_df.reindex(columns=column_order)
        final_df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')
        print("\n" + "═" * 50)
        print(f"✅ HOÀN TẤT! Đã thêm {len(results_table)} bản ghi.")
        print(f"📍 {OUTPUT_CSV}")
        print("═" * 50)
    else:
        print("⚠️ Không có bản ghi nào được xử lý.")