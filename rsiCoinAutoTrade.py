import time
import pyupbit
import requests

access = "your key"
secret = "your key"
myToken = "your token"

#현재가 조회
def get_current_price(ticker):
    """현재가 조회"""
    try:
        return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]
    except Exception:
        df = pyupbit.get_ohlcv(ticker, interval="minute1", count=1)
        return df['close'].iloc[0]

#현재 거래량 조회
def get_current_volume(ticker):
    """현재 거래량 조회"""
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["bid_size"]

#슬랙 메세지 보내기
def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

# Upbit에 로그인
upbit = pyupbit.Upbit(access, secret)
print("Rsi Crypto AutoTrade start")

#로그인, 내 잔고 내역을 슬랙에 알림
post_message(myToken,"#cryptoautotrade", "*"*20)
post_message(myToken,"#cryptoautotrade", "RSI 코인 자동매매 실행")
post_message(myToken,"#cryptoautotrade", "잔액: " + str(int(upbit.get_balance("KRW"))) + "원")
post_message(myToken,"#cryptoautotrade", "*"*20)

# 볼린저 밴드 하단 도달 여부 확인 함수
def is_below_bollinger_band(ticker, interval='minute15', ma=20, sigma=2):
    df = pyupbit.get_ohlcv(ticker, interval = interval, count = ma)
    close_prices = df['close']
    ma = close_prices.rolling(window=20).mean()
    std = close_prices.rolling(window=20).std()
    lower_band = ma - (std * sigma)
    return close_prices.iloc[-1] <= lower_band.iloc[-1]

# 이동 평균선 기간 설정
long_window = 20

# 매수할 금액 (예: 8000원)
buy_amount = 10000

# 자동매매 실행 후 손익
gain = 0

while True:
    try:
        # 모든 코인정보 가져오기
        all_tickers = pyupbit.get_tickers(fiat="KRW")

        # 티커 심볼 별로 현재의 1시간 거래량을 가져오기
        volume_info = {ticker: pyupbit.get_ohlcv(ticker, interval="hour1", count=1)['volume'][0] for ticker in all_tickers}

        # 모든 코인의 거래량 총합 계산
        total_volume = sum(volume_info.values())

        # 전체 코인의 수
        num_coins = len(all_tickers)

        # 평균 거래량 계산
        average_volume = total_volume / num_coins

        # 평균 이상의 코인 심볼 리스트 만들기
        high_volume_tickers = [ticker for ticker, volume in volume_info.items() if volume > average_volume]

        # 내 잔고
        my_account_list = {}
        my_account_KRW = upbit.get_balance("KRW")

        # 결과 출력
        print("평균 이상의 코인 심볼 리스트:", high_volume_tickers)

        for ticker in high_volume_tickers:
            # 15분간격 정보 가져오기
            df = pyupbit.get_ohlcv(ticker, interval="minute15", count=long_window+15)

            #현재가 조회
            current_price = get_current_price(ticker) 

            #내 계좌 코인 정보
            balance = upbit.get_balance(ticker.replace("KRW-", ""))

            # 이동 평균 계산
            df['MA_long'] = df['close'].rolling(window=long_window).mean()

            # 현재 이동 평균 계산
            current_MA_long = (df['MA_long'][-1] * (long_window-1) + current_price) / (long_window)
 
            print("종목명 : " + str(ticker), end=", ")
            print("현재가격 : " + str(current_price) + "원")

            # 매수 조건 확인
            #1_rsi 하단에 닿음
            #2_거래량
            if  is_below_bollinger_band(ticker):

                # 현재 잔고 확인
                #balance = upbit.get_balance(ticker.replace("KRW-", ""))

                # 매수 조건 확인 및 매수 주문
                if balance * current_price < 100:
                    krw_balance = upbit.get_balance("KRW")
                    if krw_balance > buy_amount:  # 최소 매수 금액 설정
                        #buy_amount = krw_balance * buy_ratio
                        upbit.buy_market_order(ticker, buy_amount * 0.9995)  # 수수료 고려

                        print("*"*20)
                        print("매수종목명 : " + ticker)
                        print("현재가격 : " + str(current_price))
                        print("*"*20 + "\n")

                        #매수시 슬랙 알림
                        post_message(myToken,"#cryptoautotrade", "*"*20)
                        post_message(myToken,"#cryptoautotrade", str(ticker) + " 매수 : " + str(buy_amount) + "원")

                        # 현재 잔고 확인
                        balance = upbit.get_balance("KRW")
                        post_message(myToken,"#cryptoautotrade", "보유현금: " +  str(int(balance)) + "원")
                        post_message(myToken,"#cryptoautotrade", "*"*20)

                        # 매수 주문 후 잔고 업데이트 대기
                        time.sleep(5)
            
            # 매도(이평선보다 가격이 오를 경우) 조건 확인
            elif  current_price > current_MA_long:

                # 현재 잔고 확인
                #balance = upbit.get_balance(ticker.replace("KRW-", ""))
                if balance * current_price >= 5000:
                    upbit.sell_market_order(ticker, balance)
                    print("*"*20)
                    print("매도종목명 : " + str(ticker))
                    print("현재가격 : " + str(balance))
                    print("*"*20 + "\n")

                    #매도시 슬랙 알림
                    post_message(myToken,"#cryptoautotrade", "*"*20)
                    post_message(myToken,"#cryptoautotrade", str(ticker) + " 매도 : " + str(balance * current_price) + "원")
                    post_message(myToken,"#cryptoautotrade", str(ticker) + " 실현손익 : " + str(int(balance * current_price * 0.9995 - buy_amount)) + "원")
                    gain += int(balance * current_price * 0.9995 - buy_amount)
                    post_message(myToken,"#cryptoautotrade", "자동매매 누적실현손익 : " + str(gain) + "원")

                    # 현재 잔고 확인
                    balance = upbit.get_balance("KRW")
                    post_message(myToken,"#cryptoautotrade", "보유현금: " +  str(int(balance)) + "원")
                    post_message(myToken,"#cryptoautotrade", "*"*20)

        # 내 잔고 확인
        my_account_KRW = upbit.get_balance("KRW")
        print("*"*20)
        print("내 잔고")
        print("현금: " + str(my_account_KRW) + "원")
        print("*"*20+"\n")
        print("탐색중...\n")

        # 5초마다 반복
        time.sleep(5)  

    except Exception as e:
        print(e)
        #슬랙으로 에러 메시지 전송
        if(e!=0):
            post_message(myToken,"#cryptoautotrade", e)
        time.sleep(1)