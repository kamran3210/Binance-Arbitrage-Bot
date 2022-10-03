import time, os, asyncio, printer
from binance import AsyncClient, BinanceSocketManager
from binance.enums import *
from binance.exceptions import BinanceAPIException, BinanceOrderException
from binance.client import Client
from colorama import Fore, Style

p = printer.Printer()

with open("api.txt") as f:
    api_key = f.readline().strip()
    api_secret = f.readline().strip()
#client = Client(api_key, api_secret)

clear = lambda: os.system('cls')

# coin_base, coin_alt and alt_coin must be valid symbols (TODO: check these are valid automatically)
base = "USDT"
alt = "GBP"
coin = "BTC"
coin_base = {"symbol":coin+base, "stream":f"{(coin+base).lower()}@bookTicker", "precision":6, "min":10}
coin_alt = {"symbol":coin+alt, "stream":f"{(coin+alt).lower()}@bookTicker", "precision":6, "min":10}
alt_base = {"symbol":alt+base, "stream":f"{(alt+base).lower()}@bookTicker", "precision":2, "min":10}
# TODO: get precision and min for each symbol pair automatically
base_bal = 0

minimum_profit = 1 # recommended minimum = 1.004

def floor(n, d): # floor n at d decimal places
    return int(n*10**d)/10**d

# Calculate percentage profit from executing the trade base => coin => alt => base
def calculate_buy_with_base():
    if not("bestBid" in coin_alt and "bestBid" in alt_base and "bestAsk" in coin_base): # if we haven't actually got price data
        return 0
    
    # buy base => coin
    coin_qty = min(
        base_bal / coin_base["bestAsk"] * 0.999,
        coin_base["askQty"],
        coin_alt["bidQty"],
        alt_base["bidQty"] / coin_alt["bestBid"] # How much alt we can sell as a coin value
        )
    # Floor to meet maximum precision
    coin_qty = floor(coin_qty, coin_base["precision"])
    if coin_qty == 0:
        return 0
    # Cost of buying this much coin = initial investment
    coin_total_price = coin_qty * coin_base["bestAsk"]
    
    
    # sell coin => alt
    #alt_bal = floor(coin_bal, coin_alt["precision"]) * coin_alt["bestBid"] * 0.999
    tradable_coin_qty = floor(coin_qty * 0.999, coin_alt["precision"])
    alt_qty = tradable_coin_qty * coin_alt["bestBid"]
    
    # sell alt => base
    #new_base_bal = floor(alt_bal, alt_base["precision"]) * alt_base["bestBid"] * 0.999
    tradable_alt_qty = floor(alt_qty * 0.999, alt_base["precision"])
    base_qty = tradable_alt_qty * alt_base["bestBid"] * 0.999
    
    return base_qty / coin_total_price

# Calculate percentage profit from executing the trade base => alt => coin => base
def calculate_buy_with_alt():
    if not("bestBid" in coin_base and "bestAsk" in alt_base and "bestAsk" in coin_alt):
        return 0
    # buy base => alt
    alt_qty = min(
        base_bal / alt_base["bestAsk"],
        alt_base["askQty"],
        coin_alt["askQty"] * coin_alt["bestAsk"],
        coin_base["bidQty"] * coin_alt["bestAsk"]
        )
    # Floor to meet maximum precision
    alt_qty = floor(alt_qty, alt_base["precision"])
    if alt_qty == 0:
        return 0
    # Cost of buying this much alt
    alt_total_price = alt_qty * alt_base["bestAsk"]
    
    # buy alt => coin
    tradable_alt_qty = alt_qty * 0.999
    coin_total_price = tradable_alt_qty
    coin_qty = floor(tradable_alt_qty / coin_alt["bestAsk"], coin_alt["precision"])
    
    # sell coin => base
    tradable_coin_qty = floor(coin_qty * 0.999, coin_base["precision"])
    base_qty = tradable_coin_qty * coin_base["bestBid"] * 0.999
    
    return base_qty / alt_total_price
    
# Print percentage profit info from both calculations and return the profits
def check_prices():
    # Theoretical return if we go from base => coin => alt => base
    p.print(f"{base} => {coin} => {alt} => {base}")
    buy_with_base = calculate_buy_with_base()
    if buy_with_base > minimum_profit:
        p.print(end=Fore.GREEN)
    elif buy_with_base < 1:
        p.print(end=Fore.RED)
    p.print(buy_with_base)
    p.print(end=Style.RESET_ALL)

    # Theoretical return if we go from base => alt => coin => base
    p.print(f"{base} => {alt} => {coin} => {base}")
    buy_with_alt = calculate_buy_with_alt()
    if buy_with_alt > minimum_profit:
        p.print(end=Fore.GREEN)
    elif buy_with_alt < 1:
        p.print(end=Fore.RED)
    p.print(buy_with_alt)
    p.print(end=Style.RESET_ALL)
    
    return buy_with_base, buy_with_alt

# Attempt to convert all available alt into base
async def alt_to_base_market(client):
    alt_bal = await get_balance(client, alt) # Update balance
    try:
        print(f"Selling {alt} to {base} with market order")
        trade = await client.create_order(
            symbol=alt_base["symbol"],
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=floor(alt_bal, alt_base["precision"])
            )
        await asyncio.sleep(5)
        return True
        # TODO: replace this with a way to wait for order to be filled rather than waiting an arbitrary amount of time
    except BinanceAPIException as e:
        print(e)
        return False
    except BinanceOrderException as e:
        print(e)
        return False
        
# Attempt to convert all available coin into base
async def coin_to_base_market(client):
    coin_bal = await get_balance(client, coin) # Update balance
    try:
        print(f"Selling {alt} to {base} with market order")
        trade = await client.create_order(
            symbol=coin_base["symbol"],
            side=SIDE_SELL,
            type=ORDER_TYPE_MARKET,
            quantity=floor(coin_bal, coin_base["precision"])
            )
        await asyncio.sleep(5)
        return True
        # TODO: replace this with a way to wait for order to be filled rather than waiting an arbitrary amount of time
    except BinanceAPIException as e:
        print(e)
        return False
    except BinanceOrderException as e:
        print(e)
        return False

# Execute the trade base => coin => alt => base
async def execute_buy_with_base(client):
    # Amount of coin to buy = min(
    #   coin we can afford,
    #   coin available to buy
    #   how much coin we can sell to alt
    #   how much alt (in terms of coin) we can sell to base
    #   )
    coin_qty = min(
        base_bal / coin_base["bestAsk"],
        coin_base["askQty"],
        coin_alt["bidQty"],
        alt_base["bidQty"] / coin_alt["bestBid"] # How much alt we can sell as a coin value
        )
    # Floor to meet maximum precision
    coin_qty = floor(coin_qty, coin_base["precision"])
    
    ############# Buy base => coin #############
    # Cost of buying this much coin
    coin_total_price = coin_qty * coin_base["bestAsk"]
    # If we do not have enough funds for the trade
    if base_bal < coin_total_price:
        print(f"Insufficient funds! (needed {coin_total_price}{base})")
        return False
    # If this trade is smaller than the minimum allowed trade
    if coin_total_price < coin_base["min"]:
        print(f"Trade too small! {coin_total_price}{base}")
        return False
    # Attempt to execute the first trade
    try:
        print(f"Attempting to buy {coin_qty}{coin} for a total of {coin_total_price}{base}")
        trade1 = await client.create_order(
            symbol=coin_base["symbol"],
            side=SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_FOK, # Fill or kill: trade must be filled instantly
            quantity=coin_qty,
            price=coin_base["bestAsk"]
            )
        #print(trade1)
    except BinanceAPIException as e:
        print(e)
        return False
    except BinanceOrderException as e:
        print(e)
        return False
    # If trade 1 successfully filled
    if "status" in trade1 and trade1["status"] == "FILLED":
        print(f"Bought {coin_qty}{coin} for a total of {trade1['cummulativeQuoteQty']}{base}")
    else:
        print(f"Trade 1 ({base} => {coin}) did not fill!")
        return False
    
    ############# Sell coin => alt #############
    # Calculate amount of alt after the next trade
    tradable_coin_qty = floor(coin_qty * 0.999, coin_alt["precision"])
    alt_qty = tradable_coin_qty * coin_alt["bestBid"]
    # We cannot check if our actual alt quantity is more than we predict without slowing down trades
    # Check if the trade is big enough (should be if the logic is correct)
    if alt_qty < coin_alt["min"]:
        print(f"Trade too small! {alt_qty}{alt}")
        await coin_to_base_market(client)
        return False
    # Attempt to execute the second trade
    try:
        print(f"Attempting to sell {tradable_coin_qty}{coin} for a total of {alt_qty}{alt}")
        trade2 = await client.create_order(
            symbol=coin_alt["symbol"],
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_FOK, # Fill or kill: trade must be filled instantly
            quantity=tradable_coin_qty,
            price=coin_alt["bestBid"]
            )
        #print(trade2)
    except BinanceAPIException as e:
        print(e)
        await coin_to_base_market(client)
        return False
    except BinanceOrderException as e:
        print(e)
        await coin_to_base_market(client)
        return False
    # If trade 2 successfully filled
    if "status" in trade2 and trade2["status"] == "FILLED":
        print(f"Sold {tradable_coin_qty}{coin} for a total of {trade2['cummulativeQuoteQty']}{alt}")
    else:
        print(f"Trade 2 ({coin} => {alt}) did not fill!")
        # Convert coin back to base after failed trade
        await coin_to_base_market(client)
        return False
    
    ############# Sell alt => base #############
    # Calculate amount of base after the next trade
    tradable_alt_qty = floor(alt_qty * 0.999, alt_base["precision"])
    base_qty = tradable_alt_qty * alt_base["bestBid"]
    # Check if the trade is big enough (should be if the logic is correct)
    if base_qty < alt_base["min"]:
        print(f"Trade too small! {base_qty}{base}")
        await alt_to_base_market(client)
        return False
    try:
        print(f"Attempting to sell {tradable_alt_qty}{alt} for a total of {base_qty}{base}")
        trade3 = await client.create_order(
            symbol=alt_base["symbol"],
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_FOK, # Fill or kill: trade must be filled instantly
            quantity=tradable_alt_qty,
            price=alt_base["bestBid"]
            )
        #print(trade3)
    except BinanceAPIException as e:
        print(e)
        await alt_to_base_market(client)
        return False
    except BinanceOrderException as e:
        print(e)
        await alt_to_base_market(client)
        return False
    # If trade 3 successfully filled
    if "status" in trade3 and trade3["status"] == "FILLED":
        print(f"Sold {tradable_alt_qty}{alt} for a total of {trade3['cummulativeQuoteQty']}{base}")
    else:
        print(f"Trade 3 ({alt} => {base}) did not fill!")
        # Convert alt back to base after failed trade
        await alt_to_base_market(client)
        return False
    
    #await asyncio.sleep(5)
    clear()
    return True
    
# Execute the trade base => alt => coin => base
async def execute_buy_with_alt(client):
    # Amount of alt to buy = min(
    #   alt we can afford,
    #   alt available to buy
    #   how much coin (in terms of alt) we can buy with alt
    #   how much coin (in terms of alt) we can sell to base
    #   )
    alt_qty = min(
        base_bal / alt_base["bestAsk"],
        alt_base["askQty"],
        coin_alt["askQty"] * coin_alt["bestAsk"],
        coin_base["bidQty"] * coin_alt["bestAsk"]
        )
    # Floor to meet maximum precision
    alt_qty = floor(alt_qty, alt_base["precision"])
    
    ############# Buy base => alt #############
    # Cost of buying this much alt
    alt_total_price = alt_qty * alt_base["bestAsk"]
    # If we do not have enough funds for the trade
    if base_bal < alt_total_price:
        print(f"Insufficient funds! (needed {alt_total_price}{base})")
        return False
    # If this trade is smaller than the minimum allowed trade
    if alt_total_price < alt_base["min"]:
        print(f"Trade too small! {alt_total_price}{base}")
        return False
    # Attempt to execute the first trade
    try:
        print(f"Attempting to buy {alt_qty}{alt} for a total of {alt_total_price}{base}")
        trade1 = await client.create_order(
            symbol=alt_base["symbol"],
            side=SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_FOK, # Fill or kill: trade must be filled instantly
            quantity=alt_qty,
            price=alt_base["bestAsk"]
            )
        #print(trade1)
    except BinanceAPIException as e:
        print(e)
        return False
    except BinanceOrderException as e:
        print(e)
        return False
    # If trade 1 successfully filled
    if "status" in trade1 and trade1["status"] == "FILLED":
        print(f"Bought {alt_qty}{alt} for a total of {trade1['cummulativeQuoteQty']}{base}")
    else:
        print(f"Trade 1 ({base} => {alt}) did not fill!")
        return False
        
    ############# Buy alt => coin #############
    # Cost of buying this much coin
    tradable_alt_qty = alt_qty * 0.999
    coin_total_price = tradable_alt_qty
    coin_qty = floor(tradable_alt_qty / coin_alt["bestAsk"], coin_alt["precision"])
    # If this trade is smaller than the minimum allowed trade
    if tradable_alt_qty < coin_alt["min"]:
        print(f"Trade too small! {tradable_alt_qty}{alt}")
        alt_to_base_market(client)
        return False
    # Attempt to execute the second trade
    try:
        print(f"Attempting to buy {coin_qty}{coin} for a total of {coin_total_price}{alt}")
        trade2 = await client.create_order(
            symbol=coin_alt["symbol"],
            side=SIDE_BUY,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_FOK, # Fill or kill: trade must be filled instantly
            quantity=coin_qty,
            price=coin_alt["bestAsk"]
            )
        #print(trade2)
    except BinanceAPIException as e:
        print(e)
        await alt_to_base_market(client)
        return False
    except BinanceOrderException as e:
        print(e)
        await alt_to_base_market(client)
        return False
    # If trade 2 successfully filled
    if "status" in trade2 and trade2["status"] == "FILLED":
        print(f"Bought {coin_qty}{coin} for a total of {trade2['cummulativeQuoteQty']}{alt}")
    else:
        print(f"Trade 2 ({alt} => {coin}) did not fill!")
        # Convert alt back to base after failed trade
        await alt_to_base_market(client)
        return False
        
    ############# Sell coin => base #############
    # Calculate amount of base after the next trade
    tradable_coin_qty = floor(coin_qty * 0.999, coin_base["precision"])
    base_qty = tradable_coin_qty * coin_base["bestBid"]
    # Check if the trade is big enough (should be if the logic is correct)
    if base_qty < coin_base["min"]:
        print(f"Trade too small! {base_qty}{base}")
        coin_to_base_market(client)
        return False
    try:
        print(f"Attempting to sell {tradable_coin_qty}{coin} for a total of {base_qty}{base}")
        trade3 = await client.create_order(
            symbol=coin_base["symbol"],
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            timeInForce=TIME_IN_FORCE_FOK, # Fill or kill: trade must be filled instantly
            quantity=tradable_coin_qty,
            price=coin_base["bestBid"]
            )
        #print(trade3)
    except BinanceAPIException as e:
        print(e)
        await coin_to_base_market(client)
        return False
    except BinanceOrderException as e:
        print(e)
        await coin_to_base_market(client)
        return False
    # If trade 3 successfully filled
    if "status" in trade3 and trade3["status"] == "FILLED":
        print(f"Sold {tradable_coin_qty}{coin} for a total of {trade3['cummulativeQuoteQty']}{base}")
    else:
        print(f"Trade 3 ({coin} => {base}) did not fill!")
        # Convert coin back to base after failed trade
        await coin_to_base_market(client)
        return False
    
    return True

# Wait for up to s seconds (default 60) to recieve a order filled update for the given orderId
async def wait_for_order_filled(us, orderId, s=60):
    start_time = time.time()
    while True:
        res = json.loads(await us.recv())
        p.print("Received user update")
        if res["e"] == "executionReport":
            if res["X"] == "FILLED" and res["i"] == orderId:
                p.print("Order filled!")
                return True
        current_time = time.time()
        if current_time - start_time > s:
            return False

# Await a message from multiplex socket and update the corresponding symbol's price data
async def get_prices(ms):
    res = await ms.recv()
    #p.print(end="3")
    if res != None:
        # If we received an error
        if "e" in res and res["e"] == "error":
            p.print("Error!")
            p.print(res)
        # If we received order book update
        elif "stream" in res and "data" in res:
            d = res["data"]
            # received coin/base update
            if res["stream"] == coin_base["stream"]:
                coin_base["bestBid"] = float(d["b"])
                coin_base["bidQty"] = float(d["B"])
                coin_base["bestAsk"] = float(d["a"])
                coin_base["askQty"] = float(d["A"])
                coin_base["updateTime"] = time.time()
            # received coin/alt update
            elif res["stream"] == coin_alt["stream"]:
                coin_alt["bestBid"] = float(d["b"])
                coin_alt["bidQty"] = float(d["B"])
                coin_alt["bestAsk"] = float(d["a"])
                coin_alt["askQty"] = float(d["A"])
                coin_alt["updateTime"] = time.time()
            # received alt/base update
            elif res["stream"] == alt_base["stream"]:
                alt_base["bestBid"] = float(d["b"])
                alt_base["bidQty"] = float(d["B"])
                alt_base["bestAsk"] = float(d["a"])
                alt_base["askQty"] = float(d["A"])
                alt_base["updateTime"] = time.time()

# Get the account balance of the specified symbol
async def get_balance(client, symbol):
    res = await client.get_asset_balance(asset=symbol)
    if "free" in res:
        return float(res["free"])

async def main():
    # Initialise client and sockets
    client = await AsyncClient.create(api_key, api_secret)
    bm = BinanceSocketManager(client)
    ms = bm.multiplex_socket([
        coin_base["stream"],
        coin_alt["stream"],
        alt_base["stream"]
        ])
    #us = bm.user_socket()
    await ms.__aenter__()
    #await us.__aenter__()
    
    # Get account balance
    global base_bal
    base_bal = await get_balance(client, base)
    # Time of last trade, initialised to 0
    previous_trade_time = 0
    # Time of oldest data's update, initialised to 0
    oldest_data_age = 0

    ### Main Loop ###
    while True:
        p.reset_cursor()
        p.print(f"{base} balance: {base_bal}")
        
        start_time = time.time()
        await get_prices(ms)
        # Print percentage profit info from both calculations and return the profits
        buy_with_base, buy_with_alt = check_prices()
        end_time = time.time()
        
        # If every pair has received data and has an update time
        if "updateTime" in coin_base and "updateTime" in coin_alt and "updateTime" in alt_base:
            oldest_update_time = min([coin_base["updateTime"], alt_base["updateTime"], coin_alt["updateTime"]])
            oldest_data_age = end_time - oldest_update_time
            p.print(f"Oldest data is {round(oldest_data_age, 3)} seconds old")
        
        # Oldest data cannot be more than this many seconds for a trade to be executed
        maximum_data_age = 2
        # Don't execute a trade if oldest data hasn't updated since last trade (prevent consecutive failed trades)
        # i.e. time since oldest data updated ? time since last trade
        maximum_data_age = min(maximum_data_age, end_time - previous_trade_time)
        
        p.print(f"Maximum data age is {round(maximum_data_age, 3)} seconds old")
        
        p.draw() # Draw the print queue and clear all text below it
        p.clear_q() # Empty the print queue
        
        if oldest_data_age < maximum_data_age: # Don't execute trades with old data
            result = None
            old_base_bal = base_bal
            # base => coin => alt => base
            if buy_with_base > minimum_profit:
                print(f"Starting balance: {base_bal}{base}")
                result = await execute_buy_with_base(client)
                base_bal = await get_balance(client, base) # Update balance
                print(f"New balance: {base_bal}{base}")
                previous_trade_time = time.time()
                clear()
            # base => alt => coin => base
            elif buy_with_alt > minimum_profit:
                print(f"Starting balance: {base_bal}{base}")
                result = await execute_buy_with_alt(client)
                base_bal = await get_balance(client, base) # Update balance
                print(f"New balance: {base_bal}{base}")
                previous_trade_time = time.time()
                clear()
            #if result == False:
                #time.sleep(10) # give time to read
            #break
        else:
            print("Data too old!")
        
    await ms.__aexit__(None, None, None)
    #await us.__aexit__(None, None, None)
    await client.close_connection()


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())