import time, printer, math
from binance.client import Client
from binance.enums import *
from binance.exceptions import *
from colorama import init, Fore, Style
init()

with open("api.txt") as f:
    api_key = f.readline().strip()
    api_secret = f.readline().strip()
client = Client(api_key, api_secret, testnet = False)

#money=1000
trade_amount = 20
base = "USDT"
alt = "GBP"
coin = "BTC"

minimum_profit = 1.004

#balance = open("balance.txt", "w")

p = printer.Printer()

def get_balance(asset):
    return float(client.get_asset_balance(asset=asset)["free"])
    
def in_open_order(symbol):
    open_orders = client.get_open_orders()
    print(open_orders)
    return True if len(open_orders) > 0 else False
    
def is_order_filled(symbol, order_id):
    try:
        if client.get_order(symbol=symbol, orderId=order_id)["status"] == "FILLED":
            print("filled")
            return True
        return False
    except BinanceAPIException: # maybe trade has already closed?
        # my_trades = client.get_my_trades(symbol=symbol, limit=1)
        # if my_trades[0]["orderId"] == order_id:
            # # Order has been at least partially filled
            # if get_balance
        # return # Some error occured?
        return is_order_filled(symbol, order_id)
    
def limit_buy(symbol, amount, price):
    return client.create_order(
        symbol=symbol,
        side=SIDE_BUY,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=amount,
        price=str(price))
        
def limit_sell(symbol, amount, price):
    return client.create_order(
        symbol=symbol,
        side=SIDE_SELL,
        type=ORDER_TYPE_LIMIT,
        timeInForce=TIME_IN_FORCE_GTC,
        quantity=amount,
        price=str(price))
        
def return_to_base():
    time.sleep(5) # Let API and client catch up
    try:
        coin_balance = get_balance(coin)
        o = client.create_order(
            symbol=coin+base,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=int(coin_balance*10**6)/10**6)
        print(o)
    except:
        pass
        
    try:
        alt_balance = get_balance(alt)
        o = client.create_order(
            symbol=alt+base,
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=int(coin_balance*10**2)/10**2)
        print(o)
    except:
        pass

def buy_with_base(coin_base_buy_price, coin_alt_sell_price, alt_base_sell_price):

    global base_balance
    if base_balance > trade_amount:
        
        start_time = time.time()
        
        old_balance = base_balance
        print()
        print(f"Buying {int(10**6*trade_amount/coin_base_buy_price)/10**6 * coin_base_buy_price}{base} worth of {coin} at {coin_base_buy_price}")
        trade1 = limit_buy(coin + base, int(10**6*trade_amount/coin_base_buy_price)/10**6, coin_base_buy_price)
        print(trade1)
        if trade1["status"] != "FILLED":
            print("Waiting for order to fill...")
            while in_open_order(coin + base):
                #print("Waiting...")
                current_time = time.time()
                if current_time - start_time > 1:
                    try:
                        client.cancel_order(symbol=trade1["symbol"], orderId=trade1["orderId"])
                        print("Order took too long, canceled!")
                    except: # Maybe the order was filled whilst trying to cancel?
                        break
                    return_to_base()
                    return
        print("Order filled\n")
        
        coin_balance = get_balance(coin)
        print(f"{coin} balance: {coin_balance}")
        print(f"Selling {int(coin_balance*10**6)/10**6} of {coin} to {alt} at {coin_alt_sell_price}")
        trade2 = limit_sell(coin + alt, int(coin_balance*10**6)/10**6, coin_alt_sell_price)
        print(trade2)
        if trade2["status"] != "FILLED":
            print("Waiting for order to fill...")
            while in_open_order(coin + alt):
                #print("Waiting...")
                time.sleep(0.3)
                current_time = time.time()
                if current_time - start_time > 30:
                    try:
                        client.cancel_order(symbol=trade2["symbol"], orderId=trade2["orderId"])
                        print("Order took too long, canceled!")
                    except:
                        break
                    return_to_base()
                    return
        print("Order filled\n")
        
        alt_balance = get_balance(alt)
        print(f"{alt} balance: {alt_balance}")
        print(f"Selling {int(alt_balance*10**2)/10**2} of {alt} to {base} at {alt_base_price}")
        trade3 = limit_sell(alt + base, int(alt_balance*10**2)/10**2, alt_base_sell_price)
        print(trade3)
        if trade3["status"] != "FILLED":
            print("Waiting for order to fill...")
            while in_open_order(alt + base):
                #print("Waiting...")
                time.sleep(0.9)
                current_time = time.time()
                if current_time - start_time > 90:
                    print("Order took too long, canceled!")
                    client.cancel_order(symbol=trade3["symbol"], orderId=trade3["orderId"])
                    return_to_base()
                    return
        print("Order filled\n")
        
        base_balance = get_balance(base)
        print(f"Profit: {base_balance-old_balance}")
        time.sleep(10)
    else:
        print("Insufficient funds!")
        time.sleep(1)
        
def buy_with_alt(alt_base_buy_price, coin_alt_buy_price, coin_base_sell_price):

    global base_balance
    if base_balance > trade_amount:
        
        start_time = time.time()
        
        old_balance = base_balance
        print()
        print(f"Buying {int(10**2*trade_amount/alt_base_buy_price)/10**2 * alt_base_buy_price}{base} worth of {alt} at {alt_base_buy_price}")
        trade1 = limit_buy(alt + base, int(10**2*trade_amount/alt_base_buy_price)/10**2, alt_base_buy_price)
        print(trade1)
        if trade1["status"] != "FILLED":
            print("Waiting for order to fill...")
            while in_open_order(alt + base):
                #print("Waiting...")
                current_time = time.time()
                if current_time - start_time > 1:
                    try:
                        client.cancel_order(symbol=trade1["symbol"], orderId=trade1["orderId"])
                        print("Order took too long, canceled!")
                    except: # Maybe the order was filled whilst trying to cancel?
                        break
                    return_to_base()
                    return
        print("Order filled\n")
        
        alt_balance = get_balance(alt)
        print(f"{alt} balance: {alt_balance}")
        print(f"Buying {int(10**6*alt_balance/coin_alt_buy_price)/10**6 * coin_alt_buy_price}{alt} worth of {coin} at {coin_alt_buy_price}")
        trade2 = limit_buy(coin + alt, int(10**6*alt_balance/coin_alt_buy_price)/10**6, coin_alt_buy_price)
        print(trade2)
        if trade2["status"] != "FILLED":
            print("Waiting for order to fill...")
            while in_open_order(coin + alt):
                #print("Waiting...")
                time.sleep(0.3)
                current_time = time.time()
                if current_time - start_time > 30:
                    try:
                        client.cancel_order(symbol=trade2["symbol"], orderId=trade2["orderId"])
                        print("Order took too long, canceled!")
                    except:
                        break
                    return_to_base()
                    return
        print("Order filled\n")
        
        coin_balance = get_balance(coin)
        print(f"{coin} balance: {coin_balance}")
        print(f"Selling {int(coin_balance*10**6)/10**6} of {coin} to {base} at {coin_base_sell_price}")
        trade3 = limit_sell(coin + base, int(coin_balance*10**6)/10**6, coin_base_sell_price)
        print(trade3)
        if trade3["status"] != "FILLED":
            print("Waiting for order to fill...")
            while in_open_order(coin + base):
                #print("Waiting...")
                time.sleep(0.9)
                current_time = time.time()
                if current_time - start_time > 90:
                    print("Order took too long, canceled!")
                    client.cancel_order(symbol=trade3["symbol"], orderId=trade3["orderId"])
                    return_to_base()
                    return
        print("Order filled\n")
        
        base_balance = get_balance(base)
        print(f"Profit: {base_balance-old_balance}")
        time.sleep(10)
    else:
        print("Insufficient funds!")
        time.sleep(1)

try:
    while True:   
                
        coin_base_ticker = client.get_symbol_ticker(symbol = coin + base)
        coin_alt_ticker = client.get_symbol_ticker(symbol = coin + alt)
        alt_base_ticker = client.get_symbol_ticker(symbol = alt + base)
        
        coin_base_price = coin_base_ticker['price']
        coin_alt_price = coin_alt_ticker['price']
        alt_base_price = alt_base_ticker['price']
        
        # coin_base_order_book = client.get_order_book(symbol= coin + base)
        # coin_alt_order_book = client.get_order_book(symbol = coin + alt)
        # alt_base_order_book = client.get_order_book(symbol = alt + base)
        
        # # Highest buyers are willing to buy
        # coin_base_highest_bid = float(coin_base_order_book['bids'][0][0])
        # coin_alt_highest_bid = float(coin_alt_order_book['bids'][0][0])
        # alt_base_highest_bid = float(alt_base_order_book['bids'][0][0])
        # # Lowest sellers are willing to sell
        # coin_base_lowest_ask = float(coin_base_order_book['asks'][0][0])
        # coin_alt_lowest_ask = float(coin_alt_order_book['asks'][0][0])
        # alt_base_lowest_ask = float(alt_base_order_book['asks'][0][0])
        
        # Last price
        coin_base_highest_bid = float(coin_base_price)
        coin_alt_highest_bid = float(coin_alt_price)
        alt_base_highest_bid = float(alt_base_price)
        # Last price
        coin_base_lowest_ask = float(coin_base_price)
        coin_alt_lowest_ask = float(coin_alt_price)
        alt_base_lowest_ask = float(alt_base_price)

        p.clear_text()
        
        base_balance = get_balance(base)
        p.print(f"Balance: {base_balance}\n")
        
        p.print(f"{base} => {coin} => {alt} => {base}:")
        # if we can buy coin with base cheaper than alt => buy with base, sell with alt
        if coin_alt_highest_bid * alt_base_highest_bid / coin_base_lowest_ask > minimum_profit:
            #BusdTogbp()
            
            #if not in_open_order():
            
            #break
            p.print(end=Fore.GREEN)
        elif coin_alt_highest_bid * alt_base_highest_bid / coin_base_lowest_ask < 1:
            p.print(end=Fore.RED)
        p.print(coin_alt_highest_bid * alt_base_highest_bid / coin_base_lowest_ask)
        p.print(end=Style.RESET_ALL)
        
        p.print()
        
        p.print(f"{base} => {alt} => {coin} => {base}:")
        # if we can buy coin with alt cheaper than base => buy with alt, sell with base
        if coin_base_highest_bid / (alt_base_lowest_ask * coin_alt_lowest_ask) > minimum_profit:
            #gbpToBusd()
            p.print(end=Fore.GREEN)
        elif coin_base_highest_bid / (alt_base_lowest_ask * coin_alt_lowest_ask) < 1:
            p.print(end=Fore.RED)
        p.print(coin_base_highest_bid / (alt_base_lowest_ask * coin_alt_lowest_ask))
        p.print(end=Style.RESET_ALL)
        
        p.draw()
        
        if coin_alt_highest_bid * alt_base_highest_bid / coin_base_lowest_ask > minimum_profit:
            buy_with_base(coin_base_lowest_ask, coin_alt_highest_bid, alt_base_highest_bid)
        
        elif coin_base_highest_bid / (alt_base_lowest_ask * coin_alt_lowest_ask) > minimum_profit:
            buy_with_alt(alt_base_lowest_ask, coin_alt_lowest_ask, coin_base_highest_bid)
            
except KeyboardInterrupt:
    #balance.close()
    pass