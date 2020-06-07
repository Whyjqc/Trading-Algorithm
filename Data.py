# -*- coding: utf-8 -*-
"""
Created on Mon Mar  2 03:52:26 2020

@author: why_j

Day Trades

    Thursday 12 Mar 2020

"""

# This import is specific to using the Alpaca broker
import alpaca_trade_api as tradeapi
import pickle
import schedule
import statistics
import time
from datetime import datetime
# Please note that I am set up to use a paper account.
# To use a live account change "paper" to "live".
from paper_config import APCA_API_KEY_ID,APCA_API_SECRET_KEY,APCA_API_BASE_URL

# Link with Alpaca
api = tradeapi.REST(APCA_API_KEY_ID, APCA_API_SECRET_KEY,APCA_API_BASE_URL, api_version='v2')
account=api.get_account()
clock = api.get_clock()

# At a point in the past I scraped a list of S&P 500
# tickers off of a website and put them in a pickle
# file. Here I load the pickle file.
call_list=pickle.load(open('sp500tickers.pickle','rb'))

# At the end of every ticker in the file a "\n" was 
# attatched. Here I remove it.
for i in range(505):
    call_list[i]=call_list[i].rstrip('\n')

# Alpaca can only take so many queries at once. Here
# I break the list down so that all 502 tickers are
# not used at once. The list is broken into six lists
# that I call universes. I call the list of universes
# a multiverse. This is what you get when a physics
# student starts programing.
length=len(call_list)
number_of_universes=length//100+1
def division(call_list,n):
    for i in range(0,len(call_list),n):
        yield call_list[i:i+n]
        
multiverse=list(division(call_list,100))

# These are important global variables. The stock list
# allows information to travel from one function to 
# another, or even from one day to another. It's used
# a bit like saving progress. The previous_day_trades
# helps me not run afoul of the PDT rule. That is the
# rule established for Americans that we can not make
# more than three day trades in a five day period.

stock=[]
previous_day_trades = 0


def bull_or_bear():
    # I used this to help me be aware of whether the market
    # was opening higher or lower than when it had closed.
    # I wanted to be aware of this as I tracked by
    # algorithm's performance.
    date=datetime.now()
    date=date.isoformat()
    data=api.get_barset('SPY','1Min',limit=2,until=date)
    if data['SPY'][1].c > data['SPY'][0].c:
        print('Bull!')
    else:
        print('Bear!')

def sma(data,ticker,start,stop):
    # I often used a smooth moving average in my
    # algorithms. This code is versatile enough to be
    # across all of them.
    total=0
    length=stop-start
    for i in range(start,stop):
        total=total+data[ticker][i].c
    avg=total/length
    return avg

def buy(date,data,ticker):
    # Things get a bit complicated here. I am drawinfg
    # from programing, stock trading and statistics,
    # all with their own jargon. I can't write a small
    # paper explaining each term to those who may
    # be familiar with perhaps two of these subjects
    # but not all three. Please bear with me and make
    # liberal use of context clues.
    
    # Here is where I decide whether or not to take a
    # position. I first verify that the price action is
    # trending upward. I then make sure that the
    # current price is less than 75 percent of a
    # standard deviation in the downward direction
    # because I am using a mean reversion strategy.
    # I am taking price information in one minute 
    # aggregation periods. I make sure the most recent 
    # closing price is higher than the openinfg price
    # to make sure that the most recent candle is 
    # green. I use then check standard deviation to 
    # determine if there is enough volotility in the 
    # stock to warent attention. Finally I ensure the
    # closing price of the last candle is above the 
    # smooth moving average over the last nine candles.
    # If it is that establishes an upward direction
    # and the algorithm determines how many shares
    # I can buy and takes a position.
    sample=[]
    for i in range(180):
        sample.append(data[ticker][i].c)
    mark1=statistics.stdev(sample)*0.75
    avg=sma(data,ticker,0,180)
    sma9=sma(data,ticker,171,180)
    mark2=avg-mark1
    if data[ticker][179].c > data[ticker][0].c and data[ticker][179].c < mark2 and data[ticker][179].c > data[ticker][179].o and mark1 > 0.25 and data[ticker][179].c > sma9:
        capital=float(account.buying_power)-10
        shares=capital//data[ticker][179].c
        api.submit_order(ticker, shares, 'buy', 'market','day')
        bought=[ticker,shares]
        stock.append(bought)
        return True
    else:
        return False
    
def sell(stock,ticks):
    # Here a position is monitored in one minute
    # intervals. The function records the highest price
    # attained in the position. Once that price dips
    # below 0.04% or the highest it had obtained, 
    # the shares are sold.
    
    print('Check!!!!')
    price=0
    day_trade=0
    while ticks<380:
        time.sleep(60)
        date=datetime.now()
        date=date.isoformat()
        data=api.get_barset(stock[0][0],'1Min',limit=1,until=date)
        ticks+=1
        if data[stock[0][0]][0].c > price:
            price = data[stock[0][0]][0].c
        elif data[stock[0][0]][0].c < price*0.996:
            api.submit_order(stock[0][0], stock[0][1], 'sell', 'market','day')
            stock.clear()
            day_trade=1
            time.sleep(300)
            ticks+=5
            break
    # Two types of information is passed on. First,
    # that a day trade has taken place and should be
    # counted so that I do not voilate the PDT rule.
    # Second is the amount of time taken in the
    # position. The importance of measuring this time
    # will be explained later.
    result=[day_trade,ticks]
    return result      
      

def initiate(): 
    # This is where the functions above are brought
    # together to try and make money. The variable,
    # ticks, is set at zero. It measures time in 
    # minutes so that the algorithm will shut itself
    # down at the end of the trading day.
    
    ticks=0
    daytrade=previous_day_trades
    print("Initiated")
    bull_or_bear()
    # While I have done less than 3 day trades in the
    # last five trading days, the market is open the 
    # code runs.
    while daytrade<3 and ticks < 380:
        print('Check!')
        ticks+=1
        time.sleep(60)
    # Here the code makes sure I have at least 500 
    # dollars in buying power. It sometimes takes a 
    # few minutes after selling a stock for that money
    # to become available again to buy more. Therefore
    # if at least 500 dollars isn't available, the
    # algorithm waits five minutes and then checks 
    # again.
        while float(account.buying_power) < 500:
            print('Waiting')
            time.sleep(300)
            ticks+=5
        date=datetime.now()
        date=date.isoformat()
        check=False
        if len(stock)==0:
            print('Check!!')
            for universe in multiverse:
                if check:
                    break
                try:
                    data=api.get_barset(universe,'1Min',limit=180,until=date)
                    for ticker in universe:
                        if buy(date,data,ticker):
                            check=True
                            break
                except:
                    print('ERROR IN buy: ',ticker)
        else:
            print('Check!!!')
            try:
                result=sell(stock,ticks)
                daytrade=daytrade+result[0]
                print('Day Trade Count: ',daytrade)
                ticks=ticks+result[1]
            except:
                print('ERROR IN sell: ',stock)
            
 
# This section allows the algorithm to start when
# the trading day starts. In the central time zone the
# market opens at 8:30
schedule.every().day.at('08:31').do(initiate)

while True:
    schedule.run_pending()
    time.sleep(60)
                   
