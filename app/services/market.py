from typing import Dict
from curl_cffi import requests as curl_requests
import yfinance as yf
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

class MarketService:
    @staticmethod
    # 미국 3대 주요 지수 조회
    def get_market_summary_legacy() -> Dict:

        session = curl_requests.Session(impersonate="chrome")
        
        us_3 = { "다우": "^DJI", "S&P500": "^GSPC", "나스닥": "^IXIC"}
        total_list = []
        
        for key, value in us_3.items():
            # 최근 2일 데이터 (등락률 계산 시 필요)
            stock_df_tail = yf.download(value, progress=False, session=session, period="2d")
            # print('stock', stock_df_tail)

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
        session.close()
        
        return {"data": total_list}
            
    @staticmethod
    def get_market_summary_single() -> Dict:
        """단일 ticker 데이터를 가져오는 함수"""

        # 브라우저(TLS) 환경을 흉내는 세션 생성
        session = requests.Session(impersonate="chrome")

        us_3 = [ "^DJI", "^GSPC", "^IXIC" ]

        start_time = time.time()
        try:
            # 최근 2일 데이터 (등락률 계산 시 필요)
            stock_df_tail = yf.download(f"{us_3[0]} {us_3[1]} {us_3[2]}", progress=False, session=session, period="2d")

            # if stock_df_tail.empty:
            #     logging.warning(f"{key} ({value}) 데이터가 없습니다.")
            #     return None

            # if len(stock_df_tail) < 2:
            #     logging.warning(f"{key} ({value}): 최소 2일 이상의 데이터가 필요합니다.")
            #     return None

            stock_df_tail_close = stock_df_tail["Close"] # 종가만 추출

            # 등락률 계산: (오늘 종가 - 전일 종가 / 전일 종가) * 100

            total_list = []

            for ticker in us_3:
                try:
                    cur_close = round(stock_df_tail_close.iloc[1][ticker], 2)
                    prev_close = round(stock_df_tail_close.iloc[0][ticker], 2)

                except (IndexError, KeyError) as e:
                    logging.error(f"Data access error for {str(e)}")
                    continue

                change_rate = round(((cur_close - prev_close) / prev_close * 100), 2) # 셋째 자리에서 반올림

                item = { 
                        "ticker": ticker, 
                        "prev_close": prev_close,
                        "cur_close": cur_close,
                        "change_rate": change_rate
                        }
                total_list.append(item)
                end_time = time.time()

            return {"data": total_list}
        
        except Exception as e:
            logging.error(f"Error processing {str(e)}")
        
        finally:
            session.close()  # 세션 명시적 종료

    @staticmethod
    # 미국 3대 주요 지수 조회 (병렬 처리)
    def get_market_summary_con() -> Dict:
        start_time = time.time()
        
        us_3 = { "다우": "^DJI", "S&P500": "^GSPC", "나스닥": "^IXIC"}
        total_list = []
        
        # ThreadPoolExecutor를 사용한 병렬 처리
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 모든 ticker를 동시에 실행
            future_to_ticker = {
                executor.submit(MarketService._fetch_single_ticker, key, value): key 
                for key, value in us_3.items()
            }
            
            # 결과 수집
            for future in as_completed(future_to_ticker):
                ticker_key = future_to_ticker[future]
                try:
                    result = future.result()
                    if result:
                        total_list.append(result)
                except Exception as e:
                    logging.error(f"Error processing {ticker_key}: {str(e)}")
        
        end_time = time.time()
        logging.info(f"Market summary fetched in {end_time - start_time:.2f} seconds")
        
        return {"data": total_list}