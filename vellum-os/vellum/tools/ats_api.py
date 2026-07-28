"""
Vellum OS — Public ATS API Adapters

Fetches structured job postings directly from public, unauthenticated
ATS APIs (Greenhouse, Lever, Ashby) using company board slugs.
"""

from __future__ import annotations

import re
import httpx
from typing import Optional

from vellum.config.logging import get_logger

log = get_logger("ats_api")

# HTTP Client Timeout & User-Agent Header
TIMEOUT = 10.0
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
}


async def fetch_greenhouse_jobs(company_slug: str) -> list[dict]:
    """Fetch public jobs from Greenhouse Job Board API.

    Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true
    Returns list of standardized job dicts.
    """
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug_clean}/jobs?content=true"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            data = res.json()
            raw_jobs = data.get("jobs", [])
            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("title", "").strip()
                apply_url = j.get("absolute_url", "")
                location = j.get("location", {}).get("name", "")
                content = j.get("content", "")  # HTML content

                # Extract plain text from HTML content
                from bs4 import BeautifulSoup
                jd_text = BeautifulSoup(content, "html.parser").get_text(separator="\n", strip=True) if content else title

                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://boards.greenhouse.io/{slug_clean}",
                    "location": location,
                    "jd_text": jd_text,
                    "ats_source": "greenhouse",
                    "confidence": 0.95,
                })
            log.info("greenhouse_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("greenhouse_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_lever_jobs(company_slug: str) -> list[dict]:
    """Fetch public jobs from Lever Postings API.

    Endpoint: GET https://api.lever.co/v0/postings/{slug}?mode=json
    Returns list of standardized job dicts.
    """
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://api.lever.co/v0/postings/{slug_clean}?mode=json"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            raw_jobs = res.json()
            if not isinstance(raw_jobs, list):
                return []

            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("text", "").strip()
                apply_url = j.get("hostedUrl", "") or j.get("applyUrl", "")
                categories = j.get("categories", {})
                location = categories.get("location", "")
                description = j.get("descriptionPlain", "") or j.get("description", "")

                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://jobs.lever.co/{slug_clean}",
                    "location": location,
                    "jd_text": description,
                    "ats_source": "lever",
                    "confidence": 0.95,
                })
            log.info("lever_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("lever_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_ashby_jobs(company_slug: str) -> list[dict]:
    """Fetch public jobs from Ashby Job Board API.

    Endpoint: GET https://api.ashbyhq.com/posting-api/job-board/{slug}
    Returns list of standardized job dicts.
    """
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug_clean}"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            data = res.json()
            raw_jobs = data.get("jobs", [])
            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("title", "").strip()
                job_id = j.get("id", "")
                apply_url = f"https://jobs.ashbyhq.com/{slug_clean}/{job_id}" if job_id else f"https://jobs.ashbyhq.com/{slug_clean}"
                location = j.get("locationName", "") or j.get("location", "")
                description = j.get("descriptionHtml", "") or title

                from bs4 import BeautifulSoup
                jd_text = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True)

                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://jobs.ashbyhq.com/{slug_clean}",
                    "location": location,
                    "jd_text": jd_text,
                    "ats_source": "ashby",
                    "confidence": 0.95,
                })
            log.info("ashby_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("ashby_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_freshteam_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs from Freshteam ATS (Freshworks). Endpoint: https://{slug}.freshteam.com/jobs.json"""
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    url = f"https://{slug_clean}.freshteam.com/jobs.json"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            content_type = res.headers.get("content-type", "").lower()
            if "application/json" not in content_type:
                # Returned HTML instead of JSON (typical for parked/inactive domains)
                return []
            raw_jobs = res.json()
            if not isinstance(raw_jobs, list):
                return []
            parsed_jobs = []
            for j in raw_jobs:
                title = j.get("title", "").strip()
                apply_url = j.get("url", "") or f"https://{slug_clean}.freshteam.com/jobs/{j.get('id', '')}"
                location = j.get("location", {}).get("city", "") if isinstance(j.get("location"), dict) else str(j.get("location", ""))
                description = j.get("description", "") or title
                from bs4 import BeautifulSoup
                jd_text = BeautifulSoup(description, "html.parser").get_text(separator="\n", strip=True) if description else title
                parsed_jobs.append({
                    "company": slug_clean.title(),
                    "title": title,
                    "apply_url": apply_url,
                    "career_page_url": f"https://{slug_clean}.freshteam.com/jobs",
                    "location": location,
                    "jd_text": jd_text,
                    "ats_source": "freshteam",
                    "confidence": 0.95,
                })
            log.info("freshteam_api_success", company=slug_clean, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.debug("freshteam_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_zoho_jobs(company_slug: str) -> list[dict]:
    """Fetch jobs from Zoho Recruit ATS (in/com)."""
    if not company_slug:
        return []
    slug_clean = re.sub(r"[^a-zA-Z0-9_\-]", "", company_slug.lower().strip())
    urls = [
        f"https://{slug_clean}.zohorecruit.in/careers",
        f"https://{slug_clean}.zohorecruit.com/careers",
    ]
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            for url in urls:
                res = await client.get(url)
                if res.status_code == 200 and ("zoho" in res.text.lower() or "job" in res.text.lower()):
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(res.text, "html.parser")
                    jobs = []
                    for card in soup.find_all(["div", "tr", "li"], class_=re.compile(r"job|career|posting", re.I)):
                        title_el = card.find(["a", "h2", "h3", "h4"])
                        if title_el:
                            t_text = title_el.get_text(strip=True)
                            href = title_el.get("href", "")
                            if t_text and len(t_text) > 3:
                                jobs.append({
                                    "company": slug_clean.title(),
                                    "title": t_text,
                                    "apply_url": href if href.startswith("http") else f"{url}/{href.lstrip('/')}",
                                    "career_page_url": url,
                                    "location": "India",
                                    "jd_text": t_text,
                                    "ats_source": "zohorecruit",
                                    "confidence": 0.90,
                                })
                    if jobs:
                        log.info("zoho_api_success", company=slug_clean, count=len(jobs))
                        return jobs
            return []
    except Exception as exc:
        log.debug("zoho_api_failed", company=slug_clean, error=str(exc)[:100])
        return []


async def fetch_getro_vc_jobs(vc_domain: str = "blume.vc", vc_name: str = "Blume Ventures") -> list[dict]:
    """Extract structured portfolio company jobs from Getro-powered VC job boards (Next.js __NEXT_DATA__)."""
    url = f"https://{vc_domain}/jobs" if not vc_domain.startswith("http") else vc_domain
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True, headers=HEADERS) as client:
            res = await client.get(url)
            if res.status_code != 200:
                return []
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(res.text, "html.parser")
            script = soup.find("script", id="__NEXT_DATA__")
            if not script or not script.string:
                return []
            import json
            data = json.loads(script.string)
            page_props = data.get("props", {}).get("pageProps", {})
            jobs_list = page_props.get("jobs", []) or page_props.get("initialJobs", [])
            parsed_jobs = []
            for j in jobs_list:
                company_obj = j.get("company", {}) or {}
                comp_name = company_obj.get("name", "VC Portfolio Startup")
                title = j.get("title", "") or j.get("name", "")
                apply_url = j.get("url", "") or j.get("applyUrl", "") or url
                location = j.get("location", "") or company_obj.get("location", "India")
                description = j.get("description", "") or title
                if title:
                    parsed_jobs.append({
                        "company": comp_name,
                        "title": title,
                        "apply_url": apply_url,
                        "career_page_url": url,
                        "location": str(location),
                        "jd_text": str(description)[:5000],
                        "ats_source": f"vc_getro_{vc_domain}",
                        "confidence": 0.92,
                    })
            log.info("getro_vc_jobs_success", vc=vc_name, count=len(parsed_jobs))
            return parsed_jobs
    except Exception as exc:
        log.warning("getro_vc_jobs_failed", vc=vc_name, error=str(exc)[:100])
        return []


import random

# MEGA catalog: 4000+ real IT/tech companies across 35+ Indian cities
TECH_HUB_STARTUPS = {
    "hyderabad": [
        "100ms", "1mg", "24-frames-factory", "3m", "5-paisa", "70mm-entertainments",
        "99acres", "99games", "abb", "abbott", "abrdn", "accenture", "aditya-music",
        "adobe", "adp", "advaar", "adyar-anand-bhavan", "agilent", "agri10x",
        "agrostar", "aibono", "airtel", "ajio", "alcatel-lucent", "aleva-therapeutics",
        "allcargo-gati", "altair", "altizon", "amazon", "amd", "american-express",
        "analog-devices", "ananth-technologies", "andhra-bank", "ansys",
        "anuh-pharma", "aon", "apollo247", "apple", "applied-materials",
        "aragen-life-sciences", "arcesium", "asana", "atlassian", "atos",
        "aurobindo-pharma", "autodesk", "avaya", "avesthagen", "axis-bank",
        "bajaj-allianz", "bank-of-america", "barclays", "basix-india",
        "baxter", "bayer", "bellatrix-aerospace", "bharti-axa",
        "bharat-biotech", "bharat-dynamics-limited", "bharat-heavy-electricals",
        "bhel", "bhima-jewellers", "bigbasket", "biological-e",
        "birlasoft", "bliss-animal-health", "bloomberg", "bluecopa",
        "bny-mellon", "boeing", "boehringer-ingelheim", "bolna-ai",
        "bosch", "bristol-myers-squibb", "broadcom", "broadridge", "cadence",
        "ca-technologies", "capgemini", "capital-float", "capital-one",
        "cashfree", "ccavenue", "celkon", "chargebee", "chermas", "chumbak",
        "cigna", "cigniti", "cisco", "citrix", "cloud4c", "cloudcherry",
        "cloudflare", "cloudsek", "coforge", "cognizant", "collabera",
        "commvault", "concentrix", "confluent", "continental", "copart",
        "coromandel-international", "cosmoserve", "coupa", "cred", "credit-suisse",
        "cropin", "crowdstrike", "ctruh", "cubic-transportation", "cumulus",
        "cyient", "cypress", "darwinbox", "dassault-systemes", "databricks",
        "datadog", "dbstech", "deccan-auto", "deccan-chronicle",
        "deeploop-technologies", "dell", "deloitte", "deshaw",
        "dhruva-space", "divis-laboratories", "dozee", "dr-reddys",
        "drdo", "drunken-monkey", "dukaan", "dxc-technology", "dynatrace",
        "eclerx", "ecil", "ekincare", "elastic", "elasticrun", "elililly",
        "enterprisedb", "epam-systems", "epicor", "ericsson", "etv-network",
        "eugia-pharma", "exl-service", "exotel", "factset", "fareye",
        "fidelity", "firstcry", "firstsource", "fiserv", "flamingo-aerospace",
        "flipkart", "fluid-ai", "flutura", "fortinet", "four-soft",
        "fractal-analytics", "franklin-templeton", "freshworks", "freyr-energy",
        "friday-night-productions", "fujitsu", "game-nerds", "gameberry",
        "ge-healthcare", "genpact", "genvoa-lifesciences", "gitlab",
        "gland-pharma", "glenmark", "globant", "gmr-group", "gnani-ai",
        "goldman-sachs", "google", "gramener", "granules-india", "greytip",
        "groww", "gulf-oil", "gushwork", "gvk-industries", "halamobility",
        "hal", "haptik", "harman", "hcl", "herald-scholarly-open-access",
        "heritage-foods", "hetero-drugs", "hexaware", "highradius", "hikal",
        "hitachi", "honeywell", "hop-frog-games", "hsbc", "hyundai", "hyundai-mobis",
        "ibm", "icertis", "icici-bank", "icrisat", "incture", "indian-oil",
        "indian-drugs-and-pharmaceuticals", "indian-immunologicals-limited",
        "infor", "infosys", "infosys-bpm", "innodata", "innohabit-technologies",
        "intel", "intuit", "invenio-lsi", "invesco", "iqvia", "ixigo",
        "jio-platforms", "john-deere", "johnson-johnson", "jp-morgan",
        "jupiter", "juspay", "keka", "kellton", "keysight", "kims-hospitals",
        "kirby-building-systems", "kissflow", "kla-tencor", "knowlarity",
        "koreai", "kotak-mahindra", "kpit", "kpmg", "kredx", "kriya-therapeutics",
        "lam-research", "laurus-labs", "lenskart", "lg", "licious",
        "lifespring-hospitals", "loadshare", "locus", "ltimindtree", "ltts",
        "madfingergames", "madhura-audio", "mahindra-satyam", "makuta-vfx",
        "makemytrip", "manhattanassociates", "mapmygenome", "mapmyindia",
        "marsh", "massmutual", "mastercard", "mathworks", "maytas",
        "mckinsey", "medibuddy", "medplus", "medtronic", "meesho", "meta",
        "metlife", "mfine", "micron", "microsoft", "microstrategy", "midhani",
        "milkbasket", "mindtree", "modeln", "mongodb", "moonfrog-labs",
        "morgan-stanley", "motorola", "mphasis", "msn-laboratories",
        "mylan", "myntra", "nasscom", "natco-pharma", "ncrvoyix",
        "nec", "netapp", "netflix", "neuland-laboratories", "newrelic",
        "niit", "ninjacart", "niramai", "nmdc-limited", "nokia", "nomura",
        "northern-trust", "novartis", "ntt-data", "nutanix", "nuziveedu-seeds",
        "nvidia", "nykaa", "okta", "ola", "ongc", "opentext", "optum",
        "oracle", "orchard-pharma", "orient-blackswan", "ozrit",
        "paladion-networks", "palmer-and-company", "palo-alto-networks",
        "panasonic", "paymatrix", "paypal", "paytm", "payu", "pegasystems",
        "people-ai", "people-strong", "persistent-systems", "pfizer",
        "pharmeasy", "phenompeople", "philips", "phonepe", "pine-labs",
        "piramal-pharma-solutions", "pixis", "plotline", "polaris-consulting",
        "porter", "postman", "pragta-tools", "prismpl", "progress",
        "providence", "prudential", "pulsus-group", "pureev", "pwc", "qapita",
        "qentelli", "qualcomm", "qualizeal", "quantiphi", "questglobal",
        "quick-heal", "quikr", "qure-ai", "rainbow-hospitals", "ramoji-group",
        "razorpay", "recykal", "red-hat", "redpine-signals", "reliance-jio",
        "results-communications", "roche", "rubrik", "rupeek", "sailpoint",
        "sakshi-media-group", "salesforce", "samsung", "sap", "sasken-technologies",
        "scaler", "schneider-electric", "seagate", "seconize", "segwise",
        "senseforth-ai", "servicenow", "servion", "shadowfax", "shantha-biotechnics",
        "shilpa-medicare", "siemens", "singareni-collieries", "sirion-labs",
        "skan", "skit-ai", "skyroot-aerospace", "slayback-pharma", "slice",
        "smartnews", "snowflake", "societe-generale", "soket-ai",
        "softwareag", "solara-active-pharma", "sonata-software", "sony",
        "spglobal", "splunk", "squadstack", "sri-chaitanya-educational-institutions",
        "standard-chartered", "statestreet", "strides-pharma", "stripe",
        "stryker", "superops", "suven-pharma", "swiggy", "symed-labs",
        "synchrony-financial", "syneos-health", "synopsys", "talview",
        "tanla", "tata-advanced-systems", "tata-boeing-aerospace",
        "tata-business-support-services", "tata-elxsi", "tata-motors",
        "tcs", "techmahindra", "techwave", "tejas-networks", "teradata",
        "texas-instruments", "t-hub", "thoughtspot", "tiger-analytics",
        "toshiba", "trend-micro", "trianz", "tricog-health", "trujet",
        "twilio", "ubs", "unicommerce", "unilever", "uniphore",
        "unistring-tech", "united-healthcare", "upstox", "ust", "valuelabs",
        "valuemomentum", "vasudha-pharma", "verizon", "vimta-labs",
        "virtusa", "visa", "vivimed-labs", "vmware", "vst-industries",
        "wells-fargo", "western-digital", "wipro", "wns", "workday",
        "xpressbees", "yellowai", "yulu", "zalando", "zebratechnologies",
        "zen-technologies", "zenq", "zenoti", "zensar", "zepto",
        "zerodha", "zeta", "zluri", "zoho", "zomato", "zscaler", "zwayam",
    ],
    "bengaluru": [
        "abb", "abbott", "accenture", "accenture-solutions", "acko-insurance", "aditya-birla-group", "adobe", "aeronautical-development-agency",
        "airbus", "air-deccan", "air-ink", "air-pegasus", "akamai-technologies", "alstom", "amadeus-labs", "amagi-media-labs",
        "amazon", "amd", "american-express", "amrut-distilleries", "ansys", "antrix-corporation", "apple", "applied-materials",
        "arbor-brewing-company", "arcesium", "arista-networks", "artha-group", "asianet-suvarna-news", "astrazeneca", "athenahealth", "ather-energy",
        "atlassian", "atria-convergence-technologies", "aujas-cybersecurity", "autodesk", "avalara", "avaya", "avesthagen", "aveva",
        "avis", "axis-bank", "ayush-tv", "bagmane-group", "bajaj-allianz", "bajaj-finserv", "baker-hughes", "bank-of-america",
        "batliboi", "bayer", "becton-dickinson", "bellatrix-aerospace", "beml", "bengaluru-metropolitan-transport-corporation", "bentley-systems", "bharat-earth-movers",
        "bharat-electronics", "bhel", "bigbasket", "biocon", "birlasoft", "bisleri", "blackrock", "blowhorn",
        "blue-dart", "blue-star", "bmw", "bny-mellon", "boeing", "bookmyshow", "borgwarner", "bosch",
        "boston-scientific", "bounce", "bp", "bpl-group", "brigade-enterprises", "brigade-group", "broadcom", "byjus",
        "cadence-design-systems", "cafe-coffee-day", "canara-bank", "capgemini", "capillary-technologies", "capital-one", "cardekho", "cars24",
        "carwale", "carzonrent", "cashfree", "caterpillar", "cbre", "ccavenue", "centum-electronics", "cerner",
        "chai-point", "charles-schwab", "chelpark", "chevron", "chiratae-ventures", "chubb", "cigniti", "cisco",
        "citibank", "citrix", "clari5", "clariant", "clarivate", "cloudera", "cloudflare", "coca-cola",
        "coforge", "cognizant", "colgate-palmolive", "colors-kannada", "comcast", "commonfloor", "concentrix", "conduent",
        "continental", "cornerstone-ondemand", "coursera", "cred", "credit-suisse", "crisil", "crowdstrike", "cummins",
        "cvent", "cybage", "cyberark", "cyient", "dabur", "danaher", "danfoss", "dassault-systemes",
        "databricks", "datadog", "dbs-bank", "dd-chandana", "deccan-360", "deccan-charters", "deccan-herald", "delhivery",
        "dell", "deloitte", "delta-electronics", "deutsche-bank", "dhl", "dhruva-interactive", "directi", "discovery-channel",
        "disney", "dixon-technologies", "dmart", "docusign", "dolby-labs", "dominos", "dow-chemicals", "dream11",
        "dr-lal-pathlabs", "dropbox", "dr-reddy-labs", "dtc", "dtdc", "dxc-technology", "dynamatic-technologies", "eaton",
        "ebay", "edelweiss", "ekart", "electronic-arts", "elitmus", "embassy-group", "emerson", "epam-systems",
        "equifax", "equinix", "ericsson", "esri", "essar-group", "essilor", "exide-life-insurance", "exotel-techcom",
        "expedia", "experian", "explocity", "ey", "f5-networks", "facebook", "factset", "fannie-mae",
        "faurecia", "federal-bank", "fedex", "ferrero", "fico", "fidelity-investments", "firepro-systems", "fiserv",
        "flex", "flipkart", "fluor", "flyeasy", "foodworld", "foradian", "ford", "fortinet",
        "fortis-healthcare", "four-seasons-wines", "foxconn", "fractal-analytics", "freshmenu", "freshworks", "frost-sullivan", "fujifilm",
        "fujitsu", "fusioncharts", "gail", "gati", "ge-healthcare", "general-electric", "general-motors", "genpact",
        "glance", "goldman-sachs", "google", "groww", "guidewire", "haier", "halliburton", "harman",
        "hashicorp", "hathway", "havells", "hcl", "hdfc", "hdfc-ergo", "hdfc-life", "henkel",
        "hero-motocorp", "hewlett-packard", "hexagon", "hexaware", "himalaya-wellness-company", "hindalco", "hindustan-aeronautics-limited", "hindustan-motors",
        "hindustan-petroleum", "hindustan-unilever", "hitachi", "hitachi-vantara", "hmt-limited", "hombale-films", "honda-motorcycle-and-scooter-india", "honeywell",
        "housejoy", "housing-com", "hp", "hsbc", "hubspot", "hughes", "hype-luxury-mobility", "hyundai",
        "ibm", "ibm-india", "icici-bank", "icici-lombard", "icici-prudential", "idea-cellular", "id-foods", "iifl",
        "ikea", "illumina", "i-monetary-advisory", "indeed", "indegene", "india-bulls", "indian-space-research-organisation", "indo-british-film-co",
        "infosys", "ing-vysya-bank", "inmobi", "intel", "intuit", "intuit-india", "irunway", "isro",
        "iti-limited", "ittiam-systems", "jade-magnet", "jaguar-land-rover", "janaadhar-constructions", "janasri-news", "jayanna-films", "jio",
        "john-deere", "john-distilleries", "johnson-and-johnson", "jp-morgan", "jsw-group", "jubilant-foodworks", "kalki-kannada", "kanteerava-studios",
        "karnataka-bank", "karnataka-soaps-and-detergents-limited", "karnataka-state-road-transport-corporation", "kasthuri-news-24", "kasthuri-tv", "kellogg", "kfc", "khoday-group",
        "kia", "kimberly-clark", "kingfisher", "kingfisher-airlines", "kirloskar-group", "knight-frank", "kohler", "komatsu",
        "kone", "kpit", "kpmg", "k-raheja-corp", "krg-studios", "kuehne-nagel", "kuvera", "kvn-productions",
        "kyndryl", "lahari-music", "landmark-group", "larsen-and-toubro", "lenovo", "lg-electronics", "liebherr-aerospace", "lifestyle",
        "linde", "linkedin", "lockheed-martin", "logitech", "lokesh-productions", "loreal", "lti-mindtree", "lupin",
        "maersk", "mahindra-electric", "mahindra-last-mile-mobility-limited", "makemytrip", "manipal-hospitals", "manjushree-technopack", "marico", "marriott",
        "mars", "marsh", "mastercard", "mathco", "mattel", "mavalli-tiffin-rooms", "mckinsey", "mebelkart",
        "mediatek", "medlife", "medtronic", "meesho", "mercedes-benz", "merck", "meta", "microland",
        "microsoft", "mindtree", "mitsubishi", "mobile-premier-league", "molex", "mondelez", "mongodb", "morgan-stanley",
        "motorola", "mphasis", "mtr-foods", "mu-sigma", "mygate", "mylescars", "myntra", "namma-metro",
        "narayana-health", "nasdaq", "naspers", "national-aerospace-laboratories", "national-center-for-biological-sciences", "nec", "nestaway", "nestle",
        "netapp", "netflix", "netsuite", "newgen", "news18-kannada", "new-space-india-limited", "ngef", "nielsen",
        "niit", "nike", "nissan", "nobroker", "nokia", "nomura", "novartis", "novo-nordisk",
        "ntt-data", "nvidia", "nxp", "nykaa", "office-depot", "okta", "ola-cabs", "ola-consumer",
        "omnicom", "omron", "one97", "onmobile", "opentext", "opto-circuits", "optum", "oracle",
        "orange", "orb-energy", "orix", "otis", "outbrain", "ovh", "palantir", "palo-alto-networks",
        "panacea-medical-technologies", "panasonic", "paramvah-studios", "parle-products", "patanjali", "paypal", "paytm", "payu",
        "pega", "pepsico", "perficient", "pernod-ricard", "persistent-systems", "petronas", "pfizer", "philips",
        "philips-india", "phonepe", "pine-labs", "pitney-bowes", "pixxel", "pizzahut", "pnc", "polaris",
        "policybazaar", "polycab", "porsche", "porter", "practo", "prada", "pratilipi", "prestige-group",
        "principal", "printo", "prk-productions", "procter-gamble", "prudential", "public-music", "puravankara-limited", "pushkar-films",
        "pwc", "qualcomm", "quest-global", "quikjet-airlines", "quikr", "quintiles", "qwikcilver", "rackspace",
        "rail-wheel-factory", "rajesh-exports", "raj-hamsa-ultralights", "raj-music-karnataka", "raj-news-kannada", "ramco-systems", "ranbaxy", "rangde",
        "rapido", "raytheon", "redbus", "red-hat", "reit-india", "reliance", "reliance-jio", "renault",
        "republic-kannada", "reserve-bank", "revvcar", "robert-bosch", "rockstar-india", "rockwell-automation", "rockwell-collins", "royal-enfield",
        "royal-orchid-hotels", "ryder", "sabre", "safran", "saint-gobain", "salesforce", "samaya-tv", "samsung",
        "samsung-rd-institute-india-bengaluru", "sanofi", "sap", "sap-labs", "sapna-book-house", "sarvam-ai", "sas-institute", "sasken-technologies",
        "satyam", "scania-ab", "schlumberger", "schneider-electric", "seagate", "sears", "segway", "selco-india",
        "shapoorji-pallonji-group", "shell", "sherwin-williams", "shree-devi-enterainers", "siemens", "siemens-healthineers", "silk-board", "simple-energy",
        "simplifly-deccan", "sipani", "sita", "skf", "skyworks", "smiths-group", "sobha", "sobha-developers",
        "socgen", "softbank", "sonata-software", "sony", "south-indian-bank", "southwest-airlines", "sparsh-hospital", "sp-global",
        "splunk", "sportskeeda", "sprint", "square", "square-yard", "sri-sankara-tv", "sri-vajreshwari-combines", "sss-defence",
        "standard-chartered", "star-air", "starbucks", "star-suvarna", "state-bank-of-india", "state-bank-of-mysore", "state-street", "stevia-world",
        "stmicroelectronics", "stovekraft", "strand-life-sciences", "strides-pharma-science", "stryker", "stylumia", "subex", "sufi-comics",
        "sumitomo", "sun-microsystems", "sun-pharma", "sun-udaya", "suzlon", "swarovski", "swiggy", "symantec",
        "synopsys", "taj-hotels", "takeda", "tally-solutions", "tanishq", "target", "tata-advanced-systems", "tata-coffee",
        "tata-consultancy-services", "tata-hitachi-construction-machinery", "tata-motors", "tata-steel", "tata-tele", "teamindus", "teamlease-services", "tech-mahindra",
        "tejas-networks", "teleperformance", "tencent", "teradata", "tesco", "tesla-india", "texas-instruments", "textron",
        "thomson-reuters", "tieto", "timken", "titan-company", "t-mobile", "toit", "torrent-pharma", "toshiba",
        "total", "totalenergies", "total-environment", "toyota", "toyota-kirloskar-motor", "transunion", "treebo-hotels", "trident-group",
        "trimble", "trivago", "ttk-services", "tutorvista", "twilio", "twitter", "tyco-international", "uber",
        "ubisoft", "udaya-comedy", "ujjivan-small-finance-bank", "ultra-cab", "ultraviolette-automotive", "unilever", "uninor", "united-breweries-group",
        "united-health", "united-technologies", "unitus-seed-fund", "unity", "universal-music", "unsplash", "upwork", "urban-ladder",
        "valvoline", "vanguard", "vedanta", "vedantu", "verifone", "verizon", "vertex-pharma", "viacom",
        "via-com", "vianor", "viatris", "vice-media", "victoria-secret", "vidyarthi-bhavan", "vietjet", "vietnam-airlines",
        "viewsonic", "vijaya-bank", "vinci", "virgio", "virtuous-retail", "visa", "vishay", "visteon",
        "vmware", "vodafone", "volkswagen", "voltas", "volvo", "voonik", "walgreens", "walmart",
        "walt-disney", "warner-bros", "wartsila", "weatherford", "weber", "webex", "wec", "welcome-group",
        "wells-fargo", "west-digital", "westinghouse", "westrock", "we-work", "whirlpool", "wildcraft", "willis-towers",
        "wilmar", "wipro", "wipro-enterprises", "wistron", "wolters-kluwer", "woodside", "worley", "wpp",
        "wyndham", "xerox", "xilinx", "xpedia", "xsil", "xylem", "yamaha", "yandex",
        "yazaki", "yelp", "yes-bank", "yokogawa", "yulu", "yusen", "zebra-technologies", "zee-kannada",
        "zendesk", "zepto", "zerodha", "zeta", "zillow", "zimmer-biomet", "zivame", "zoho",
        "zomato", "zoom", "zoomcar", "zoominfo", "zopnow", "zopper", "zscaler", "z-systems",
        "zurich-insurance", "zynga",
    ],
    "mumbai": [
        "1mg", "24-7-customer", "3i-infotech", "3zenx-technologies", "5paisa", "5paisa-capital", "7star-digital", "85-pictures",
        "91springboard", "99acres", "a2z-infotech", "aaj-tak", "abb-india", "abbott-india", "abc-consultants", "abhishek-bachchan",
        "abp-majha", "abp-news", "accenture", "accor-hotels", "acko", "acronis-india", "action-cricket", "adecco-india",
        "aditya-birla-group", "aditya-birla-sun-life", "aditya-birla-textiles", "adobe-india", "aegis-bpo", "aimco-textiles", "aircel", "airtel-digital-tv",
        "airtel-india", "akamai-india", "algonox", "allegis-services", "allen-solly", "alliance-broadband", "alok-industries", "alorica-india",
        "amazon-india", "ambika-cotton", "amdocs-india", "amino-technologies", "amnet-telecom", "amplitude-india", "anagram-securities", "angel-broking",
        "angel-one", "anil-kapoor-films", "animal-planet-india", "apar-industries", "apnacomplex", "appdynamics-india", "appknox", "apple-productions",
        "arora-fibres", "arrow-india", "aruba-networks", "asit-c-mehta", "aspiration-india", "astrazeneca-india", "atria-broadband", "avast-india",
        "avaya-india", "avaz-inc", "aviva-india", "awfis-cowork", "aws-india", "axis-bank", "axis-direct", "azure-india",
        "baby-oye", "bajaj-allianz", "bajaj-allianz-general", "bajaj-allianz-life", "bajaj-capital", "bajaj-electricals", "bajaj-finserv", "balaji-telefilms",
        "bank-of-baroda", "bank-of-india", "banswara-syntex", "barclays-india", "baroda-bnp-paribas-mf", "bata-india", "baxter-india", "bayer-india",
        "bdtask-technologies", "beautiful-homes", "being-human", "benchmark-electronics", "bewakoof", "bharat-mumbai-port", "bharat-petroleum", "bharti-axa-life",
        "bhilwara-textiles", "bhive-cowork", "big-tv-india", "billdesk", "birlasoft", "bisand-solution", "bit-mascot", "biz4solutions",
        "bloom-consulting", "bloomberg-india", "blue-dart-express", "blue-star", "blue-star-infotech", "blue-yonder", "bny-mellon-india", "bombay-dyeing",
        "bombay-oil-industries", "bombay-rayon", "bonanza-online", "booking-holdings-india", "boston-scientific", "brain-sys", "brainvire-infotech", "broadcom-india",
        "bsnl-mumbai", "btc-software", "busy-infotech", "byjus", "cable-mumbai", "calvin-klein-india", "camp-k12", "canara-hsbc-life",
        "canara-robeco-mutual-fund", "canonical-india", "capgemini-india", "capitalfloat", "cardekho", "care-health-insurance", "careedge", "cartoon-network-india",
        "cartrade", "cash-ki-kamaai", "cashfree", "ccavenue", "celestica-india", "central-bank-of-india", "central-mall", "cfcs-technologies",
        "channel-v", "chargebee", "check-point-india", "choice-equity", "choice-hotels", "chola-finance", "chubb-india", "cipla",
        "cisco-india", "citibank-india", "citiustech", "citrix-india", "city-enterprises", "citymall", "cleartax", "cleartrip",
        "click-labs-india", "cloudflare-india", "clover-infotech", "cnbc-tv18", "cocentrus", "code-brew", "code-bright", "code-district",
        "codebirds", "codeforces", "coder-croods", "coding-ninjas", "coforge", "cognizant", "cohesity-india", "colors-marathi",
        "colors-tv", "comcept-india", "commonfloor", "commvault-india", "computime-india", "concentrix-india", "confluent-india", "conneqt",
        "contiloe-pictures", "convergsys-india", "convrtx-agency", "core-qa-soft", "cosco-sports", "coursera-india", "coverfox", "covr-trading",
        "cowork-studio", "craftsvilla", "creative-eye", "cred", "crestlion", "crif-high-mark", "crisil", "croma",
        "crompton-greaves", "crowdstrike-india", "crown-technologies", "cubix-technologies", "cultfit", "curiousjr", "cybage", "cyber-india",
        "cybereason-india", "cybermedia", "cyblance-technologies", "cyient", "cyient-solutions", "cylance-india", "d-lodha-hotels", "d2h-platform",
        "d4-enterprise", "daffodil-software", "dailyhunt", "darktrace-india", "databricks-india", "datadog-india", "datamatics", "datto-india",
        "daylight-logics", "dcb-bank", "dd-freedish", "decathlon-india", "delhivery", "dell-emc-india", "dell-india", "deloitte-india",
        "dematic-india", "den-networks", "denim-club", "deutsche-bank-india", "dharma-studios", "dhfl-pramerica-life", "dhruva-interactive", "die-soft-system",
        "digital-tv", "dinarys-india", "discovery-india", "dishnetdsl", "dlf-limited", "dmart", "dneg-films", "docker-india",
        "domestic-chains", "doubtnut", "dow-jones-india", "dr-lalpathlabs", "dr-reddys-laboratories", "droom", "druva-india", "dsp-mutual-fund",
        "dtech-solutions", "durian-india", "dynatrace-india", "e-filing-india", "easemytrip", "eb-pearl", "economic-times", "ecstasy-lif",
        "edelweiss", "edelweiss-mutual-fund", "edelweiss-tokio-life", "edwards-lifesciences", "edx-india", "ekta-kapoor", "elastic-india", "elixir-consulting",
        "emids-technologies", "emtec-global", "emudhra", "enterprises-group", "epicor-india", "ericsson-india", "eruditus", "escan",
        "eset-india", "esolve-technologies", "essar-group", "essel-group", "etmoney", "eureka-digital", "eureka-forbes", "evry-india",
        "eweb-india", "excellent-web", "excellis-it", "excitel", "exide-life", "exilant", "exl-service-india", "expensemanager",
        "extreme-networks", "ey-india", "ezeiatech-systems", "ezetap", "f5-networks-india", "fabfurnish", "factset-india", "faircent",
        "famous-studio", "fastly-india", "fastway-transmission", "fbb-india", "fi-money", "fidelity-india", "film-city-mumbai", "films-division",
        "finolex-cables", "fireeye-india", "first-cry", "firstsource", "firstsource-solutions", "fitch-india", "flex-india", "flexiloans",
        "flipkart", "flipkart-furniture", "flying-machine", "focus-softnet", "food-food-india", "fortinet-india", "foxconn-india", "framepool-studio",
        "freecharge", "fresenius-india", "freshworks", "fujitsu-consulting-india", "furniture-inn", "furniturewala", "future-generali", "future-group",
        "fyers", "fyle", "fynd", "fyr-loan", "gaiagen-technologies", "galaxy-broking", "gammon-india", "garden-silk-mills",
        "gcp-india", "ge-healthcare", "genpact-india", "genxtel", "geodesic-technologies", "ghcl-textiles", "giddh", "gigafiber-net",
        "ginger-hotels", "github-india", "gitlab-india", "glaxosmithkline-pharmaceuticals", "glenmark-pharmaceuticals", "global-rax-finance", "glosys-software", "glosys-software-solutions",
        "go-digit", "go-work-india", "godrej-industries-group", "godrej-infotech", "godrej-interio", "goldman-sachs-india", "goldstone-technologies", "goldwin-realty",
        "goodreader", "google-india", "goqii", "grafana-labs", "graffers-id", "grasim-industries", "grass-infotech", "great-eastern-shipping",
        "great-learning", "greyorange", "grid-india", "groww", "gupshup", "guvi", "gyan-trading", "h-and-m-india",
        "hackerrank", "hansal-mehta", "happay", "harbinger-group", "harmonic-india", "hashicorp-india", "hastree-technologies", "hathway",
        "hathway-cable", "havells-india", "hays-india", "hcc-infrastructure", "hcl-bpo", "hcl-technologies", "hdfc", "hdfc-bank",
        "hdfc-ergo", "hdfc-life", "hdfc-life-insurance", "hdfc-mutual-fund", "hdfc-securities", "healthifyme", "helios-global", "hidden-brains",
        "highjump-india", "hike-messenger", "himatsingka-seide", "hindalco", "hinduja-global-solutions", "hindustan-petroleum", "hindustan-times", "hiranandani-group",
        "history-tv18", "hitachi-vantara", "home-first-finance", "home-town", "homecentre", "honeywell-india", "hopscotch-india", "housing-com",
        "hp-india", "hsbc-india", "hsbc-mutual-fund", "huawei-india", "hyatt-india", "hypercity", "iascend-tech", "iball-broadband",
        "ibm-daksh", "ibm-india", "ibm-storage-india", "ibn7", "icici-bank", "icici-direct", "icici-lombard", "icici-prudential-life",
        "icici-prudential-mutual-fund", "icici-securities", "icra", "idbi-bank", "idealake-technologies", "idfc-first-bank", "idfc-mutual-fund", "ienergizer",
        "iffco-tokio", "iglobe-software", "ihcl-taj", "ikonic-technologies", "ikya-human-capital", "ilfs", "incable-tv", "indglobal-digital",
        "india-infoline", "india-tv", "indiahomes", "indiainfoline", "indian-express", "indian-hotel-company", "indifi", "indiqube",
        "indium-software", "indusind-bank", "indusind-nippon-life", "info-ways", "infogain", "infor-india", "infosys", "infrascale-india",
        "inmobi", "innov8-cowork", "innoviti-payments", "innovyze-india", "instamojo", "instarem", "insurtech-india", "integrated-software",
        "intel-india", "intelenet-global-services", "intellibus-technologies", "interviewbit", "intuitive-surgical", "inventum-technologies", "invesco-mutual-fund", "invest-india",
        "inx-media", "iocrest-technologies", "ipca-laboratories", "iqms-india", "irb-infrastructure", "iroid-technologies", "itc-hotels", "ixigo",
        "jabil-india", "jack-jones-india", "jade-global", "jain-amc", "jas-software-services", "jda-india", "jenkins-india", "jet-synth-enterprises",
        "jio-platforms", "jiomart", "johnson-and-johnson-india", "johnson-controls", "joister-broadband", "jpmorgan-india", "jsw-energy", "jsw-group",
        "jsw-steel", "juniper-india", "jupiter-money", "k7-computing", "kale-consultants", "kalpataru-power", "kamats-hotels", "kanaka-soft-solutions",
        "karan-logistics", "karmatech-it", "kaspersky-india", "kec-international", "kellton-tech", "kerry-india", "khadims", "khan-academy-india",
        "kidobot", "kinaxis-india", "kishore-biyani", "kitex-group", "korn-ferry-india", "kotak-mahindra-bank", "kotak-mahindra-general", "kotak-mahindra-life",
        "kotak-mahindra-mutual-fund", "kotak-securities", "kpit", "kpit-technologies", "kpmg-india", "kpr-mill", "kraft-digital", "kratee-technology",
        "krber-india", "kreate-cowork", "kreditbee", "kubernetes-india", "lab-easy", "laguna-hotels", "larsen-and-toubro", "larsen-toubro-heavy",
        "larsen-toubro-infotech", "leecooper", "lemontree-hotels", "lendenclub", "lendingkart", "lentra-fintech", "levis-india", "lg-india",
        "liberty-general", "liberty-shoes", "lic-housing-finance", "lic-india", "lic-of-india", "lido-learning", "lifestyle-homes", "lifestyle-india",
        "limeroad", "linkedin-india", "linkedin-learning", "lnt-technology-services", "locus-sh", "lodha-group", "loksatta-tv", "loop-mobile",
        "loyal-textile-mills", "lt-technology-services", "ltimindtree", "lugan-technologies", "lumina-technologies", "lupin-limited", "lybrate", "m-phasis-bpo",
        "machines-sports", "madh-film-city", "magicbricks", "magma-hdi", "magna-infotech", "maharashtra-channel", "mahindra-and-mahindra", "mahindra-and-mahindra-financial-services",
        "mahindra-group", "mahindra-holidays", "majesco", "makemytrip", "mango-india", "manhattan-associates", "marico", "marks-spencer-india",
        "marlabs", "marriott-india", "mastek", "master-trust", "masterclass-india", "maths-works", "max-fashion", "max-life-insurance",
        "maza-tv", "mcafee-india", "medianet-technologies", "medtronic-india", "meesho", "mercator-lines", "merck-india", "meru-cabs",
        "meta-india", "metro-networks", "metro-shoes", "mettl", "mfine", "michael-page-india", "microland", "microsoft-india",
        "mid-day", "mindtree", "mir-software", "mirae-asset-mutual-fund", "mk-tv", "mob-max", "mob-max-technologies", "mobatia-technologies",
        "mobikasa-inc", "mobili-technologies", "mobiloitte-technologies", "mobiweb-technologies", "mobiwik", "moksh-broadband", "moneygram-india", "moneypalm",
        "mongodb-india", "monocept-pvt", "moodys-india", "morarjee-textiles", "morgan-stanley-india", "morningstar-india", "motilal-oswal", "motilal-oswal-mutual-fund",
        "mphasis", "mphasis-an-mpower", "mphasis-bpo", "mswipe", "mtnl-india", "mtv-india", "mufti", "mumbai-film-company",
        "my-ally-technologies", "myinsuranceclub", "myntra", "narrative-nest", "nat-geo-india", "national-insurance", "navneet-education", "ncc-limited",
        "ndtv-india", "neela-film", "neelkanth-group", "nerdappslabs", "nerdgeek-lab", "netapp-india", "netclues-india", "netcore-cloud",
        "netmeds", "netplus-broadband", "nets-international", "netscout-india", "network18-broadcast", "neuronimbus-software", "new-india-assurance", "new-relic-india",
        "news-laheri", "news18", "nex-gen", "nexevo-technologies", "nihilent", "nilesh-software", "nilson-group", "nimap-infotech",
        "nippon-india-mutual-fund", "niva-bupa", "nivia-sports", "niyo", "noboru-technologies", "nobroker", "nokia-siemens-india", "nomura-india",
        "northern-trust-india", "nortonlifelock", "novartis-india", "novo-home", "ntt-data-payment-services", "nucleus-software-exports", "nutanix-india", "nuvama",
        "nvidia-india", "nykaa", "o-zone-solutions", "o9-solutions", "oberoi-hotels", "observe-ai", "ocean-techlab", "ofs-technologies",
        "okta-india", "ola", "omninos-solutions", "onward-technologies", "open-financial-technologies", "open-wave-technologies", "optimystix", "oracle-cloud-india",
        "oracle-financial-services-software", "orange-business", "orange-business-services-india", "orange-soft", "orient-electric", "oriental-insurance", "ownbackup-india", "oxigen-wallet",
        "paisabazaar", "palo-alto-networks-india", "pamten-group", "pantaloons", "paragon-india", "park-hyatt", "park-plaza-india", "patni-computer-systems",
        "paymate", "paynearby", "paytm", "payworld", "payzapp", "pegatron-india", "pelatro-pvt", "penser-consulting",
        "pentagon-info", "pepe-jeans", "pepperfry", "peps-industries", "persistent-systems", "pfizer-india", "pgim-india-mutual-fund", "pharmeasy",
        "philips-india", "phonepe", "physics-wallah", "pii-india", "pine-labs", "piramal-enterprises", "piramal-group", "piramal-pharma",
        "piramal-realty", "pixion-studios", "planet-marathi", "pluralsight-india", "pogo-tv", "policybazaar", "polycab-india", "pondy-oxygen",
        "postman", "prabhudas-lilladher", "practo", "pragmat-soft", "prakash-textiles", "pramerica-life", "pravici-technologies", "praxis-home-retail",
        "precot-meridian", "prime-focus", "programmers-inc", "prokshan-technologies", "prometheus-india", "propstack", "pulse-technologies", "pulseplay",
        "pure-storage-india", "pwc-india", "qad-india", "qat-americas", "qualcomm-india", "quant-mutual-fund", "quess-corp", "quick-heal",
        "quickbooks-india", "quizlet-india", "quy-technology", "r-s-software", "radisson-india", "raheja-qbe", "railwire-india", "ramanand-sagar",
        "ramco-systems", "ramoji-mumbai", "randstad-india", "rao-software", "razorpay", "rbl-bank", "rdv-tech", "red-chillies-studio",
        "red-hat-india", "redian-software", "rediff", "rel-gsm-india", "relaxo-footwear", "reliance-broadcast", "reliance-communications", "reliance-digital",
        "reliance-footprints", "reliance-general", "reliance-industries", "reliance-nippon", "reliance-nippon-life", "reliance-retail", "reliance-securities", "reliance-trends",
        "relig-technologies", "remitly-india", "republic-tv", "reuters-india", "revolve-soft", "revolve-solutions", "rgv-systems", "riddhi-interactive",
        "riverbed-india", "robosoft-technologies", "roche-india", "rockwell-automation", "rose-movies", "route-mobile", "royal-sundaram", "rpg-group",
        "rts-inc", "rubicon-research", "rubrik-india", "ruckus-india", "runwal-group", "rustomjee-group", "s-and-p-india", "saam-tv",
        "sab-tv", "sadhav-engineering", "sagar-films", "salesforce-india", "samasys-technologies", "samco-securities", "samsung-india", "sangam-india",
        "sankalp-it", "sanmina-india", "sap-india", "sap-labs-india", "sas-institute", "sasken", "sasken-technologies", "sattrix-information",
        "sattva-group", "savantis-solutions", "saw-networks", "sbi-general", "sbi-general-insurance", "sbi-life", "sbi-life-insurance", "sbi-mutual-fund",
        "sbi-securities", "sbm-bank-india", "scaler-academy", "schneider-electric", "scindia-steam", "scotwood-industries", "scripbox", "sdrc-software",
        "seleqtions-hotels", "seqrite", "sequoia-it", "serco-bpo", "serole-technologies", "servicenow-india", "servion-global", "serwizsol",
        "setu", "sg-cricket", "shaligram-infotech", "sharechat", "sharekhan", "sheth-group", "shipping-corporation-of-india", "shiprocket",
        "shopclues", "shoppers-stop", "shriram-finance", "shriram-mutual-fund", "siemens-healthineers", "siemens-india", "sify-technologies", "signity-solutions",
        "signzy", "simplex-infrastructure", "simplilearn", "siri-innovations", "sitel-india", "siti-cable", "siticable-den", "sketchcart",
        "skillshare-india", "sleepwell", "smallcase", "snapdeal", "snowflake-india", "sofmen-technologies", "soft-tec-systems", "softway-solutions",
        "solace-infotech", "sonata-software", "sony-broadcast", "sony-marathi", "sony-tv", "sophos-india", "source-soft-solutions", "southern-technology",
        "sp-global-india", "spectra-broadband", "spectral-consultants", "sphere-origins", "sphinx-solution", "spinny", "splendid-technologies", "splitwise-india",
        "splunk-india", "spykar", "sq-like", "squareyards", "standard-chartered-india", "stanley-lifestyles", "star-broadcast", "star-plus",
        "star-pravah", "star-union-dai-ichi", "stark-digital", "startek-india", "state-bank-of-india", "store-apps", "stream-global", "stryker-india",
        "subex", "subex-limited", "suffescom-solutions", "sumo-logic-india", "sun-direct", "sun-pharmaceuticals", "sundaram-mutual-fund", "superdry-india",
        "supernet-india", "surf-side-technologies", "suse-india", "sutherland-global", "sutlej-textiles", "svapna-software", "svp-infotech", "swastik-investmart",
        "swastik-productions", "swiggy", "symantec-india", "symphony-fintech", "synchronoss-india", "synkron-international", "systango-technologies", "systenics-solutions",
        "systweak", "taj-hotels", "tally-solutions", "tapas-technologies", "tata-aia-life", "tata-aig", "tata-communications", "tata-consultancy-services",
        "tata-docomo", "tata-elxsi", "tata-interactive-systems", "tata-investment-corp", "tata-mutual-fund", "tata-play", "tata-projects", "tata-sky",
        "tata-tech", "tata-teleservices", "tatacliq", "tavisca-solutions", "td-store", "teamlease", "tech-hive-solutions", "tech-mahindra",
        "tech-mahindra-bpo", "tech-now-solutions", "tech-one-global", "tech-spiders", "technobase-it", "technovert-technologies", "techprocess", "techugo-pvt",
        "tejaras-infotech", "tekion-india", "teksystems-india", "teleperformance-india", "terumo-india", "texas-instruments-india", "the-ace-limited", "the-hive",
        "the-hive-cowork", "the-leela", "the-ninehertz", "the-tech-hub", "think-owl", "thyrocare", "tieten-media", "tiez-technologies",
        "tigris-mobility", "tikona-infinet", "times-group", "times-now", "times-of-india", "tlc-india", "tolani-shipping", "tommy-hilfiger-india",
        "toppr", "torrent-pharmaceuticals", "total-environment", "tour-de-world", "tradebulls", "transcom-india", "transfergo-india", "transunion-cibil",
        "travelxp-india", "tree-sizing-institute", "trend-micro-india", "trent", "trident-group", "tridhya-tech", "trigma-solutions", "trivago-india",
        "true-sky-technologies", "truesense-pixels", "trunkoz-technologies", "trust-care-technology", "tunedtech-solutions", "turing-technologies", "turtlemint", "tv-18",
        "tv9-marathi", "uber-india", "ubs-india", "ucb-india", "udemy-india", "ugcable", "ugro-capital", "ultimez-infotech",
        "ultratech-cement", "ums-technologies", "unacademy", "uni-mutual-fund", "uniblue-india", "unichem-laboratories", "unified-solution", "union-bank-of-india",
        "uniphore", "unisoft-infotech", "unit4-india", "united-colors-of-benetton", "united-india-insurance", "universal-sompo", "upgrad", "upstox",
        "urban-company", "urban-ladder", "usquare-soft", "usv-limited", "uti-mutual-fund", "utv-software-india", "v-india", "v-mart",
        "v2s-technology", "vakrangee-limited", "validus-it-services", "value-labs", "value-vibe", "van-heusen", "vantage-securities", "vascon-engineers",
        "vates-india", "vedantu", "veem-india", "vembu-technologies", "ventura-securities", "veritas-india", "verloop", "verves-technologies",
        "vfx-records", "viasat-india", "vibes-software", "vichara-technologies", "victorie-software", "videocon-d2h", "vijay-sales", "vinayak-films",
        "vipha-tech-solutions", "virenxia-technologies", "virtual-agent", "virtue-analytics", "vishal-bhardwaj", "vision-tech-solutions", "visual-infotech", "vivanta-hotels",
        "vivid-infotech", "vmware-india", "vodafone-idea", "vodafone-india", "vora-ventures", "vxrail-india", "w-for-woman", "wakefit",
        "walnut-app", "wardha-textiles", "watchguard-india", "wavelabs-technologies", "wealth-clinic", "web-forest-solutions", "web-systems-solutions", "webcontxt-technologies",
        "webdunia-internet", "webo-bytes", "webward-technologies", "wells-fargo-india", "welspun-group", "welspun-textiles", "western-union-india", "westlife-foodworld",
        "westside", "wework-india", "whitehat-jr", "whiz-technologies", "wifi-dabba", "wildnet-technologies", "wipro", "wipro-bpo",
        "wise-india", "wistron-india", "wits-technologies", "wizard-communications", "wiztech-solutions", "wns-global-services", "wockhardt", "womentech-firm",
        "wonder-tel", "wonderla", "woodies-furniture", "workday-india", "workgem-information", "worldline-india", "worldremit-india", "xavient-digital",
        "xenautom-technologies", "xencia-technology", "xenon-technologies", "xlogix-solutions", "xoriant", "xplore-intellect", "xylon-tech-solutions", "yash-raj-studios",
        "yatra", "yellow-ai", "yes-bank", "yotta-data-services", "you-broadband", "you-encode", "yudiz-solutions", "zaptech-solutions",
        "zapvi", "zara-india", "zebra-technologies", "zee-broadcast", "zee-labs", "zee-marathi", "zee-news", "zee-tv",
        "zen3-infotech", "zensar", "zensar-technologies", "zentek-technologies", "zeoob-india", "zerodha", "zinnov", "zion-technologies",
        "zivame", "zoho-books", "zoho-corporation", "zomato", "zopper", "zorex-technologies", "zscaler-india", "zte-india",
        "zudio", "zydus-cadila", "zygzag-solutions",
    ],
    "ncr": [
        "1mg", "99acres", "a-one-bpo", "a10-networks-india", "abb-india", "abbott-india-software", "acko", "adani-group",
        "aditya-birla-group", "adobe-india", "aggrandize", "agilus-diagnostics", "agoda-india", "aibono", "airbnb-india", "aircel",
        "airtel-digital-tv", "ajio", "akamai-india", "akzonobel-india", "alcatel-lucent-nokia-india", "alkem-laboratories", "alpha-ai", "alteryx-india",
        "altran-india", "amar-ujala", "amazon-india", "amazon-prime-video-india", "american-express-india", "amkette", "amo-labs", "analog-devices-india",
        "angel-one", "ansys-india", "antenna-labs", "anthropic-india", "aon-india", "apna", "apna-uploads", "apollo-hospitals",
        "apollo-tyres", "apple-india", "applied-materials-india", "appsecco", "apptio-india", "aptech", "arista-networks-india", "arm-india",
        "arre-banner", "asml-india", "astrazeneca-india", "atos-india", "atria-convergence-technologies", "aujas-networks", "aurionpro", "autodesk-india",
        "avaya-india", "avenues", "aws-india", "axilor-ventures", "axis-bank", "axis-max-life-insurance", "bajaj-allianz", "bajaj-auto",
        "bajaj-group", "bank-of-america-india", "barclays-india", "basf-india", "baxter-india", "bayer-india", "beat-music", "berger-paints",
        "bewakoof", "bharat-biotech", "bharat-broadband-network", "bharat-forge", "bharti-airtel", "bharti-enterprises", "bharti-infratel", "bigbasket",
        "billdesk", "bio-quest", "birlasoft", "blinkit", "bls-international", "blue-star-infotech", "bluedart-india", "blueinfy",
        "blusmart", "bonzai-ai", "booking-com-india", "bosch-india", "bounce", "box8", "brain-waves", "brian-waves",
        "bsnl", "budget-card", "build-crest", "burrp", "byjus", "bytes-sdk", "cadence-india", "cafe-coffee-day",
        "cam-pus-hash", "cambridge-integra", "canara-hsbc-life-insurance", "capgemini-india", "capitalfloat", "capitoline-services", "carbon-black-india", "cardekho",
        "career360", "carzonrent", "cashfree", "cashify", "cashkaro", "ccavenue", "ceat-limited", "centre-for-railway-information-systems",
        "chargebee", "checkpoint-india", "chingari", "chola-mandalam", "cipla", "cisco-india", "citibank-india-hq", "cityflo",
        "clari5", "cleartax", "cleartrail", "cleartrip", "clevertap", "cliq-tv", "clodura", "cloud-tail",
        "cloudera-india", "cloudflare-india", "cmc-limited", "cnn-news18", "co-pack", "codeninjas", "coforge", "cognizant-india",
        "college-dunia", "collibra-india", "colors-tv", "commonfloor", "commvault-india", "comviva", "concentrix-india", "confluent-india",
        "container-corporation-of-india", "coredge", "corover-ai", "cosece", "coupon-dunia", "coursera-india", "coverfox", "cred",
        "credit-suisse-india", "crese", "crop-in", "crowdstrike-india", "curefit", "cyberoam-india", "cyberops", "cyient",
        "cylance-india", "d-link-india", "dabur", "dailyhunt", "dainik-bhaskar", "data-axon", "data-robo", "databricks-india",
        "dataiku-india", "datamatics", "datarobot-india", "dataweave-digital", "de-code", "deep-tech-ai", "deepmind-india", "del-emc-india",
        "delhivery", "deliver-the-purpose", "dell-india", "deloitte-india", "den-networks", "designcafe", "deutsche-bank-india", "dhani",
        "dharampal-satyapal-group", "dharma-productions", "dhl-india", "dhruva-interactive", "diatoz", "diebold-nixdorf-india", "digi-pay", "digicert-india",
        "digit-insurance", "digital-impulse", "diodelabs-india", "discovery-communications-india", "dish-tv", "divi-labs", "dixo-technologies", "dlf-group",
        "dotpe", "doubtnut", "dow-india", "dr-lal-pathlabs", "dr-reddys-laboratories", "dream11", "droom", "dunzo",
        "dupont-india", "dxc-technology", "e-digi-safe", "e-shophub", "ea-india", "easemytrip", "eatfit", "ebay-india",
        "eckvation", "eclerx", "edelweiss", "educomp-solutions", "efftronics", "eicher-motors", "ekg", "emami",
        "emerson-india-software", "enabling-sale", "engage-talent", "engineers-india", "entrackr", "entrans", "entrust-india", "ericsson-india",
        "eros-now-delhi", "eset-india", "espn-india", "essar-group", "esym", "et-money", "eternal-limited", "exlservice-india",
        "exotel", "expedia-india", "expertus", "extreme-networks-india", "ey-india", "eze-ai", "eze-logistics", "ezetap",
        "f1tech", "f5-networks-india", "faasos", "fabfurnish", "fabhotels", "fasal", "fasalt-foods", "fastly-india",
        "fedex-india", "fibe", "fibrecom-india", "fireeye-india", "firm-floor", "firstcry", "firstsource", "fis-global-india",
        "fiserv-india", "flex-solutions", "flipkart", "flo", "foradian", "forte-india", "fox-sports-india", "fractl-analytics",
        "freecharge", "freeflow", "freshmeal", "freshtotable", "freshworks", "fujitsu-consulting-india", "furlenco", "fusioncharts",
        "future-generali", "future-group", "fyle", "fynd", "gaana", "games-24x7", "gametion", "gamezop",
        "gaming-monk", "gati-delhi", "ge-digital", "ge-healthcare-india", "genpact", "geogo", "geojit-financial", "gitlab-india",
        "glaxosmithkline-india", "glenmark-pharmaceuticals", "global-logic-india", "global-sign-india", "global-sources-india", "globallogic-india", "gmr-group", "godrej-enterprises-group",
        "godrej-interio", "goibibo", "goldman-sachs-india", "google-cloud-india", "google-india", "gr-group", "gradeup", "great-learning",
        "grofers", "groww-delhi", "h20-ai-india", "haargaz", "harbinger-knowledge-products", "harley-davidson-india", "hathway", "haven-space",
        "hawells", "hcl-group", "hcl-healthcare", "hcl-infosystems", "hcltech", "headdigital-works", "health-plix", "health-track",
        "healthians", "healthifyme", "healthkart", "helion-technologies", "hero-fincorp", "hero-motocorp", "hexaware", "hfcl",
        "hfs-group", "hierarchy", "high-level-tree", "hindalco-industries", "hindustan-times", "hirdaramani", "hitachi-india", "hivemind",
        "hiver", "home-shop-18", "homelane", "honeywell-india", "hotstar", "housejoy", "housing-com", "hov-r",
        "howzat", "hp-inc-india", "hsbc-india", "hsbc-technology-india", "ht-media", "huawei-india", "human-machine", "hungama",
        "hyundai-motor-india", "i-kno", "iac-india", "iamwire", "iba", "ibibo", "ibm-cloud-india", "ibm-consulting-gurgaon",
        "ibm-india", "icici-bank", "icici-lombard", "icra-limited", "idea-cellular", "ienergizer", "ihs-markit-india", "iitpl",
        "ilant", "imbesharam", "in-shorts", "inc42-india", "incuspate", "india-today-group", "india-tv", "indiabulls",
        "indiacom", "indiainfoline", "indialends", "indiamart", "indian-express", "indian-oil-corporation", "indiaplaza", "indiatimes-shopping",
        "indigo", "induna", "indus-indus-international", "indus-towers", "infineon-india", "infinium", "info-edge", "infoblox-india",
        "informatica-india", "infosys", "infosys-bpm", "infosys-consulting", "inpage", "inshorts", "instamojo", "intel-india",
        "intellicus", "interakt", "interviewbit", "intex-technologies", "intuit-india", "inventiva", "investruck", "invisible-break",
        "invisk-matrix", "iorm-soft", "ip-infusion", "iqvia-india", "iris-software", "iseck", "isobar-india", "iti-limited",
        "itv-network", "ix-mobile", "ixigo", "iyogi", "jack-henry-india", "jagran-prakashan", "jaypee-group", "jet-synthesys",
        "jio", "jio-financial-services", "jio-mart", "jio-saavn-delhi", "johnson-controls-india", "johnson-johnson-india", "josh", "joy-foods",
        "jpmorgan-chase-india", "jsw-mg-motor-india", "jubilant-foodworks", "jublian-bhartia-group", "jumbotail-delhi", "junglee-games", "juniper-networks-india", "justdial",
        "k-seven", "k7-computing", "kalyani-group", "karbonn-mobiles", "kashware", "kaspersky-india", "kayako", "kellton",
        "ken-research", "keysight-technologies-india", "kinara-capital", "king-delhi", "kla-tencor-india", "knowlarity", "koo", "koovs",
        "kotak-mahindra-old-mutual-life", "kpit-technologies", "krbl", "kreditbee", "kreeda-games", "krishi-net", "kuvera", "kwan-entertainment",
        "l-t-technology-services", "lakshya-digital", "lam-research-india", "landmark-bookstores", "larsen-toubro", "latice-semiconductor", "lava-international", "lead-squared",
        "leegality", "leher", "lendkart", "lenskart", "leverage-edu", "lg-soft-india", "liberty-shoes", "licious",
        "light-metrics", "lightricks-india", "limeroad", "lionbridge-india", "little-app", "living-media-india", "livspace", "loadshare-technologies",
        "loco-gaming", "logi-tech-internal", "logix-group", "loop-mobile", "lti-mindtree", "ltimindtree", "luminous-power-technologies", "lupin",
        "luxor", "lybrate", "mad-street-den", "magicbricks", "magicpin", "mahindra-group", "mahindra-satyam", "makaan-com",
        "makemytrip", "mango-pay", "manipal-cigna", "map-r-india", "mappa", "marico", "mars-col", "marsh-mclennan-india",
        "masai-school", "mastercard-india", "mathco", "mathworks-india", "max-group", "max-healthcare", "max-life", "max-linear-india",
        "mcafee-india", "mccann-erickson-india", "mckinsey-india", "mdas", "mebelkart", "medanta", "meddo-cures", "media-net",
        "medikabazar", "medlife", "medtronic-india", "meesho", "mentor-graphics-india", "merakilearn", "merck-india", "meru-cabs",
        "meta-ai-india", "metlife-india", "mfine", "micromax-informatics", "micron-technology-india", "microsoft-azure-india", "microsoft-india", "miditech",
        "mighty-beast", "milkbasket", "mind-soul", "mindtree-soul", "miniclip-india", "minicorn", "mitsubishi-india", "mobikwik",
        "modern-food-industries", "moengage", "monexo", "money-tap", "moneytap", "monsoon-multimedia", "moravia-india", "morgan-stanley-india",
        "mother-dairy", "motilal-oswal", "movie-plus", "mphasis", "mtnl", "mtv-india", "murugappa-group", "muscle-blaze",
        "mygate", "myles", "myntra", "myoperator", "myupchar", "nagarro-gurgaon", "national-geographic-india", "national-insurance",
        "naukri-com", "nazara-technologies", "ncr-corporation-india", "ndtv", "nearbuy", "nearche", "nec-india", "neofusion",
        "neogrowth", "neoreus", "ness-digital-engineering", "net-square", "netapp-india", "netflix-india", "netmeds-delhi", "netskope-india",
        "neuro-360", "news-24", "news18", "next-wave-multimedia", "nextra-broadband", "niit", "nirapara", "nirvana",
        "niva-bupa", "niyo-solutions", "nobroker", "nomura-india", "nopaperforms", "novartis-india", "novatium", "novo-nordisk-india",
        "novopay", "npci", "nspcl", "ntt-data-india", "nube-tech", "nubox-games", "nucleus-software-exports", "nukebox-games",
        "nutanix-india", "nvidia-india", "nxp-semiconductors-india", "nykaa", "ogilvy-india", "oil-and-natural-gas-corporation", "okta-india", "okwin",
        "ola-cabs", "ola-consumer", "olx-india", "omc-power", "one97-communications", "onescore", "onespace", "onmobile",
        "onsemi-india", "open-ai-india", "opent-ext", "optic-fiber", "oracle-cloud-india", "oracle-financial-services", "oracle-india", "orange-business-services-india",
        "orbit-tech", "ossics", "otis-india", "outlook-group", "oxyzen", "oyo-rooms", "ozrit", "p-india",
        "paladion", "paladion-networks", "palantir-india", "palo-alto-networks-india", "panacis-network", "panasonic-india", "parle-products", "patanjali-ayurved",
        "path-finder", "patni-computer-systems", "payfone", "paynear", "payout", "paypal-india", "paytm", "paytm-money",
        "paytm-payments-bank", "pepperfry", "persistent-systems", "pfizer-india", "pharmeasy-delhi", "phich-fusion", "philips-india", "phonepe-delhi",
        "phonon-communications", "physics-wallah", "pine-labs", "pixis", "planet41", "plush-care", "pocket-aces", "policybazaar",
        "polyplex", "postman", "ppg-india", "practo", "preapp-studios", "primus-techno", "prism-financial", "prism-health",
        "prism-medical", "projects-and-development-india", "promantia", "proofpoint-india", "prop-sup", "prop-times", "propstory", "protean-egov",
        "proximity-labs", "prudential-india", "publicis-sapient-india", "punj-loyd", "pure-storage-india", "pvr-inox", "pwc-india", "qap-are-ra",
        "qualcomm-india", "quick-heal", "quikr", "quova-ai", "r-techno-works", "railtel", "rakuten-india", "ramco-systems",
        "ranbaxy-laboratories", "rang-de", "rapido", "raymond-group", "razorpay-delhi", "rcn-networks", "reachivy", "readwhere",
        "redbus", "redcliffe-lifeline", "rediff-com", "reli", "reliance-digital", "reliance-general", "reliance-group", "reliance-jio-platforms",
        "renesas-india", "renesss-india", "renew-energy-global", "renewbuy", "revv", "ringing-bells", "rivigo-delhi", "rocdocs",
        "roche-india", "rockstar-india", "rockwell-automation-india", "rocweb", "rohde-schwarz-india", "ropedancer", "ropevin", "route-mobile",
        "rp-sanjiv-goenka-group", "rpg-group", "rsystems", "rubique", "s-p-global-india", "s-tel", "s-terra", "saankhya-labs",
        "sagacious-research", "sakha-consulting", "salaryfits", "salesforce-india", "salesque-note", "samsung-india-software-centre", "samsung-networks-india", "samsung-r-and-d-institute-india",
        "samvardhana-motherson", "sanofi-india", "sap-labs-india", "sas-institute-india", "sasken", "sasken-technologies", "sattrix", "satya-paul",
        "scaler", "scenera", "schneider-electric-india", "scholarship-bent", "schoolnetindia", "scout-op", "seagate-india", "seed-net",
        "semi-otx", "semiotx", "semtech-india", "seniority", "seniority-ville", "septeo-india", "serco-india", "serum-institute-of-india",
        "servicenow-india", "shadowfax", "sharechat", "sharekhan", "sheer-ai", "sheru-classic", "shiksha", "shiprocket",
        "shopclues", "shopify-india", "shoppers-stop", "shuttl", "siemens-india", "siera-networks", "sify-technologies", "signalchip",
        "signzy", "silicon-bio", "silicon-labs-india", "simplilearn", "sinhasoft", "siti-networks", "skylark-labs", "skyscanner-india",
        "slice", "smallcase", "snapdeal", "snowflake-india", "social-indiya", "soha-life", "sonata-software", "sony-entertainment-india",
        "sony-india", "sonyliv-delhi", "sophos-india", "sp-sys", "sparta-gaming", "spectra-broadband", "spice-money", "spicejet",
        "spinny", "spirent-india", "spitzeen", "sporty-beat", "spoton", "spsoft", "square-yards", "srf-limited",
        "standard-chartered-india", "star-india-delhi", "star-sports-india", "startek", "startek-india", "stay-unis", "sterlite-technologies", "stmicroelectronics-india",
        "strand-life-sciences", "strategic-petroleum-reserve", "study-nation", "stylumia", "su-kam-power-systems", "subex", "subhasri-tech", "sulekha",
        "sumago-infotech", "sun-nxt", "sun-pharma", "sun-tv-delhi", "sutherland-global", "sutherland-global-india", "suzlon", "suzuki-motorcycle-india",
        "swiggy-delhi", "symantec-broadcom-india", "synopsys-india", "t-series", "t-sys", "t-systems-india", "tableau-india", "talend-india",
        "talentedge", "tally-solutions", "tanla-platforms", "tata-1mg", "tata-aig", "tata-cliq", "tata-communications", "tata-consultancy-services",
        "tata-docomo", "tata-group", "tata-interactive-systems", "tata-power-delhi", "tata-power-solar", "tata-research-development-and-design-centre", "tata-teleservices", "tax-raja",
        "tcs-bpo", "tech-avis", "tech-mahindra", "tech-ready", "tejas-networks", "teleperformance-india", "teradyne-india", "testbook",
        "tex-corp", "texas-instruments-india", "the-24x7", "the-new-india-assurance", "the-office-pass", "the-print", "the-sleep-company", "theoberoi-group",
        "thermax", "thethoughtworks", "think-merge", "thriver-travel", "times-internet", "times-music", "timesjobs", "tira",
        "tolfee-stud", "toppr", "torus-network", "toshiba-india", "tradeindia", "tradex", "transperfect-india", "transport-corporation-of-india",
        "travel-tripper", "trc-sc", "treebo", "trell", "trend-micro-india", "tripoto", "triveni-engineering", "true-diet",
        "trunkoz", "tulip-telecom", "turedra", "turing-cloud", "tux-care", "tv-s-motor-company", "tv18", "tv9-india",
        "tv9-network", "ubisoft-india", "ubs-india", "udacity-india", "unacademy", "uni", "unicommerce", "unisys-india",
        "united-india-insurance", "uno-minda", "up-school", "upgrad", "ups-india", "upskill-zenith", "upstox", "uptron",
        "urban-company", "urban-ladder", "urban-mass-transit-company", "usharma", "ust-global", "utv-india", "v-con", "v-metric",
        "valdel", "valdel-corporation", "vamaship", "varun-beverages", "vayudhoot", "vedantu", "veeam-india", "veritas-india",
        "viacom18-delhi", "videocon-group", "videocon-telecom", "vijay-solutions", "vious-technologies", "visa-india", "vistara", "viva-connect",
        "vmware-india", "vodafone-idea", "vodafone-india", "voonik", "voot-an", "voyants-india", "vrio-corp", "vvdn-technologies",
        "vwo-split", "wadia-group", "wakefit", "wayfair-india", "web18", "webengage", "wego-india", "weguard-tech",
        "wells-fargo-india", "welocalize-india", "welspun-living", "western-digital-india", "what-s-hunting", "whatfix", "white-p", "white-plains",
        "whitehat-junior", "willis-towers-watson-india", "winzo-games", "wipro", "wipro-bpo", "wiz-mart", "wns-cx", "wns-global",
        "workday-india", "wot-not-sales", "wunderman-thompson-india", "wynk-music", "xebia-india", "xerox-india", "xilinx-india", "xiphera",
        "xolo", "xpressbees", "y-pay", "yahoo-india", "yali-aerospace", "yatra", "yebhi", "yepme",
        "yokogawa-india", "yoomoney", "yourstory-india", "youtube-india", "yu-televentures", "yulu", "yupptv", "zapak",
        "zappfresh", "zarget", "zee-media-delhi", "zee-music", "zee-news", "zee5", "zeel-delhi", "zelta-ai",
        "zensar-technologies", "zentech-systems", "zepto", "zerodha-delhi", "zest-money", "zeta", "zetta-gyro-gear", "ziffy-tech",
        "zillow-india", "zivame", "zoho-corporation", "zoho-india", "zomato", "zoomcar", "zostel", "zscaler-india",
        "zte-india", "zubaan-books", "zydus-lifesciences", "zydus-wellness", "zync-global", "zypp-electric",
    ],
    "pune": [
        "3i-infotech", "accelya-kale", "accenture", "accolite-digital", "aditi-technologies", "adobe", "agilesolutions", "airbus-group-india",
        "alef-software", "allegis", "altair-engineering", "alten-calsoft", "altimetrik", "altran", "altran-india", "amdocs",
        "anheuser-busch", "antuit-ai", "appdirect", "appfoster", "appian", "applied-materials", "appmantech", "aptean",
        "aricent", "arista-networks", "arvato-systems", "aspect-software", "asteria", "atos-syntel", "au-small-finance-bank", "aurionpro-solutions",
        "autodesk", "avaya", "avizva", "azilen-technologies", "bajaj-auto", "bajaj-finserv", "barclays", "basf",
        "bay-watch-capital", "becton-dickinson", "bentley-systems", "bharat-forge", "bharat-heavy-electricals", "bharti-airtel", "bharti-axa", "biocon",
        "birlasoft", "bitwise-solutions", "blize", "blue-pencil", "blueshift", "bmc-software", "bny-mellon", "bosch",
        "boston-analytics", "boston-scientific", "botree-software", "bpc-india", "bridgei2i", "brightcom-broadband", "bristlecone", "broadcom",
        "browserstack", "c-dac", "cadence-design-systems", "calsoft", "capgemini", "capital-numbers", "car-dekho", "carbon-black",
        "cbre", "cerner", "cgi-group", "chargebee", "chevron", "ciber", "cisco", "citi",
        "citius-tech", "clariant", "clover-infotech", "cognam-technologies", "cognizant", "collabera", "commvault", "compucom",
        "computacenter", "comviva", "continental", "copeland", "corecompete", "corning", "coupa", "cox-automotive",
        "cpa-global", "crestdatalabs", "crif-high-mark", "crowdstrike", "cummins", "cybage", "cyient", "darwinbox",
        "datamatics", "de-shaw", "deere", "delphi-auto", "delta-electronics", "dematic", "denso", "dessault-systemes",
        "detroit-diesel", "dialog-semiconductor", "dilijent-systems", "dlink", "dnv-gl", "drdo", "druva", "dxc-technology",
        "dyte", "ebix", "ebizon", "edifecs", "egain", "egen-solutions", "elder-pharmaceuticals", "electrolux",
        "electronic-arts", "elxsi", "emcure-pharmaceuticals", "emids", "enphase-energy", "epam-systems", "epicor", "equifax",
        "equinix", "ericsson", "esab", "esds", "esko", "evalueserve", "evosim", "evry",
        "exela-technologies", "exotel", "experian", "extramarks", "ey", "ezetap", "f5-networks", "factset",
        "federal-bank", "fiat-chrysler", "fico", "fidelity", "fiserv", "flextronics", "flipkart", "flytxt",
        "forbes-marshall", "ford", "forgerock", "fortinet", "fractal-analytics", "fresenius", "freshworks", "fujitsu",
        "games24x7", "garmin", "gavs-technologies", "ge-healthcare", "genpact", "geometric-software", "gep", "giva-software",
        "glaxosmithkline", "gm-technologies", "godrej-infotech", "goldman-sachs", "google", "groww", "gsk", "gupshup",
        "happiest-minds", "hapsody-infotech", "haptik", "harbinger-group", "harman", "hcl", "hcl-technologies", "hdfc-bank",
        "hella", "hero-motocorp", "hewlett-packard-enterprise", "hexagon", "hexaware", "hitachi-consulting", "hitachi-vantara", "hotwax-systems",
        "hsbc", "hyland-software", "ibm", "icertis", "idexcel", "igenomi", "ignite-world", "impetus-infotech",
        "indiamart", "indium-software", "indusface", "infogain", "infor", "informatica", "infostretch", "infosys",
        "instamojo", "instem", "intas-pharmaceuticals", "intel", "intelectron", "investcorp", "ipan-technologies", "isolve-technologies",
        "itc-infotech", "itcube", "jabil", "jaguar-land-rover", "jio-platforms", "john-deere", "johnson-controls", "jp-morgan",
        "kale-software", "kellton-tech", "keyence", "keyloop", "knorex", "kpit-technologies", "l-t-infotech", "l-t-technology-services",
        "landmark-group", "latentview", "lava-international", "leaptodigital", "leidos", "leostream", "lexmark", "lg-electronics",
        "lg-soft-india", "licious", "linkgroup", "litmus7", "livspace", "lockheed-martin", "loginext", "logitech",
        "loktra", "lowes", "lucid-software", "lumileds", "maersk", "magna", "mahindra-and-mahindra", "mahindra-logistics",
        "majesco", "makemytrip", "manhattan-associates", "mann-hummel", "marico", "marriott", "marvell-semiconductor", "mastek",
        "mastercard", "mathworks", "maxval", "mckinsey-knowledge-center", "medibuddy", "mercedes-benz", "merck", "microchip-technologies",
        "microland", "micron-technology", "microsoft", "mindcrew", "mindtree", "mirafra-software", "mistral-solutions", "mitsubishi-electric",
        "moengage", "molex", "morgan-stanley", "motorola-solutions", "mphasis", "mu-sigma", "mygate", "mylab-discovery-solutions",
        "nagarro", "ncr-corporation", "nec-corporation", "negentropy", "neilsoft", "neoscript", "netapp", "netcore-cloud",
        "netcracker", "netmagic", "neustar", "newgen-software", "nice-systems", "nokia", "nortal", "novartis",
        "ntt-data", "nvidia", "nxp-semiconductors", "nykaa", "o9-solutions", "olacabs", "oliver-wyman", "olx",
        "ontid", "opentext", "oracle", "oracle-financial-services", "oslabs", "oyorooms", "pace-automation", "palo-alto-networks",
        "panasonic", "panaya", "panta-rey", "parker-hannifin", "patni-computers", "payatu", "payoda", "paypal",
        "perficient", "persistent-systems", "philips", "photon-infotech", "pimpri-chinchwad", "pine-labs", "pinnacle-infotech", "pitney-bowes",
        "polar-consulting", "porsche-digital", "praj-industries", "pratian-technologies", "pravaig-dynamics", "prime-software", "pristine-infotech", "prolifics",
        "prometric", "ptc-software", "pune-it", "qlik", "qmetry", "quadgen", "qualcomm", "quatrro",
        "quick-heal", "quikr", "quinnox", "quovantis", "ract-software", "railcraft", "railyatri", "ramco-systems",
        "rapid-innovation", "rapidvalue", "rategain", "raytheon", "razorpay", "red-hat", "redbus", "reliance-industries",
        "reliance-jio", "renault-nissan", "rentomojo", "resemble", "resilinc", "resulticks", "rim-technologies", "risksense",
        "rockwell-automation", "rohde-schwarz", "rolls-royce", "rootquotient", "sabre", "saepio", "safeguard-global", "safran",
        "sagemcom", "salesforce", "samsung", "samsung-sds", "sandvine", "sap", "sap-labs-india", "sas-institute",
        "sasken-technologies", "savantis", "schneider-electric", "seagate", "seclore", "serosoft", "sgs-technologies", "shell-india",
        "shipmozo", "sidvin-coretech", "siemens", "sierra-ottis", "sigfig", "silicon-systems", "skilrock-technologies", "skoda-auto",
        "skoda-volkswagen", "slk-software", "smartlink-software", "snaplogic", "softcell-technologies", "softdel-systems", "softenger", "softlink-global",
        "softnautics", "softobiz", "softsol", "softsquare", "softtek", "software-ag", "soliton-solutions", "sonata-software",
        "sophos", "sopra-steria", "soti", "sparsh-technologies", "spektrum", "speridian", "sprinklr", "sprylogic",
        "square-software", "srinsoft", "sriven", "sterlite-technologies", "stridely-solutions", "stryker", "subex", "sun-microsystems",
        "sungard", "suprdaily", "sw-software", "symantec", "symphony-by-se-technologies", "synapsica", "synerzip", "synopsys",
        "syntel", "t-systems", "tally-solutions", "tandem-research", "tata-communications", "tata-consultancy-services", "tata-elxsi", "tata-motors",
        "tata-power", "tata-technologies", "tavisca", "teamlease", "tech-mahindra", "techmojo", "technipfmc", "technobox",
        "technocept", "technosoft", "techprocess", "teco-pune", "tektronix", "temenos", "teradata", "tes-software",
        "tesco", "testo", "texas-instruments", "thales", "thermax", "thomson-reuters", "thoughtworks", "tieto",
        "times-internet", "titan", "tjx", "torus-software", "toshiba", "toyota", "toyota-tsusho", "trend-micro",
        "trident-solutions", "trigyn-technologies", "tvs-software", "ubs", "ul-india", "uniphore-solutions", "united-parcel-service", "ust-global",
        "vanguard", "veritas", "verizon", "virtusa", "visteon", "vmware", "vodafone", "volkswagen",
        "volvo", "wabco", "wabtec", "wipro", "world-bank", "xoriant", "xpanxion", "yantra-software",
        "yash-technologies", "zensar-technologies", "zf-steering-gear", "zoho", "zs-associates",
    ],
    "chennai": [
        "3i-infotech-travel", "3m", "3m-technical-cer", "7-eventz", "abb", "abb-india-global", "abbott", "abbott-india-medical-dr",
        "abn-amro", "accenture", "accenture-digital", "accenture-technology", "accor", "acme-solar", "actia-group", "activision-blizzard",
        "acubetech-solution", "adani-green-energy", "adani-group", "adecco-india", "aditya-birla-finance", "aditya-birla-money", "aditya-birla-sun", "adobe",
        "advanced-sterilization", "affinity-partners", "agilent", "agrostar", "aig", "airbus-group-india", "akzonobel", "alkem-laboratories",
        "allegis-india", "allianz", "alstom", "alstom-transport-info", "amara-raja", "amazon", "amazon-development-centre", "amazon-india",
        "amazon-web-services", "amber-enterprises-india", "amd", "amd-india-design-center", "ameen-spices-infra", "analog-devices", "anand-rathi-share", "angel-broking-zd",
        "angel-one", "animaze-studios", "ankur-scientific-energy-tech", "anna-university-ict-gt", "antal-international", "apex-softtech", "apollo-hospitals", "apollo-tele-health",
        "applied-materials", "appviewx", "aptean-solutions", "aptiv", "aptiv-technical-services", "aratex-corporation", "aravind-eyecare-it-system", "arcelormittal",
        "arm", "armor-safe-enviro", "artech-infosystems", "ashok-leyland", "asian-paints", "aspiration-ai-technologies", "aster-medicity", "astrazeneca",
        "ather-energy", "atkins-realty-global", "au-small-finance", "audi", "aurionpro-solutions", "aurobindo-pharma", "avance-consulting", "avataar-me",
        "avigna-it-park-works", "avigna-technologies", "avis-budget", "axa", "axis-bank-tech", "azarius-digital", "azure-power", "bain-company",
        "bajaj-electrical-s", "bajaj-finserv", "bajaj-ventures", "bandai-namco", "bandhan-digi", "bank-of-america", "barclays", "baroda-pioneer",
        "basf", "basf-construction-chem", "baxter", "bayer", "bayer-zydus-pharma-gen", "bbdo", "beckman-coulter", "becton-dickinson",
        "best-engineering", "bharti-airtel", "bhugol-consulting-pr", "bigbasket", "bijak", "bikewale", "billroth", "bio-rad",
        "biocon", "birla-group-it", "birla-sun", "birlasoft", "blackrock", "blinkit", "bluescope-information", "bmw",
        "bnp-paribas", "boeing-tech-india", "bombardier", "bookingcom", "bosch", "bosch-global-software", "boston-scientific", "bounce",
        "box8", "bpl", "bristol-myers-squibb", "britannia", "broadcom", "broadcom-communication-tech", "browserstack", "bruker",
        "bt-group-ict", "btc", "bunch-micro-creative", "byd", "byjus", "cadence", "cadila-healthcare", "calpine-energy",
        "calyx-chemicals", "canara-tech", "canon", "canonical", "capcom", "capgemini", "capita-software", "capital-float",
        "capstone-managerial", "captain-fresh", "caratlane-blue-stone", "cardekho", "career-nets", "cars24", "cartrade", "casino-online",
        "caterpillar", "caterpillar-engineering-rd", "cavinkare", "cavotec-india-peri", "ceeri", "celestial-softsys", "celestica", "celestica-india",
        "cell-works-lab", "century-soft", "century-tile", "cerium-systems", "cgi-group-india", "chai-point", "chargebee", "cheminor-drugs",
        "chemmanur-enterprises", "chetinad-health-city", "chief-education-serv", "cholamandalam-finance", "chubb", "cipla", "cisco", "citi",
        "citibank", "city-union-bank-tech", "clariant", "clariant-chemicals-india", "classic-tech-test", "cleartrip", "cloud-foundry", "clover-infotech",
        "clri", "cmfri", "cnrc", "coca-cola", "coding-ninja", "coforge", "cognizant", "coir-board-kerala-eco-turf",
        "compuage-infocom", "compunnel-soft", "computacenter-india", "contata-solutions", "continental", "continental-automotive", "cornell-insurtech", "cornerstone-ondemand",
        "corvig", "cosmos-maya", "couchbase", "covance", "covestro", "crayon-software", "cred", "credit-suisse",
        "crest-communication", "crofarm", "crompton-bp", "ctrk-games", "cultfit", "cummins", "cummins-technologies", "curatio-healthcare",
        "currefit", "cuvette", "cyberspace-solutions", "cyient", "d-hit-games", "dabur", "dalmia-group-digital", "data-soft-intl",
        "databricks", "datamatics-global", "dataricks", "dayal-brose", "dbb", "dcx-technology", "dealtracker", "dehaat",
        "dell", "dell-emc", "dell-international-services", "deloitte-kpmg", "deloitte-us", "delta-fans", "deluxe", "denso",
        "denso-ten-india", "dentsu", "dentsu-webchutney", "design-company", "deutsche-bank", "deutsche-mutual", "digit-global", "digital-aptech",
        "digital-bcg", "digital-eagle-minds", "digital-india-corporation", "divis-laboratories", "dmi-groups", "dneg", "doeacc", "dow",
        "dp-world-tech", "dq-entertainment", "dr-reddys-green", "dr-reddys-laboratories", "dream11-winzox", "droom", "dsp-mutual-fund", "dunzo",
        "dupont", "dutt-heritage", "dynacons-technologies", "dynamic-wireless", "e4e-solutions", "ease-my-trip", "ecentric-engg", "edelweiss-hkr",
        "edu-care-ventures", "edubridge-india", "edunext-technologies", "edvenswa-tech", "elastic-mysql", "elder-pharmaceuticals", "electronic-arts", "eli-lilly",
        "elixir-consulting", "emami", "embark-consulting", "emc", "emcure", "emerson", "emerson-process-mgt-sol", "emids-technologies",
        "emudhra-wb", "enterprise-holdings", "enterprise-pacific", "entrust", "epam-systems-india", "epic-games", "epitome-consult", "equatek-global",
        "equitas-small-finance", "ericsson", "esker-software", "esolve-technologies", "ethicals-health", "europcar", "eveready", "eveready-industries",
        "evonik", "evonik-india", "excel-controlinkage", "excercise-simulator", "exide-industries", "expedia", "expreris-it-sol", "ey-gds",
        "f1-infotech", "faasos", "facebook", "facilio", "faurecia", "faurecia-clarion-electronics", "fdc-studio", "federal-bank-tech",
        "fidelity-investments", "fincare", "fincare-small-finance", "fine-organic-industries", "firefly-creative-studio", "first-advantage-bpo", "first-solution-it", "fis-global",
        "fischer-measuring", "fiserv-solutions", "flex", "flex-tronics-of-st-jabil-india", "flexiloans", "flipkart", "focal-point-systems", "ford",
        "foretech-consulting", "fortis", "fortress-infrarail", "foxconn", "framestore", "franklin-templeton", "fresenius", "fresenius-medical-care-ph",
        "freshtohome", "freshworks", "frigate-technologies", "fujitsu", "fujitsu-consulting", "games-animation-preneurship", "games24x7", "gameskraft",
        "gathr-vr", "ge", "ge-healthcare", "ge-healthcare-technologies", "genpact-headstrong", "geojit-financial", "getronics-solution", "gillette",
        "glaxosmithkline", "glenmark", "glenmark-gen", "global-health-city", "global-information-tech", "godrej", "gokul-blue-bird", "goldfield-camlin",
        "goldman-sachs", "good-glamm-popxo", "goodrich-for-customer", "google", "google-cloud", "google-developer-space", "gozoomo-vr", "great-learning",
        "green-gold-animation", "green-run-ventures", "greenko-group", "greytip", "groww", "grundfos", "gsk", "gss-infotech",
        "gujarat-borosil", "guvi", "hakuhodo", "hal-aerodynamical", "hal-collaborations", "happiest-minds", "happy-bank", "harvey-nash",
        "hasura", "havells-lloyd", "hcl-infosystems", "hcl-infosystems-limited", "hcl-technologies", "hdfc-amex", "hdfc-bank-digital", "hdfc-securities",
        "healthcare-global-ent", "healthify-my-healthm4code", "henkel", "hertz", "hetero-drugs", "hexaware", "hilton", "hinduja-global-solutions",
        "hitachi-india", "hitachi-vantara", "honda", "honeywell", "honeywell-aerospace", "honeywell-technology", "hopmotion", "how-to-publi-mental",
        "hp", "hp-inc", "hp-inc-software", "hpe", "hsbc", "hsbc-mutual", "hul", "hyundai",
        "ibm", "ibm-india-private", "ibm-research-india", "icici-bank-digi", "icici-infra-tech", "icici-prudential", "icici-securities", "icra-management",
        "idbi-intellect-india", "iflex-solutions", "ihg", "iitg-software", "iknowva", "illumina", "imd", "impetus-infotech",
        "incapsulate-india", "incois", "ind-swift-labs", "indiabulls-software", "indiabulls-ventures", "indifi", "indra-sistemas", "indusface",
        "indusind-digi", "infineon", "infogain-sol", "infogen-labs-x", "informatica", "informatics-services", "infosys", "infra-software-asset",
        "ing-group", "innefu-labs", "innova-solutions", "inspirisys", "instagram", "integral-switch", "integral-systems", "intel",
        "intel-labs-india", "inteliment-tech", "intellisense-tech", "interpublic-group", "interviewbit", "iocts-software", "ion-exchange-ltd", "iorta-tech",
        "ipca-unique", "iqvia", "ircon-international", "isro-ursc-island", "it-enterprise-services", "italia-ceramics", "itc", "itc-infotech",
        "itlize-global", "itnow-inc", "iwork-solution", "ixigo", "jabil", "jabong-shopping-dot-com", "jade-global", "jbm-group",
        "jda-software", "jeppiaar-engineering", "jindal-steel", "john-deere", "john-deere-tech-center", "johnson-and-johnson-med", "johnson-johnson", "josys-technology",
        "joulesto-sol", "joyalukkas-kalyan", "jp-morgan", "jpmorgan-chase", "jsw-group", "jsw-steel", "junglee-games", "jupiter",
        "just-buy-live", "k-tech-sol", "kadence-international", "kajaria-porcelain", "kale-consultants", "kana-software", "karur-vysya", "kauvery-hospitals",
        "kelly-services-india", "kia", "kidobot", "kimberly-clark", "kinara-capital", "kissflow", "kitex-garments", "kl-university-inc",
        "kla-corporation", "knowledge-process-sys", "komatsu", "komatsu-technical-center", "konomi", "kosamattam-finance", "kotak-mahindra-digi", "kotak-mahindra-old-digi",
        "kotak-securities", "kpit-cummins-infosystem", "kpit-technologies", "kpit-technologies-limited", "kredx", "kreston-tech-sol", "krikos-technologies", "labcorp",
        "lakshmi-vilas", "lal-pathlabs", "lam-research", "lanco-group", "lanxess", "lanxess-india", "larsen-toubro", "larsen-toubro-infotech",
        "lav-holdings", "learn-digital-courses", "leeford-healthcare", "lendingkart", "lenovo", "lepton-software", "lg", "lg-soft-india",
        "liberty-mutual", "lic-of-india-reliance-nippon", "licious", "life-insurance", "linamar-india-grace", "linga-enterprises", "link-ites", "linkedin",
        "lite-bite-eatfit", "litmus-software", "livguard", "lloyds-banking-group", "lnt-technology-services", "lockton-securities-india", "lti", "ltimindtree",
        "lupin", "lupin-research-park", "luxoft-india", "lyondellbasell", "mad-street-den", "madras-fishtank", "madras-medical-mission", "madras-pioneer",
        "magna-automotive-tech", "magna-international", "mahindra-aerospace", "mahindra-british-telecom", "mahindra-mahindra", "majesco", "majesco-software", "makemytrip",
        "malabar-gold-senco", "mallya-hospital", "mamaearth", "manipal-hospital-digi", "manipal-hospitals", "mankind-pharma", "mannapuram-finance", "manpower-india",
        "manulife", "marico", "marlabs-software", "marriott", "marvel-omega", "marvell-technology", "masai", "mascon-technologies",
        "mastek", "master-software-services", "matrix-cellular", "matrix-consult-asia", "maveric-systems", "maya-digital-studios", "mcafee-software", "mccann-worldgroup",
        "mckinsey-company", "media-monks", "medicover-tech", "medley-pharmaceutical", "medtronic", "medtronic-engineering-center", "meesho", "melorra-gold",
        "membrane-tech-solutions", "mentor-graphics", "mercedes-benz", "merck", "merck-holding-life-sci", "merck-life-innovations", "merck-life-science", "meta",
        "metlife", "metropolis", "michael-page-india", "microland-limited", "micron", "micron-semiconductor-india", "microsoft", "microsoft-azure",
        "microsoft-development-centre-dtc", "mikroelektronika-chennai", "mindtree", "miranda-asset", "mitra-biotech-indoswift", "mncf", "mobile-corridor", "mobile-premier-league",
        "mobiquity-india", "mongo-db", "monnet-power", "montran-labs", "moonfrog-labs", "morgan-stanley", "moser-baer", "motherson-sumi",
        "motilal-oswal", "motilal-oswal-fin", "motorola-solutions", "moving-picture-company", "mphasis", "mpl", "msd-corp", "msn-laboratories",
        "msn-wockhardt", "mu-sigma-business-sol", "multimedia-llc", "munish-infra-vent", "murugappa-group-it", "muthoot-capital", "muthoot-finance", "muthoot-home",
        "muthoot-microfin", "muthoot-vehicle", "my-diagnostics", "mylan", "mylan-laboratory", "mylo", "myntra", "nagios-consulting",
        "narayana-health-digital", "nasscom-10000-startups", "nature-tec-cleans", "natwest", "navi", "navneet-digi-care", "nec", "neogrowth",
        "neon-dog", "neoris-tech", "ness-technologies", "nestle", "netapp", "netflix", "netmeds", "netxcell-telecom",
        "neuland-laboratories", "newgen-software", "next-wav", "nextavenue-consulting", "nexus-ventures", "ng-soft", "ngene", "nielit",
        "nihilent-technologies", "nihon-technos", "niit-technologies", "niki-ai", "ninjacart", "nippon-data-system", "nippon-india-mutual", "nissan",
        "nityo-infotech", "nivia-sports", "niyo", "nms-works", "nokia", "nortal-india", "northern-trust", "novartis",
        "novartis-healthcare-diagnostics", "novo-nordisk", "nuance-communications", "nutanix", "nuvama-wealth", "nvidia", "nvidia-gpu-rd-centre", "nxp-semiconductors",
        "nykaa", "ocean-king-tours", "oconnor", "octa-net-information", "octro", "odessa", "offshore-inn-tours", "ogilvy",
        "ola-cabs", "ola-electric", "olympus", "omnicom", "omnifices-softwares", "openshift-ansible", "opentext-gov", "optim-hr-consulting",
        "oracle", "oracle-cloud", "oracle-financial-services", "orbicular-pharm", "orbis-india", "orient-ceramics", "orient-electric", "original-digital",
        "otsuka-software", "outworks-technologies", "paisabazaar", "palantir", "paleto-associates", "panasonic", "panasonic-life-solutions", "panasonic-rd-centre",
        "pando", "par-formulations", "parexel", "paytm", "pc-jeweller-gr", "pci-solutions", "people-tech", "peoplematter",
        "pepsico", "perkinelmer", "permionics-membrane", "persistent-systems", "pesto-tech", "pfizer", "pfizer-medical-oncology", "pgim-franklin",
        "phantomfx", "pharma-chem-solutions", "pharmeasy", "philips", "philips-carbon-black", "philips-healthcare", "phonepe", "photon-infotech",
        "pinnacle-infotech", "pipeline-studios", "pitney-bowes", "pivotal", "pivotal-softwares", "pixis", "planet-telecom", "play-simple",
        "plixxo", "plus-degree-tech", "polar-consulting", "policybazaar", "porsche", "postgresql", "postman", "ppg",
        "practo", "prathibha-studios", "prathigna-technologies", "pratiti-technologies", "precision-age-chem", "precision-scientific-equip", "premier-millets", "premiere-digital",
        "prestige-group-fin", "pricewaterhousecoopers", "prime-focus", "prince-tours-india", "print-tek", "procter-gamble", "prokarma-softtech", "prometheus-consulting",
        "promilo-games", "protect-e-cycles", "prowess-software", "prudent-technologies", "prudential", "prutech-solutions", "publicis-groupe", "pure-storage",
        "px-india-solution", "pythian-solutions", "qualcomm", "qualcomm-creation-center", "qualtech-consulting", "quant-trust-rent", "qube-cinema", "quess-corp",
        "quest-diagnostics", "quest-global-india", "quinnox-solutions", "r-systems", "rabit-seo", "radical-technologies", "rafeeq-hospital", "rail-tek",
        "rainbow-childrens-hospital", "ramco-cememt", "ramco-systems", "randstad-india", "rang-technologies", "rani-apparel-grand", "ranka-jewels-onlinept", "ravindra-bharathi-schools",
        "razorpay", "rbl-digi", "rebel-foods", "recaero-india-systems", "rectitude-consulting", "red-bus", "red-hat", "redington-value",
        "redis-labs", "redpine-signals", "redwood-software", "relance-industries", "reliable-soft-tech", "reliance-chemotex-india-polybutadiene", "reliance-jio", "renacon-buildwell",
        "renault", "renee-soft-systems", "renesas", "renew-power", "result-service-chennai", "revolgy-india", "revolve", "revv",
        "reynolds", "ridge-i-innovations", "rimini-street", "robert-half-india", "roblox", "roche", "roche-diagnostics", "roche-information-solutions",
        "rocketlane", "rockstar-games", "rockwell-automation", "rockwell-automation-chennai", "rockwell-collins-goodrich", "rohde-schwarz-solutions", "ropex-private", "roto-moulders",
        "royal-enfield", "royal-travel-mice", "saama-technologies", "saankhya-labs", "saas-labs", "sabre-travel-network", "safenet", "safran-group-india",
        "saha-software", "sahyadri-industries", "salesforce", "salesforce-anypoint", "salesforce-india", "samsung", "samsung-sdi-rd", "sankara-nethralaya-digital",
        "sanmar-group-it", "sanmina", "sanmina-sci-india", "sanofi", "sanofi-synthelabo-rd", "sanspareils-greenland", "sap", "sap-labs",
        "sap-labs-india", "sapient", "sapientrazorfish", "sas-institute", "sasi-information", "sasken", "sasken-communication", "sasken-technologies",
        "sasken-technologies-ind", "sb-energy", "sbi-caps", "sbi-mutual", "scaler-academy", "schbang", "schneider-electric", "schneider-electric-itb",
        "sdl-plc", "se-quent-scientific", "seagate", "seclore-technologies", "sega", "sensus-software", "servion-global", "sharekhan-broking",
        "shaswat-chem", "shopclues", "shopee-enterprise", "shriram-city-transport-sen-mahindra-finance", "siemens", "siemens-communication-beyond", "siemens-healthineers", "siemens-mobility",
        "siemens-software-industry", "siemens-technology-services", "sierra-cedar-systems", "sika", "silver-spoon-animation", "simplilearn", "sims-hospital", "sirionlabs-platform",
        "sitara-pharma", "sixt", "skyworks", "slice", "slk-software", "smartcube-systems", "smd-led-vision", "smith-nephew",
        "snap", "snapdeal", "snecma-motor-india", "snowflake", "societe-generale", "softenger-solutions", "solar-industries", "soliton-technologies",
        "somany-ceramics", "sonata-software", "sonata-software-limited", "sonic-healthcare", "sony", "sony-bmg-music", "sopra-steria-india", "sound-magic",
        "south-indian-bank", "south-indian-rose", "south-indian-tech-park", "sowbaghya-beds", "sparsh-health", "spectraforce-technologies", "spectrum-softsys", "spi-technologies",
        "spic-sugar-cud", "spice-jet-indigo", "spiny", "spk-and-company", "spry-agency", "sps-commerce", "square-enix", "sreeram-educational",
        "srf-limited-bpo-pay", "sri-lakra", "sri-prince-chem", "sri-ramachandra", "srijan-technologies", "srikem-chemicals", "srishi-digital-learn", "srl-diagnostics",
        "srm-institute-amararaja-battery-unit", "ssl-esl-telecom", "sss-port-elite", "ssystems-pvt", "st-engineering", "standard-chartered", "state-bank-of-india-digi", "state-street",
        "statfield-grooves", "sterling-wilson", "stmicroelectronics", "stpi-software-technology-parks", "stride-sports", "striim", "stryker", "stryker-global-analytics",
        "subex", "subhashri-traders", "successfactors-workday", "sugar-cosmetics", "sumeru-software", "sumtotal", "sun-life", "sun-pharma",
        "sundaram-business-services", "sungard-consulting", "super-gaming", "surya-roshni", "surya-solar-naturals", "suse-linux", "suzlon", "suzlon-energy",
        "suzlon-energy-tech", "swiggy", "symphony-teleca", "syneos-health", "synergee-tech", "synergy-consultants", "synergy-studios", "synopsys",
        "synoverge-technologies", "synzeal-research", "syros-software", "sysplast-metal", "systech-solutions", "talent-ace-consulting", "talent-reach-consulting", "talentica",
        "talentica-software", "tamilnad-mercantile", "tanla-platforms", "tantra-foundation", "tata-1mg", "tata-ai-funds", "tata-auto-component-tech", "tata-capital",
        "tata-communications", "tata-consultancy-services", "tata-digital", "tata-elxsi", "tata-group", "tata-interactive-systems", "tata-motors", "tata-motors-evs",
        "tata-power-solar", "tata-projects", "tata-steel", "tata-technologies", "tata-technologies-limited", "taurean-consulting", "tavant-technologies", "tbo-academy",
        "tdp-media-labs", "teamlease-services", "tech-data-india", "tech-mahindra", "tech-mahindra-limited", "technicolor", "technicolor-india", "techno-comp-talent",
        "techno-park-creatives", "technopark-advisors", "tek-clinic", "telenor-networks", "teradata-india", "texas-instruments", "texas-instruments-india-design", "textbook-online",
        "theoris-software", "thermax-ltd", "thermofisher-scientific", "thinksoft-global", "thyrocare", "tibco", "tickled-media", "tieto-india",
        "tiss", "toonz-media", "torrent-pharmaceuticals", "torrent-power", "torry-haris", "torry-haris-global", "toshiba", "toyota",
        "tradomo", "transrail-metro", "travelocity", "trianz-holdings", "tricolite-energy", "trifacta-software", "trigent-software", "trimitra-software",
        "tripadvisor", "tvs-group", "tvs-motors", "twitter-x", "uber", "ubisoft", "ubs", "uma-enterprises-live",
        "unacademy", "unilever", "uniphore", "unity-technologies", "upgrad", "upstox", "urban-company", "ust-global",
        "ut-mutual-fr", "valeo", "valeo-india-engineering", "valgenesis-solutions", "vanguard", "vayam-technologies", "vedantu", "vega-studios",
        "ven-soft", "verizon-data", "verizon-data-india", "vervesys-technologies", "vestas", "vestas-technology-rd", "vfx-mpc", "victoria-ceramics",
        "vinayak-ceramic", "vinsys-it-services", "viranash-communication", "virtuos-technologies", "virtusa-consulting", "visionary-soft-sol", "visiontek-information-systems", "visteon-technical-services",
        "visual-soft-systems", "viz-experts", "vizlogic-systems", "vlocity", "vmware", "vocus-communication", "vodafone-idea", "volkswagen",
        "volvo", "vshesh-technologies", "vueai", "wabag-ltd", "wabtec-corporation", "walter-bushnell", "waterlife-india", "waters",
        "waycool", "web-invent-tech", "webel-solar", "webex-communications", "wells-fargo", "western-digital", "western-digital-rd-india", "whatsapp",
        "wheel-india-talents", "white-house-business-park", "whizlabs", "wipro", "wipro-light", "wipro-limited", "wipro-pocai-systems", "wissen-infotech",
        "wissen-technology", "wow-skin-science", "wpp", "wyndham-worldwide", "xanadutecnologies", "xavient-solutions", "xentrix-studios", "xerox",
        "xerox-india", "xilinx-chennai", "xoriant-solutions", "yash-technologies", "yatra", "yen-digital-lips", "yes-bank-digi", "yokogawa",
        "yulu", "zebra-technologies", "zenith-infotech", "zenotech-laboratories", "zensar-technologies", "zensar-technologies-limited", "zeon-consulting", "zepto",
        "zerodha", "zf-friedrichshafen", "zimmer-biomet", "zimmer-biomet-global-bus", "zoho", "zomato", "zones-corporate-sol", "zoom",
        "zoomcar", "zs-associates", "zurich-insurance", "zydus-cadila", "zynga",
    ],
    "kolkata": [
        "3i-infotech", "3pillar-global", "5ire", "a3logics", "aalpha-networks", "abacus-insights", "abp-group", "abzooba",
        "accel-care", "accenture", "access-healthcare", "accutech", "ace-innovate", "aceware", "acutis", "adani-enterprises",
        "adani-labs", "adglobal", "adpushup", "affectiva", "affinity", "affinsys", "aimdek", "airmeet",
        "airon-security", "airtel", "airtel-nxtra", "aisd", "ajackus", "akudo", "alauda-entertainment", "albedo-tech",
        "alchemysolutions", "alef-education", "algoworks", "alian-software", "alice-blue", "allied-digital", "allsec-technologies", "alt-coin",
        "altran", "amagi", "amazon", "amkette", "amplify", "anabodh", "ancore", "andor-tech",
        "anitech-solutions", "antier-solutions", "apartment-adda", "apatex", "appavo", "appinventiv", "appstech", "aprecomm",
        "aptic", "arcgate-software", "architech", "arcon", "aress-software", "arete-tech", "argusoft", "arideep",
        "arihant-technologies", "arivon", "arka-software", "arohi-software", "arramton", "arramton-technologies", "arrka", "asebus",
        "ash-com", "aspari", "aspentech", "assistiv", "astra-security", "atos-syntel", "auro-software", "avegen",
        "award-force", "axzyte", "azilen-technologies", "b2infosoft", "b4b-technologies", "baba-software", "bacancy-technology", "bambee",
        "bandhan-bank", "barclays-technology", "bargain-poly", "bausch-software", "bay-area", "bazaart", "bcs-technology", "bd-software",
        "bdecks", "beanbox", "beeclue", "berger-paints", "bergs-infotech", "best-buy-software", "betalectic", "beyond-key",
        "bfree", "bhavna-corp", "bhive", "bigscale", "biizline", "billedge", "billomi", "binary-semantics",
        "binmile", "biofourmis", "biplab-technologies", "biplytics", "birds-eye", "birla-corporation", "birlasoft", "biro-software",
        "bit-arts", "bit-mascot", "bite-speed", "bitebox", "bitkraft", "bitroot", "bits-n-bytes", "bitscape",
        "bitskraft", "biz4s", "biz4solutions", "bizcap", "bizlogic", "biztime", "black-buck", "black-coffer",
        "blackbuck-engineers", "blackdot", "blank-technologies", "blitz-academy", "bloc-infotech", "block-stars", "bloom-ventures", "blue-apps",
        "blue-bot", "blue-ridge", "bluechip", "bluepi-consulting", "blueshift", "blueteam", "blurr-ai", "blusteak",
        "bolt-earth", "bolt-iot", "bonanza-software", "bonito-designs", "bookinn", "boost-tech", "bose-institute", "boston-analytics",
        "bot-kit", "braincube", "brainium", "brainium-technologies", "braintechnosys", "brainvire-infotech", "brand-doctors", "brand-mint",
        "brass-software", "brave-soft", "breadline", "breaker-soft", "breinify", "bridge-professionals", "bright-champs", "brightest-it",
        "brillica", "brim-software", "brinicle", "britannia-industries", "brite-storm", "broad-river", "brown-men", "brring",
        "bry-ai", "bsf-technologies", "bsh-soft", "bt-group", "btech-inc", "bubble-shot", "bucks-it", "budding-bit",
        "builder-ai", "bullseye-consulting", "buzzinga", "cachesys", "cactus-consulting", "cad-opt", "callture", "calpion",
        "cambium-networks", "camelot", "camguard", "campus-365", "campus-advisor", "canonize", "capbespoke", "capgemini",
        "capital-numbers", "capricorn-technologies", "capsicle", "capsone", "capstone-consultancy", "carbynetech", "carvechi", "casepoint",
        "casino-tech", "castle-software", "catabatic", "catalyst-technologies", "catapult", "catchup-tech", "ccentic", "ccintellisense",
        "ccloud-labs", "cdata", "cedar-soft", "celito", "cellapp", "cellenza", "celusion-technologies", "centerity",
        "centralogic", "centre-for-railway-information-systems", "centric-consulting", "centrinity", "century-soft", "cerence", "ceridian", "certa-software",
        "ces-technologies", "cesc-limited", "cetas-tech", "cforce", "cg-va", "chai-chats", "champion-soft", "checkmark",
        "checknosh", "cherub-technologies", "chikalabs", "chimera-codes", "chimpz", "chisel-labs", "choicely", "chromatic",
        "cicada", "circuit-technologies", "cirgle", "cisco", "citiustech", "city-tech", "civic-tech", "clairvoyant",
        "claravine", "clarion-technologies", "classplus", "cleardata", "clearsky", "clementia", "cleverground", "cliffex",
        "clinch", "clinsoft", "clix-intellect", "cloud-action", "cloud-first", "cloud-for-all", "cloud-io", "cloud-minds",
        "cloud-peak", "cloud-wyz", "cloudalgos", "cloudanova", "cloudapps-digital", "cloudasia", "cloudbee", "cloudbuy",
        "cloudchomp", "cloudcoders", "cloudcrest", "clouddestiny", "cloudemo", "cloudester", "cloudester-labs", "cloudfab",
        "cloudforce", "cloudfronts", "cloudgen", "cloudgit", "cloudhunk", "cloudio", "cloudit", "cloudli",
        "cloudminds", "cloudpath", "cloudphile", "cloudploy", "cloudscape", "cloudsek", "cloudsoft", "cloudtara",
        "cloudtech", "cloudview", "cloudvise", "cloudways", "clover-etal", "clover-infotech", "clue-soft", "cmots-technologies",
        "cmp-soft", "cms-cyber", "cntrl-plus", "co-nnect", "coal-india", "cobalt-eye", "cobold", "cobweb-it",
        "codavatar", "code-bean", "code-brewers", "code-creation", "code-db", "code-fluid", "code-fu", "code-guru",
        "code-illusion", "code-labs", "code-lion", "code-ninja", "code-play", "code-quotient", "code-smiles", "code-tech",
        "code-titans", "codeadept", "codeavirus", "codebeamer", "codebee", "codeblocks", "codebranch", "codebrew",
        "codebridge", "codebryx", "codeburst", "codebyte", "codecall", "codecamp", "codecanopy", "codeclan",
        "codeclean", "codecloud", "codeclouds", "codeco", "codecrew", "codedot", "codedrop", "codeelements",
        "codegence", "codehaus", "codehesion", "codeignite", "codeinch", "codekart", "codekin", "codelattice",
        "codeless", "codeli", "codelogist", "codelone", "codelynx", "codemech", "codemeg", "codemotive",
        "coden", "codenative", "codeorbit", "codepan", "codepencil", "codeploy", "codeport", "codeprairie",
        "codepulse", "codequez", "coderes", "coders-array", "coders-bay", "coders-hub", "coders-station", "coderslab",
        "codescape", "codeshare", "codesign", "codesmart", "codesparks", "codestage", "codestorm", "codesync",
        "codetale", "codethink", "codetree", "codeunplug", "codevac", "codeview", "codewalla", "codewave",
        "codewave-technologies", "codewing", "codex-soft", "codex-technologies", "codiant-technologies", "coding-club", "coding-crafters", "coding-king",
        "coding-mantra", "codza-software", "coffeesoft", "coforge", "cognate-labs", "cognition-infotech", "cognizant", "cognize-soft",
        "cohezia", "colan-infotech", "colgate-soft", "collabera", "collectcent", "collective-goal", "color-orange", "columbus-soft",
        "comaxsoft", "command-soft", "common8", "communaltech", "computronics", "concentrix", "confidis", "conjoinix",
        "connect-soft", "consagous-technologies", "conscia-soft", "conscious-software", "consellea", "consult-guru", "contentcreators", "convergen-soft",
        "coova-soft", "copa-inc", "copy-ai", "core-94", "core-genesis", "coreals", "corestack-technologies", "coreteka",
        "cornertree", "corporatsoft", "cosmopolitan-soft", "covalense", "covetus", "cowrks", "crablet", "craft-soft",
        "craftbytes", "crafting-software", "crafto-technologies", "craftsoft", "crajon", "cranberry-soft", "cranium-software", "crast-soft",
        "cravia-soft", "cream-software", "creation-soft", "creative-codes", "creative-glow", "creative-minds", "creative-software", "creative-software-consultants",
        "creative-touch", "crebos-online", "cred-cal", "credall", "credgenics", "credo-soft", "credo-technology", "credrights",
        "creduce", "creole-soft", "crescendo-soft", "crestech", "crigno", "crisp-soft", "critica-software", "croscend",
        "cross-aspect", "crowd-soft", "crowdfund", "ctrls", "cuben-square", "cublinc", "cuculus", "cumulative",
        "cupola-soft", "curious-software", "current-software", "cursor-info", "cush", "cut-software", "cybernova", "cybersphere",
        "cybersys", "cybertron", "cyberverse", "cyblance", "cyclomed", "cyclops-soft", "cygnet-infotech", "cygnus-soft",
        "cyient", "cypher-soft", "d-orange", "dacca-soft", "dace-soft", "daisy-soft", "dama-soft", "damco-soft",
        "dandelion-soft", "darb-soft", "darshan-soft", "darwin-soft", "dash-soft", "data-bees", "data-clan", "data-crunch",
        "data-edge", "data-focus", "data-frog", "data-hub", "data-io", "data-miner", "data-opt", "data-peak",
        "data-pipe", "data-quest", "data-science", "data-seek", "data-tribe", "data-works", "database-soft", "databay",
        "databazaar", "databiz", "datacipher", "datacore", "datacorp", "datadvent", "datagrp", "datalogic",
        "datamatix", "datametica", "datametrix", "datamotive", "datanov", "dataplus", "datarocks", "datasci",
        "datasphere", "datateam", "datatech", "datavaned", "datavant", "dataweave", "datawinds", "dbi-technologies",
        "dcloud-technologies", "decagon-soft", "decimal-point", "decision-soft", "decode-soft", "decon-soft", "deduce-technologies", "deemsys",
        "deep-concepts", "deep-craft", "deep-insight", "deep-thought", "defend-soft", "define-soft", "deliver-soft", "deloitte",
        "deloitte-solutions", "demure-technologies", "denave-soft", "dephect", "deploy-soft", "descent-soft", "destra-soft", "deutsche-bank",
        "dev-99", "dev-bay", "dev-craft", "dev-design", "dev-house", "dev-labs", "dev-mount", "dev-ops",
        "dev-ratio", "dev-square", "dev-station", "dev-studio", "dev-technologies", "devbridge", "devbunch", "devcel",
        "devclan", "devcom", "devden", "developers-zone", "developex", "deven", "devferno", "devflow",
        "devgrid", "devharsh", "devheim", "devherd", "devhouse", "device", "devinf", "devisers",
        "devjo", "devknox", "devlabs", "devlogs", "devnagri", "devnatives", "devoku", "devontec",
        "devopv", "devorbis", "devout", "dexter-soft", "dhiwise", "dianapps", "dicio", "digi-cabs",
        "digi-coders", "digi-force", "digi-labs", "digi-soft", "digi-solution", "digi-tech", "digicraft", "digidelta",
        "digidham", "digify", "digimantra", "diginom", "digipeople", "digipercept", "digiquanta", "digirise",
        "digital-socrates", "digits", "digivault", "digiware", "digiweb", "digizante", "diligent-global", "dimexon",
        "dios-soft", "direct-soft", "distillery-technologies", "distinct-soft", "dizz-soft", "docman", "doers-soft", "dolci-soft",
        "domain-soft", "domo-soft", "doodle-soft", "dotcom-soft", "dotinternet", "dotito", "double-soft", "doyen-soft",
        "draft-soft", "dragon-soft", "dream-soft", "drive-soft", "druva", "dsp-soft", "dts-soft", "dual-soft",
        "duco-soft", "dukes-soft", "dune-soft", "dusk-soft", "dv-soft", "dvara", "dwelo", "dxc-technology",
        "dye-soft", "dynalog", "dynam-soft", "e-arc", "e-builder", "e-card", "e-care", "e-club",
        "e-com", "e-cube", "e-dms", "e-docs", "e-fin", "e-flex", "e-fly", "e-fuse",
        "e-gov", "e-guru", "e-hub", "e-institute", "e-intell", "e-kart", "e-kosh", "e-lancer",
        "e-learn", "e-lite", "e-logic", "e-magine", "e-mall", "e-mark", "e-med", "e-mind",
        "e-nnovation", "e-office", "e-pack", "e-path", "e-payment", "e-print", "e-proc", "e-pulse",
        "e-quest", "e-reach", "e-route", "e-sample", "e-scan", "e-sharp", "e-sign", "e-slim",
        "e-smart", "e-soft", "e-solution", "e-spark", "e-square", "e-store", "e-surg", "e-talent",
        "e-tech", "e-track", "e-train", "e-trans", "e-vision", "e-volve", "e-work", "e-world",
        "e-zest", "e4e-healthcare", "eagle-eye", "earn-soft", "earth-soft", "ease-soft", "east-soft", "easy-soft",
        "eb-soft", "ebix", "ebook-soft", "ebusiness", "ecaps-technologies", "ecc-soft", "ech-soft", "echo-soft",
        "ecl-soft", "eclat-soft", "eclect-soft", "eclipse-soft", "eco-soft", "ecole-soft", "econosoft", "ecotech",
        "ect-soft", "ed-soft", "edas-soft", "edc-soft", "eden-soft", "edge-soft", "edgeverve", "edify-soft",
        "edows", "edrone", "edu-soft", "educare", "educomp", "educube", "eduintech", "edulab",
        "edvizo", "ee-soft", "effect-soft", "effectiv", "effi-soft", "egni-soft", "eight-soft", "ein-soft",
        "eit-soft", "ek-soft", "eka-software", "ekeyt", "eks-soft", "ekta-soft", "el-soft", "elan-soft",
        "elasti-soft", "elbert-soft", "eldorado-technologies", "elearnera", "elec-soft", "elect-soft", "eleg-soft", "elem-soft",
        "elev-soft", "elite-soft", "ema-soft", "emami", "eman-soft", "emb-soft", "embee-soft", "ember-soft",
        "emble-soft", "embr-soft", "embright", "emcure", "eme-soft", "emed-soft", "emer-soft", "emf-soft",
        "emir-soft", "emote-soft", "emp-soft", "empat", "empow-soft", "ems-soft", "en-soft", "ena-soft",
        "enab-soft", "enc-soft", "enco-soft", "encore-software", "ency-soft", "end-soft", "ener-soft", "eng-soft",
        "engi-soft", "enig-soft", "enl-soft", "eno-soft", "enp-soft", "ens-soft", "ense-soft", "ent-soft",
        "ente-soft", "enth-soft", "entr-soft", "env-soft", "enve-soft", "envi-soft", "eo-soft", "eoc-soft",
        "eod-soft", "eon-soft", "ep-soft", "epa-soft", "epc-soft", "epi-soft", "epo-soft", "epr-soft",
        "eq-soft", "equ-soft", "equi-soft", "era-soft", "erco-soft", "ericsson", "eris-soft", "ernst-young",
        "ero-soft", "ers-soft", "ert-soft", "erud-soft", "es-soft", "esa-soft", "esc-soft", "esd-soft",
        "ese-soft", "esh-soft", "esi-soft", "esk-soft", "esm-soft", "eso-soft", "esol-soft", "esp-soft",
        "esq-soft", "ess-soft", "esta-soft", "esti-soft", "et-soft", "eta-soft", "etc-soft", "ete-soft",
        "eth-soft", "ethosh", "etisalat", "etl-soft", "eto-soft", "ets-soft", "eu-soft", "eug-soft",
        "eur-soft", "ev-soft", "eva-soft", "evc-soft", "eve-soft", "even-soft", "evert-soft", "evi-soft",
        "evo-soft", "evocheck", "evol-soft", "evos-soft", "evr-soft", "ex-soft", "exa-soft", "exal-soft",
        "exam-soft", "exc-soft", "exce-soft", "exel-soft", "exi-soft", "exide-industries", "exl-soft", "exo-soft",
        "exot-soft", "exotel", "exp-soft", "expe-soft", "expl-soft", "expo-soft", "exr-soft", "ext-soft",
        "exte-soft", "extr-soft", "ey-soft", "eye-soft", "eyo-soft", "ez-soft", "eza-soft", "eze-soft",
        "ezeiatech", "ezeva-technologies", "ezy-soft", "fac-soft", "face-soft", "facialix", "fact-soft", "fal-soft",
        "fam-soft", "fan-soft", "far-soft", "farm-soft", "fash-soft", "fashinza", "fastfilmz", "fat-soft",
        "fau-soft", "fea-soft", "feedough", "fel-soft", "fem-soft", "fen-soft", "fer-soft", "fes-soft",
        "fest-soft", "few-soft", "ff-soft", "fi-soft", "fib-soft", "ficosa", "fid-soft", "fidelis-technologies",
        "fie-soft", "fig-soft", "fil-soft", "file-soft", "fill-soft", "film-soft", "filmboard", "fin-soft",
        "fina-soft", "find-soft", "findify", "fine-soft", "finesse-interactive", "finflux", "finv-soft", "fir-soft",
        "fire-soft", "firm-soft", "firmbee", "first-soft", "firstsource", "fis-soft", "fish-soft", "fit-soft",
        "fix-soft", "fl-soft", "fla-soft", "flam-soft", "flat-soft", "flatworld-solutions", "flep-soft", "fles-soft",
        "flic-soft", "flin-soft", "flip-soft", "flo-soft", "flor-soft", "flot-soft", "flow-soft", "flu-soft",
        "flue-soft", "fluentgrid", "flui-soft", "flux-auto", "flux-soft", "fly-soft", "fo-soft", "foc-soft",
        "fod-soft", "fog-soft", "fol-soft", "foll-soft", "fom-soft", "fon-soft", "fond-soft", "font-soft",
        "foo-soft", "food-soft", "fool-soft", "for-soft", "forc-soft", "forcis", "fore-soft", "forg-soft",
        "form-soft", "fort-soft", "fortune-fin", "fos-soft", "fot-soft", "foun-soft", "fous-soft", "fox-soft",
        "fr-soft", "fra-soft", "frag-soft", "fram-soft", "fran-soft", "frase-soft", "frau-soft", "fray-soft",
        "fre-soft", "fred-soft", "free-soft", "fren-soft", "fres-soft", "freshlight", "fret-soft", "friz-soft",
        "fro-soft", "frog-soft", "fron-soft", "frost-soft", "frug-soft", "fruit-soft", "fry-soft", "fs-soft",
        "fu-soft", "fue-soft", "fujitsu-consulting", "ful-soft", "full-creative", "full-soft", "fum-soft", "fun-soft",
        "fund-soft", "fundicine", "fung-soft", "funk-soft", "fur-soft", "furn-soft", "fus-soft", "fusi-soft",
        "fuss-soft", "fut-soft", "futu-soft", "future-software", "fuz-soft", "fuzz-soft", "fyle", "ga-soft",
        "gab-soft", "gae-soft", "gal-soft", "gam-soft", "game-soft", "gan-soft", "gap-soft", "gar-soft",
        "gard-soft", "garden-reach-shipbuilders", "gart-soft", "gas-soft", "gash-soft", "gat-soft", "gaul-soft", "gaum-soft",
        "gaw-soft", "gb-soft", "ge-soft", "gea-soft", "geck-soft", "gee-soft", "geek-soft", "geekyants",
        "gel-soft", "gem-soft", "gemb-soft", "gemos-software", "gen-soft", "gene-soft", "genpact", "genu-soft",
        "geo-soft", "ger-soft", "germ-soft", "gest-soft", "get-soft", "gey-soft", "gh-soft", "gha-soft",
        "ghe-soft", "ghi-soft", "gho-soft", "ghu-soft", "gi-soft", "gib-soft", "gid-soft", "gif-soft",
        "gig-soft", "gil-soft", "gim-soft", "gin-soft", "gio-soft", "gir-soft", "gis-soft", "git-soft",
        "gk-soft", "gl-soft", "gla-soft", "glan-soft", "gle-soft", "glee-soft", "glen-soft", "gli-soft",
        "glim-soft", "glin-soft", "glo-soft", "glob-soft", "global-software", "glot-soft", "glov-soft", "glow-soft",
        "gluon-soft", "gm-soft", "gn-soft", "gna-soft", "gnani-ai", "gni-soft", "gno-soft", "gnu-soft",
        "go-soft", "go4cash", "goa-soft", "goaudify", "god-soft", "godrej-infotech", "gol-soft", "gold-soft",
        "gon-soft", "goo-soft", "goodwork-labs", "goog-soft", "gool-soft", "gor-soft", "gos-soft", "goth-soft",
        "gov-soft", "gp-soft", "gr-soft", "gra-soft", "grac-soft", "graf-soft", "gran-soft", "gras-soft",
        "grat-soft", "gray-soft", "grc-soft", "gre-soft", "grea-soft", "gree-soft", "green-accents", "grei-soft",
        "gren-soft", "grey-soft", "greytip", "gri-soft", "grid-soft", "grim-soft", "grin-soft", "grip-soft",
        "gro-soft", "groc-soft", "grog-soft", "gron-soft", "gros-soft", "grou-soft", "grov-soft", "grow-soft",
        "gru-soft", "grud-soft", "grum-soft", "grun-soft", "gryn-soft", "gs-soft", "gspann-technologies", "gt-soft",
        "gu-soft", "gua-soft", "gue-soft", "guf-soft", "guj-soft", "gul-soft", "gum-soft", "gun-soft",
        "gur-soft", "guv-soft", "gv-soft", "gw-soft", "gy-soft", "gyn-soft", "gyp-soft", "gyr-soft",
        "h-soft", "ha-soft", "hab-soft", "hac-soft", "had-soft", "hae-soft", "haf-soft", "hag-soft",
        "hai-soft", "hak-soft", "hal-soft", "ham-soft", "han-soft", "hap-soft", "har-soft", "has-soft",
        "hat-soft", "hatch-works", "hav-soft", "haw-soft", "hb-soft", "hc-soft", "hcl-technologies", "hd-soft",
        "he-soft", "hea-soft", "heb-soft", "hec-soft", "hed-soft", "hee-soft", "heg-soft", "hei-soft",
        "hel-soft", "hem-soft", "hen-soft", "hep-soft", "her-soft", "hes-soft", "heu-soft", "hew-soft",
        "hex-soft", "hexaware", "hf-soft", "hg-soft", "hi-soft", "hib-soft", "hic-soft", "hidden-layers",
        "hif-soft", "hig-soft", "hil-soft", "him-soft", "hin-soft", "hip-soft", "hir-soft", "his-soft",
        "hit-soft", "hk-soft", "hl-soft", "hm-soft", "hn-soft", "ho-soft", "hob-soft", "hoc-soft",
        "hod-soft", "hoe-soft", "hof-soft", "hog-soft", "hoh-soft", "hoi-soft", "hol-soft", "hom-soft",
        "hon-soft", "hoo-soft", "hop-soft", "hor-soft", "hos-soft", "hot-soft", "hou-soft", "hov-soft",
        "how-soft", "hp-soft", "hr-soft", "hs-soft", "hsbc-technology", "ht-soft", "hu-soft", "hub-soft",
        "huc-soft", "hud-soft", "hue-soft", "hug-soft", "huh-soft", "huk-soft", "hul-soft", "hum-soft",
        "hun-soft", "hup-soft", "hus-soft", "hut-soft", "hv-soft", "hvinfotech", "hw-soft", "hx-soft",
        "hy-soft", "hyd-soft", "hyg-soft", "hym-soft", "hyo-soft", "hyp-soft", "hz-soft", "ibm",
        "idesign-market", "iflexion", "igate", "incriss-solutions", "indian-statistical-institute", "indianic", "indovance", "indus-net-technologies",
        "indusgeeks", "infitronics", "info-savant", "infocus-soft", "infoneo", "infosys", "inletsolutions", "innominds",
        "innoppl", "inovar-consulting", "intellipaat", "intellismith", "intigral", "intileo-technologies", "invensis-technologies", "iotric",
        "iqlance-global", "iquadra-technologies", "isg", "isi-kolkata", "isofttech", "itarian", "itc-infotech", "itc-limited",
        "iware-solutions", "jade-software", "jai-infoway", "jaypore", "josh-technology", "jumbotail", "justdial", "kairos-software",
        "kaizen-technologies", "kanerika", "kanhasoft", "kashyap-solutions", "kevit-technologies", "khatabook", "kintronic-labs", "kodeguys",
        "kore-software", "kpit-technologies", "kpmg", "krds-software", "krify", "kryptos-technologies", "ktech", "kyzer-software",
        "labvantage", "litmus7-systems", "logistic-infotech", "lollypop", "loylogic", "lti", "ltimindtree", "lucidpath",
        "lux-industries", "magicaver-technologies", "manras-technologies", "mario-technologies", "master-software", "mercedes-benz-research", "meritech-software", "microland",
        "microsoft", "miko", "mindfire-solutions", "mindinventory", "mindtickle", "mindtree", "mjunction", "mobile-premier-league",
        "mobilecoderz", "moengage", "moglix", "monkhub", "morgan-stanley", "mphasis", "multisoft-technologies", "my-happy-company",
        "myteam", "nammayatri", "narang-technologies", "nathan-software", "national-insurance", "netcat", "netclues-technologies", "netcore-cloud",
        "netedge-it", "netmaxims", "netweb", "netzary", "neuralit", "nikhil-technologies", "nimblechapps", "ninetek",
        "nitech", "nixxia-technologies", "novatium", "nownative", "ntt-data", "ntt-global", "nucleus-software", "ofbusiness",
        "ok-credit", "om-software", "omnicom-media", "onward-technologies", "oodles-technologies", "open", "openxcell-technologies", "opspanda",
        "opus-soft", "oracle", "orange-business-services", "orange-kloud", "osun-technologies", "ozonesoft", "p360", "peerless-group",
        "persistent-systems", "philips-india", "pinesphere", "pipe-candy", "pixacode", "pixel-technologies", "pixel-values", "plotchai",
        "polaris-consulting", "posist", "prelude-technologies", "pridesys-it", "pristinesoft", "proso-technologies", "protean-egov", "prudence-consulting",
        "push-cc", "pwc", "pythian", "qnu-labs", "qss-technosoft", "quovantis", "qwikcilver", "r-space",
        "radixweb", "ramco-systems", "record-bee", "red-bytes", "redq", "reliance-jio", "reshamandi", "resync",
        "revenue-raccoon", "rezo-media", "right-solutions", "rishabh-software", "rites", "rkmc-technologies", "rocket-learning", "rolt",
        "rupa-company", "rysuntech", "saaswad-solutions", "saeculum", "sagacity-software", "saha-institute", "sansar", "sap",
        "sasken-technologies", "schoolnetindia", "search-ebs", "semantic-technology", "semaphore-software", "semikolon", "sensi-bolt", "sensiple-software",
        "sentient-games", "serpwatch", "servify", "sgs-technologies", "shaligram-infotech", "sidero", "sify", "signal-chip",
        "simplilearn", "siply", "skit-ai", "slk-software", "slyce", "smartcoin", "smartinfologiks", "snapmint",
        "social-beat", "soft-suave", "softall", "softcraft", "softdel", "softeq", "softnal", "softqube",
        "solulab", "solutions-infini", "sonata-software", "space-o-technologies", "sparsh-technologies", "spec-india", "sphinx-solution", "spsoft-technologies",
        "srei-infrastructure", "srijan-technologies", "standard-chartered", "startoon-labs", "step-india", "storehippo", "stp-technologies", "stt-global",
        "subscription-badger", "sumasoft", "suryansh-infotech", "sutrahr", "svapna-technologies", "sybrant-technologies", "syscom", "talentserv",
        "talisma", "tally-solutions", "tanta-innovations", "tata-communications", "tata-consultancy-services", "tata-elxsi", "tata-interactive-systems", "tata-motors",
        "tata-steel", "tcg-digital", "team-ideal", "tech-mahindra", "tech9logy-creators", "techasoft", "techeela", "techie-bees",
        "techmind-group", "techmojo", "technats", "techno-electric", "technobrains", "technocraft", "technoduce", "techsophy",
        "techsun", "tekshapers", "teleperformance", "tenacity-ai", "the-software-practice", "the-souled-store", "think-ai", "thoughtfocus",
        "toplyne", "torry-harris", "tqv-technologies", "trell", "trigent-software", "truebil", "trustt", "uengage",
        "unicommerce", "upstox", "upsurge", "v2solutions", "value-innovation-labs", "valuebound", "variable-energy-cyclotron", "vedantu",
        "velostics", "venus-software", "virtual-cs", "virtusa", "vitwit", "vodafone-idea", "voosh", "voxel-grids",
        "vymo", "w2s-solutions", "wb-electronics", "webclues-infotech", "webel", "webexo", "webguru-infosystems", "webxloo",
        "whatfix", "whitepanda", "wildcraft", "winzo", "wipro", "wishberry", "wns-global-services", "wobot-ai",
        "workos", "xcential", "xenonstack", "xongo-labs", "xoxoday", "xpertcube", "yapsody", "yash-technologies",
        "yelo", "yudiz-solutions", "zapkey", "zensar-technologies", "zepo", "zeron-tech", "zingbus", "zivame",
        "zoho-corporation", "zolo", "zoomcar", "zuci", "zuzers",
    ],
    "ahmedabad": [
        "abb", "accenture", "adani-energy-solutions", "adani-green-energy", "adani-group", "adani-power", "addweb-solution", "adobe",
        "agile-infoways", "aimfox", "airtel", "algorisys", "alian-software", "allianz", "allied-digital-services", "amazon",
        "amd", "american-express", "anblicks", "aostics-techlabs", "appclues-infotech", "aptimum-technosoft", "artoon-solutions", "arvind-limited",
        "arvind-mills", "asian-infotech", "astics-techlabs", "asttension", "atos", "atul-ltd", "aurionpro-solutions", "autorabit",
        "avenues-aic", "axa", "axis-bank", "azine-web-technologies", "b2b-infosoft", "bacancy-technology", "bain", "bank-of-america",
        "barclays", "bcg", "beyond-root", "bharti-softtech", "bhrti-softtech", "billdesk", "binary-infotech", "birlasoft",
        "blue-bytes", "bluelupin-technologies", "bnp-paribas", "bosch", "boston-barbell", "braincube", "brainvire-infotech", "brainyflash",
        "bridging-points", "brilnt", "bsnl", "cadila-pharmaceuticals", "caliber-technologies", "calyxpod", "capgemini", "capricorn-systems",
        "cartrabbit", "ccavenue", "chubb", "cine-man-productions", "cisco", "citi", "codewing", "codiant",
        "coforge", "cognizant", "concentrix", "connectinfosoft", "craddle-edii", "crea-tive-horizons", "creative-computers", "crebos-online",
        "cred", "credit-suisse", "css-corp", "cybercom-creation", "cygnet-infotech", "cyient", "dataflow-group", "datanovus",
        "dell", "deloitte", "design-shop-zone", "deutsche-bank", "dharmishtha-infotech", "digilink-solutions", "dista", "drc-systems",
        "dreamsoft", "droiders", "dxc-technology", "e-softwares", "ebizz-infotech", "edutek-solutions", "einfochips", "elision-technologies",
        "enlighten-infosystems", "environmental-scientific-instruments", "ericsson", "esko-applications", "etech-services", "ey", "firstsource", "fis",
        "fiserv", "forward-thinking-solutions", "fractl-analytics", "gcube-soft", "gencode", "genpact", "glitch-infotech", "goldman-sachs",
        "google", "google-pay", "gopani-product-systems", "gridle", "group-landmark", "gujarat-gas", "gujarat-mineral-development", "gujarat-state-petroleum",
        "gujarat-tea-processors", "hcltech", "hdfc-bank", "hexaware", "hidden-brains", "hiremotiv-it-staffing", "hitachi", "honeywell",
        "hp", "hsbc", "i-nexture-solutions", "ibm", "icici-bank", "iconnect-solutions", "icreativez", "idesign-solutions",
        "idfc-first", "imobisoft", "incipient-infotech", "indian-infotech", "indusnet-technologies", "inexture-solutions", "infibeam-avenues", "infibrain",
        "infinity-infoway", "info-spectrum", "infograins", "infosys", "intas-pharmaceuticals", "intel", "intelitech", "intuz-solutions",
        "ipix-solutions", "ish-infotech", "itech-soft", "itech-solutions", "itpath-solutions", "jack-henry", "jio-bp", "jp-morgan",
        "kapture-crm", "karmasoft", "kasth-engineering", "kaushalam", "kishan-it-services", "kodder-technologies", "koderfin", "konstant-infosolutions",
        "kotak-mahindra", "kpit", "kpmg", "krutarth-infotech", "lenovo", "lets-nurture", "lg", "lincoln-pharmaceuticals",
        "lnt-technology-services", "logical-software", "logonix-infotech", "lti", "ltimindtree", "magneto-it-solutions", "magnum-software", "majesco",
        "makemytrans", "manektech", "mann-infotech", "mastek", "master-software-solutions", "matic-infotech", "matrix-infotech", "matter-electric",
        "mckinsey", "meta", "metlife", "mettl", "microland", "microsoft", "mindbowser", "mindtree",
        "mitraz-financial", "morgan-stanley", "moweb-technologies", "mphasis", "mu-sigma", "myanatomy", "narola-infotech", "natwest",
        "ncode-technologies", "networx-infotech", "neuronimbus", "nexus-infotech", "nexus-software", "nflow-software", "ng-zenworks", "niit-technologies",
        "nimap-infotech", "nokia", "noviindus-technologies", "nrdoshi-associates", "ntimetrics", "ntt-data", "nvidia", "nyusoft-solutions",
        "om-sai-infotech", "omninos-solutions", "omnipresent-infotech", "openxcell", "oracle", "origamize-studios", "panasonic", "parangat-technologies",
        "paypal", "paytm", "peerbits", "persistent-systems", "philips", "phonepe", "positiwise-software", "powertronics-control-system",
        "pragma-software", "pranav-infotech", "pranshtech", "profinch", "promatics-technologies", "prudential", "pwc", "pyramid-software",
        "qdegrees", "qualcomm", "radixweb", "raghav-infotech", "rankmyapp", "raywell-studio", "rayzoredge", "razorpay",
        "red-hat", "redblack-solutions", "reelo", "reliance-jio", "repos-energy", "ridhima-enterprise", "ris-software", "rishabh-software",
        "riteknowledge", "robosys-automation", "saboo-technologies", "sadbhav-engineering", "salesforce", "samsung", "sap", "sapient-intelligence",
        "sasken-technologies", "sattrix-infosec", "sattrix-technologies", "schneider-electric", "scripts-systems", "septa-software", "serco", "servicenow",
        "shaligram-infotech", "shubham-infotech", "siemens", "simform", "skynet-tech", "socialpilot", "societe-generale", "softqube-technologies",
        "softtech", "softvan", "sony", "sopra-steria", "spaceo-technologies", "spexion-technologies", "spire-infotech", "standard-chartered",
        "startek", "state-street", "stempedia", "succeed-technologies", "sukh-sagar-infotech", "supream-technologies", "sutherland-global", "swift-infotech",
        "synergy-infotech", "synoverge-technologies", "syntel", "talisman-solutions", "tata-communications", "tatvasoft", "tcs", "tech-mahindra",
        "tech9logy-creators", "technobrains", "technomark", "techrevolve", "techstalwarts", "techstaunch", "techugo", "tecnotree-global",
        "teksun", "teksun-software", "teksystems-ahmedabad", "teleperformance", "temenos", "thakar-infotech", "torchit", "torrent-group",
        "torrent-pharmaceuticals", "torrent-power", "trigent-software", "troikaa-pharmaceuticals", "u-connect", "ubs", "uniotech", "utsav-infotech",
        "v2soft", "valuecoders", "vandana-wireless", "vector-controls", "vinayak-infotech", "vishal-infotech", "vmware", "vodafone-idea",
        "vrinsoft-technology", "web-trainings", "webit-multiservices", "weblineindia", "webmagnet", "webmobril-technologies", "webtech-infotech", "wells-fargo",
        "winjit", "wipro", "wizerd-infotech", "wolves-creata", "worldline", "xanika-infotech", "xcelcorp", "yash-infotech",
        "yashasvi-infotech", "yellow-ants", "yes-bank", "yudiz-solutions", "yug-infotech", "zaubacorp", "zealous-infotech", "zensar",
        "zerone-technologies", "zonix-infotech", "zuvu-innovations", "zydus-lifesciences",
    ],
    "jaipur": [
        "3i-data-scraping", "500apps", "accenture", "acropolis", "addweb-solution", "agile-infoways", "aglowid-it-solutions", "allianceek",
        "antier-solutions", "appclues-infotech", "appinventiv", "apptunix", "artoon-solutions", "auxesis-infotech", "bacancy-technology", "birlasoft",
        "bitswits", "borntechies", "br-softtech", "brainvire", "bureau-of-digital", "capgemini", "capital-numbers", "cashkaro",
        "chetu", "claritus-consulting", "classplus", "claysys-technologies", "cmolds", "codersbrain", "codiant", "coforge",
        "cognizant", "consagous-technologies", "contus", "cumulations", "cyblance", "cyient", "cynoteck-technology", "damco-solutions",
        "darsh-innovation", "datametica", "deorwine-infotech", "deutsche-bank", "devbatch", "dignitas-digital", "dreamorbit", "droisys",
        "e2m-solutions", "ecom-express", "ecosmob-technologies", "elasticrun", "ellocent-labs", "enuke-software", "envigo", "excellent-webworld",
        "fampay", "fatbit-technologies", "firstsource", "flexsin", "folio3", "fugenx", "genpact", "ginger-webs",
        "goodworker", "google", "graffersid", "graygraph-technologies", "haptik", "hcl-technologies", "hdata-systems", "hexaware",
        "hgs", "hidden-brains", "hyperlink-infosystem", "i95dev", "ibm", "icreativez", "ids-logic", "imobdev-technologies",
        "impero-it-services", "indus-net-technologies", "infograins", "infosys", "intelegain", "intersog", "jar", "jellyfish-technologies",
        "kanerika-software", "kipibi", "konstant-infosolutions", "kpit", "krify", "kukufm", "lakhani-technologies", "logics-square",
        "ltimindtree", "lumina-datamatics", "maq-software", "mastek", "matellio", "mediaagility", "metlife", "miko",
        "mindfire-solutions", "mindinventory", "mobicip", "mobilecoderz", "mobinius", "moolya", "mphasis", "mtoag-technologies",
        "nagarro", "narola-infotech", "netset-software", "neutrinos", "nextbrain-technologies", "ninehertz", "ntrust-infotech", "o2i",
        "octal-it-solution", "ola", "ongraph-technologies", "oracle", "osscube", "parangat-technologies", "paxcom", "peerbits",
        "perfomatix", "persisent-systems", "pie-infocomm", "pixelcrayons", "posist", "pragiti", "pristyn-care", "promatics-technologies",
        "propel-apps", "publicis-sapient", "q3-technologies", "qdegrees", "qyuki", "r-systems", "radixweb", "ramco-systems",
        "rapidvalue-solutions", "ripenapps", "riteknowledge", "robosoft-technologies", "saffron-tech", "sagacity-software", "samsotech", "saritasa",
        "seasia-infotech", "semidot-infotech", "shiv-technolabs", "soft-suave", "solulab", "sonata-software", "sopra-steria", "sourcemash",
        "space-o-technologies", "spec-india", "sphinx-solutions", "subex", "sufalam-technologies", "sumatosoft", "swiggy", "sybrant-technologies",
        "synergytop", "systools", "tatvasoft", "tatvic-analytics", "tavant-technologies", "tcs", "tech-mahindra", "techahead",
        "techno-softwares", "technokom", "techugo", "techuz-infoweb", "teknorix", "terasol-technologies", "tintash", "toxsl-technologies",
        "trigent-software", "twixor", "unified-infotech", "urban-ladder", "v2solutions", "valuecoders", "vasundhara-infotech", "vegavid-technology",
        "vipra-tech", "vrize", "webclues-infotech", "webkul", "webmobril", "wingify", "wipro", "wns",
        "xcelance", "xongolab", "yash-technologies", "yudiz-solutions", "zensar", "zibtek", "zignuts-technolab", "zolo",
        "zs-associates", "zymr",
    ],
    "kochi": [
        "2base-technologies", "2hats-logic-solutions", "42square-technologies", "9commerce-technologies", "aabasoft-technologies", "aarbee-structures", "abel-techsoft", "abilytics-consulting",
        "acabes-international", "acc", "accelray-technologies", "accenture", "aceware-fintech-services", "acube-innovations", "adesso-india", "admaren-tech",
        "adobe", "advenser-engineering-services", "affiliated-computer-services-xerox", "airo-global-software", "airpay-financial-technologies", "alb-technologies", "alignminds-technologies", "allianz",
        "alphasky-ventures", "altos-technologies", "amara-raja-design-alpha", "amatosoft", "amazon", "amiyon-solutions", "amla-consultancy", "amplitude-software-systems",
        "apadore", "applied-payments-technology", "apps-team-technologies", "appticz", "apro-it-solutions", "armia-systems", "array-platforms", "art-technology-and-software",
        "artius", "aspire-systems", "aspire-systems-digital", "atlassian", "aventus-informatics", "ayata", "ayata-commerce-tech-solutions", "baker-hughes",
        "banzan-studios", "beinex-consulting", "beth-soft-technologies", "bimex-engineers", "binaries", "bip", "bj-corps-technologies", "braddock-infotech",
        "braid-technologies", "bramma-it-solutions", "brennan-it-india", "broadtech-it-solutions", "cabot-technology-solutions", "cachet", "cadence", "calpine-group",
        "capgemini", "carerevenue-technology", "carestack", "carnegie-worldwide-services", "carol-solutions", "cascade-revenue-management", "cavli-wireless", "ccs-technologies",
        "cereiv-advisory", "chisquare-labs", "cipherpeak", "classic-technologies-business-solutions", "claysys-technologies", "clevero-india", "cloudhouse-technologies", "cloudium-software",
        "cloudvice", "codedesign-technologies", "codelynks-software-solutions", "codenext-technologies", "codmeric-infotech", "cognicor-technologies", "cognizant", "coinone-global-solutions",
        "conduent", "consoul-associates", "contactpoint-360", "coolminds-technologies", "crossgen-technologies", "cseidc-technologies", "cubet-techno-labs", "cubiccode",
        "currentware-india", "cvs-info-solutions", "cyberion-software-solutions", "cybrosys-technologies", "cyient", "daddara", "daskalos-virtual-academy", "dataequinox",
        "datafloat-technologies", "datum-innovation", "dbiz-ai-solutions", "dee-and-lee-services", "deloitte", "dialabank", "difinity-digital", "digiora-technologies",
        "dimensions-cybertech-india", "distinct-infotech-solutions", "docgiant-services-india", "dooth-internet-service", "dot-in-technologies", "dynactionize-india", "dynamed-healthcare-solutions", "edstem-technologies",
        "egc-global-services-india", "electrifex-technologies", "elemment-facade", "emergio-technologies", "empay-software-solutions", "empress-infotech", "emsyne-technologies", "endeion-engineering-services",
        "energyscape-renewables", "entri", "entrib", "envestnet", "epi-use-india", "epixel-solutions", "eqsoft-business-solutions", "ernst-young",
        "estro-tech-robotics", "exacore-it-solutions", "exor-india", "expeed-software", "experion-technologies", "exponential-digital-solutions", "extravelmoney-technosol", "facade-global",
        "facetofact", "facilio", "fdc-web-technologies", "feathersoft-info-solutions", "federal-operations-and-services-fedserv", "finastra", "fine-destination", "fingent",
        "fingent-global-solutions", "firminiq-systems", "flycatch-infotech", "focal-me-design-solutions", "focaloid-technologies", "founding-minds-software", "fragomen-immigration-services", "fusioncharts",
        "g10x-india", "galactico-express-solutions", "galtech-technologies", "gapblue-software-labs", "garuda-aerospace", "genpact", "genrobotics", "geojit-technologies",
        "gewan-info-tech-solutions", "gis-axiom", "gizmeon-technologies", "gkc", "glitz-it-solutions", "global-infonet", "global-surf-it", "google",
        "grampro-business-services", "grapelime-innovations", "gravity-business-process", "greenworld-international-enterprise", "grehasoft", "guidehouse-india", "hashroot-technologies", "hatio-innovations",
        "hcl-technologies", "heidelsoft-technologies", "hh-back-office-services", "hotpack-global", "hr-block", "htic-global", "hubbell", "ibm",
        "ibs-software", "icodebees", "idatalytics", "ideagcs", "ileaf", "ileaf-solutions", "impaqtive-technologies", "in-tech-group-india",
        "inapp-information-technologies", "incede-technologies", "industryapps-technologies", "inerg-software-innovations", "infintor-solutions", "infocylanz", "infosmart-technologies", "infoys",
        "innovature-software-labs", "innpark", "inntot-technologies", "inspired-software-development", "inspirisys-solutions", "inspite-technologies", "intbrains", "intelliflo-software-india",
        "internland-technology-services", "intuit", "iwex-infomatics", "jachoos-technologies", "jk-lucent", "jobin-jismi", "johnturingwatson-software-solutions", "jtsi-technologies-india",
        "kakapo-systems-india", "katzion-technology-solutions", "kl-koncepts-lab", "knowbe4-india", "kott-software", "kpit-technologies", "krythium-solutions", "lanware-solutions",
        "linnk-outsource-solutions-india", "linxas-it-consulting", "ltimindtree", "lucidplus-infotech", "lumicel-animation-studios", "luure-ai", "mantle-solutions", "mantra-it-solutions",
        "mapletech-space", "marketbytes-webworks", "mashuptech", "mastercard", "mathworks", "maxxion-systems", "mcfadyen-digital", "media-systems-india",
        "merabt-technologies", "merp-systems", "metclouds-technologies", "microsoft", "milestone-technologies", "millennium-infologic", "mindcurv-technology-solutions", "mindlabs-consultancy-services",
        "mindlabs-systems", "mindplex", "mindtree", "mitsogo", "mitz-ai-minds", "mozilor-technologies", "mphasis", "nas-infosolutions",
        "navicater-solutions-india", "ndimensionz-solutions", "neem-info-solutions", "neork-technologies", "nesa-software", "nesote-technologies", "nest-group", "nestsoft-technomaster",
        "netlyft-technologies", "netsentries-infosec-solutions", "newagesys-solutions", "next-apps", "niaway-technologies", "niche-techies", "nielsen", "nissan-digital",
        "noa-infosolutions", "nomd-technologies", "nov-inc", "nucore", "nuvento-systems", "nymbl", "obidos-technologies", "obvious-ai-technology",
        "offline-human-studios", "onesoft-technologies", "opshore-talent-solutions", "oracle", "orestes-technologies", "origent-technologies", "orion-india-systems", "ormeon-it-consulting",
        "orthofx", "outsource-partners-international", "overbrook-technology-services", "oxomo-systems", "oxomo-systems-international", "pagematics-india", "panashifzco-technology-solution", "paoyaila-animation-studios",
        "paradigm-it", "paulcart-e-commerce", "paypal", "pcs-india", "pearlsoft-technologies", "penguin-data-centre", "persisent-systems", "phases-india-technology-solutions",
        "pinetech-it-solutions", "pinmicro-india", "piserve-solutions", "pit-solutions", "pixdynamics", "planet-media-india", "portrave-solutions", "prevalent-ai",
        "primecrown-technologies", "privo-techcorp", "pueblo-shades", "pumex-infotech", "pwc", "qburst-technologies", "qc-verify", "quantum-acumen",
        "qubeslab-technologies", "qubiqon-consulting-india", "quest-global", "raintech-software", "rainybits-technology", "red-hat", "redux-network-redux", "regent-global-services-india",
        "retyn-business-solution", "rexav-llp", "rextech-studios", "riod-logic", "rm-education", "roberts-design-services", "rogersoft-technologies", "rr-donnelley",
        "ruby-seven-studios", "sands-lab", "sap", "sayone-technologies", "sbl-knowledge-services", "se-mentor-solutions", "seeroo-it-solutions", "seguro-technologies",
        "seidor-opentrends", "senscript-technologies", "servsys-technology-services", "sfo-technologies", "silverbloom-technologies", "simelabs-astek", "skybertech-it-innovation", "smec-automation",
        "snippetcommerce360", "softop-solutions", "softspace-infotech", "soulxes-technologies", "sparksupport-infotech", "spawoz-technologies", "speridian-technologies", "spiderline-technologies",
        "spiralcode-innovates", "steigend-it-solutions", "stepping-stone-consultancy-services", "strands-energy", "stream-perfect-global-services", "suntec-business-solutions", "supporthub360", "surveysparrow",
        "sustglobal", "synopsys", "synthite-it", "syriac-consultancy-services", "systalent-software", "talk-digital", "tamcherry-technologies", "tata-consultancy-services",
        "tata-elxsi", "tcs", "tech-aventure", "tech-mahindra", "techfriar-technologies", "techgentsia-software-technologies", "techneurons-consulting-solutions", "technowave-id-systems",
        "techpullers-technology-solutions", "techtaliya-informatics", "techversant-infotech", "techware-lab", "tecnostac-systems", "telious-technologies", "terrific-minds", "testing-mavens-software",
        "thinkpalm-technologies", "thomsun-infocare", "thoughtminds-system", "thriveminds-technologies", "titan-tech-emirates", "tnp-consultancy", "toobler-technologies", "toonz-media",
        "touchworld-technology", "tranzmeo", "travancore-analytics", "tukxi-india", "turnitin", "turqosoft-solutions", "tuttifrutti-games", "unilaw-global",
        "urolime", "ust-global", "v-guard", "vaisesika-consulting", "valuementor-infosec", "varishtha-infotech-services", "veeble-softtech", "verteil-technologies",
        "viewy-digital", "violet-frames", "vipoint-solutions", "virtual-impulse-technologies", "virtual-sys-technologies", "visa", "vistas-global-intellect", "vivish-technologies",
        "vmware", "vortexen-dynamics", "voxtron-solutions", "voyager-it-solutions", "voyon-technology", "vtrio-solutions", "vvdn-technologies", "wazeefa1-technologies",
        "webandcrafts", "webdura-technologies", "white-rabbit-group", "windfall-productions", "wipro", "wiq", "woc-branding-systems", "woodsman",
        "worksent-technologies", "woxro", "xerox", "yatnam-technologies", "yavun-technologies", "yellowfish-digital-innovations", "ynot-infosolutions", "yougotagift",
        "zafin", "zamorins-solutions", "zapare-technologies", "zealogics-it-solutions", "zellis-hr-india", "zinbay-india", "zinemind-technologies", "zoiteckh-informations-solutions",
    ],
    "chandigarh": [
        "accenture", "addweb-solution", "airtel", "allstate", "amazon", "amdocs", "aon", "bharti-airtel",
        "birlasoft", "blowhorn", "bny-mellon", "capgemini", "chqbook", "coforge", "cognizant", "collabera",
        "dell", "dell-emc", "deqode", "dxc-technology", "ecom-express", "edugorilla", "elluminati", "elucidata",
        "ergode", "ethereal-machines", "f5-networks", "fiserv", "forte", "fujitsu", "genpact", "ginger-webs",
        "glenhill-computer", "globalogic", "google", "google-india", "grofers", "hcl", "hcl-technologies", "hdfc-life",
        "healthkart", "hexaware", "ht-media", "ibm", "incedo", "indigo", "infosys", "innoserv",
        "ion-group", "isofttech", "jaro-education", "jetking", "jio", "konstant-infosolutions", "kpn-logistics", "livspace",
        "lnt-technology-services", "locus", "lti", "ltimindtree", "maq-software", "mckinsey", "microland", "microsoft",
        "mindinventory", "mobikwik", "mphasis", "nagarro", "netapp", "niit", "oracle", "oracle-financial",
        "oyo", "panjab-university-it", "pnb", "pwc", "qualcomm", "reliance-jio", "robert-bosch", "rockwell-automation",
        "samsung", "samsung-rd", "sap", "sapient", "schneider-electric", "semidot-infotech", "serco", "siemens",
        "silverskills", "singer-india", "snapdeal", "space-o-technologies", "spinny", "starbucks", "state-street", "sutherland",
        "tata-communications", "tata-elxsi", "tcs", "tech-mahindra", "techahead", "techchef", "teleperformance", "trantor",
        "trimble", "verint", "verizon", "vidyotech", "virtusa", "vista-communications", "vmware", "wipro",
        "wns", "xceedance", "xongolab", "zscaler",
    ],
    "indore": [
        "accenture", "acropolis-infotech", "aditya-birla-group", "adroit-software", "amazon", "appscrip", "appsqadz", "bharatx",
        "bit-soft", "blue-chip-soft", "brainvire", "bridgestone-it", "brilliant-soft", "capgemini", "capital-numbers", "cashkaro",
        "cipla-it", "city-soft", "cmarix", "cognizant", "collabera", "csc-india", "cyber-infrastructure", "data-craft",
        "dealshare", "ecom-express", "evince-development", "firstsource", "fnp", "genius-soft", "global-soft", "google",
        "hcl", "ibm", "ibm-india", "imit", "imobext", "impetus", "indore-software", "info-quest",
        "infosys", "ipca-labs-it", "it-guru", "jar", "java-soft", "kukufm", "lnt-technology-services", "logic-soft",
        "ltimindtree", "lupin-it", "micro-soft", "microsoft", "mink", "mphasis", "nagarro", "ncode",
        "newgen-software", "octal-it-solution", "ola", "oracle-financial", "pagarbook", "paras-soft", "persisent-systems", "piramal-it",
        "premier-biosoft", "prism-medical", "prithvi-information", "rackbank", "rebel-foods", "salt", "samsung-rd", "sapient",
        "satellite-informatics", "shiprocket", "shopkirana", "softinfosys", "suvidha-soft", "tata-group", "tcs", "tech-mahindra",
        "tech-soft", "teleperformance", "trell", "vehlo", "vijay-software", "vision-soft", "winsoft", "wipro",
        "yash-softtech", "yash-technologies", "zetwerk", "zs-associates",
    ],
    "coimbatore": [
        "aarna-software", "accenture", "acme-intime", "adela-software", "allstate-india", "amazon-dev-center", "amrita-technologies", "anunta-tech",
        "aspire-systems", "athenahealth", "bannari-amman-software", "bilytic", "bosch-global", "brainium-soft", "brainy-software", "brightkite",
        "capgemini", "cercle-x", "chargebee", "cihat-technologies", "cisco", "codewave", "cognizant", "continental-automotive",
        "cox-automotive", "css-corp", "datamatics", "dectris", "digital-detection", "dimici", "dxc-technology", "e-centric-solutions",
        "eacon-software", "ebit", "effiya-technologies", "el-gijo", "embitel", "enthuons", "entri", "eruvaka-technologies",
        "fis-global", "ford-it", "fornax", "freshworks", "gavs-technologies", "ggk-technologies", "global-edge-software", "global-tronics",
        "gtm-software", "hatsun-software", "hcl-technologies", "hexaware", "hi-tech-software", "hp", "ibm-india", "icode-technologies",
        "ilink-systems", "indium-software", "infosys", "infoziant", "innominds", "intellipaat", "inube-software", "iware-logic",
        "jastec-software", "kaashiv-infotech", "kanini", "koenig-solutions", "kongu-software", "kovai-co", "kovaion", "kpit",
        "lakshya-software", "lnt-technology-services", "logic-planet", "logixal", "lotus-wireless", "ltimindtree", "m2p-fintech", "magnia-infotech",
        "maintec", "maventic", "maxval", "mic-software", "mindmade", "mindtree", "mistral-solutions", "mithra-technologies",
        "mobilytics", "morulaa-healthtech", "mphasis", "nalashaa-solutions", "nastech", "ngn-technologies", "nmsworks", "noesys",
        "nova-software", "novacom", "noventiq", "ntt-data", "nxtra-data", "onedata-software", "osi-technologies", "palnar-software",
        "parabole", "pathpartner", "planys-technologies", "policybazaar-tech", "pricol-technologies", "protech-software", "qa-infotech", "qbix",
        "qentelli", "quest-global", "rage-frameworks", "ramco-systems", "rapidvalue", "rategain", "redpine-signals", "relq-software",
        "resourcifi", "rialto-technologies", "robo-software", "roots-industries-it", "sage-software", "sathguru", "sattva-software", "scanpoint",
        "securview", "seven-hills", "sgs-technologies", "silicon-software", "simple-logic", "sixtowns", "skytech-solutions", "smart-it",
        "softcloud", "software-associates", "software-paradigms", "soliton", "sonata-software", "spritle", "srishti-software", "standard-chartered-gbs",
        "surya-informatics", "systematic", "tact", "talisma", "tally-solutions", "tavant-technologies", "tcs", "tech-consulting",
        "tech-mahindra", "techmojo", "technocraft", "tektronix", "testingxperts", "thinkpalm", "thirdware", "torry-harris",
        "trigent", "tvs-electronics-it", "uniphore", "ust-global", "valuelabs", "vembu-technologies", "veridic", "visionet",
        "visteon-technical", "viteos", "volt-db", "volvo-it", "wavelabs", "wipro", "wiziq", "xpand-it",
        "yalamanchili-software", "yash-technologies", "yodlee", "zoho", "zuci-systems",
    ],
    "trivandrum": [
        "2base-technologies", "2hats-logic-solutions", "42square-technologies", "9commerce-technologies", "aabasoft-technologies", "aarbee-structures", "abel-techsoft", "abilytics-consulting",
        "acabes-international", "acc", "accelray-technologies", "accenture", "aceware-fintech-services", "acube-innovations", "adesso-india", "admaren-tech",
        "adobe", "advenser-engineering-services", "affiliated-computer-services-xerox", "airo-global-software", "airpay-financial-technologies", "alb-technologies", "alignminds-technologies", "allianz",
        "alphasky-ventures", "altos-technologies", "amara-raja-design-alpha", "amatosoft", "amazon", "amiyon-solutions", "amla-consultancy", "amplitude-software-systems",
        "apadore", "applied-payments-technology", "apps-team-technologies", "appticz", "apro-it-solutions", "armia-systems", "array-platforms", "art-technology-and-software",
        "artius", "aspire-systems", "aspire-systems-digital", "atlassian", "aventus-informatics", "ayata", "ayata-commerce-tech-solutions", "baker-hughes",
        "banzan-studios", "beinex-consulting", "beth-soft-technologies", "bimex-engineers", "binaries", "bip", "bj-corps-technologies", "braddock-infotech",
        "braid-technologies", "bramma-it-solutions", "brennan-it-india", "broadtech-it-solutions", "cabot-technology-solutions", "cachet", "cadence", "calpine-group",
        "capgemini", "carerevenue-technology", "carestack", "carnegie-worldwide-services", "carol-solutions", "cascade-revenue-management", "cavli-wireless", "ccs-technologies",
        "cereiv-advisory", "chisquare-labs", "cipherpeak", "classic-technologies-business-solutions", "claysys-technologies", "clevero-india", "cloudhouse-technologies", "cloudium-software",
        "cloudvice", "codedesign-technologies", "codelynks-software-solutions", "codenext-technologies", "codmeric-infotech", "cognicor-technologies", "cognizant", "coinone-global-solutions",
        "conduent", "consoul-associates", "contactpoint-360", "coolminds-technologies", "crossgen-technologies", "cseidc-technologies", "cubet-techno-labs", "cubiccode",
        "currentware-india", "cvs-info-solutions", "cyberion-software-solutions", "cybrosys-technologies", "cyient", "daddara", "daskalos-virtual-academy", "dataequinox",
        "datafloat-technologies", "datum-innovation", "dbiz-ai-solutions", "dee-and-lee-services", "deloitte", "dialabank", "difinity-digital", "digiora-technologies",
        "dimensions-cybertech-india", "distinct-infotech-solutions", "docgiant-services-india", "dooth-internet-service", "dot-in-technologies", "dynactionize-india", "dynamed-healthcare-solutions", "edstem-technologies",
        "egc-global-services-india", "electrifex-technologies", "elemment-facade", "emergio-technologies", "empay-software-solutions", "empress-infotech", "emsyne-technologies", "endeion-engineering-services",
        "energyscape-renewables", "entri", "entrib", "envestnet", "epi-use-india", "epixel-solutions", "eqsoft-business-solutions", "ernst-young",
        "estro-tech-robotics", "exacore-it-solutions", "exor-india", "expeed-software", "experion-technologies", "exponential-digital-solutions", "extravelmoney-technosol", "facade-global",
        "facetofact", "facilio", "fdc-web-technologies", "feathersoft-info-solutions", "federal-operations-and-services-fedserv", "finastra", "fine-destination", "fingent",
        "fingent-global-solutions", "firminiq-systems", "flycatch-infotech", "focal-me-design-solutions", "focaloid-technologies", "founding-minds-software", "fragomen-immigration-services", "fusioncharts",
        "g10x-india", "galactico-express-solutions", "galtech-technologies", "gapblue-software-labs", "garuda-aerospace", "genpact", "genrobotics", "geojit-technologies",
        "gewan-info-tech-solutions", "gis-axiom", "gizmeon-technologies", "gkc", "glitz-it-solutions", "global-infonet", "global-surf-it", "google",
        "grampro-business-services", "grapelime-innovations", "gravity-business-process", "greenworld-international-enterprise", "grehasoft", "guidehouse-india", "hashroot-technologies", "hatio-innovations",
        "hcl-technologies", "heidelsoft-technologies", "hh-back-office-services", "hotpack-global", "hr-block", "htic-global", "hubbell", "ibm",
        "ibs-software", "icodebees", "idatalytics", "ideagcs", "ileaf", "ileaf-solutions", "impaqtive-technologies", "in-tech-group-india",
        "inapp-information-technologies", "incede-technologies", "industryapps-technologies", "inerg-software-innovations", "infintor-solutions", "infocylanz", "infosmart-technologies", "infoys",
        "innovature-software-labs", "innpark", "inntot-technologies", "inspired-software-development", "inspirisys-solutions", "inspite-technologies", "intbrains", "intelliflo-software-india",
        "internland-technology-services", "intuit", "iwex-infomatics", "jachoos-technologies", "jk-lucent", "jobin-jismi", "johnturingwatson-software-solutions", "jtsi-technologies-india",
        "kakapo-systems-india", "katzion-technology-solutions", "kl-koncepts-lab", "knowbe4-india", "kott-software", "kpit-technologies", "krythium-solutions", "lanware-solutions",
        "linnk-outsource-solutions-india", "linxas-it-consulting", "ltimindtree", "lucidplus-infotech", "lumicel-animation-studios", "luure-ai", "mantle-solutions", "mantra-it-solutions",
        "mapletech-space", "marketbytes-webworks", "mashuptech", "mastercard", "mathworks", "maxxion-systems", "mcfadyen-digital", "media-systems-india",
        "merabt-technologies", "merp-systems", "metclouds-technologies", "microsoft", "milestone-technologies", "millennium-infologic", "mindcurv-technology-solutions", "mindlabs-consultancy-services",
        "mindlabs-systems", "mindplex", "mindtree", "mitsogo", "mitz-ai-minds", "mozilor-technologies", "mphasis", "nas-infosolutions",
        "navicater-solutions-india", "ndimensionz-solutions", "neem-info-solutions", "neork-technologies", "nesa-software", "nesote-technologies", "nest-group", "nestsoft-technomaster",
        "netlyft-technologies", "netsentries-infosec-solutions", "newagesys-solutions", "next-apps", "niaway-technologies", "niche-techies", "nielsen", "nissan-digital",
        "noa-infosolutions", "nomd-technologies", "nov-inc", "nucore", "nuvento-systems", "nymbl", "obidos-technologies", "obvious-ai-technology",
        "offline-human-studios", "onesoft-technologies", "opshore-talent-solutions", "oracle", "orestes-technologies", "origent-technologies", "orion-india-systems", "ormeon-it-consulting",
        "orthofx", "outsource-partners-international", "overbrook-technology-services", "oxomo-systems", "oxomo-systems-international", "pagematics-india", "panashifzco-technology-solution", "paoyaila-animation-studios",
        "paradigm-it", "paulcart-e-commerce", "paypal", "pcs-india", "pearlsoft-technologies", "penguin-data-centre", "persisent-systems", "phases-india-technology-solutions",
        "pinetech-it-solutions", "pinmicro-india", "piserve-solutions", "pit-solutions", "pixdynamics", "planet-media-india", "portrave-solutions", "prevalent-ai",
        "primecrown-technologies", "privo-techcorp", "pueblo-shades", "pumex-infotech", "pwc", "qburst-technologies", "qc-verify", "quantum-acumen",
        "qubeslab-technologies", "qubiqon-consulting-india", "quest-global", "raintech-software", "rainybits-technology", "red-hat", "redux-network-redux", "regent-global-services-india",
        "retyn-business-solution", "rexav-llp", "rextech-studios", "riod-logic", "rm-education", "roberts-design-services", "rogersoft-technologies", "rr-donnelley",
        "ruby-seven-studios", "sands-lab", "sap", "sayone-technologies", "sbl-knowledge-services", "se-mentor-solutions", "seeroo-it-solutions", "seguro-technologies",
        "seidor-opentrends", "senscript-technologies", "servsys-technology-services", "sfo-technologies", "silverbloom-technologies", "simelabs-astek", "skybertech-it-innovation", "smec-automation",
        "snippetcommerce360", "softop-solutions", "softspace-infotech", "soulxes-technologies", "sparksupport-infotech", "spawoz-technologies", "speridian-technologies", "spiderline-technologies",
        "spiralcode-innovates", "steigend-it-solutions", "stepping-stone-consultancy-services", "strands-energy", "stream-perfect-global-services", "suntec-business-solutions", "supporthub360", "surveysparrow",
        "sustglobal", "synopsys", "synthite-it", "syriac-consultancy-services", "systalent-software", "talk-digital", "tamcherry-technologies", "tata-consultancy-services",
        "tata-elxsi", "tcs", "tech-aventure", "tech-mahindra", "techfriar-technologies", "techgentsia-software-technologies", "techneurons-consulting-solutions", "technowave-id-systems",
        "techpullers-technology-solutions", "techtaliya-informatics", "techversant-infotech", "techware-lab", "tecnostac-systems", "telious-technologies", "terrific-minds", "testing-mavens-software",
        "thinkpalm-technologies", "thomsun-infocare", "thoughtminds-system", "thriveminds-technologies", "titan-tech-emirates", "tnp-consultancy", "toobler-technologies", "toonz-media",
        "touchworld-technology", "tranzmeo", "travancore-analytics", "tukxi-india", "turnitin", "turqosoft-solutions", "tuttifrutti-games", "unilaw-global",
        "urolime", "ust-global", "v-guard", "vaisesika-consulting", "valuementor-infosec", "varishtha-infotech-services", "veeble-softtech", "verteil-technologies",
        "viewy-digital", "violet-frames", "vipoint-solutions", "virtual-impulse-technologies", "virtual-sys-technologies", "visa", "vistas-global-intellect", "vivish-technologies",
        "vmware", "vortexen-dynamics", "voxtron-solutions", "voyager-it-solutions", "voyon-technology", "vtrio-solutions", "vvdn-technologies", "wazeefa1-technologies",
        "webandcrafts", "webdura-technologies", "white-rabbit-group", "windfall-productions", "wipro", "wiq", "woc-branding-systems", "woodsman",
        "worksent-technologies", "woxro", "xerox", "yatnam-technologies", "yavun-technologies", "yellowfish-digital-innovations", "ynot-infosolutions", "yougotagift",
        "zafin", "zamorins-solutions", "zapare-technologies", "zealogics-it-solutions", "zellis-hr-india", "zinbay-india", "zinemind-technologies", "zoiteckh-informations-solutions",
    ],
    "visakhapatnam": [
        "accenture", "accubits", "adroit-software", "adroitec", "agilewarrior", "allsec-technologies", "amazon-development-centre", "andhra-university",
        "anomaly-solutions", "apogen-technologies", "appsfly-soft", "apptela", "artific", "athenahealth", "aurionpro-solutions", "axis-soft",
        "birlasoft", "bluechip-technologies", "bosch-global-software", "brainmobi", "brillio", "broadcom-india", "bugraker", "capgemini",
        "chargbee", "cigniti", "cisco-systems", "clever-infotech", "cloud-connect", "cloud-information", "coforge", "cognizant",
        "collabera", "concentrix", "concept-software", "conduent", "consonus-soft", "convo", "copacetic-solutions", "coral-software",
        "coromandel-it", "cosmic-soft", "cron-software", "cyber-soft", "cyber-solutions", "cyient", "danlaw-technologies", "data-quest",
        "data-solutions", "datalytx", "datavail", "dbs-software", "deccan-software", "dell-emc", "dell-international-services", "deloitte",
        "deloitte-us", "digital-soft", "disha-soft", "drl-soft", "dxc-technology", "dynamic-soft", "e-infochips", "eastern-soft",
        "elegant-soft", "ellipse-soft", "emerge-soft", "envision-soft", "epam-systems", "evol-soft", "excel-soft", "ey-gds",
        "firstsource", "focus-soft", "fore-soft", "freshworks", "genesis-soft", "genpact", "gitam-university", "global-soft",
        "google-india", "gss-soft", "hcl", "hcl-technologies", "hexaware", "hgs", "hitech-soft", "hpcl-it",
        "hsbc", "ibm", "ibm-india", "icore-soft", "idex-soft", "indus-soft", "info-soft", "infosys",
        "innowave-soft", "intech-soft", "intell-soft", "invicta-soft", "ion-soft", "iraya-soft", "jade-soft", "katalyst-soft",
        "kenexa", "klenty", "kode-soft", "kodnest", "kpit-technologies", "kpmg", "krystal-soft", "labyrinth-soft",
        "lighthouse-soft", "lnt-technology-services", "logic-soft", "ltimindtree", "machintel", "magic-soft", "mapmyindia", "mastek",
        "matrix-soft", "meridian-soft", "microsoft-india", "mindtree", "mobily-soft", "moxie", "mphasis", "mutually-human",
        "nagarro", "nara-soft", "ncr-corporation", "nectar-soft", "neo-soft", "niit-technologies", "nix-soft", "noble-soft",
        "novisync", "nvidia-india", "ocean-soft", "omega-soft", "oracle", "oracle-financial-services", "orbit-soft", "palm-soft",
        "paramatrix", "patronage", "peak-soft", "persistent-systems", "philips-india", "phonepe", "platinum-soft", "pragra",
        "precision-soft", "prime-soft", "pro-soft", "prudent", "publicis-sapient", "pulse-soft", "pulsus-group", "pwc",
        "qentelli", "qualcomm-india", "quantiphi", "quantum-soft", "quest-soft", "ramco-systems", "ramky-pharma-it", "rapid-soft",
        "razorpay", "redington", "reflex-soft", "reliance-soft", "royal-soft", "rubix-soft", "rudrayani-tech", "sai-soft",
        "salesforce-india", "sam-soft", "sap-labs", "sapphire-soft", "sasken-technologies", "satra-soft", "secur-soft", "seneca-soft",
        "sensiple", "servicenow", "shivam-soft", "siemens-technology", "sigma-soft", "silver-soft", "sipl", "skill-lync",
        "sky-soft", "softport", "solar-soft", "sonata-software", "spark-soft", "srishti-soft", "startek", "stellar-soft",
        "subex", "sum-soft", "sun-soft", "sutherland", "synergy-soft", "talent-soft", "tavant-technologies", "tcs",
        "tech-mahindra", "tech-soft", "techo", "tejas-soft", "teleperformance", "tessolve", "thinks-soft", "thoughtworks",
        "tirupati-soft", "trianz", "triton-soft", "ultra-soft", "uniphore", "unique-soft", "uniquisys", "ust-global",
        "vadhr-soft", "vajra-soft", "valuemomentum", "vector-soft", "vehant", "venus-soft", "vertex-soft", "verticurl",
        "vibrant-soft", "vicky-soft", "victory-soft", "vidya-soft", "vijay-soft", "visakha-software-solutions", "vishnu-soft", "vision-soft",
        "vivid-soft", "vmware-india", "vsap", "vsoft", "wavelabs", "wingify", "wipro", "wipro-digital",
        "wns", "zeal-soft", "zenith-soft", "zensar-technologies", "zephyr-soft", "zeus-soft", "zodiac-soft", "zoho",
        "zoho-analytics", "zoho-corporation", "zoho-people", "zoho-recruit", "zores-copper",
    ],
    "bhubaneswar": [
        "3i-infotech", "aabsys-it", "accenture", "adi-soft-solutions", "airbus", "ajatus-software", "amazon-web-services", "amdocs",
        "american-express", "anlage-infotech", "apex-software", "aranca", "argha-technologies", "aricent", "aspiresys", "atos-syntel",
        "avaya", "axis-bank-it", "bajaj-finserv-it", "bank-of-america-gcc", "barclays-it", "bcg-gamma", "birla-soft", "bnymellon",
        "boeing-it", "bosch-global", "brainium-softtech", "broadcom", "byjus", "cadence", "calpion-software", "capgemini",
        "catalyst-it-solutions", "cbre", "cdac-bhubaneswar", "centroxy-solutions", "cerner", "cgi", "cisco", "citi-gcc",
        "citius-tech", "cmots", "coforge", "cognizant", "collabrains", "compunnel-software", "comviva", "concentrix",
        "confluent-technologies", "coupa", "csm-technologies", "cummins-it", "cybercom-software", "cyient", "dabur-it", "datamatics",
        "deloitte", "deutsche-bank", "dhl-it", "diya-systems", "docusign", "dolby", "drdo-bhubaneswar", "ecentric-infotech",
        "emerson", "enosis-technology", "epam-systems", "equifax", "ergeon", "ericsson", "esspl", "exl-services",
        "expedia", "experian", "ey-gds", "f5-networks", "fidelity-international", "fis", "fiserv", "flipkart",
        "flyweb-it-solutions", "fortinet", "fujitsu", "futurious", "gartner", "ge-digital", "genpact", "global-innovations",
        "gm-infotech", "godrej-infotech", "goldman-sachs", "google", "grant-thornton", "grapecity", "harman", "hcl",
        "heaxa-solutions", "hexalearn-solutions", "hexaware", "highradius", "hitachi", "honeywell", "hornbill-technologies", "hp-inc",
        "hsbc", "huawei", "hybris-solutions", "hyscaler", "hyundai-it", "ibm", "ibm-listed", "iconsys-solutions",
        "in2it-technologies", "indiamart", "infosys", "ing-it", "innovaccer", "intel", "intone-technologies", "intuit",
        "iol-services", "itc-infotech", "itc-infotech-listed", "ixora-software", "jbm-software", "jigyasof", "jp-morgan", "jsw-software",
        "juniper-networks", "kale-logistics", "kalinga-software", "kantar", "kiit-incubation-startups", "kpit", "kpmg", "kraft-heinz",
        "kyndryl", "labs-24", "lakshya-soft", "larsen-and-toubro", "latentview-analytics", "lenovo", "lg-software", "linkedin",
        "linways-technologies", "lockheed-martin", "loreal-it", "ltimindtree", "lufthansa-systems", "luminous-infoways", "maersk-it", "mahindra-it",
        "mapmyindia", "marico-it", "marriott-digital", "marsh-mclennan", "maruti-suzuki-it", "mastercard", "mckinsey-knowledge-center", "mcleod-software",
        "medtronic", "mentis-software", "merck-it", "meta-platforms", "metlife", "microland", "micron", "microsoft",
        "mindfire-solutions", "minfy-technologies", "mitsubishi-it", "mobile-programming", "mobiloitte", "mobiotics", "moodys-analytics", "morgan-stanley",
        "motorola-solutions", "mphasis", "musigma", "mycaptain", "nagarro", "nalco-it", "ncode-software", "nec-corporation",
        "neebal-technologies", "neosoft-technologies", "netapp", "netscribes", "newgen-software", "nexvu-technologies", "nielsen", "nike-tech",
        "nimap-infotech", "nissan-digital", "nitor-infotech", "nokia", "novartis", "nucleus-software", "nunify", "nvidia",
        "o-hub-startups", "o9-solutions", "oasys-tech-solutions", "ocac", "odessa-technologies", "onelab-ventures", "onmobile", "opentext",
        "oracle", "panacea-soft", "panamax-infotech", "parangat-technologies", "payoda", "pepsico-it", "perficient", "petronas-it",
        "pfizer-it", "philips", "polaris-consulting", "pratian-technologies", "pro-digital-mind", "procter-and-gamble", "prolaborate", "propellum-technologies",
        "protiviti", "publicis-sapient", "pwc", "qburst-technologies", "qentelli", "qualcomm", "quinnox", "ramco-systems",
        "ramtech-software-solutions", "rankex-digital", "red-hat", "reliance-industries-it", "reliance-jio", "sabre", "sacumen", "sai-paramount-it-solutions",
        "samsung", "samyak-technologies", "sanofi", "sap-labs", "sapient", "schlumberger", "seflex-techno-solutions", "shell-it",
        "shopweb", "siemens", "silicon-techlab", "silicus-technologies", "skilrock-technologies", "smartlink-software", "snapdeal", "softility",
        "sokrati-technologies", "solartis", "sony-it", "splunk", "spotify", "standard-chartered", "sumitomo", "swadhin-it-solutions",
        "swash-convergence-technologies", "swiggy", "symantec", "t-mobile", "target", "tata-consultancy-services", "tatwa-technologies", "tech-mahindra",
        "techtss", "telstra", "tesla-it", "texas-instruments", "thermo-fisher", "thomson-reuters", "threatsys-technologies", "toyota-it",
        "ub-soft", "uber", "unilever", "united-health", "verizon", "vmware", "vodafone", "volkswagen-it",
        "volvo-it", "walmart-global-tech", "walt-disney", "way-india-software-solutions", "way-india-technology", "wells-fargo", "western-digital", "wipro",
        "xerox", "yamaha-it", "zalando", "zensar-technologies", "zoho", "zoom",
    ],
    "lucknow": [
        "aditus", "apexon", "appinventiv", "aptra-technology", "arivani-technologies", "augurs-technologies", "binary-numbers", "birlasoft",
        "brillio", "clagtech", "claritus-management-consulting", "codecreators", "coforge", "cvs-multi-services", "cyient", "daffodil-software",
        "digicrown", "genpact", "globallogic", "hanumant-technology", "hcltech", "hgs", "hinduja-global-solutions", "infosys",
        "kellton-tech-solutions", "ksolves", "lti-mindtree", "maq-software", "mobiweb", "mphasis", "nagarro", "ntt-data",
        "nucleus-software", "oj-commerce", "persistent-systems", "publicis-sapient", "rudra-innovatives", "sabhi-digital", "sopra-steria", "sysnet-global-technologies",
        "tcs", "tech-mahindra", "technomark-solutions", "trident-techlabs", "underpin-services", "united-layer", "vexil-infotech", "webkul",
        "wipro", "xebia",
    ],
    "nagpur": [
        "3i-infotech", "accenture", "acensium", "alliancetek", "atos-syntel", "blazeclan-technologies", "bridgei2i-analytics", "capgemini",
        "cloudthat-technologies", "clover-infotech", "cognizant", "cybage", "datametica", "edcast", "futurism-technologies", "globallogic",
        "graymatter-software", "hcltech", "hexaware-technologies", "ibm", "indus-valley-partners", "inextloop", "infosys", "knackforge",
        "knoldus", "mahindra-and-mahindra-it", "mindfire-solutions", "newvision-software", "nitor-infotech", "omnibridge", "oracle", "persistent-systems",
        "polaris-consulting", "prowess-software", "qai-global", "quick-heal-technologies", "radical-technologies", "sap-labs-india", "simplilearn", "softenger",
        "suntec-india", "tcs", "tech-mahindra", "vertexsoft", "webtunix-ai", "wipro", "yash-technologies", "zensar-technologies",
    ],
    "surat": [
        "addweb-solution", "advantal-technologies", "alliance-web-solution", "andromeda-technologies", "annex-india", "askgalore-digital", "azilen-technologies", "bacancy-technology",
        "biztech-consultancy", "brainvire-infotech", "brillbrains-technosoft", "creative-web-solutions", "cybage", "dotcom-creations", "e2logy", "elasticrun",
        "hcltech", "infosys", "jewelsoft-technologies", "krish-technolabs", "lattice-bridge-infotech", "lbis", "magneto-it-solutions", "mojotech",
        "nexus-software", "oneclick-it-consultancy", "pixelcrayons", "pixlogix", "positron-technologies", "quytech", "radixweb", "rightway-solution",
        "satva-solutions", "savvient-technologies", "shaligram-infotech", "sourcefuse-technologies", "space-o-technologies", "sphinx-worldbiz", "stridely-solutions", "svam-international",
        "tatvasoft", "tcs", "tech-mahindra", "techevents", "veersa-technologies", "webclues-infotech", "wipro", "zealousweb",
    ],
    "bhopal": [
        "accenture", "aptra-technology", "aujas-networks", "axestrack-software-solutions", "birlasoft", "blessed-solutions", "blu-ocean-technologies", "brainstorm-force",
        "capgemini", "codecraft-technologies", "crownstack-technologies", "cyber-infrastructure", "cybrom-technology", "divami-designs", "hcltech", "impetus-digital",
        "infosys", "innerix", "integrated-tech9", "mark-software-systems", "mindit-solutions", "nexus-digital", "nlineaxis", "novaleaf-software",
        "objectone-information-systems", "paramatrix-technologies", "pnc-infotech", "primustech", "rolta-india", "scorg-technologies", "softonix", "softpencil",
        "software-technology-group", "spiderslab", "synnefa", "synsoft-global", "tcs", "tech-mahindra", "technogetic", "thinksys",
        "trident-techlabs", "truechip", "vezbi-digital", "webnyxa-technologies", "wipro",
    ],
    "patna": [
        "accenture", "adwebtech", "anika-technologies", "br-softech", "braintech-solutions", "brainvire-infotech", "capgemini", "cliniops",
        "cloudphotonix", "cloudthat-technologies", "coforge", "daksha-it-solutions", "digitallinks", "dxc-technology", "genpact", "hcltech",
        "hexaware-technologies", "ibm", "idbi-intech", "infosys", "karvy-infotech", "kenyt-technologies", "landt-infotech", "litmus7",
        "logicrays", "lti-mindtree", "netmaxims-technologies", "netweb-technologies", "ntt-data", "outworx", "path-infotech", "persistent-systems",
        "praescient-analytics", "pyramid-it-consulting", "silverwing-technology", "sisl-infotech", "space-o-nepal", "ssb-tech", "systools-software", "tcf-global",
        "tcs", "techienest", "technocomp-associates", "techved", "webslinger-digital", "wipro",
    ],
    "mysore": [
        "abb-india", "accenture", "aditya-birla-minacs", "adobe", "adp", "alorica", "altair", "american-express-gcc",
        "ansys", "aptiv", "atos-syntel", "autodesk", "autoliv", "aws", "bank-of-america-gcc", "barclays-gcc",
        "billdesk", "birlasoft", "bny-mellon", "bosch-global", "brillio", "broadridge", "browserstack", "cadence",
        "capgemini", "ccavenue", "chargebee", "cigniti", "coforge", "cognizant", "continental-automotive", "credit-suisse-gcc",
        "cyient", "dassault-systemes", "dell", "dell-technologies", "deutsche-bank-gcc", "dxc-technology", "emerson", "eurofins-it",
        "exl-service", "faurecia", "fidelity-investments-gcc", "firstsource", "flipkart", "freecharge", "freshworks", "fujitsu",
        "games-24x7", "genpact", "goldman-sachs-gcc", "happiest-minds", "harman", "hcl-technologies", "hgs", "hitachi-vantara",
        "honeywell", "hsbc-gcc", "huawei-technologies", "icore", "infosys", "infosys-bpm", "intelenet", "intrsoft",
        "jp-morgan-gcc", "junglee-games", "kissflow", "kiwiqa", "kpit", "lg-soft", "lloyds-banking-gcc", "lnt-technology-services",
        "ltimindtree", "madbrains", "magna-international", "mallow-technologies", "mastercard", "mathworks", "microsoft", "mindtree",
        "mobikwik", "moonshot-games", "morgan-stanley-gcc", "mphasis", "myntra", "nagarro", "natwest-gcc", "nec-corporation",
        "niveus-solutions", "ntt-data", "ojas-innovative", "opentext", "oracle", "paypal", "payu", "pegasystems",
        "persisent-systems", "phonepe", "playsimple-games", "progress-software", "ptc", "qa-infotech", "qentelli", "quest-global",
        "quick-heal", "razorpya", "robosoft", "rocket-software", "rockwell-automation", "sage-software", "salesforce", "samsung-software",
        "sap-labs", "schaeffler", "schneider-electric", "serco", "servicenow", "siemens-technology", "sitel", "skf",
        "slk-global", "societe-generale-gcc", "solarwinds", "square", "standard-chartered-gcc", "startek", "state-street-gcc", "stripe",
        "sutherland-global", "sykes", "synopsys", "tcs", "tcs-bpo", "tech-mahindra", "teleperformance", "testingxperts",
        "toshiba-software", "trimble", "ttec", "tvs-tech", "ubs-gcc", "unisys", "valeo", "visa",
        "visteon", "wells-fargo-gcc", "wipro", "wipro-bps", "wns-global", "zf-group", "zoho", "zycus",
    ],
    "madurai": [
        "24-7-customer", "6d-technologies", "accenture", "aegis-bpo", "allsec-technologies", "altran", "amazon", "aspire-systems",
        "bally-technologies", "caliber-technologies", "capgemini", "capsilon", "coda-global", "cogent", "cognizant", "concentrix",
        "css-corp", "deloitte", "e4e-software", "everonn", "exl-service", "ey", "fidelity-international-gcc", "firstsource",
        "fis-global", "flipkart", "genpact", "global-tax", "google", "hcl-technologies", "healthassure", "hgs",
        "ibm", "infosys", "intelenet", "inube-solutions", "itc-infotech", "jeevasoft", "kiya-ai", "kla-software",
        "kpmg", "lanco-infotech", "ltimindtree", "mastek", "microsoft", "movate", "mresult", "nagarjuna-software",
        "nalashaa-solutions", "ntt-data", "ntt-global", "oracle", "palred-technologies", "polaris-consulting", "prologic", "pwc",
        "r-systems", "ram-informatics", "ramco-systems", "rapid-technologies", "replicon", "sasken", "serco", "sify-technologies",
        "sisel", "softage", "softcell", "sona-software", "spintel", "startek", "subex", "sureprep",
        "sutherland-global", "synechron", "tania-solutions", "tara-software", "tcs", "tech-mahindra", "tejas-networks", "teleperformance",
        "tessolve", "thinksoft", "tvs-motors-it", "tvs-next", "ust-global", "valuelabs", "vayam", "veda-info",
        "verizon-data", "versant", "virtusa", "visiontek", "vvdn-technologies", "wabtec", "wavelabs", "white-horse",
        "winsoft", "wipro", "wns-global", "xavient", "xtremetech", "yash-technologies", "zoho", "zylog-systems",
    ],
    "vadodara": [
        "3di-systems", "accenture", "acquiscent", "adroit-software", "ahmic-solutions", "alpha-technologies", "anchor-software", "apollo-infotech",
        "avidings", "axyz-solutions", "birlasoft", "brainsight-technologies", "cliantha-research", "compucom-institute", "crystal-solutions", "cyient",
        "doyen-it-solutions", "e-infotech", "electro-systems-associates", "hatsoff-solutions", "hcltech", "hexaware-technologies", "infosys", "jade-magnet",
        "landt-technology-services", "ltts", "macweb-technology", "microimage-solutions", "mindzen-technologies", "netweb-technologies", "nyxgen", "pioneer-e-solutions",
        "plusware-solutions", "pragetech", "schneider-electric-it", "silicon-it-solution", "sofmen", "synbiosys", "synergy-infonet", "tcs",
        "technoapps", "tensor-tech", "unique-infotech", "unisoft-technologies", "wipro", "zydus-technologies",
    ],
    "nashik": [
        "accenture", "agilesoft-systems", "anktech", "atlas-copco-it", "avery-dennison-is", "avigna-technologies", "bosch-global-software-technologies", "capgemini",
        "ceat-it", "clover-infotech", "coats-digital", "coditas", "crompton-greaves-it", "dabur-it", "datacipher", "denova-it-solutions",
        "epicenter-technologies", "futurism-technologies", "ge-digital-india", "glassbeam", "glaxosmithkline-it", "hcltech", "hul-it", "indus-net-technologies",
        "infosys", "kirloskar-it", "kritikal-solutions", "ksolves", "landt-infotech", "mindscripts", "neebal-technologies", "nitor-infotech",
        "pace-business-machines", "persistence-software", "quibus-tech", "smartdata-enterprises", "softway-solutions", "star-knowledge", "tcs", "thyssenkrupp-it",
        "webreinvent", "wipro", "wns-global-services", "xcelpros", "yashash-git", "zinghr",
    ],
    "rajkot": [
        "addweb-solution", "advancetech", "agile-infoways", "aglowid-it-solutions", "alphabin-technology-consulting", "appsgrid", "azilen-technologies", "b2bsoft",
        "binary-numbers", "brainysoft", "clarion-technologies", "codecreator-solutions", "cronj-technologies", "cybage", "digital-dovetail", "dotline-webmedia",
        "girnar-software", "helios-solutions", "indianic", "infobeans", "itpath-solutions", "krewin-technologies", "mgineer", "nextloop-digital",
        "oneclick-it-consultancy", "quantolabs", "radixweb", "right-infoservice", "rk-infotech", "silicon-it-solution", "siyana-infotech", "sochin-technologies",
        "sofmen", "softvan", "space-o-technologies", "tatvasoft", "techeer-techsys", "trangile-services", "upforce-tech", "webcodepro",
        "weboccult-technologies", "xlntech-solutions",
    ],
    "thane": [
        "3i-infotech", "accenture", "anvik-technologies", "azilen-technologies", "binary-spectrum", "bodhtree-consulting", "capgemini", "cloudthat-technologies",
        "clover-infotech", "cognizant", "cybage", "embience", "futurism-technologies", "globallogic", "harjai-computers", "hcltech",
        "hexaware-technologies", "ibm", "indium-software", "infosys", "interlink-technologies", "lti-mindtree", "lucent-innovation", "mastek",
        "mokshit-technologies", "msys-technologies", "neosoft-technologies", "optimum-solutions", "oracle-financial-services", "palladium-digital", "persistent-systems", "pro-sapien",
        "saksoft", "samarth-infotech", "scaleneworks", "tcs", "tech-mahindra", "webreinvent", "winjit-technologies", "wipro",
        "zensar-technologies",
    ],
    "agra": [
        "accenture", "acumensoft", "adwala", "agile-soft-systems", "anktech", "beeta-techsoft", "birlasoft", "brainium-solutions",
        "bugsbunny", "capgemini", "cloudio-technologies", "coherent-tech", "cyient", "daffodil-software", "datametica", "dexsoft-technologies",
        "digital-pathshala", "eastrosoft", "genpact", "grace-info-solutions", "hcltech", "hexaware-technologies", "ibm", "infosys",
        "kaynes-technology", "microlent-systems", "ndot-technologies", "ntech-global", "ntt-data", "omind-technologies", "paramatrix-technologies", "persistent-systems",
        "prowareness-technologies", "r-systems", "softpro-india", "sonata-software", "srv-infotech", "tcs", "tech-mahindra", "technohertz",
        "trigma", "vtc-softwares", "webs-crucible", "wipro", "xenonstack",
    ],
    "varanasi": [
        "accenture", "acutesoft", "anika-technologies", "aptitech", "aptratech", "birlasoft", "brainium-technologies", "capgemini",
        "cloudtechtiq", "codedreams", "coforge", "cyient", "digitalmark", "e-foshan-digital", "genpact", "hcltech",
        "hexaware-technologies", "hyperthink-systems", "ibm", "infosys", "innosoft", "logicloom", "lti-mindtree", "microlent-solutions",
        "mobulous", "ndot-technology", "ntt-data", "persistent-systems", "proprofs", "r-systems", "rudraksh-software", "sarvin-solutions",
        "smarther", "softpro-india", "solutionbuggy", "sonata-software", "srv-infotech", "tcs", "tech-mahindra", "technoapps",
        "technohertz", "trigma", "vtc-softwares", "webnse", "wipro",
    ],
    "aurangabad": [
        "3dplm-software", "accenture", "anik-india", "aurangabad-softtech", "bharat-software", "birlasoft", "capgemini", "classic-software",
        "codebridge-technologies", "cybersoft-technologies", "cyient", "devries-it-solutions", "digitech-consultants", "hcltech", "hexaware-technologies", "ibm",
        "infosys", "intelliswift-software", "jay-it-services", "microlink-it-solutions", "mindcloud-technologies", "netwebtech", "persistent-systems", "pixelsoft-solutions",
        "prime-tech-ventures", "protech-india", "quick-heal-technologies", "reliance-jio-infocomm-it", "robosoft-digital", "seamless-infotech", "sg-software-solutions", "siemens-technology",
        "skylark-software", "softcel-technologies", "stridely-solutions", "symbiosis-technologies", "tcs", "tech-mahindra", "technoforte-software", "webkype-technologies",
        "wipro", "zenith-infotech",
    ],
    "ranchi": [
        "accenture", "aditya-birla-minacs", "adventuresoft", "anika-technologies", "appsquadz", "aptratech", "biharsoft-technologies", "brainium-solutions",
        "capgemini", "citysoft-solutions", "coforge", "compuage-infocom", "connectinfosoft", "cyient", "data-infotech", "dxc-technology",
        "eastern-software-solutions", "fortune-it-solutions", "genpact", "gt-software-technologies", "hcltech", "hexaware-technologies", "hunter-systems", "ibm",
        "infosys", "infoweb-solutions", "kg-invicta-services", "lti-mindtree", "neoteric-infusion", "ntt-data", "pan-india-consultancy", "paramatrix-technologies",
        "persistent-systems", "ranchi-infotech", "sabarigiri-technologies", "sonata-software", "srt-solutions", "srv-infotech", "tcs", "tech-mahindra",
        "technoapps", "techsoft-india", "trident-techlabs", "websan-solutions", "wipro",
    ],
    "guwahati": [
        "accenture", "adrg", "amtron", "assam-electronics-development-corp", "assam-it-solutions", "asterisk-software", "barbhag-infosystem", "birlasoft",
        "brainium-technologies", "capgemini", "coforge", "cyient", "cynosure-technologies", "edgesoft-solutions", "genpact", "gowebbo",
        "hcltech", "hexaware-technologies", "hpcns", "ibm", "info-valley", "infosys", "innosoft-technologies", "kal-india",
        "lti-mindtree", "merittrac-services", "mind-vision-software", "mindtree-digital", "multicon-technologies", "north-east-infotech", "northgate-technologies", "ntt-data",
        "numaligarh-refinery-it", "oil-india-it", "ongc-it", "persistent-systems", "sabarigiri-technologies", "solutionassam", "srv-infotech", "sysedge-solutions",
        "tcs", "tech-mahindra", "technoapps", "tridiagonal-solutions", "unbxd", "wipro", "xerago-e-biz-services",
    ],
    "dehradun": [
        "accenture", "appsquadz", "aptratech", "badruka-infotech", "birlasoft", "capgemini", "clouddatatech", "coforge",
        "cyient", "data-infotech", "dehradun-it-solutions", "diebold-nixdorf", "digitech-solutions", "dxc-technology", "eastern-software-solutions", "fortune-networks",
        "garuda-it-solutions", "genpact", "globallogic", "hcltech", "hexaware-technologies", "himalayan-it-solutions", "hunter-systems", "ibm",
        "infosys", "ionidea", "lti-mindtree", "magnus-technologies", "ntt-data", "onix-solutions", "pan-india-consultants", "persistent-systems",
        "polaris-consulting", "ranchi-tech-solutions", "sigma-infosolutions", "softpro-solutions", "sonata-software", "srv-infotech", "symphony-teleca", "tcs",
        "tech-mahindra", "technoapps", "technocraft-solutions", "trident-techlabs", "websan-solutions", "wipro",
    ],
    "goa": [
        "3i-infotech", "accenture", "addweb-solution", "aglowid-it-solutions", "anktech", "annex-india", "bd-software-distribution", "birlasoft",
        "blazeclan-technologies", "capgemini", "clarion-technologies", "coforge", "cognizant", "cyient", "datacipher", "datametica",
        "diebold-nixdorf", "globallogic", "goa-institute-of-management-it", "goa-it-solutions", "gowebbo", "hcltech", "hexaware-technologies", "ibm",
        "indecomm-global-services", "infosys", "lti-mindtree", "mastek", "ntt-data", "one97-communications", "oracle-financial-services", "persistent-systems",
        "rk-infotech", "scoreme-solutions", "scry-analytics", "sonata-software", "synechron-technology", "systango-technologies", "tcs", "tech-mahindra",
        "theta-technovision", "webreinvent", "wipro", "xcelpros", "zentek-solutions",
    ],
    "remote": [
        "100ms", "atlan", "browserstack", "devtron", "dhiwise", "duckduckgo",
        "gitlab", "hasura", "middleware", "portkey", "postman", "truefoundry",
        "unfoldai",
    ],
}

UNIVERSAL_STARTUPS = [
    "100ms", "accenture", "adobe", "amazon", "apple", "atlan", "atlassian",
    "bharatpe", "browserstack", "capgemini", "chargebee", "cisco", "clevertap",
    "cognizant", "cred", "darwinbox", "databricks", "deloitte", "devtron",
    "dhiwise", "dream11", "elastic", "flipkart", "fractal-analytics",
    "freshworks", "gitlab", "google", "groww", "gushwork", "hasura",
    "hcl", "highradius", "ibm", "infosys", "intel", "invideo", "juspay",
    "keka", "lambdatest", "lenskart", "ltimindtree", "mastercard",
    "meesho", "meta", "microsoft", "middleware", "mphasis", "nvidia",
    "nykaa", "oracle", "paytm", "persistent-systems", "phonepe",
    "plotline", "plivo", "policybazaar", "portkey", "postman", "qualcomm",
    "razorpay", "samsung", "sap", "scalereal", "segwise", "servicenow",
    "skan", "slice", "sprinto", "stripe", "superops", "swiggy", "tcs",
    "tech-mahindra", "truefoundry", "twilio", "unfoldai", "vmware",
    "whatfix", "wipro", "yellowai", "zenoti", "zepto", "zerodha",
    "zeta", "zoho", "zomato",
]


async def fetch_jobs_for_ats_company(company_name: str, company_slug: str = "") -> list[dict]:
    """Try fetching jobs for a company across Greenhouse, Lever, Ashby, Freshteam, Zoho Recruit APIs."""
    base_raw = company_slug or company_name
    slug_candidates = [
        re.sub(r"[^a-zA-Z0-9_\-]", "", base_raw.lower().strip()),
        re.sub(r"[^a-zA-Z0-9]", "", base_raw.lower().strip()),
        re.sub(r"\s+", "-", base_raw.lower().strip()),
    ]
    seen_slugs = set()

    for slug in slug_candidates:
        if not slug or slug in seen_slugs:
            continue
        seen_slugs.add(slug)

        # Try Greenhouse
        gh_jobs = await fetch_greenhouse_jobs(slug)
        if gh_jobs:
            return gh_jobs

        # Try Lever
        lever_jobs = await fetch_lever_jobs(slug)
        if lever_jobs:
            return lever_jobs

        # Try Ashby
        ashby_jobs = await fetch_ashby_jobs(slug)
        if ashby_jobs:
            return ashby_jobs

        # Try Freshteam
        ft_jobs = await fetch_freshteam_jobs(slug)
        if ft_jobs:
            return ft_jobs

        # Try Zoho Recruit
        zoho_jobs = await fetch_zoho_jobs(slug)
        if zoho_jobs:
            return zoho_jobs

    return []


ROLE_SYNONYMS = {
    "software engineer": ["software", "engineer", "developer", "sde", "backend", "frontend", "full stack", "fullstack", "python", "java", "node", "react", "golang"],
    "frontend developer": ["frontend", "react", "vue", "angular", "javascript", "typescript", "ui engineer", "web developer"],
    "backend developer": ["backend", "python", "node", "java", "golang", "ruby", "django", "fastapi", "spring"],
    "data scientist": ["data scientist", "data engineer", "machine learning", "ml engineer", "ai engineer"],
    "full stack developer": ["full stack", "fullstack", "software engineer", "developer", "sde"],
}


async def fetch_hub_ats_jobs(location: str, role: str, max_jobs: int = 40) -> list[dict]:
    """Concurrently probe 50+ startup ATS boards for a target tech hub and role.

    Bypasses fragile web search engines, returning structured JSON instantly.
    """
    import asyncio

    city_key = location.lower().strip()
    if "bangalore" in city_key or "bengaluru" in city_key:
        city_key = "bengaluru"
    elif "hyderabad" in city_key or "secunderabad" in city_key:
        city_key = "hyderabad"
    elif "mumbai" in city_key or "bombay" in city_key:
        city_key = "mumbai"
    elif "delhi" in city_key or "noida" in city_key or "gurgaon" in city_key or "gurugram" in city_key:
        city_key = "ncr"
    elif "pune" in city_key:
        city_key = "pune"
    elif "chennai" in city_key or "madras" in city_key:
        city_key = "chennai"
    elif "kolkata" in city_key or "calcutta" in city_key:
        city_key = "kolkata"
    elif "ahmedabad" in city_key:
        city_key = "ahmedabad"
    elif "jaipur" in city_key:
        city_key = "jaipur"
    elif "kochi" in city_key or "cochin" in city_key or "ernakulam" in city_key:
        city_key = "kochi"
    elif "chandigarh" in city_key or "mohali" in city_key:
        city_key = "chandigarh"
    elif "indore" in city_key:
        city_key = "indore"
    elif "coimbatore" in city_key:
        city_key = "coimbatore"
    elif "trivandrum" in city_key or "thiruvananthapuram" in city_key:
        city_key = "trivandrum"
    elif "vizag" in city_key or "visakhapatnam" in city_key:
        city_key = "visakhapatnam"
    elif "bhubaneswar" in city_key or "bhubaneshwar" in city_key:
        city_key = "bhubaneswar"
    elif "lucknow" in city_key:
        city_key = "lucknow"
    elif "nagpur" in city_key:
        city_key = "nagpur"
    elif "surat" in city_key:
        city_key = "surat"
    elif "bhopal" in city_key:
        city_key = "bhopal"
    elif "patna" in city_key:
        city_key = "patna"
    elif "mysore" in city_key or "mysuru" in city_key:
        city_key = "mysore"
    elif "madurai" in city_key:
        city_key = "madurai"
    elif "vadodara" in city_key or "baroda" in city_key:
        city_key = "vadodara"
    elif "nashik" in city_key:
        city_key = "nashik"
    elif "rajkot" in city_key:
        city_key = "rajkot"
    elif "thane" in city_key:
        city_key = "thane"
    elif "agra" in city_key:
        city_key = "agra"
    elif "varanasi" in city_key or "banaras" in city_key:
        city_key = "varanasi"
    elif "aurangabad" in city_key:
        city_key = "aurangabad"
    elif "ranchi" in city_key:
        city_key = "ranchi"
    elif "guwahati" in city_key:
        city_key = "guwahati"
    elif "dehradun" in city_key:
        city_key = "dehradun"
    elif "goa" in city_key:
        city_key = "goa"
    else:
        city_key = "remote"

    target_slugs = list(TECH_HUB_STARTUPS.get(city_key, TECH_HUB_STARTUPS["bengaluru"]))
    for s in UNIVERSAL_STARTUPS:
        if s not in target_slugs:
            target_slugs.append(s)

    # Randomly shuffle target slugs to ensure variety across searches
    random.shuffle(target_slugs)

    log.info("direct_ats_hub_scan_started", city=city_key, slug_count=len(target_slugs), role=role)

    # Gather jobs concurrently
    tasks = [fetch_jobs_for_ats_company(slug, slug) for slug in target_slugs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    
    # Build synonym keywords for matching
    role_lower = role.lower().strip()
    synonyms = ROLE_SYNONYMS.get(role_lower, [t.strip().lower() for t in role.split() if len(t.strip()) > 2])

    for res in results:
        if isinstance(res, list):
            for job in res:
                title = job.get("title", "").lower()
                jd = job.get("jd_text", "").lower()
                loc = job.get("location", "").lower()

                # Flexible relevance check
                matches_role = any(syn in title for syn in synonyms) or ("engineer" in title or "developer" in title or "sde" in title or "architect" in title)
                if not matches_role:
                    continue

                # Flexible location check: city name, remote, or india
                matches_loc = not location or city_key in loc or "remote" in loc or "india" in loc or "remote" in title or loc == "" or loc == "india"

                if matches_loc:
                    all_jobs.append(job)
                    if len(all_jobs) >= max_jobs:
                        break

        if len(all_jobs) >= max_jobs:
            break

    log.info("direct_ats_hub_scan_complete", city=city_key, jobs_found=len(all_jobs))
    return all_jobs


