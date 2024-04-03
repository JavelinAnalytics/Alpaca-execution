# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 03:56:31 2024

@author: yarno
"""

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest, MarketOrderRequest, TakeProfitRequest, StopLossRequest, LimitOrderRequest
from alpaca.trading.enums import AssetClass, OrderSide, TimeInForce, OrderClass, OrderType, OrderStatus
from alpaca.data.historical import CryptoHistoricalDataClient, StockHistoricalDataClient
from alpaca.data.requests import CryptoLatestQuoteRequest, StockLatestQuoteRequest
from alpaca.common.exceptions import APIError
import time
from config_alpaca import API_KEY, SECRET_KEY

trading_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)
crypto_data_client = CryptoHistoricalDataClient()
stock_data_client = StockHistoricalDataClient(api_key=API_KEY, secret_key=SECRET_KEY)

account = trading_client.get_account()
buying_power = account.buying_power
print(f'${account.buying_power} is available as buying power')

def list_of_us_equities():
    params = GetAssetsRequest(asset_class=AssetClass.US_EQUITY)
    assets = trading_client.get_all_assets(params)
    return assets

def list_of_crypto_pairs():
    params = GetAssetsRequest(asset_class=AssetClass.CRYPTO)
    assets = trading_client.get_all_assets(params)
    return assets

def return_latest_price(ticker, orderside):
    if ticker in list_of_us_equities():
        params = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        latest_quote = stock_data_client.get_stock_latest_quote(params)
    else:
        params = CryptoLatestQuoteRequest(symbol_or_symbols=ticker)
        latest_quote = crypto_data_client.get_crypto_latest_quote(params)
    
    if orderside == 'buy':
        return latest_quote[ticker].ask_price
    else:
        return latest_quote[ticker].bid_price   

orders = {}
    
def open_new_trade(ticker:str, ordertype:str, orderside:str, notional=None, qty=None, limitprice=None, takeprofit=None, stoploss=None):
    """
    Function for opening new trades, supported markets: US equities and crytpocurrencies
    Ticker for equities should be all caps (AAPL), for cryptos should represent the pair in all caps (BTC/USDT)
    Ordertype should denote market or limit, for market and limit orders respectively
    Orderside should denote buy or sell, for buying and selling (if open position) /shorting (if no open position), respectively
    Notional should denote the usd value of the trade, only use for stock market orders
    Qty should denote the amount of shares or tokens to trade, only use for stock limit orders (non-fractiona only) and crypto
    Takeprofit and stoploss denote market prices, are only supported for US Equities
    """
    #Logic for all exception handling prior to submitting order
    if notional is None and qty is None:
        print('Either notional or qty must be passed')
        return
    
    try:
        asset = trading_client.get_asset(ticker)
    except Exception as e:
        print(f'Asset {ticker} is not supported: {e}')
        return
    if not asset.tradable:
        print(f'Asset {ticker} is not tradable')
        return
    
    if orderside == 'buy':
        order_side = OrderSide.BUY
    elif orderside == 'sell':
        order_side = OrderSide.SELL
    else:
        print(f'Invalid input {orderside}')
        return
    
    if ordertype == 'market':
        order_type = OrderType.MARKET
    elif ordertype == 'limit':
        order_type = OrderType.LIMIT
    else:
        print(f'Invalid input {orderside}')
        return
    
    if notional and qty:
        print('Both notional and qty cannot be passed')
        return
        
    if ticker in list_of_crypto_pairs():
        if qty:  
            traded_token = ticker.split('/')[0]
            usd_pair = f'{traded_token}/USD'                             
            dollar_amount = qty * float(return_latest_price(usd_pair, orderside))
            if dollar_amount > float(buying_power):
                print(f'Amount converted to dollars: {dollar_amount} exceeds available funds: {buying_power}')
                return
        else:
            print('For crypto trades qty must be provided not notional')
            return
    
    if ticker in list_of_us_equities() and ordertype == 'market':
        if notional:
            if notional > float(buying_power):
                print(f'Notional: {notional} exceeds available funds: {buying_power}')
                return
        else:
            print('For us equities market orders notional must be provided not qty')
            return
        
    if ticker in list_of_us_equities() and ordertype == 'limit':
        if qty and type(qty) == int:
            dollar_amount = qty * float(return_latest_price(ticker, orderside))
            if dollar_amount > float(buying_power):
                print(f'Amount converted to dollars: {dollar_amount} exceeds available funds:{buying_power}')
                return
        else:
            print('For us equities limit orders only integer, non-fractional qty must be provided not notional or fractional qty')
            return
    
    if ordertype == 'limit' and limitprice is None:
        print('Limit price must be included with limit order type')
        return
    
    #Logic for market orders
    if ordertype == 'market':
        if ticker in list_of_us_equities():
            #If trading stocks at market price with take profit and stop loss
            if takeprofit and stoploss:
                market_order_data = MarketOrderRequest(
                    symbol=ticker,
                    notional=notional,
                    side=order_side,
                    type=order_type,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=TakeProfitRequest(takeprofit),
                    stop_loss=StopLossRequest(stoploss)
                )
            elif (takeprofit is None and stoploss is not None) or (takeprofit is not None and stoploss is None):
                #If trading stocks at market price with take profit
                if takeprofit:
                    market_order_data = MarketOrderRequest(
                        symbol=ticker,
                        notional=notional,
                        side=order_side,
                        type=order_type,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.OTO,
                        take_profit=TakeProfitRequest(takeprofit)
                    )
                #If trading stocks at market price with stop loss
                else:
                    market_order_data = MarketOrderRequest(
                        symbol=ticker,
                        notional=notional,
                        side=order_side,
                        type=order_type,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.OTO,
                        stop_loss=StopLossRequest(stoploss)
                    )
            #If trading stocks at market price without take profit or stop loss
            else:
                market_order_data = MarketOrderRequest(
                    symbol=ticker,
                    notional=notional,
                    side=order_side,
                    type=order_type,
                    time_in_force=TimeInForce.DAY,
                )
        #If trading crypto at market price
        else:
            if takeprofit is None and stoploss is None:
                market_order_data = MarketOrderRequest(
                    symbol=ticker,
                    qty=qty,
                    side=order_side,
                    type=order_type,
                    time_in_force=TimeInForce.GTC
                )
            else:
                print('Crypto orders do not support take profit and stop loss')
                return
        
        market_order = trading_client.submit_order(order_data=market_order_data)
        orders[ticker] = market_order
        return market_order.id
    
    #Logic for limit orders
    else:
        if ticker in list_of_us_equities():
            #If trading stocks with limit orders plus take profit and stop loss
            if takeprofit and stoploss:
                limit_order_data = LimitOrderRequest(
                    symbol=ticker,
                    limit_price=limitprice,
                    qty=qty,
                    side=order_side,
                    type=order_type,
                    time_in_force=TimeInForce.DAY,
                    order_class=OrderClass.BRACKET,
                    take_profit=TakeProfitRequest(takeprofit),
                    stop_loss=StopLossRequest(stoploss)
                )
            elif (takeprofit is None and stoploss is not None) or (takeprofit is not None and stoploss is None):
                #If trading stocks with limit orders plus take proft
                if takeprofit:
                    limit_order_data = LimitOrderRequest(
                        symbol=ticker,
                        limit_price=limitprice,
                        qty=qty,
                        side=order_side,
                        type=order_type,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.OTO,
                        take_profit=TakeProfitRequest(takeprofit)
                    )
               #If trading stocks with limit orders plus stop loss
                else:
                    limit_order_data = LimitOrderRequest(
                        symbol=ticker,
                        limit_price=limitprice,
                        qty=qty,
                        side=order_side,
                        type=order_type,
                        time_in_force=TimeInForce.DAY,
                        order_class=OrderClass.OTO,
                        stop_loss=StopLossRequest(stoploss)
                    )
            #If trading stocks with limit orders without take profit and stop loss
            else:
                limit_order_data = LimitOrderRequest(
                    symbol=ticker,
                    limit_price=limitprice,
                    qty=qty,
                    side=order_side,
                    type=order_type,
                    time_in_force=TimeInForce.DAY
                )
        #If trading crypto with limit orders
        else:
            if takeprofit is None and stoploss is None:
                limit_order_data = LimitOrderRequest(
                    symbol=ticker,
                    limit_price=limitprice,
                    qty=qty,
                    side=order_side,
                    type=order_type,
                    time_in_force=TimeInForce.GTC
                )
            else:
                print('Crypto orders do not support take profit and stop loss')
                return
        
        limit_order = trading_client.submit_order(order_data=limit_order_data)
        orders[ticker] = limit_order
        return limit_order.id

#Obtain fees: approach through positions    
def fee_simulator(order):
    #Check if order has filled status
    if order.status == OrderStatus.EXPIRED:
        print("Order expired without fill, fees calculated upon fill")
        return
    if order.status != OrderStatus.FILLED and order.status != OrderStatus.PARTIALLY_FILLED:
        print("Order not yet filled, fees calculated upon fill")
        return
    
    try:
        ticker = order.symbol
        side = order.side
        if '/' in ticker:
            ticker = ticker.replace('/', '')
        if ticker[-3:] == 'BTC' and side == OrderSide.BUY:
            ticker = ticker.replace('BTC', 'USD')
        if ticker[-4:] == 'USDT' and side == OrderSide.BUY:
            ticker = ticker.replace('USDT', 'USD')
        if ticker[-4:] == 'USDC' and side == OrderSide.BUY:
            ticker = ticker.replace('USDC', 'USD')
        position = trading_client.get_open_position(ticker)
    except APIError:
        print("Position not found")
        return
    
    cost_basis = float(position.cost_basis)
    avg_entry_price = float(position.avg_entry_price)
    qty = float(position.qty)
    trading_fees = cost_basis - (avg_entry_price * qty)
    return trading_fees

if __name__ == '__main__':
    
    #Replace params with your selections
    order_id = open_new_trade(ticker='ETH/BTC', ordertype='market', orderside='buy', qty=1) 
    
    time.sleep(10)
    
    order = trading_client.get_order_by_id(order_id)
    
    fee_simulator(order)
    
    
    
    
    
    
    


    
    
    
    
    
    
    
        
    
    
    
    


        
          
            
         
                
            
                
            
        
        
                        
                    
                    
                
                
            
            
        
    
        
