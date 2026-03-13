from fastapi import FastAPI, HTTPException
from vnstock import Vnstock, register_user
from datetime import datetime, timedelta

# Xác thực API Key (Gói Free)
register_user(api_key="vnstock_7415f142e42b8812cddb3b5a8cf3ea20")

app = FastAPI(
    title="Supreme V5 Stage 0 Data Engine",
    description="API cung cấp Data Pack toàn diện, tích hợp Missingness Control theo chuẩn V5 Algorithmic Operating System"
)

@app.get("/api/v1/stage0/{ticker}")
def get_stage0_data(ticker: str):
    ticker = ticker.upper().strip()
    now = datetime.today()
    end_date = now.strftime('%Y-%m-%d')
    start_1y = (now - timedelta(days=365)).strftime('%Y-%m-%d')
    start_3y = (now - timedelta(days=365*3)).strftime('%Y-%m-%d')

    # Khởi tạo đối tượng Vnstock (Sử dụng nguồn VCI ổn định nhất hiện tại)
    stock = Vnstock().stock(symbol=ticker, source='VCI')
    vnindex = Vnstock().stock(symbol='VNINDEX', source='VCI')

    # --- KHỐI 1: OHLCV DAILY (Cốt lõi cho Stage 3 & 4) ---
    try:
        df_daily = stock.quote.history(start=start_1y, end=end_date, interval='1D')
        daily_ohlcv = df_daily.tail(100).to_dict('records') if not df_daily.empty else []
        is_daily_missing = len(daily_ohlcv) == 0
    except:
        daily_ohlcv = []
        is_daily_missing = True

    # Luật Hard Force-Abstain của V5: Thiếu giá Daily là ngưng toàn bộ
    if is_daily_missing:
        raise HTTPException(status_code=404, detail="Core missingness > 0.15. FORCE_ABSTAIN = TRUE. Không có dữ liệu giá Daily.")

    # --- KHỐI 2: OHLCV WEEKLY (Cấu trúc dài hạn - Stage 3) ---
    try:
        df_weekly = stock.quote.history(start=start_3y, end=end_date, interval='1W')
        weekly_ohlcv = df_weekly.tail(100).to_dict('records') if not df_weekly.empty else []
        is_weekly_missing = len(weekly_ohlcv) == 0
    except:
        weekly_ohlcv = []
        is_weekly_missing = True

    # --- KHỐI 3: VNINDEX (Bối cảnh Regime & Intermarket - Stage 1) ---
    try:
        df_vnindex = vnindex.quote.history(start=start_1y, end=end_date, interval='1D')
        vnindex_ohlcv = df_vnindex.tail(60).to_dict('records') if not df_vnindex.empty else []
        is_vnindex_missing = len(vnindex_ohlcv) == 0
    except:
        vnindex_ohlcv = []
        is_vnindex_missing = True

    # --- KHỐI 4: THÔNG TIN DOANH NGHIỆP (Tường lửa sự kiện - Stage 0) ---
    try:
        profile_df = stock.company.profile()
        profile_data = profile_df.to_dict('records')[0] if not profile_df.empty else "Không có dữ liệu Profile"
    except:
        profile_data = "Lỗi khi truy xuất thông tin doanh nghiệp"

    # --- KHỐI 5: TÍNH TOÁN MISSINGNESS CONTROL THUẬT TOÁN V5 ---
    # Ước tính Miss_core dựa trên dữ liệu lấy được vs dữ liệu V5 yêu cầu
    miss_core_score = 0.0
    if is_weekly_missing: miss_core_score += 0.05
    if is_vnindex_missing: miss_core_score += 0.05
    # Cộng thêm 0.05 mặc định vì gói Free không có Order-book/Slippage proxies
    miss_core_score += 0.05 

    # --- ĐÓNG GÓI JSON THEO CHUẨN ĐẦU VÀO V5 ---
    return {
        "Analysis_Metadata": {
            "Asset": ticker,
            "Venue_Context": "Vietnam Stock Exchange (HOSE/HNX/UPCOM)",
            "Calculated_Miss_Core": round(miss_core_score, 2),
            "Event_Firewall_Status": "Pending GPT Inference",
            "Data_Quality_Flags": {
                "Daily_OHLCV": "Available",
                "Weekly_OHLCV": "Available" if not is_weekly_missing else "Missing",
                "VNINDEX_Breadth": "Available" if not is_vnindex_missing else "Missing",
                "Microstructure_Orderbook": "Missing (Free Tier Constraint)",
                "Options_Derivatives_Context": "Missing"
            }
        },
        "Data_Pack": {
            "Company_Profile": profile_data,
            "Market_Regime_VNINDEX_60D": vnindex_ohlcv,
            "Structure_Weekly_HTF": weekly_ohlcv,
            "Trigger_Daily_LTF": daily_ohlcv
        }
    }
