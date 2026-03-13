from fastapi import FastAPI, HTTPException
from vnstock import Vnstock, register_user
from datetime import datetime, timedelta

# Xác thực bằng API Key bạn vừa được cấp
register_user(api_key="vnstock_7415f142e42b8812cddb3b5a8cf3ea20")

# Khởi tạo API
app = FastAPI(
    title="Supreme V5 Stage 0 Data Engine",
    description="API cung cấp Data Pack cho hệ thống V5 (Powered by Vnstock V3)"
)

@app.get("/api/v1/stage0/{ticker}")
def get_stage0_data(ticker: str):
    try:
        ticker = ticker.upper().strip()
        end_date = datetime.today().strftime('%Y-%m-%d')
        start_date = (datetime.today() - timedelta(days=365)).strftime('%Y-%m-%d')

        # 1. Khởi tạo đối tượng lấy dữ liệu chuẩn Vnstock V3
        stock = Vnstock().stock(symbol=ticker, source='TCBS')
        
        # 2. Kéo dữ liệu OHLCV (Bắt buộc cho Stage 0 của V5 Engine)
        df_ohlcv = stock.quote.history(start=start_date, end=end_date, interval='1D')
        
        if df_ohlcv is None or df_ohlcv.empty:
            raise HTTPException(status_code=404, detail=f"Dữ liệu cốt lõi của {ticker} bị thiếu (Miss_core > 0.15). Force-Abstain = TRUE.")

        # Lấy 60 ngày gần nhất để tối ưu bộ nhớ cho GPT
        recent_ohlcv = df_ohlcv.tail(60).to_dict(orient='records')

        # 3. Kéo dữ liệu hồ sơ doanh nghiệp (Context)
        try:
            profile_df = stock.company.profile()
            profile_data = profile_df.to_dict(orient='records')[0] if not profile_df.empty else "Không có thông tin"
        except:
            profile_data = "Lỗi khi lấy thông tin doanh nghiệp"

        # 4. Trả về cấu trúc JSON 
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
