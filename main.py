from fastapi import FastAPI
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import traceback
import os

# Cài đặt API Key vào biến môi trường hệ thống (Chuẩn an toàn nhất)
os.environ["VNSTOCK_API_KEY"] = "vnstock_7415f142e42b8812cddb3b5a8cf3ea20"

app = FastAPI(
    title="Supreme V5 Stage 0 Data Engine",
    description="API cung cấp Data Pack chuẩn V5 - Bọc lỗi toàn diện"
)

@app.get("/api/v1/stage0/{ticker}")
def get_stage0_data(ticker: str):
    try:
        # Đưa lệnh import vào trong hàm. Nếu lỗi, web không bị sập mà sẽ in ra JSON
        from vnstock import Vnstock
        
        ticker = ticker.upper().strip()
        now = datetime.today()
        end_date = now.strftime('%Y-%m-%d')
        start_1y = (now - timedelta(days=365)).strftime('%Y-%m-%d')
        start_3y = (now - timedelta(days=365*3)).strftime('%Y-%m-%d')

        # Khởi tạo theo đúng chuẩn Quickstart V3
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        
        # --- KHỐI 1: DAILY OHLCV ---
        try:
            df_daily = stock.quote.history(start=start_1y, end=end_date, interval='1D')
            daily_ohlcv = df_daily.tail(100).to_dict('records') if (df_daily is not None and not df_daily.empty) else []
        except:
            daily_ohlcv = []
            
        if len(daily_ohlcv) == 0:
            return JSONResponse(status_code=404, content={"detail": "Core missingness > 0.15. FORCE_ABSTAIN = TRUE. Không tìm thấy dữ liệu giá Daily."})

        # --- KHỐI 2: WEEKLY OHLCV ---
        try:
            df_weekly = stock.quote.history(start=start_3y, end=end_date, interval='1W')
            weekly_ohlcv = df_weekly.tail(100).to_dict('records') if (df_weekly is not None and not df_weekly.empty) else []
        except:
            weekly_ohlcv = []

        # --- KHỐI 3: VNINDEX ---
        try:
            vnindex = Vnstock().stock(symbol='VNINDEX', source='TCBS')
            df_vnindex = vnindex.quote.history(start=start_1y, end=end_date, interval='1D')
            vnindex_ohlcv = df_vnindex.tail(60).to_dict('records') if (df_vnindex is not None and not df_vnindex.empty) else []
        except:
            vnindex_ohlcv = []

        # --- KHỐI 4: PROFILE ---
        try:
            profile_df = stock.company.profile()
            profile_data = profile_df.to_dict('records')[0] if (profile_df is not None and not profile_df.empty) else "Lỗi/Trống thông tin"
        except:
            profile_data = "Lỗi truy xuất Profile"

        # --- TRẢ VỀ JSON ---
        return {
            "Analysis_Metadata": {
                "Asset": ticker,
                "Event_Firewall_Status": "Pending GPT Inference",
                "Data_Completeness": {
                    "Daily": "OK" if len(daily_ohlcv) > 0 else "Missing",
                    "Weekly": "OK" if len(weekly_ohlcv) > 0 else "Missing",
                    "VNINDEX": "OK" if len(vnindex_ohlcv) > 0 else "Missing"
                }
            },
            "Data_Pack": {
                "Company_Profile": profile_data,
                "Market_Regime_VNINDEX_60D": vnindex_ohlcv,
                "Structure_Weekly_HTF": weekly_ohlcv,
                "Trigger_Daily_LTF": daily_ohlcv
            }
        }
        
    except Exception as e:
        # Nếu có bất kỳ lỗi gì, nó sẽ in ra màn hình trình duyệt chứ KHÔNG BAO GIỜ bị lỗi 500 trắng xoá nữa
        return JSONResponse(status_code=500, content={
            "Lỗi_Hệ_Thống": str(e),
            "Chi_Tiết_Kỹ_Thuật": traceback.format_exc()
        })
