import requests
import time
from datetime import datetime


def check_http(url, retries=3, delay=2):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) WebsiteMonitor/2.0"
    }

    attempts = []
    final_status = "DOWN"
    final_response_time = 0

    for attempt_idx in range(1, retries + 1):
        start = time.time()
        attempt_time = datetime.now().strftime('%H:%M:%S')

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=(5, 10),
                allow_redirects=True
            )
            duration = int((time.time() - start) * 1000)

            # Treat response < 500 as UP / SUCCESS
            if response.status_code < 500:
                final_status = "UP"
                final_response_time = duration

                attempts.append({
                    "attempt": attempt_idx,
                    "status": "SUCCESS",
                    "status_code": response.status_code,
                    "response_time": duration,
                    "timestamp": attempt_time,
                    "message": f"{response.status_code} OK in {duration} ms"
                })
                break
            else:
                attempts.append({
                    "attempt": attempt_idx,
                    "status": "FAILED",
                    "status_code": response.status_code,
                    "response_time": duration,
                    "timestamp": attempt_time,
                    "error": f"Server error HTTP {response.status_code}"
                })

        except requests.exceptions.Timeout:
            duration = int((time.time() - start) * 1000)
            attempts.append({
                "attempt": attempt_idx,
                "status": "FAILED",
                "status_code": 0,
                "response_time": duration,
                "timestamp": attempt_time,
                "error": f"Timeout after {duration}ms"
            })
        except requests.exceptions.ConnectionError:
            duration = int((time.time() - start) * 1000)
            attempts.append({
                "attempt": attempt_idx,
                "status": "FAILED",
                "status_code": 0,
                "response_time": duration,
                "timestamp": attempt_time,
                "error": "Connection refused / DNS lookup failed"
            })
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            attempts.append({
                "attempt": attempt_idx,
                "status": "FAILED",
                "status_code": 0,
                "response_time": duration,
                "timestamp": attempt_time,
                "error": str(e) or "Check failed"
            })

        if attempt_idx < retries:
            time.sleep(delay)

    return {
        "status": final_status,
        "response_time": final_response_time,
        "attempts": attempts
    }