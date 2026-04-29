import os
from openai import OpenAI

# ==========================================
# 1. KẾT NỐI SERVER (LM STUDIO / LOCAL LLM)
# ==========================================
BASE_URL = "http://192.168.0.215:1234/v1"
API_KEY = "not-needed"
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ==========================================
# 2. CẤU HÌNH XỬ LÝ (PERFORMANCE)
# ==========================================
CHUNK_SIZE = 100      # Số dòng CSV gửi đi mỗi lượt = 800 token (tùy thuộc số cột của mỗi agent sẽ nhận)
TIMEOUT_LONG = 600    # Dành cho Model lớn (120B/70B) khi tổng hợp
TIMEOUT_SHORT = 180    # Dành cho Model nhỏ (8B) khi bóc tách bảng

# ==========================================
# 3. CHIA LẠI HỘI ĐỒNG (PRIORITY_MAP)
# Mỗi Key tương ứng với một Block trong Guideline Quốc Gia
# ==========================================
PRIORITY_MAP = {
    # --- NHÓM TỔNG HỢP (Block 9: FINAL SYNTHESIS) ---
"COUNCIL_ALLERGIES": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it",
    ],
"COUNCIL_MEDICINES": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it",
    ],
"COUNCIL_CEASED_MEDICINES": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it",
    ],
"COUNCIL_INVESTIGATIONS": [
        "deepseek-r1-distill-llama-8b",
        "llama-3.1-8b-instruct",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it",
    ],
"COUNCIL_RECOMMENDATIONS": [
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "gemma-3-27b-it",
    ],
"COUNCIL_DIAGNOSES": [
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "deepseek-r1-distill-llama-8b",
        "llama-3.1-8b-instruct",
        "gemma-3-27b-it",
    ],
"COUNCIL_PROCEDURES": [
        "deepseek-r1-distill-llama-8b",
        "llama-3.1-8b-instruct",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it",
    ],
"COUNCIL_PRESENTATIONS": [
        "deepseek-r1-distill-llama-8b",
        "llama-3.1-8b-instruct",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it",
    ],
"COUNCIL_ALERTS": [
        "deepseek-r1-distill-llama-8b",
        "llama-3.1-8b-instruct",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it"
    ],
"COUNCIL_FOLLOWS": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it"
    ],
"COUNCIL_INFOS": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it"
    ],
"COUNCIL_RECIPIENTS": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "gemma-3-27b-it"
    ],
"COUNCIL_SUMMARY": [
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "gemma-3-27b-it",
    ],

"COUNCIL_MAPPING": [
        "llama-3.1-8b-instruct",
        "gemma-3-27b-it",
        "deepseek-r1-distill-llama-8b",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
    ],

"CHAIRMAN": [
        "llama-3.3-70b-instruct",
        "openai/gpt-oss-120b",
        "llama-3.1-8b-instruct",
        "gemma-3-27b-it",
    ],

"CLIENT": [
        "llama-3.1-8b-instruct",
        "deepseek-r1-distill-llama-8b",
        "gemma-3-27b-it",
        "llama-3.3-70b-instruct",
        "deepseek-r1-distill-llama-70b",
        # danh cho LMSTUDIO: "openai/gpt-oss-120b", "qwen3-235b-a22b",
    ],
}

# ==========================================
# 4. THÔNG SỐ TỐI ƯU (PARAMS)
# ==========================================
PARAMS = {
    "synthesis": {  # Dành cho văn bản tự sự, cần suy luận
        "temperature": 0.0,
        "max_tokens": 8000,
        "top_p": 0.1
    },
    "extraction": { # Dành cho bảng biểu, cần chính xác tuyệt đối
        "temperature": 0.0,
        "max_tokens": 4000,
        "top_p": 0.1
    }
}

# ==========================================
# 5. QUẢN LÝ XOAY VÒNG & THÔNG SỐ (MODEL MANAGER)
# ==========================================
class ModelManager:
    FAILED_RESOURCES_MODELS = set()  # Danh sách đen các model gây lỗi VRAM

    @classmethod
    def mark_failed(cls, model_name):
        """Đánh dấu model bị lỗi để các Council sau không gọi nhầm"""
        if model_name not in cls.FAILED_RESOURCES_MODELS:
            print(f"⚠️ [SYSTEM] Blacklisting {model_name} due to VRAM/Resource error.")
            cls.FAILED_RESOURCES_MODELS.add(model_name)

    @staticmethod
    def get_model(role, attempt=0):
        """
        Lấy model theo thứ tự ưu tiên từ trên xuống dưới trong PRIORITY_MAP.
        Nếu attempt vượt quá số lượng model hiện có, nó sẽ báo lỗi hoặc trả về None.
        """
        role_clean = role.upper().strip()

        # 1. Kiểm tra xem Role có tồn tại trong cấu hình không
        if role_clean not in PRIORITY_MAP:
            print(f"[ERROR] Role '{role_clean}' không tồn tại trong PRIORITY_MAP.")
            return None

        models = PRIORITY_MAP[role_clean]

        # 2. Kiểm tra xem attempt có nằm trong phạm vi danh sách không
        # Điều này đảm bảo đi đúng thứ tự từ trên xuống (0 -> 1 -> 2...)
        if attempt < len(models):
            return models[attempt]
        else:
            print(f"[WARN] Đã thử hết toàn bộ model cho role {role_clean}. Không còn model dự phòng.")
            return None

    @staticmethod
    def get_params(role):
        """Tự động trả về bộ Params dựa trên tính chất công việc của Agent"""
        role_upper = role.upper()

        # Nhóm các Agent cần viết lách, tóm tắt, suy luận sâu
        synthesis_keywords = ["INVESTIGATIONS", "SUMMARY", "RECOMMENDATIONS", "PRESENTATIONS", "PROCEDURES"]

        if any(keyword in role_upper for keyword in synthesis_keywords):
            return PARAMS["synthesis"]
        return PARAMS["extraction"]

    @staticmethod
    def get_timeout(model_name):
        """Quyết định thời gian chờ (Timeout) dựa trên kích thước/độ phức tạp của Model"""
        name_lower = model_name.lower()

        # Tự động gán timeout dài cho các model siêu lớn hoặc dòng DeepSeek R1
        if any(size in name_lower for size in ["235b", "120b", "70b", "r1"]):
            return TIMEOUT_LONG
        return TIMEOUT_SHORT


print(f"✅ ModelManager Streamlined: Ready for {len(PRIORITY_MAP)} synchronized councils.")