import time
import pyupbit
import requests

access = "yourKey"
secret = "yourKey"
myToken = "yourKey"


#슬랙 메세지 보내기
def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

# Upbit에 로그인
upbit = pyupbit.Upbit(access, secret)
print("Rsi Crypto AutoTrade start")

#실행을 슬랙으로 알림
post_message(myToken,"#cryptoautotrade", "*"*20)
post_message(myToken,"#cryptoautotrade", "RSI 자동 알림 실행")
post_message(myToken,"#cryptoautotrade", "*"*20)

#현재가 조회
def get_current_price(ticker):
    """현재가 조회"""
    try:
        return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]
    except Exception:
        df = pyupbit.get_ohlcv(ticker, interval="minute1", count=1)
        return df['close'].iloc[0]

# 볼린저 밴드 상단 도달 여부 확인 함수
def is_above_bollinger_band(df, ma=20, sigma=2):
    close_prices = df['close']
    ma = close_prices.rolling(window=20).mean()
    std = close_prices.rolling(window=20).std()
    upper_band = ma + (std * sigma)
    return close_prices.iloc[-1] >= upper_band.iloc[-1]
  
# 볼린저 밴드 하단 도달 여부 확인 함수
def is_below_bollinger_band(df, ma=20, sigma=2):
    close_prices = df['close']
    ma = close_prices.rolling(window=20).mean()
    std = close_prices.rolling(window=20).std()
    lower_band = ma - (std * sigma)
    return close_prices.iloc[-1] <= lower_band.iloc[-1]

# 이동 평균선 기간 설정
long_window = 20
    
while True:
    try:
       # 모든 코인정보 가져오기
        all_tickers = pyupbit.get_tickers(fiat="KRW")

       # 티커 심볼 별로 현재의 30분간 거래량을 가져오기
        volume_info = {}
        for ticker in all_tickers:
            ohlcv_data = pyupbit.get_ohlcv(ticker, interval="minute30", count=1)
            if ohlcv_data is not None and not ohlcv_data.empty:
                # 현재 가격 * 거래량을 평균 거래대금으로 계산
                volume_info[ticker] = pyupbit.get_current_price(ticker) * ohlcv_data['volume'].iloc[0]

        # 모든 코인의 거래대금 총합 계산
        total_volume = sum(volume_info.values())

        # 전체 코인의 수
        num_coins = len(all_tickers)

        # 평균 거래대금 계산
        average_volume = total_volume / num_coins

        # 평균 이상의 코인 심볼 리스트 만들기
        high_volume_tickers = [ticker for ticker, volume in volume_info.items() if volume > average_volume]
        print("평균 이상 거래대금을 가진 코인 리스트:", high_volume_tickers)

        for ticker in high_volume_tickers:
            print(ticker)
            print("종목명 : " + str(ticker))

            # 15분간격 정보 가져오기
            df = pyupbit.get_ohlcv(ticker, interval="minute15", count=long_window)

            #현재가 조회
            current_price = get_current_price(ticker) 

            #내 계좌 코인 정보
            balance = upbit.get_balance(ticker.replace("KRW-", ""))

            # 이동 평균 계산
            df['MA_long'] = df['close'].rolling(window=long_window).mean()

            # 현재 이동 평균 계산
            current_MA_long = (df['MA_long'][-1] * (long_window-1) + current_price) / (long_window)

            # 볼린저 밴드 하단 도달 여부 확인
            if is_below_bollinger_band(df):
                post_message(myToken, "#cryptoautotrade", f"볼린저 밴드 하단 도달: {ticker}")
                print("볼린저 밴드 하단 도달")


            #내 계좌 코인 보유 여부 확인
            if balance * current_price >= 5000:
                #이평선(20)보다 가격이 높아졌을 경우
                if current_price > current_MA_long:
                    post_message(myToken, "#cryptoautotrade", f"이평선 도달: {ticker}")
                    print("이평선 도달")

                # 볼린저 밴드 상단 도달 여부 확인
                if is_above_bollinger_band(df):
                    post_message(myToken, "#cryptoautotrade", f"볼린저 밴드 상단 도달: {ticker}")
                    print("볼린저 밴드 상단 도달")
            print()

    except Exception as e:
        print(e)
        #슬랙으로 에러 메시지 전송
        if(e!=0):
            post_message(myToken,"#cryptoautotrade", e)
        time.sleep(1)