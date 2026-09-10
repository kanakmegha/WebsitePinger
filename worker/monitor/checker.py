import requests
import time


def check_http(url):
    try:
        start = time.time()
        res = requests.get(url, timeout=900)
        duration = int((time.time() - start) * 1000)

        status = "UP" if res.status_code < 400 else "DOWN"

        return {
            "status": status,
            "response_time": duration,
            "status_code": res.status_code
        }

    except Exception:
        return {
            "status": "DOWN",
            "response_time": 0,
            "status_code": 0
        }