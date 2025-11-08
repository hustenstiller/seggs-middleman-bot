import aiohttp
import asyncio

API_URL = "https://min-api.cryptocompare.com/data/pricemulti"

async def get_live_rates(from_symbols: list[str], to_symbols: list[str]) -> dict | None:
    """Fetches live currency rates asynchronously using aiohttp."""
    fsyms = ",".join(from_symbols).upper()
    tsyms = ",".join(to_symbols).upper()
    params = {'fsyms': fsyms, 'tsyms': tsyms}

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(API_URL, params=params) as response:
                response.raise_for_status()
                rates = await response.json()
                
                if "Response" in rates and rates["Response"] == "Error":
                    print(f"Currency API Error: {rates.get('Message', 'Unknown error')}")
                    return None
                
                print(f"Successfully fetched live rates: {rates}")
                return rates

    except aiohttp.ClientError as e:
        print(f"ERROR: Could not fetch currency rates with aiohttp: {e}")
        return None
    except asyncio.TimeoutError:
        print("ERROR: Timeout while fetching currency rates.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_live_rates: {e}")
        return None