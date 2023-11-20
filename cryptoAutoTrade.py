import time
import pyupbit
import requests

access = "yourAccessToken"
secret = "yourSecretToken"
myToken = "yourSlackToken"

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
print("Crypto AutoTrade start")

#로그인, 내 잔고 내역을 슬랙에 알림
post_message(myToken,"#cryptoautotrade", "*"*20)
post_message(myToken,"#cryptoautotrade", "코인 자동매매 실행")
post_message(myToken,"#cryptoautotrade", "잔액: " + str(int(upbit.get_balance("KRW"))) + "원")
post_message(myToken,"#cryptoautotrade", "*"*20)

# 이동 평균선 기간 설정
short_window = 5
mid_window = 10
long_window = 20

# 매수할 비율 설정 (예: 10% => 0.1)
buy_ratio = 0.2

# 자동매매 실행 후 손익
gain = 0

while True:
    try:
        # 모든 코인정보 가져오기
        tickers = pyupbit.get_tickers(fiat="KRW")

        # 내 잔고
        my_account_list = {}
        my_account_KRW = upbit.get_balance("KRW")

        for ticker in tickers:
            # 15분간격 정보 가져오기
            df = pyupbit.get_ohlcv(ticker, interval="minute15", count=long_window+15)

            #현재가 조회
            current_price = get_current_price(ticker) 

            #현재 거래량 조회
            #current_volume = get_current_volume(ticker)

            #내 계좌 코인 정보
            balance = upbit.get_balance(ticker.replace("KRW-", ""))

            # 이동 평균 계산
            df['MA_short'] = df['close'].rolling(window=short_window).mean()
            df['MA_mid'] = df['close'].rolling(window=mid_window).mean()
            df['MA_long'] = df['close'].rolling(window=long_window).mean()

            # 현재 이동 평균 계산
            current_MA_short = (df['MA_short'][-1] * (short_window-1) + current_price) / (short_window)
            current_MA_mid = (df['MA_mid'][-1]* (mid_window-1) + current_price) / (mid_window)
            current_MA_long = (df['MA_long'][-1] * (short_window-1) + current_price) / (long_window)

            # rsi 계산
            df['rsi'] = df['close'].diff(1)

            #일정 기간(150분) 거래대금
            df['price_volume'] = df['volume'].rolling(window=10).mean() * current_price
 
            print("종목명 : " + str(ticker), end=", ")
            print("현재가격 : " + str(current_price) + "원")

            # 매수(골든 크로스, 거래량) 조건 확인
            #k = 1.3 #코인 평균 누적 거래금액의 k배 만큼 높을시 매수
            #1_골든 크로스
            #2_상승세
            #3_매수세
            #4_거래량
            if current_MA_short >= current_MA_long and current_MA_short > current_MA_mid and df['MA_short'].iloc[-1] <= df['MA_long'].iloc[-1]\
                and df['MA_short'].iloc[-2] < df['MA_long'].iloc[-2] and df['MA_long'].iloc[-15] < df['MA_long'].iloc[-1]\
                and df['MA_mid'].iloc[-15] < df['MA_mid'].iloc[-1] and df['rsi'].iloc[-1] > df['rsi'].iloc[-2] and df['price_volume'].iloc[-1] > 200000000:

                # 현재 잔고 확인
                #balance = upbit.get_balance(ticker.replace("KRW-", ""))

                # 매수 조건 확인 및 매수 주문
                if balance * current_price < 10:
                    krw_balance = upbit.get_balance("KRW")
                    #if krw_balance > (5000 / buy_ratio):  # 최소 매수 금액 설정
                    if krw_balance > 8000:  # 최소 매수 금액 설정
                        #buy_amount = krw_balance * buy_ratio
                        buy_amount = 8000
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
            
            # 매도(이평선 크로스) 조건 확인
            elif  current_MA_short <= current_MA_long and current_MA_short <= current_MA_mid:

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
                    post_message(myToken,"#cryptoautotrade", str(ticker) + " 실현손익 : " + str(int(balance * current_price * 0.9995 - 8000)) + "원")
                    gain += int(balance * current_price * 0.9995 - 8000)
                    post_message(myToken,"#cryptoautotrade", "자동매매 총실현손익 : " + str(gain) + "원")

                    # 현재 잔고 확인
                    balance = upbit.get_balance("KRW")
                    post_message(myToken,"#cryptoautotrade", "보유현금: " +  str(int(balance)) + "원")
                    post_message(myToken,"#cryptoautotrade", "*"*20)

            # 1.5% 상승시 매도
            elif current_price * balance >= 8000 * 0.9995 * 1.015:
                upbit.sell_market_order(ticker, balance)
                print("*"*20)
                print("매도종목명 : " + str(ticker))
                print("현재가격 : " + str(balance))
                print("*"*20 + "\n")

                #매도시 슬랙 알림
                post_message(myToken,"#cryptoautotrade", "*"*20)
                post_message(myToken,"#cryptoautotrade", str(ticker) + " 매도 : " + str(balance * current_price) + "원")
                post_message(myToken,"#cryptoautotrade", str(ticker) + " 실현손익 : " + str(int(balance * current_price * 0.9995 - 8000)) + "원")
                gain += int(balance * current_price * 0.9995 - 8000)
                post_message(myToken,"#cryptoautotrade", "자동매매 총실현손익 : " + str(gain) + "원")

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

        # 10초마다 반복
        time.sleep(10)  

    except Exception as e:
        print(e)
        #슬랙으로 에러 메시지 전송
        if(e!=0):
            post_message(myToken,"#cryptoautotrade", e)
        time.sleep(1)