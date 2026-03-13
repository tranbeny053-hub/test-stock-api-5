from fastapi import FastAPI, HTTPException
from vnstock import stock_historical_data, stock_profile
from datetime import datetime, timedelta
import pandas as pd

# Khởi tạo API
app = FastAPI(
    title="Supreme V5 Stage 0 Data Engine",
    description="API cung cấp Data Pack cho hệ thống Supreme Ultimate Probability Engine V5"
)

@app.get("/api/v1/stage0/{ticker}")
def get_stage0_data(ticker: str):
    """
    Lấy dữ liệu OHLCV và Profile của một mã chứng khoán.
    Ví dụ: /api/v1/stage0/FPT
    """
    try:
        ticker = ticker.upper().strip()
        # Lấy dữ liệu 1 năm tính đến hôm nay
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

        # 1. Kéo dữ liệu OHLCV (Bắt buộc cho Stage 0)
        df_ohlcv = stock_historical_data(symbol=ticker, start_date=start_date, end_date=end_date, resolution='1D', type='stock')
        
        # Kiểm tra Missingness (Thiếu hụt dữ liệu)
        if df_ohlcv is None or df_ohlcv.empty:
            raise HTTPException(status_code=404, detail=f"Dữ liệu cốt lõi (Core Data) của {ticker} bị thiếu (Miss_core > 0.15). Force-Abstain = TRUE.")

        # Lọc lấy 60 ngày gần nhất để không làm quá tải bộ nhớ (Context Window) của GPT
        recent_ohlcv = df_ohlcv.tail(60).to_dict(orient='records')

        # 2. Kéo dữ liệu hồ sơ doanh nghiệp (Venue/Context)
        try:
            profile = stock_profile(symbol=ticker)
            profile_data = profile.to_dict(orient='records')[0] if not profile.empty else "Không có thông tin"
        except:
            profile_data = "Lỗi khi lấy thông tin doanh nghiệp"

        # 3. Trả về cấu trúc JSON chuẩn bị cho V5 Engine
        return {
            "Analysis_Metadata": {
                "Asset": ticker,
                "Event_Risk_Firewall": "Pending GPT Analysis"
            },
            "Data_Pack": {
                "Profile": profile_data,
                "OHLCV_60Days": recent_ohlcv
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Chạy server (Dùng cho môi trường đám mây)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
