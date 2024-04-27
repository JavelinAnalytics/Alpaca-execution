# -*- coding: utf-8 -*-
"""
Created on Fri Mar 29 18:26:47 2024

@author: yarno
"""

import requests
import time
from config_alpaca import API_KEY, SECRET_KEY
from datetime import datetime, timedelta

trading_url = "https://api.alpaca.markets"
market_url = "https://data.alpaca.markets"
headers_get_request = {
    "accept": "application/json",
    "APCA-API-KEY-ID": f"{API_KEY}",
    "APCA-API-SECRET-KEY": f"{SECRET_KEY}"
}
headers_post_request = {
    "accept": "application/json",
    "content-type": "application/json",
    "APCA-API-KEY-ID": f"{API_KEY}",
    "APCA-API-SECRET-KEY": f"{SECRET_KEY}"
}

def safe_get_request(url, headers, params=None):
    max_retries = 5
    time_delay = 5
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to get data: {e}, retrying {attempt + 1}/{max_retries}")
            time.sleep(time_delay)
    raise Exception("Failed to return results")

def safe_post_request(url, headers, json=None):
    max_retries = 5
    time_delay = 5
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=json, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Failed to get data: {e}, retrying {attempt + 1}/{max_retries}")
            time.sleep(time_delay)
    raise Exception("Failed to return results")

account = safe_get_request(f"{trading_url}/v2/account", headers=headers_get_request)
buying_power = account.get('buying_power')
print(f"${buying_power} is available as buying power")

def list_of_us_equities():
    response = safe_get_request(f"{trading_url}/v2/assets", headers=headers_get_request, params={"status": "active", "asset_class": "us_equity"})
    return[asset['symbol'] for asset in response if asset['tradable'] == True]

def list_of_crypto_pairs():
    response = safe_get_request(f"{trading_url}/v2/assets", headers=headers_get_request, params={"status": "active", "asset_class": "crypto"})
    return[asset['symbol'] for asset in response if asset['tradable'] == True]

list_of_us_equities = list_of_us_equities()
list_of_crypto_pairs = list_of_crypto_pairs()

def return_latest_price(ticker:str, orderside:str):
    if ticker in list_of_us_equities:
        response = safe_get_request(f"{market_url}/v2/stocks/{ticker}/quotes/latest", headers=headers_get_request)
        latest_quotes = response['quote']
    if ticker in list_of_crypto_pairs:
        response = safe_get_request(f"{market_url}/v1beta3/crypto/us/latest/quotes", headers=headers_get_request, params={"symbols": ticker})
        latest_quotes = response['quotes'][ticker]
    if orderside == 'buy':
        return latest_quotes['ap']
    else:
        return latest_quotes['bp']

orders = {}
prices = {}

def open_new_trade(ticker:str, ordertype:str, orderside:str, notional=None, qty=None, limitprice=None, takeprofit=None, stoploss=None):
    """
    Function for opening new trades, supported markets: US equities and crytpocurrencies
    Ticker for equities should be all caps (AAPL), for cryptos should represent the pair in all caps (BTC/USDT)
    Ordertype should denote market or limit, for market and limit orders respectively
    Orderside should denote buy or sell, for buying and selling (if open position) /shorting (if no open position), respectively
    Shorting is only possible for US equities with non-fractionable qty
    Notional should denote the usd value of the trade
    Qty should denote the amount of shares or tokens to trade
    Takeprofit and stoploss denote market prices, are only supported for US Equities
    For stock limit orders, fractional orders will default to 'day' orders, and non-fractional orders will default to 'good until close' orders
    """
    #Logic for all exception handling prior to submitting order
    if notional is None and qty is None:
        print("Either notional or quantity must be passed")
        return
    
    if ticker not in list_of_us_equities and ticker not in list_of_crypto_pairs:
        print(f"Asset {ticker} is not supported for trading")
        return
    
    if orderside not in ['buy', 'sell']:
        print(f"Invalid input {orderside}")
        return
    
    if ordertype not in ['market', 'limit']:
        print(f"Invalid input {ordertype}")
        return
    
    if notional and qty:
        print("Both notional and qty cannot be passed")
        return
    
    if notional:
        if notional > float(buying_power):
            print(f"Notional {notional}, exceeds available funds {buying_power}")
            return
    
    if qty:
        if ticker in list_of_crypto_pairs:
            traded_token = ticker.split('/')[0]
            usd_pair = f"{traded_token}/USD"
            dollar_amount = qty * float(return_latest_price(usd_pair, orderside))
            if dollar_amount > float(buying_power):
                print(f"Amount converted to dollars {dollar_amount}, exceeds available funds {buying_power}")
                return
        else:
            dollar_amount = qty * float(return_latest_price(ticker, orderside))
            if dollar_amount > float(buying_power):
                print(f"Amount converted to dollars {dollar_amount}, exceeds available funds {buying_power}")
                return
    
    if ordertype == 'limit' and limitprice is None:
        print("Limit price must be included with limit order type")
        return
    
    if ticker in list_of_us_equities:
        if takeprofit or stoploss:
            if qty and isinstance(qty, float):
                print("For non-simple orders with take profit/stop loss, qty must be non-fractional")
                return
            if notional:
                print("For non-simple orders with take profit/stop loss, non-fractional qty must be provided not notional")
                return
    
    if ticker in list_of_us_equities:
        #Fractional orders for us equities default to 'day' orders
        if notional or isinstance(qty, float):
            time_in_force = "day"
        #Non-fractional orders for us equities default to 'good until close' orders
        else:
            time_in_force = "gtc"
    
    #Logic for market orders
    if ordertype == 'market':
        if ticker in list_of_us_equities:
            #If trading stocks at market price with take profit and stop loss
            if takeprofit and stoploss:
                response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request, 
                                             json={
                                                 "symbol": ticker,
                                                 "qty": qty,
                                                 "side": orderside, 
                                                 "type": ordertype,
                                                 "time_in_force": time_in_force,
                                                 "order_class": "bracket",
                                                 "take_profit": {"limit_price": takeprofit},
                                                 "stop_loss": {"stop_price": stoploss}
                                             }
                )
            elif (takeprofit is None and stoploss is not None) or (takeprofit is not None and stoploss is None):
                #If trading stocks at market price with take profit
                if takeprofit:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "oto",
                                                     "take_profit": {"limit_price": takeprofit}
                                                 }
                    )
                #If trading stocks at market price with stop loss
                else:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "oto",
                                                     "stop_loss": {"stop_price": stoploss}
                                                 }
                    )
            #If trading stocks at market price without take profit or stop loss
            else:
                if notional:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "notional": notional,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "simple"
                                                 }
                    )
                else:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "simple"
                                                 }
                    )
        #If trading crypto at market price
        else:
            if takeprofit is None and stoploss is None:
                if notional:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "notional": notional,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "time_in_force": "gtc",
                                                     "order_class": "simple"
                                                 }
                    )
                else:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "time_in_force": "gtc",
                                                     "order_class": "simple"
                                                 }
                    )
            else:
                print("Crypto orders do not support take profit and stop loss")
                return
        
        orders[ticker] = response
        submission_time = response['submitted_at']
        if '/BTC' in ticker:
            prices[submission_time] = {
                                     "bid/ask at fill": float(return_latest_price(ticker, orderside)), #store live bid/ask price for slippage calculations
                                     "bid/ask at submission": float(return_latest_price(ticker, orderside)), #store live bid/ask price for trading fee computation
                                     "BTC/USD at submission": float(return_latest_price('BTC/USD', orderside)) #store live btc/usd price for trading fee computation 
            } 
        else:
            prices[submission_time] = {
                                     "bid/ask at fill": float(return_latest_price(ticker, orderside)), 
                                     "bid/ask at submission": float(return_latest_price(ticker, orderside))
            } 
        return response['id']
    
    
    #Logic for limit orders
    else:
        if ticker in list_of_us_equities:
            #If trading stocks with limit orders plus take profit and stop loss
            if takeprofit and stoploss:
                response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                             json={
                                                 "symbol": ticker,
                                                 "qty": qty,
                                                 "side": orderside,
                                                 "type": ordertype,
                                                 "limit_price": limitprice,
                                                 "time_in_force": time_in_force,
                                                 "order_class": "bracket",
                                                 "take_profit": {"limit_price": takeprofit},
                                                 "stop_loss": {"stop_price": stoploss}
                                             }
                )
            elif (takeprofit is None and stoploss is not None) or (takeprofit is not None and stoploss is None):
                #If trading stocks with limit orders plus take profit
                if takeprofit:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "limit_price": limitprice,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "oto",
                                                     "take_profit": {"limit_price": takeprofit}
                                                 }
                    )
                #If trading stocks with limit orders and stop loss
                else:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "limit_price": limitprice,
                                                     "time-in_force": time_in_force,
                                                     "order_class": "oto",
                                                     "stop_loss": {"stop_price": stoploss}
                                                 }
                    )
            #If trading stocks with limit orders without take profit and stop loss
            else:
                if notional:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "notional": notional,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "limit_price": limitprice,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "simple"
                                                 }
                    )
                else:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "limit_price": limitprice,
                                                     "time_in_force": time_in_force,
                                                     "order_class": "simple"
                                                 }
                    )
        #If trading crypto with limit orders
        else:
            if takeprofit is None and stoploss is None:
                if notional:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "notional": notional,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "limit_price": limitprice,
                                                     "time_in_force": "gtc",
                                                     "order_class": "simple"
                                                 }
                    )
                else:
                    response = safe_post_request(f"{trading_url}/v2/orders", headers=headers_post_request,
                                                 json={
                                                     "symbol": ticker,
                                                     "qty": qty,
                                                     "side": orderside,
                                                     "type": ordertype,
                                                     "limit_price": limitprice,
                                                     "time_in_force": "gtc",
                                                     "order_class": "simple"
                                                 }
                    )
            else:
                print("Crypto orders do not support take profit and stop loss")
                return
        
        orders[ticker] = response
        submission_time = response['submitted_at']
        if '/BTC' in ticker:
            prices[submission_time] = {
                                     "bid/ask at fill": limitprice, # store limit price for slippage calculations
                                     "bid/ask at submission": float(return_latest_price(ticker, orderside)), # store live bid/ask price for trading fee computations
                                     "BTC/USD at submission": float(return_latest_price('BTC/USD', orderside)) # store live BTC/USD price for trading fee computations
            } 
        else:
            prices[submission_time] = {
                                     "bid/ask at fill": limitprice, 
                                     "bid/ask at submission": float(return_latest_price(ticker, orderside))
            } 
        return response['id']
    

def fee_simulator(order_id): 
    
    #Check if order has filled status
    latest_order = safe_get_request(f"{trading_url}/v2/orders/{order_id}", headers=headers_get_request)
    if latest_order['status'] != "filled":
        print("Order not yet filled, fees calculated upon fill")
        return
    
    avg_fill_price = float(latest_order['filled_avg_price'])
    filled_qty = float(latest_order['filled_qty'])
    order_type = latest_order['order_type']
    amount_at_submission = float(latest_order['qty']) if latest_order['qty'] else float(latest_order['notional']) 
    time_at_submission = latest_order['submitted_at']
    market_price_at_fill = prices[time_at_submission]['bid/ask at fill']
    
    #calculate slippage cost of order
    slippage_cost = abs(market_price_at_fill - avg_fill_price) * filled_qty
    if '/BTC' in latest_order['symbol']:
        base_token = latest_order['symbol'].split('/')[1]
        usd_pair = f"{base_token}/USD"
        orderside = latest_order['side'] 
        slippage_cost = slippage_cost * float(return_latest_price(usd_pair, orderside)) #convert slippage cost from BTC amount to USD amount if necessary
    
    #calculate trading tier fee cost for crypto, stock trading has no trading fees
    if latest_order['symbol'] in list_of_crypto_pairs:
        one_month_ago = datetime.now() - timedelta(days=30)
        one_month_ago = one_month_ago.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z"
        all_orders_last_month = safe_get_request(f"{trading_url}/v2/orders", headers=headers_get_request, 
                                                 params={
                                                     "status": "all",
                                                     "after": one_month_ago,
                                                     "direction": "desc"
                                                }
        )
    
        monthly_trading_volume = 0
        for order in all_orders_last_month:
            if order['symbol'] in list_of_crypto_pairs:
                if '/BTC' in order['symbol']:
                    traded_token = order['symbol'].split('/')[0]
                    base_token = order['symbol'].split('/')[1]
                    main_usd_pair = f"{traded_token}/USD"
                    base_usd_pair = f"{base_token}/USD"
                    orderside = order['side']
                    order_volume = float(order['qty']) if order['qty'] else float(order['notional'])
                    if order['qty']:
                        order_volume = order_volume * float(return_latest_price(main_usd_pair, orderside))
                    if order['notional']:
                        order_volume = order_volume * float(return_latest_price(base_usd_pair, orderside)) #store live BTC/USD price instead of calling it everytime
                    monthly_trading_volume += order_volume
                else:
                    order_volume = float(order['qty']) if order['qty'] else float(order['notional'])
                    if order['qty']:
                        traded_pair = order['symbol']
                        orderside = order['side']
                        order_volume = order_volume * float(return_latest_price(traded_pair, orderside))
                        monthly_trading_volume += order_volume
                    else:
                        monthly_trading_volume += order_volume
    
        if order_type == 'market': # assign taker trading tier fees based on monthly trading volumes
            if 0 <= monthly_trading_volume <= 100000:
                trading_tier_fee = 0.0025
            elif 100000 <= monthly_trading_volume <= 500000:
                trading_tier_fee = 0.0022
            elif 500000 <= monthly_trading_volume <= 1000000:
                trading_tier_fee = 0.002
            elif 1000000 <= monthly_trading_volume <= 10000000:
                trading_tier_fee = 0.0018
            elif 10000000 <= monthly_trading_volume <= 25000000:
                trading_tier_fee: 0.0015
            elif 25000000 <= monthly_trading_volume <= 50000000:
                trading_tier_fee = 0.0013
            elif 50000000 <= monthly_trading_volume <= 100000000:
                trading_tier_fee = 0.0012
            else:
                trading_tier_fee = 0.001
    
        if order_type == 'limit': # assign maker trading tier fees based on monthly trading volumes
            if 0 <= monthly_trading_volume <= 100000:
                trading_tier_fee = 0.0015
            elif 100000 <= monthly_trading_volume <= 500000:
                trading_tier_fee = 0.0012
            elif 500000 <= monthly_trading_volume <= 1000000:
                trading_tier_fee = 0.001
            elif 1000000 <= monthly_trading_volume <= 10000000:
                trading_tier_fee = 0.0008
            elif 10000000 <= monthly_trading_volume <= 25000000:
                trading_tier_fee: 0.0005
            elif 25000000 <= monthly_trading_volume <= 50000000:
                trading_tier_fee = 0.0002
            elif 50000000 <= monthly_trading_volume <= 100000000:
                trading_tier_fee = 0.0002
            else:
                trading_tier_fee = 0
    
        if '/BTC' in latest_order['symbol']:
            base_token = latest_order['symbol'].split('/')[1]
            base_usd_pair = f"{base_token}/USD"
            orderside = latest_order['side']
            if latest_order['qty']:
                trading_fees = (amount_at_submission * prices[time_at_submission]['bid/ask at submission'] * prices[time_at_submission]['BTC/USD at submission']) * trading_tier_fee
            if latest_order['notional']:
                trading_fees = (amount_at_submission * prices[time_at_submission]['BTC/USD at submission']) * trading_tier_fee 
        else:
            if latest_order['qty']:
                trading_fees = (amount_at_submission * prices[time_at_submission]['bid/ask at submission']) * trading_tier_fee
            else:
                trading_fees = amount_at_submission * trading_tier_fee
    
        total_cost = slippage_cost + trading_fees
        
    else: #stock trading has no trading fees
        total_cost = slippage_cost
    
    return total_cost
    
if __name__ == "__main__":
    
    #Replace params with your selections
    order_id = open_new_trade(ticker='ETH/BTC', ordertype='market', orderside='buy', qty=0.5)
    if order_id is not None:
        time.sleep(3)
        print("Trading fees:", fee_simulator(order_id))
        print("Order details:", list(orders.items())[-1][1])
    else:
        print("Order was not created")


    
        
    
    
    
    
    
        
        
    
    
        
    
        
        
            
        
            
        
        
                
                
                
        
            
            
    
    
    
        
    
 

    
        
