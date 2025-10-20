import requests
import time


def check_transactions(tx_id: str, chain: str):
    """
    Check confirmation status for BTC, ETH, SOL, LTC, USDT, TON.
    Returns: "confirmed", "pending", "failed", or "not_found"
    """

    try:
        # ============ BITCOIN / LITECOIN / USDT ============
        if chain in ['btc', 'ltc', 'usdt']:
            for cur in ['btc', 'ltc', 'usdt', 'ton']:
                print(f"🔔 {cur} checking...")
                if cur == 'usdt':
                    url = f"https://apilist.tronscanapi.com/api/transaction-info?hash={tx_id}"
                    r = requests.get(url)

                    if r.status_code == 429:
                        print("⚠️ Rate limit hit. Sleeping 10s...")
                        time.sleep(10)
                        continue

                    if r.status_code != 200:
                        continue
                    data = r.json()
                    confirmed = False
                    confirmations = 0

                    if isinstance(data, dict):
                        confirmed = data.get("confirmed", False)
                        confirmations = data.get("confirmations", 0)

                    if confirmed and confirmations > 0:
                        return "usdt", "confirmed"
                    else:
                        continue

                elif cur == 'ton':
                    url = f"https://toncenter.com/api/v3/transactions?hash={tx_id}"
                    r = requests.get(url)

                    if r.status_code != 200:
                        continue

                    data = r.json()
                    if data.get("transactions"):
                        tx = data["transactions"][0]
                        success = tx.get("description", {}).get(
                            "action", {}).get("success", False)
                        status = tx.get("end_status", "")

                        if success and status == "active":
                            return "ton", "confirmed"
                        else:
                            continue
                    else:
                        continue
                else:
                    token = '234e62b6bbe245bd9e4f179ae90d8930'
                    url = f"https://api.blockcypher.com/v1/{cur}/main/txs/{tx_id}token={token}"
                    r = requests.get(url, timeout=10)

                    if r.status_code == 429:
                        print("⚠️ Rate limit hit. Sleeping 10s...")
                        time.sleep(10)
                        continue

                    if r.status_code != 200:
                        continue
                    data = r.json()
                    confirmations = data.get("confirmations", 0)

                    if confirmations is None:
                        continue
                    elif confirmations > 1:
                        return cur, "confirmed"
                    else:
                        continue
            return chain, None

        # ============ ETH ============
        if chain == 'eth':
            api_key = "MVWVI5TISVZJCHVKBBVVR94EJNSFYNUY64"
            url = f"https://api.etherscan.io/v2/api?chainid=1&module=transaction&action=gettxreceiptstatus&txhash={tx_id}&apikey={api_key}"
            r = requests.get(url, timeout=10).json()
            if r.get('status') != '1':
                return "not_found"
            result = r.get("result", {})
            if result.get("status") == "1":
                return "eth", "confirmed"
            elif result.get("status") == "0":
                return "eth", "failed"
            else:
                return "eth", "pending"

        # ============ SOLANA ============
        if chain == 'sol':
            url = "https://api.mainnet-beta.solana.com"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [
                    [tx_id],
                    {"searchTransactionHistory": True}
                ]
            }
            r = requests.post(url, json=payload)

            if r.status_code != 200:
                return "sol", "not_found"

            data = r.json()
            value = data.get("result", {}).get("value", [])
            if value and "confirmationStatus" in value[0]:
                status = value[0]["confirmationStatus"]
                if status == "finalized":
                    return "sol", "confirmed"
                else:
                    return "sol", "pending"
            else:
                return "sol", "not_found"

        # ============ TON ============
        if chain == 'ton':
            url = f"https://toncenter.com/api/v3/transactions?hash={tx_id}"
            r = requests.get(url)

            if r.status_code != 200:
                return "ton", "not_found"

            data = r.json()
            if data.get("transactions"):
                tx = data["transactions"][0]
                success = tx.get("description", {}).get(
                    "action", {}).get("success", False)
                status = tx.get("end_status", "")

                if success and status == "active":
                    return "ton", "confirmed"
                else:
                    return "ton", "not_found"
            else:
                return "ton", "not_found"

    except Exception as e:
        print(f"Error checking {chain} tx {tx_id}:", e)
        return None, None
