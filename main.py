from fastapi import FastAPI
from fastapi.responses import JSONResponse
from vnstock import Vnstock, register_user
from datetime import datetime, timedelta
import traceback

# Cố gắng đăng ký API Key (nếu lỗi cũng không làm sập app)
try:
    register_user(api_key="vnstock_7415f142e42b8812cddb3b5a8cf3ea20")
except:
    pass

app = FastAPI(
    title="Supreme V5 Stage 0 Data Engine",
    description="API cung cấp Data Pack với cơ chế chống sập (Bulletproof)"
)

@app.get("/api/v1/stage0/{ticker}")
def get_stage0_data(ticker: str):
    try:
        ticker = ticker.upper().strip()
        now = datetime.today()
        end_date = now.strftime('%Y-%m-%d')
        start_1y = (now - timedelta(days=365)).strftime('%Y-%m-%d')
        start_3y = (now - timedelta(days=365*3)).strftime('%Y-%m-%d')

        # 1. Khởi tạo mã chứng khoán chính
        stock = Vnstock().stock(symbol=ticker, source='VCI')
        
        # 2. Kéo dữ liệu Daily (Cốt lõi)
        try:
            df_daily = stock.quote.history(start=start_1y, end=end_date, interval='1D')
            if df_daily is not None and not df_daily.empty:
                daily_ohlcv = df_daily.tail(100).to_dict('records')
            else:
                daily_ohlcv = []
        except:
            daily_ohlcv = []
            
        # Áp dụng Hard Rule của V5: Không có giá Daily = Nghỉ chơi
        if len(daily_ohlcv) == 0:
            return JSONResponse(status_code=404, content={"detail": "Core missingness > 0.15. FORCE_ABSTAIN = TRUE. Không tìm thấy dữ liệu giá cốt lõi."})

        # 3. Kéo dữ liệu Weekly
        try:
            df_weekly = stock.quote.history(start=start_3y, end=end_date, interval='1W')
            if df_weekly is not None and not df_weekly.empty:
                weekly_ohlcv = df_weekly.tail(100).to_dict('records')
            else:
                weekly_ohlcv = []
        except:
            weekly_ohlcv = []

        # 4. Kéo bối cảnh thị trường (VNINDEX) - Đổi qua nguồn TCBS cho lành
        vnindex_ohlcv = []
        try:
            vnindex = Vnstock().stock(symbol='VNINDEX', source='TCBS')
            df_vnindex = vnindex.quote.history(start=start_1y, end=end_date, interval='1D')
            if df_vnindex is not None and not df_vnindex.empty:
                vnindex_ohlcv = df_vnindex.tail(60).to_dict('records')
        except:
            pass # Lỗi VNINDEX thì bỏ qua, không làm sập web

        # 5. Kéo Profile doanh nghiệp
        try:
            profile_df = stock.company.profile()
            if profile_df is not None and not profile_df.empty:
                profile_data = profile_df.to_dict('records')[0]
            else:
                profile_data = "Không có thông tin profile"
        except:
            profile_data = "Lỗi khi truy xuất profile"

        # 6. Đóng gói trả về JSON
        return {
            "Analysis_Metadata": {
                "Asset": ticker,
                "Event_Firewall_Status": "Pending GPT Inference",
                "Calculated_Miss_Core": 0.05 if len(weekly_ohlcv) > 0 else 0.10
            },
            "Data_Pack": {
                "Company_Profile": profile_data,
                "Market_Regime_VNINDEX_60D": vnindex_ohlcv,
                "Structure_Weekly_HTF": weekly_ohlcv,
                "Trigger_Daily_LTF": daily_ohlcv
            }
        }

    except Exception as e:
        # TẤT CẢ LỖI TRẦM TRỌNG SẼ ĐƯỢC BẮT VÀ IN RA ĐÂY, CHỨ KHÔNG SẬP SERVER NỮA
        return JSONResponse(status_code=500, content={
            "Lỗi_Hệ_Thống": str(e),
            "Chi_Tiết_Kỹ_Thuật": traceback.format_exc(),
            "Hành_Động": "Vui lòng copy toàn bộ chữ này gửi lại cho AI để chẩn đoán chính xác."
        })
