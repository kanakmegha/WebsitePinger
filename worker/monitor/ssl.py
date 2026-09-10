import ssl
import socket
from datetime import datetime

def check_ssl(url):
    try:
        hostname = url.split("//")[-1].split("/")[0]

        context = ssl.create_default_context()
        with context.wrap_socket(socket.socket(), server_hostname=hostname) as s:
            s.settimeout(5)
            s.connect((hostname, 443))
            cert = s.getpeercert()

        exp_date = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
        days_left = (exp_date - datetime.now()).days

        return days_left

    except Exception as e:
        print("SSL error:", e)
        return -1