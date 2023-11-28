import time
import pyupbit
import requests

myToken = ""


#슬랙 메세지 보내기
def post_message(token, channel, text):
    response = requests.post("https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer "+token},
        data={"channel": channel,"text": text}
    )

#실행을 슬랙으로 알림
post_message(myToken,"#cryptoautotrade", "*"*20)
post_message(myToken,"#cryptoautotrade", "RSI 자동 알림 실행")
post_message(myToken,"#cryptoautotrade", "*"*20)

# 볼린저 밴드 상단 도달 여부 확인 함수
def is_above_bollinger_band(ticker, interval='minute15', ma=20, sigma=2):
    df = pyupbit.get_ohlcv(ticker, interval=interval, count=ma)
    close_prices = df['close']
    ma = close_prices.rolling(window=20).mean()
    std = close_prices.rolling(window=20).std()
    upper_band = ma + (std * sigma)
    print("상단 가격: " + str(upper_band.iloc[-1]))
    return close_prices.iloc[-1] >= upper_band.iloc[-1]
  
# 볼린저 밴드 하단 도달 여부 확인 함수
def is_below_bollinger_band(ticker, interval='minute15', ma=20, sigma=2):
    df = pyupbit.get_ohlcv(ticker, interval = interval, count = ma)
    close_prices = df['close']
    ma = close_prices.rolling(window=20).mean()
    std = close_prices.rolling(window=20).std()
    lower_band = ma - (std * sigma)
    print("하단 가격: " + str(lower_band.iloc[-1]))
    return close_prices.iloc[-1] <= lower_band.iloc[-1]
    
while True:
    try:
        # 모든 코인정보 가져오기
        tickers = pyupbit.get_tickers(fiat="KRW")

        for ticker in tickers:
            print("종목명 : " + str(ticker))

            # 볼린저 밴드 상단 도달 여부 확인
            if is_above_bollinger_band(ticker):
                post_message(myToken, "#cryptoautotrade", f"볼린저 밴드 상단 도달: {ticker}")
                print("볼린저 밴드 상단 도달")

            # 볼린저 밴드 하단 도달 여부 확인
            if is_below_bollinger_band(ticker):
                post_message(myToken, "#cryptoautotrade", f"볼린저 밴드 하단 도달: {ticker}")
                print("볼린저 밴드 하단 도달")
            print()

        # 10초마다 반복
        time.sleep(1)  

    except Exception as e:
        print(e)
        #슬랙으로 에러 메시지 전송
        if(e!=0):
            post_message(myToken,"#cryptoautotrade", e)
        time.sleep(1)