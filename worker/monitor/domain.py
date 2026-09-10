import whois
from datetime import datetime


def check_domain(url):
    try:
        hostname = url.split("//")[-1].split("/")[0]
        info = whois.whois(hostname)

        exp = info.expiration_date
        if isinstance(exp, list):
            exp = exp[0]

        if exp:
            if exp.tzinfo:
                exp = exp.replace(tzinfo=None)

            return (exp - datetime.now()).days

    except Exception as e:
        print("Domain error:", e)

    return -1