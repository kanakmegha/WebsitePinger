from database import add_site

WEBSITES = [
    "https://www.purelynx.com",
    "https://abdulazizsaidamericanu.org",
    "https://allstarsmartialarts.com",
    "https://AMMATransitPlanning.com",
    "https://assetman.com/",
    "https://brycorplumbing.com/",
    "https://cjiresearch.com/",
    "https://coolstartechnology.com/",
    "https://CronanRealEstate.com",
    "https://cyrellamariesoap.com",
    "https://jennsgardening.com/",
    "https://edbjohnson.com",
    "https://farbstein.com",
    "https://ffmre.org/",
    "https://intuityconsultants.com/",
    "https://iriedaughterpromotions.com/",
    "https://jwulaw.com/",
    "https://kimcareylaw.com/",
    "https://kimdeckerwrites.net/",
    "https://mmtron.com/",
    "https://momentummicro.com",
    "https://www.pcappa.org/",
    "https://pietrafina.com/",
    "https://rcmechanicalinc.com",
    "https://SFFMC.org",
    "https://SFFolkFest.org",
    "https://ElCerritoFreeFolkFestival.org",
    "https://themoncadacenter.com/",
    "https://ufesanfrancisco.org/",
    "https://wslawoffices.com/"
]

for url in WEBSITES:
    try:
        add_site(name=url, url=url)
        print(f"✅ Added: {url}")
    except Exception as e:
        print(f"⚠️ Skipped (maybe duplicate): {url}")