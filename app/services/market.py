from typing import Dict
import yfinance as yf
import logging

class MarketService:
    @staticmethod
    # 미국 3대 주요 지수 조회
    def get_market_summary() -> Dict:
        us_3 = { "다우": "^DJI", "S&P500": "^GSPC", "나스닥": "^IXIC"}
        total_list = []
        
        for key, value in us_3.items():
            # 최근 2일 데이터 (등락률 계산 시 필요)
            stock_df_tail = yf.download(value, progress=False, period="2d")

            if stock_df_tail.empty:
                logging.warning(f"{key} ({value}) 데이터가 없습니다.")
                continue

            if len(stock_df_tail) < 2:
                logging.warning(f"{key} ({value}): 최소 2일 이상의 데이터가 필요합니다.")
                continue

            #stock_df_tail = stock_df.tail(n=2) 
            stock_df_tail_close = stock_df_tail["Close"] # 종가만 추출

            # 등락률 계산: (오늘 종가 - 전일 종가 / 전일 종가) * 100
            try:
                cur_close = round(stock_df_tail_close.iloc[1][value], 2)
                prev_close = round(stock_df_tail_close.iloc[0][value], 2)
            except (IndexError, KeyError) as e:
                logging.error(f"Data access error for {key}: {str(e)}")
                continue

            change_rate = round(((cur_close - prev_close) / prev_close * 100), 2) # 셋째 자리에서 반올림

            item = { 
                    "ticker": value, 
                    "prev_close": prev_close,
                    "cur_close": cur_close,
                    "change_rate": change_rate
            }
            total_list.append(item)
        
        return {"data": total_list}