import dns.resolver

def get_dns_info(domain):
    result = {
        "ip": None,
        "nameservers": [],
        "spf": None,
        "dmarc": None
    }

    try:
        # IP
        answers = dns.resolver.resolve(domain, 'A')
        result["ip"] = answers[0].to_text()

        # NS
        ns = dns.resolver.resolve(domain, 'NS')
        result["nameservers"] = [r.to_text() for r in ns]

        # SPF
        txt = dns.resolver.resolve(domain, 'TXT')
        for r in txt:
            txt_val = r.to_text()
            if "v=spf1" in txt_val:
                result["spf"] = txt_val

        # DMARC
        dmarc_domain = f"_dmarc.{domain}"
        dmarc = dns.resolver.resolve(dmarc_domain, 'TXT')
        for r in dmarc:
            result["dmarc"] = r.to_text()

    except Exception:
        pass

    return result