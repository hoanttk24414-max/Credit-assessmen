"""
CREDIT DATA PIPELINE 2024-2025
==============================
Banks: TCB, CTG, BID, VCB, MBB

Mục tiêu:
1. Crawl toàn bộ Balance Sheet/Income Statement từ VNStock; Raw sheets chỉ xuất 2024-2025 và chuẩn hóa nhãn năm. 2025 là năm chính; 2024 chỉ lấy total_loans để tính CoR.
2. Bổ sung tổng dư nợ phân loại Nhóm 1-5, Group 2-5 và CAR 2025 từ nguồn chính thức đã đối chiếu.
3. Chuẩn hóa dữ liệu, kiểm tra missing/consistency.
4. Tính 5 chỉ tiêu dùng trong bộ BCDS:
   - NPL
   - Group 2 Ratio
   - LLR/NPL
   - CoR
   - CAR
5. Xuất:
   - output/credit_data.xlsx
   - output/credit_data_clean.csv

Lưu ý:
- Không thay dữ liệu thiếu bằng 0.
- LDR và Credit Growth không thuộc bộ 15 chỉ tiêu BCDS nên không xuất.
"""

from pathlib import Path
import platform
import sys

import pandas as pd


# ============================================================
# 1. PROJECT CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_FILE = OUTPUT_DIR / "credit_data.xlsx"
CLEAN_CSV_FILE = OUTPUT_DIR / "credit_data_clean.csv"

BANKS = {
    "Techcombank": "TCB",
    "VietinBank": "CTG",
    "BIDV": "BID",
    "Vietcombank": "VCB",
    "MBBank": "MBB",
}

# Năm chấm điểm chính là 2025.
# 2024 chỉ dùng cho total_loans để tính dư nợ bình quân trong CoR.
TARGET_YEARS = [2024, 2025]

# Chỉ giữ các biến VNStock thật sự cần cho phần credit.
VNSTOCK_VARIABLE_MAP = {
    "total_loans": {
        "sheet": "balance_sheet",
        "item_id": "loans_advances_and_finance_leases_to_customers_2",
        "unit": "ty_dong",
    },
    "credit_risk_provision": {
        "sheet": "balance_sheet",
        "item_id": "provisions_for_losses_on_loans_advances_and_finance_leases_to_customers",
        "unit": "ty_dong",
        "absolute": True,
    },
    "provision_expense": {
        "sheet": "income_statement",
        "item_id": "provision_for_credit_losses",
        "unit": "ty_dong",
        "absolute": True,
    },
}

# Input bắt buộc theo bộ tiêu chí credit.
CREDIT_REQUIRED = {
    2024: ["total_loans"],
    2025: [
        "total_loans",
        "classified_loans",
        "group_2_loans",
        "group_3_loans",
        "group_4_loans",
        "group_5_loans",
        "credit_risk_provision",
        "provision_expense",
        "car",
    ],
}


# ============================================================
# 2. VERIFIED SUPPLEMENTS 2025
# ============================================================
# Group 2-5: tỷ đồng.
# CAR: %.
# Các biến này không có trong mapping VNStock hiện tại nên được
# bổ sung từ BCTC hợp nhất kiểm toán 2025 và CBTT CAR 31/12/2025
# theo đúng bộ nguồn chính thức do nhóm thu thập.

CREDIT_SUPPLEMENTS_2025 = {
    "Techcombank": {
        # Thuyết minh 9.1: tổng dư nợ được phân loại Nhóm 1-5
        "classified_loans": (731955.772, "ty_dong"),
        "group_2_loans": (3852.272, "ty_dong"),
        "group_3_loans": (918.063, "ty_dong"),
        "group_4_loans": (1339.119, "ty_dong"),
        "group_5_loans": (5941.193, "ty_dong"),
        # CBTT CAR 31/12/2025: CAR hợp nhất = 14,61%.
        "car": (14.61, "%"),
    },
    "VietinBank": {
        # Thuyết minh 8.3: tổng dư nợ được phân loại Nhóm 1-5
        "classified_loans": (1992272.868, "ty_dong"),
        "group_2_loans": (17345.911, "ty_dong"),
        "group_3_loans": (1490.975, "ty_dong"),
        "group_4_loans": (578.479, "ty_dong"),
        "group_5_loans": (19846.742, "ty_dong"),
        # CBTT CAR 31/12/2025: CAR hợp nhất = 9,89%.
        "car": (9.89, "%"),
    },
    "BIDV": {
        # Phân tích chất lượng nợ cho vay: tổng Nhóm 1-5
        "classified_loans": (2372955.074, "ty_dong"),
        "group_2_loans": (31462.771, "ty_dong"),
        "group_3_loans": (4473.881, "ty_dong"),
        "group_4_loans": (4677.985, "ty_dong"),
        "group_5_loans": (25824.953, "ty_dong"),
        # CBTT CAR 31/12/2025: CAR hợp nhất = 9,18%.
        "car": (9.18, "%"),
    },
    "Vietcombank": {
        # Phân tích chất lượng nợ cho vay: tổng Nhóm 1-5
        "classified_loans": (1673525.675, "ty_dong"),
        "group_2_loans": (2704.636, "ty_dong"),
        "group_3_loans": (760.561, "ty_dong"),
        "group_4_loans": (222.632, "ty_dong"),
        "group_5_loans": (8686.362, "ty_dong"),
        # Basel II/Pillar 3 tại 31/12/2025: CAR hợp nhất = 11,56%.
        "car": (11.56, "%"),
    },
    "MBBank": {
        # Thuyết minh 9.1: tổng dư nợ phân tích chất lượng nợ,
        # bao gồm khoản cho vay giao dịch ký quỹ/ứng trước thuộc nợ đủ tiêu chuẩn.
        "classified_loans": (1098100.630, "ty_dong"),
        "group_2_loans": (10210.040, "ty_dong"),
        "group_3_loans": (3276.216, "ty_dong"),
        "group_4_loans": (4330.016, "ty_dong"),
        "group_5_loans": (6421.264, "ty_dong"),
        # CBTT CAR 31/12/2025: CAR hợp nhất = 11,02%.
        "car": (11.02, "%"),
    },
}

CREDIT_SUPPLEMENT_SOURCES = {
    "Techcombank": {
        "debt": (
            "Techcombank - BCTC hợp nhất kiểm toán 2025, Thuyết minh 9.1 Phân tích chất lượng nợ cho vay",
            "https://techcombank.com/content/dam/techcombank/public-site/documents/"
            "techcombank-vas-bao-cao-tai-chinh-hop-nhat-ye25.pdf",
        ),
        "car": (
            "Techcombank - Công bố thông tin tỷ lệ an toàn vốn 31/12/2025",
            "https://techcombank.com/content/dam/techcombank/public-site/documents/"
            "ty-le-an-toan-von-2h2025-final.pdf",
        ),
    },
    "VietinBank": {
        "debt": (
            "VietinBank - BCTC hợp nhất kiểm toán năm 2025, Thuyết minh 8.3 Theo chất lượng nợ cho vay",
            "https://investor.vietinbank.vn/documents/20126/667477/"
            "BCTC%20hop%20nhat%20kiem%20toan%20nam%202025_VN.pdf.pdf/"
            "4c8eda02-b420-612d-24ac-c12f2bbd3451",
        ),
        "car": (
            "VietinBank - Báo cáo công bố thông tin về tỷ lệ an toàn vốn tại 31/12/2025",
            "https://investor.vietinbank.vn/documents/20126/0/"
            "CBTT+ty+le+an+toan+von+31.12.2025.pdf/"
            "40bc76b5-2005-b371-2e46-18ae3e0d941d?t=1778467033969",
        ),
    },
    "BIDV": {
        "debt": (
            "BIDV - BCTC kiểm toán hợp nhất năm 2025, Phân tích chất lượng nợ cho vay",
            "https://bidv.com.vn/wps/wcm/connect/f40205f8-b854-48ab-aab5-e3bfcb5d7d40/"
            "20260330+-+BID+-+CBTT+BCTC+HN+2025.pdf?"
            "MOD=AJPERES&CACHEID=ROOTWORKSPACE-f40205f8-b854-48ab-aab5-e3bfcb5d7d40-pR1RUJh",
        ),
        "car": (
            "BIDV - Báo cáo công bố thông tin về tỷ lệ an toàn vốn kỳ 31/12/2025",
            "https://bidv.com.vn/wps/wcm/connect/af70916c-f5ef-41f3-8cd7-6431ad0b8d53/"
            "Bao+cao+CBTT_31.12.2025_VIE.pdf?"
            "MOD=AJPERES&CACHEID=ROOTWORKSPACE-af70916c-f5ef-41f3-8cd7-6431ad0b8d53-pS.k1MH",
        ),
    },
    "Vietcombank": {
        "debt": (
            "Vietcombank - BCTC hợp nhất kiểm toán năm 2025, Phân tích chất lượng nợ cho vay",
            "https://www.vietcombank.com.vn/-/media/Project/VCB-Sites/VCB/Nha-Dau-tu/"
            "Files/BC-dinh-ky/BCTC/2025/"
            "20260327---VCB---BCTC-hop-nhat-kiem-toan-nam-2025.pdf?ts=00010101000000",
        ),
        "car": (
            "Vietcombank - Báo cáo công bố thông tin theo Trụ cột 3 Basel II tại 31/12/2025",
            "https://www.vietcombank.com.vn/-/media/Project/VCB-Sites/VCB/Nha-Dau-tu/"
            "Files/Cong-bo-thong-tin/Thong-tin-cong-bo/2026/"
            "BC_CBTT_BASEL_II_31122025.pdf?ts=00010101000000",
        ),
    },
    "MBBank": {
        "debt": (
            "MBBank - BCTC kiểm toán hợp nhất năm 2025, Thuyết minh 9.1 Phân tích chất lượng nợ cho vay",
            "https://www.mbbank.com.vn/resources/files/NhaDauTu/2026/T03-2026/"
            "20260310---mbb---bao-cao-tai-chinh-kiem-toan-hop-nhat-nam-2025.pdf",
        ),
        "car": (
            "MBBank - Công bố tỷ lệ an toàn vốn tại ngày 31/12/2025",
            "https://www.mbbank.com.vn/resources/files/NhaDauTu/2026/T05-2026/"
            "20260527---mbb---cbtt-ty-le-an-toan-von-tai-ngay-31122025-(vn-en).pdf",
        ),
    },
}


# ============================================================
# 3. VNSTOCK
# ============================================================

def print_environment():
    print("=" * 70)
    print("BANK CREDIT DATA COLLECTOR")
    print("=" * 70)
    print(f"Python : {sys.version.split()[0]}")
    print(f"OS     : {platform.system()}")
    print(f"Project: {BASE_DIR}")

    if sys.version_info < (3, 10):
        raise RuntimeError("Project yêu cầu Python >= 3.10.")


def load_vnstock():
    try:
        from vnstock import Fundamental
        print("[OK] VNStock đã sẵn sàng.")
        return Fundamental
    except ImportError:
        print("[ERROR] Không tìm thấy VNStock.")
        print("Chạy: python -m pip install -r requirements.txt")
        raise


def normalize_dataframe(df, bank, ticker, report_type):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()

    result = df.copy()
    result.insert(0, "bank", bank)
    result.insert(1, "ticker", ticker)
    result.insert(2, "report_type", report_type)
    return result


def crawl_bank(Fundamental, bank, ticker):
    print(f"\n--- {bank} ({ticker}) ---")
    finance = Fundamental().equity(ticker)

    results = {
        "balance_sheet": pd.DataFrame(),
        "income_statement": pd.DataFrame(),
    }

    try:
        df = finance.balance_sheet(period="year", format="long")
        results["balance_sheet"] = normalize_dataframe(
            df, bank, ticker, "balance_sheet"
        )
        print(f"[OK] Balance Sheet: {len(results['balance_sheet'])} dòng")
    except Exception as error:
        print(f"[ERROR] Balance Sheet: {error}")

    try:
        df = finance.income_statement(period="year", format="long")
        results["income_statement"] = normalize_dataframe(
            df, bank, ticker, "income_statement"
        )
        print(f"[OK] Income Statement: {len(results['income_statement'])} dòng")
    except Exception as error:
        print(f"[ERROR] Income Statement: {error}")

    return results


def combine_frames(frames):
    valid = [
        df for df in frames
        if isinstance(df, pd.DataFrame) and not df.empty
    ]
    return pd.concat(valid, ignore_index=True) if valid else pd.DataFrame()


# ============================================================
# 4. CLEAN + STANDARDIZE
# ============================================================

def convert_to_billion_vnd(value):
    if pd.isna(value):
        return None
    try:
        return float(value) / 1_000_000_000
    except (TypeError, ValueError):
        return None


def extract_vnstock_value(df, bank, config, year):

    if df is None or df.empty or "bank" not in df.columns:
        return None, None

    # ---------- VNStock v5 long/tidy ----------
    if {"period", "value"}.issubset(df.columns):
        id_column = next(
            (col for col in ("id", "item_id") if col in df.columns),
            None,
        )
        if id_column is None:
            return None, None

        period_numeric = pd.to_numeric(df["period"], errors="coerce")
        rows = df[
            (df["bank"] == bank)
            & (df[id_column] == config["item_id"])
            & (period_numeric == int(year))
        ].copy()

        rows = rows[rows["value"].notna()]
        if rows.empty:
            return None, None

        row = rows.iloc[0]
        raw_value = pd.to_numeric(row["value"], errors="coerce")
        if pd.isna(raw_value):
            return None, None

        label = row.get("name", row.get("item", ""))
        source_field = "value"
        schema = "long"

    # ---------- Legacy / compatibility wide ----------
    else:
        id_column = next(
            (col for col in ("item_id", "id") if col in df.columns),
            None,
        )
        if id_column is None:
            return None, None

        rows = df[
            (df["bank"] == bank)
            & (df[id_column] == config["item_id"])
        ].copy()

        if rows.empty:
            return None, None

        # Chỉ nhận các cột có tên là năm 4 chữ số.
        year_columns = [
            col for col in df.columns
            if str(col).isdigit() and len(str(col)) == 4
        ]
        if not year_columns:
            return None, None

        year_numbers_in_output_order = [int(str(col)) for col in year_columns]
        sorted_years = sorted(year_numbers_in_output_order)

        # Theo tài liệu VNStock wide chuẩn: kỳ cũ -> kỳ mới.
        # Nếu header cũng tăng dần, nhãn năm là đúng.
        if year_numbers_in_output_order == sorted_years:
            year_to_source_column = {
                int(str(col)): col for col in year_columns
            }
            mapping_note = "wide_header_year"
        else:
            # Output legacy đang gặp: header giảm dần nhưng chuỗi giá trị vẫn
            # được xếp kỳ cũ -> kỳ mới. Ánh xạ theo vị trí, không hard-code năm.
            year_to_source_column = dict(zip(sorted_years, year_columns))
            mapping_note = "wide_position_normalized"

        source_field = year_to_source_column.get(int(year))
        if source_field is None:
            return None, None

        row = rows.iloc[0]
        raw_value = pd.to_numeric(row[source_field], errors="coerce")
        if pd.isna(raw_value):
            return None, None

        label = row.get("item", row.get("name", ""))
        schema = mapping_note

    raw_value = float(raw_value)

    if config.get("absolute", False):
        raw_value = abs(raw_value)

    value_clean = convert_to_billion_vnd(raw_value)

    evidence = (
        f"{label} "
        f"[{id_column}={config['item_id']}; "
        f"target_year={year}; source_field={source_field}; schema={schema}]"
    )

    return value_clean, evidence



def normalize_raw_years(df):
    """
    Chuẩn hóa Raw VNStock chỉ còn 2024-2025.

    Môi trường hiện tại trả wide với header 2025, 2024, 2023, 2022
    nhưng đối chiếu BCTC cho thấy chuỗi giá trị đi theo kỳ cũ -> kỳ mới.
    Hàm dùng cùng quy tắc positional mapping với extract_vnstock_value(),
    sau đó xuất nhãn năm thực 2024 và 2025.
    """
    if df is None or df.empty:
        return pd.DataFrame()

    result = df.copy()

    # Nếu VNStock thực sự trả long/tidy thì lọc trực tiếp kỳ 2024-2025.
    if {"period", "value"}.issubset(result.columns):
        period_numeric = pd.to_numeric(result["period"], errors="coerce")
        result = result[period_numeric.isin(TARGET_YEARS)].copy()
        result["period"] = pd.to_numeric(result["period"], errors="coerce").astype("Int64")
        return result.reset_index(drop=True)

    # Wide schema: nhận diện các cột năm và chuẩn hóa theo cùng logic extraction.
    year_columns = [
        col for col in result.columns
        if str(col).isdigit() and len(str(col)) == 4
    ]
    if not year_columns:
        return result.reset_index(drop=True)

    year_numbers_in_output_order = [int(str(col)) for col in year_columns]
    sorted_years = sorted(year_numbers_in_output_order)

    if year_numbers_in_output_order == sorted_years:
        year_to_source_column = {int(str(col)): col for col in year_columns}
    else:
        year_to_source_column = dict(zip(sorted_years, year_columns))

    non_year_columns = [col for col in result.columns if col not in year_columns]
    normalized = result[non_year_columns].copy()

    # Chỉ giữ đúng hai năm bài cần và đặt tên theo NĂM THỰC.
    for year in TARGET_YEARS:
        source_col = year_to_source_column.get(year)
        normalized[str(year)] = result[source_col] if source_col is not None else pd.NA

    return normalized.reset_index(drop=True)

def create_clean_vnstock_data(balance_all, income_all):
    """
    Phạm vi dữ liệu VNStock dùng cho phần credit:

    2025:
        - total_loans
        - credit_risk_provision
        - provision_expense

    2024:
        - total_loans
          Chỉ dùng cùng total_loans 2025 để tính average loans cho CoR.

    Các biến phân loại nợ (Group 2, Group 3-5, classified_loans)
    và CAR được bổ sung từ nguồn công bố chính thức.
    """
    rows = []

    source_frames = {
        "balance_sheet": balance_all,
        "income_statement": income_all,
    }

    needed_from_vnstock = {
        2025: [
            "total_loans",
            "credit_risk_provision",
            "provision_expense",
        ],
        2024: [
            "total_loans",
        ],
    }

    for bank, ticker in BANKS.items():
        for year, variables in needed_from_vnstock.items():
            for variable in variables:
                config = VNSTOCK_VARIABLE_MAP[variable]

                value, evidence = extract_vnstock_value(
                    source_frames[config["sheet"]],
                    bank,
                    config,
                    year,
                )

                rows.append({
                    "bank": bank,
                    "ticker": ticker,
                    "year": year,
                    "variable": variable,
                    "value_clean": value,
                    "unit_clean": config["unit"],
                    "source": "VNStock",
                    "source_title": None,
                    "source_url": None,
                    "evidence_text": evidence,
                    "status": "verified" if value is not None else "missing",
                })

    return pd.DataFrame(rows)


def add_credit_supplements(clean):
    rows = []

    for bank, values in CREDIT_SUPPLEMENTS_2025.items():
        ticker = BANKS[bank]

        for variable, (value, unit) in values.items():
            existing = clean[
                (clean["bank"] == bank)
                & (clean["year"] == 2025)
                & (clean["variable"] == variable)
                & clean["value_clean"].notna()
            ]

            if not existing.empty:
                continue

            source_key = "car" if variable == "car" else "debt"
            source_title, source_url = CREDIT_SUPPLEMENT_SOURCES[bank][source_key]

            rows.append({
                "bank": bank,
                "ticker": ticker,
                "year": 2025,
                "variable": variable,
                "value_clean": value,
                "unit_clean": unit,
                "source": "Official disclosure / audited report",
                "source_title": source_title,
                "source_url": source_url,
                "evidence_text": (
                    f"{source_title}; variable={variable}; "
                    f"value={value} {unit}"
                ),
                "status": "verified_supplement",
            })

    if rows:
        clean = pd.concat(
            [clean, pd.DataFrame(rows)],
            ignore_index=True,
            sort=False,
        )

    return clean


def create_credit_clean_data(clean):
    rows = []

    for bank, ticker in BANKS.items():
        for year, variables in CREDIT_REQUIRED.items():
            for variable in variables:
                hit = clean[
                    (clean["bank"] == bank)
                    & (clean["year"] == year)
                    & (clean["variable"] == variable)
                ]

                if hit.empty:
                    rows.append({
                        "bank": bank,
                        "ticker": ticker,
                        "year": year,
                        "variable": variable,
                        "value_clean": None,
                        "unit_clean": "%" if variable == "car" else "ty_dong",
                        "source": None,
                        "source_title": None,
                        "source_url": None,
                        "evidence_text": None,
                        "status": "missing",
                    })
                else:
                    row = hit.iloc[0].to_dict()
                    row["ticker"] = ticker
                    if pd.isna(row.get("value_clean")):
                        row["status"] = "missing"
                    rows.append(row)

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["bank", "year", "variable"]
    ).reset_index(drop=True)


# ============================================================
# 5. CREDIT METRICS
# ============================================================

def one_value(clean, bank, year, variable):
    hit = clean[
        (clean["bank"] == bank)
        & (clean["year"] == year)
        & (clean["variable"] == variable)
        & clean["value_clean"].notna()
    ]

    if hit.empty:
        return None

    values = pd.to_numeric(
        hit["value_clean"], errors="coerce"
    ).dropna().unique()

    if len(values) != 1:
        return None

    return float(values[0])


def safe_pct(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * 100


def calculate_credit_metrics(credit_clean):
    rows = []

    for bank, ticker in BANKS.items():
        loans_2024 = one_value(
            credit_clean, bank, 2024, "total_loans"
        )
        loans_2025 = one_value(
            credit_clean, bank, 2025, "total_loans"
        )
        classified_loans_2025 = one_value(
            credit_clean, bank, 2025, "classified_loans"
        )
        g2 = one_value(
            credit_clean, bank, 2025, "group_2_loans"
        )
        g3 = one_value(
            credit_clean, bank, 2025, "group_3_loans"
        )
        g4 = one_value(
            credit_clean, bank, 2025, "group_4_loans"
        )
        g5 = one_value(
            credit_clean, bank, 2025, "group_5_loans"
        )
        llp = one_value(
            credit_clean, bank, 2025, "credit_risk_provision"
        )
        provision_expense = one_value(
            credit_clean, bank, 2025, "provision_expense"
        )
        car = one_value(
            credit_clean, bank, 2025, "car"
        )

        npl_amount = (
            g3 + g4 + g5
            if all(x is not None for x in [g3, g4, g5])
            else None
        )

        average_loans = (
            (loans_2024 + loans_2025) / 2
            if loans_2024 is not None and loans_2025 is not None
            else None
        )

        rows.append({
            "bank": bank,
            "ticker": ticker,
            "NPL_%": safe_pct(npl_amount, classified_loans_2025),
            "Group2_%": safe_pct(g2, classified_loans_2025),
            "LLR_NPL_%": safe_pct(llp, npl_amount),
            "CoR_%": safe_pct(provision_expense, average_loans),
            "CAR_%": car,
        })

    return pd.DataFrame(rows)


# ============================================================
# 6. QUALITY CHECKS + SOURCES
# ============================================================

def create_missing_check(credit_clean):
    missing = credit_clean[
        credit_clean["value_clean"].isna()
    ].copy()

    columns = [
        "bank", "year", "variable",
        "status", "source", "evidence_text",
    ]

    if missing.empty:
        return pd.DataFrame(columns=columns)

    return missing[columns].reset_index(drop=True)


def create_consistency_check(credit_clean, metrics):
    issues = []

    for _, row in credit_clean.iterrows():
        if pd.isna(row["value_clean"]):
            continue

        expected_unit = "%" if row["variable"] == "car" else "ty_dong"

        if row["unit_clean"] != expected_unit:
            issues.append({
                "bank": row["bank"],
                "year": row["year"],
                "item": row["variable"],
                "check": "unit",
                "status": "review",
                "detail": f"Expected {expected_unit}, got {row['unit_clean']}",
            })

        if row["variable"] != "car" and float(row["value_clean"]) < 0:
            issues.append({
                "bank": row["bank"],
                "year": row["year"],
                "item": row["variable"],
                "check": "sign",
                "status": "review",
                "detail": "Negative value",
            })

    for _, row in metrics.iterrows():
        for column in ["NPL_%", "Group2_%", "CAR_%"]:
            value = row[column]
            if pd.notna(value) and not 0 <= float(value) <= 100:
                issues.append({
                    "bank": row["bank"],
                    "year": 2025,
                    "item": column,
                    "check": "range",
                    "status": "review",
                    "detail": f"Out of 0-100: {value}",
                })

    columns = [
        "bank", "year", "item",
        "check", "status", "detail",
    ]

    if not issues:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(issues, columns=columns)


def create_data_sources(credit_clean):
    columns = [
        "bank", "year", "variable",
        "value_clean", "unit_clean",
        "source", "source_title", "source_url",
        "evidence_text", "status",
    ]

    result = credit_clean.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = None

    return result[columns].copy()


def metric_definitions():
    return pd.DataFrame([
        {
            "indicator": "NPL",
            "formula": "(Group 3 + Group 4 + Group 5) / Total classified loans (Groups 1-5) * 100",
            "unit": "%",
            "direction": "LOW",
            "weight_BCDS": "14%",
        },
        {
            "indicator": "Group 2 Ratio",
            "formula": "Group 2 / Total classified loans (Groups 1-5) * 100",
            "unit": "%",
            "direction": "LOW",
            "weight_BCDS": "7%",
        },
        {
            "indicator": "LLR/NPL",
            "formula": "Credit risk provision / NPL amount * 100",
            "unit": "%",
            "direction": "HIGH",
            "weight_BCDS": "8%",
        },
        {
            "indicator": "CoR",
            "formula": "Provision expense / Average loans(2024, 2025) * 100",
            "unit": "%",
            "direction": "LOW",
            "weight_BCDS": "6%",
        },
        {
            "indicator": "CAR",
            "formula": "Official disclosed CAR at year-end 2025",
            "unit": "%",
            "direction": "HIGH",
            "weight_BCDS": "7%",
        },
    ])


# ============================================================
# 7. MAIN
# ============================================================

def main():
    print_environment()
    Fundamental = load_vnstock()

    balance_frames = []
    income_frames = []
    status_rows = []

    print("\n" + "=" * 70)
    print("CRAWL VNSTOCK - 5 BANKS")
    print("=" * 70)

    for bank, ticker in BANKS.items():
        try:
            data = crawl_bank(
                Fundamental, bank, ticker
            )

            balance_frames.append(
                data["balance_sheet"]
            )
            income_frames.append(
                data["income_statement"]
            )

            success = (
                not data["balance_sheet"].empty
                or not data["income_statement"].empty
            )

            status_rows.append({
                "bank": bank,
                "ticker": ticker,
                "source": "VNStock",
                "status": "success" if success else "review",
                "message": "",
            })

        except Exception as error:
            print(f"[ERROR] {bank}: {error}")
            status_rows.append({
                "bank": bank,
                "ticker": ticker,
                "source": "VNStock",
                "status": "error",
                "message": str(error),
            })

    # Giữ bản crawl gốc để extraction dùng đúng source field của VNStock.
    raw_balance_source = combine_frames(balance_frames)
    raw_income_source = combine_frames(income_frames)

    # Raw sheets để nộp: toàn bộ khoản mục, nhưng chỉ 2024-2025
    # và nhãn năm đã được chuẩn hóa theo năm thực tế.
    raw_balance = normalize_raw_years(raw_balance_source)
    raw_income = normalize_raw_years(raw_income_source)

    clean = create_clean_vnstock_data(
        raw_balance_source, raw_income_source
    )
    clean = add_credit_supplements(clean)

    credit_clean = create_credit_clean_data(clean)
    credit_metrics = calculate_credit_metrics(credit_clean)
    missing_check = create_missing_check(credit_clean)
    consistency_check = create_consistency_check(
        credit_clean, credit_metrics
    )
    data_sources = create_data_sources(credit_clean)
    crawl_status = pd.DataFrame(status_rows)

    credit_clean.to_csv(
        CLEAN_CSV_FILE,
        index=False,
        encoding="utf-8-sig",
    )

    with pd.ExcelWriter(
        OUTPUT_FILE,
        engine="openpyxl",
    ) as writer:
        raw_balance.to_excel(
            writer, sheet_name="Raw_Balance", index=False
        )
        raw_income.to_excel(
            writer, sheet_name="Raw_Income", index=False
        )
        credit_clean.to_excel(
            writer, sheet_name="Clean_Data", index=False
        )
        credit_metrics.to_excel(
            writer, sheet_name="Credit_Metrics", index=False
        )
        missing_check.to_excel(
            writer, sheet_name="Missing_Check", index=False
        )
        consistency_check.to_excel(
            writer, sheet_name="Consistency_Check", index=False
        )
        data_sources.to_excel(
            writer, sheet_name="Data_Sources", index=False
        )
        metric_definitions().to_excel(
            writer, sheet_name="Metric_Definitions", index=False
        )
        crawl_status.to_excel(
            writer, sheet_name="Crawl_Status", index=False
        )

    print("\n" + "=" * 70)
    print("HOÀN THÀNH")
    print("=" * 70)
    print(f"Clean input rows     : {len(credit_clean)}")
    print(f"Missing inputs       : {len(missing_check)}")
    print(f"Consistency issues   : {len(consistency_check)}")
    print(f"Excel                : {OUTPUT_FILE}")
    print(f"CSV                  : {CLEAN_CSV_FILE}")
    print("\nCredit metrics:")
    print(credit_metrics.to_string(index=False))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Đã dừng chương trình.")
    except PermissionError:
        print(
            "\n[ERROR] Không thể ghi file output. "
            "Hãy đóng credit_data.xlsx nếu đang mở rồi chạy lại."
        )
        raise
    except Exception as error:
        print(f"\n[ERROR] {error}")
        raise
