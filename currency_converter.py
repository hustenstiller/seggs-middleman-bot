import requests

API_URL = "https://min-api.cryptocompare.com/data/pricemulti"

def get_live_rates(from_symbols: list[str], to_symbols: list[str]) -> dict | None:
    try:
        fsyms = ",".join(from_symbols).upper()
        tsyms = ",".join(to_symbols).upper()
        
        params = {'fsyms': fsyms, 'tsyms': tsyms}
        response = requests.get(API_URL, params=params, timeout=5)
        response.raise_for_status()
        
        rates = response.json()
        if "Response" in rates and rates["Response"] == "Error":
            print(f"Currency API Error: {rates.get('Message', 'Unknown error')}")
            return None
            
        print(f"Successfully fetched live rates: {rates}")
        return rates

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Could not fetch currency rates: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in get_live_rates: {e}")
        return None