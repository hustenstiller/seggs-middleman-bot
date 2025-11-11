import aiohttp
import asyncio

CRYPTOCOMPARE_API_URL = "https://min-api.cryptocompare.com/data/pricemulti"
BINANCE_API_URL = "https://api.binance.com/api/v3/ticker/price"

async def get_live_rates(from_symbols: list[str], to_symbols: list[str]) -> dict | None:
    """Fetches live currency rates asynchronously using aiohttp from CryptoCompare."""
    fsyms = ",".join(from_symbols).upper()
    tsyms = ",".join(to_symbols).upper()
    params = {'fsyms': fsyms, 'tsyms': tsyms}

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(CRYPTOCOMPARE_API_URL, params=params) as response:
                response.raise_for_status()
                rates = await response.json()
                
                if "Response" in rates and rates["Response"] == "Error":
                    print(f"Currency API Error: {rates.get('Message', 'Unknown error')}")
                    return None
                
                print(f"Successfully fetched live rates via CryptoCompare: {rates}")
                return rates

    except aiohttp.ClientError as e:
        print(f"ERROR: Could not fetch currency rates with aiohttp (CryptoCompare): {e}")
        return None
    except asyncio.TimeoutError:
        print("ERROR: Timeout while fetching currency rates (CryptoCompare).")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_live_rates: {e}")
        return None

async def get_crypto_price(crypto_symbol: str) -> float | None:
    symbol = crypto_symbol.upper()
    
    if symbol != 'XMR':
        params = {'symbol': f'{symbol}USDT'}
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(BINANCE_API_URL, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = float(data['price'])
                        print(f"Successfully fetched price for {symbol} from Binance: {price}")
                        return price
                    else:
                        print(f"Info: {symbol} not found on Binance or API error (Status: {response.status}). Trying fallback.")
        except Exception as e:
            print(f"Error fetching price from Binance for {symbol}: {e}. Trying fallback.")

    print(f"Using CryptoCompare as fallback for {symbol}")
    rates = await get_live_rates([symbol], ['USD'])
    if rates and symbol in rates and 'USD' in rates[symbol]:
        price = rates[symbol]['USD']
        print(f"Successfully fetched price for {symbol} from CryptoCompare: {price}")
        return float(price)
        
    print(f"FATAL: Could not fetch price for {symbol} from any source.")
    return None

async def get_price(symbol: str) -> float | None:
    """Fetches the price of a given currency symbol in USD."""
    symbol = symbol.lower()
    
    if symbol == 'rub':
        rates = await get_live_rates(['USD'], ['RUB'])
        if rates and 'USD' in rates and 'RUB' in rates['USD']:
            usd_to_rub_rate = rates['USD']['RUB']
            return 1 / usd_to_rub_rate
        return None
    else:
        return await get_crypto_price(symbol)