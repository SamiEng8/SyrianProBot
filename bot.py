import json
import os
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.transfermarkt.com/detailsuche/spielerdetail/suche/"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "en-US,en;q=0.9",
}

DATA_DIR = Path("data")
SEEN_FILE = DATA_DIR / "seen_players.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYRIA_ID = 163

CLUB_COUNTRIES = {
    3: "Albania",
    4: "Algeria",
    5: "Andorra",
    6: "Angola",
    9: "Argentina",
    10: "Armenia",
    12: "Australia",
    127: "Austria",
    13: "Azerbaijan",
    15: "Bahrain",
    18: "Belarus",
    19: "Belgium",
    23: "Bolivia",
    24: "Bosnia-Herzegovina",
    26: "Brazil",
    276: "British India",
    231: "British Virgin Islands",
    28: "Bulgaria",
    31: "Cameroon",
    80: "Canada",
    32: "Cape Verde",
    138: "Central African Republic",
    171: "Chad",
    33: "Chile",
    34: "China",
    164: "Chinese Taipei",
    83: "Colombia",
    85: "Congo",
    36: "Costa Rica",
    38: "Cote d'Ivoire",
    37: "Croatia",
    220: "CSSR",
    88: "Cuba",
    188: "Cyprus",
    172: "Czech Republic",
    39: "Denmark",
    42: "Dominica",
    43: "Dominican Republic",
    193: "DR Congo",
    222: "East Germany (GDR)",
    44: "Ecuador",
    2: "Egypt",
    45: "El Salvador",
    189: "England",
    47: "Estonia",
    11: "Ethiopia",
    49: "Finland",
    50: "France",
    51: "Gabon",
    53: "Georgia",
    40: "Germany",
    54: "Ghana",
    56: "Greece",
    66: "Honduras",
    218: "Hongkong",
    178: "Hungary",
    73: "Iceland",
    67: "India",
    68: "Indonesia",
    71: "Iran",
    70: "Iraq",
    72: "Ireland",
    74: "Israel",
    75: "Italy",
    76: "Jamaica",
    77: "Japan",
    78: "Jordan",
    223: "Jugoslawien (SFR)",
    81: "Kazakhstan",
    82: "Kenya",
    86: "Korea, North",
    87: "Korea, South",
    244: "Kosovo",
    89: "Kuwait",
    90: "Kyrgyzstan",
    92: "Latvia",
    94: "Lebanon",
    96: "Libya",
    98: "Lithuania",
    99: "Luxembourg",
    274: "Macedonia",
    103: "Malaysia",
    104: "Maldives",
    105: "Mali",
    106: "Malta",
    279: "Mandate for Palestine",
    257: "Marshall Islands",
    207: "Martinique",
    108: "Mauritania",
    110: "Mexico",
    112: "Moldova",
    113: "Monaco",
    216: "Montenegro",
    107: "Morocco",
    116: "Myanmar",
    122: "Netherlands",
    227: "Netherlands Antilles",
    255: "Netherlands East India",
    236: "New Caledonia",
    120: "New Zealand",
    121: "Nicaragua",
    123: "Niger",
    124: "Nigeria",
    100: "North Macedonia",
    192: "Northern Ireland",
    268: "Northern Mariana Islands",
    125: "Norway",
    126: "Oman",
    240: "Palestine",
    130: "Panama",
    132: "Paraguay",
    259: "People's republic of the Congo",
    133: "Peru",
    134: "Philippines",
    135: "Poland",
    136: "Portugal",
    228: "Puerto Rico",
    137: "Qatar",
    140: "Romania",
    141: "Russia",
    146: "Saudi Arabia",
    190: "Scotland",
    149: "Senegal",
    215: "Serbia",
    150: "Serbia and Montenegro",
    153: "Singapore",
    154: "Slovakia",
    155: "Slovenia",
    69: "Solomon Islands",
    156: "Somalia",
    159: "South Africa",
    262: "Southern Sudan",
    157: "Spain",
    158: "Sri Lanka",
    160: "Sudan",
    161: "Suriname",
    273: "Swaziland",
    147: "Sweden",
    148: "Switzerland",
    165: "Tajikistan",
    167: "Thailand",
    170: "Trinidad and Tobago",
    173: "Tunisia",
    174: "Türkiye",
    175: "Turkmenistan",
    226: "Turks- and Caicosinseln",
    221: "UdSSR",
    176: "Uganda",
    177: "Ukraine",
    183: "United Arab Emirates",
    264: "United Kingdom",
    184: "United States",
    179: "Uruguay",
    180: "Uzbekistan",
    182: "Venezuela",
    185: "Vietnam",
    191: "Wales",
    186: "Yemen",
    258: "Yugoslavia (Republic)",
}

POSSIBLE_POSITIONS = [
    "Goalkeeper",
    "Sweeper",
    "Centre-Back",
    "Left-Back",
    "Right-Back",
    "Defensive Midfield",
    "Central Midfield",
    "Right Midfield",
    "Left Midfield",
    "Attacking Midfield",
    "Left Winger",
    "Right Winger",
    "Second Striker",
    "Centre-Forward",
    "Striker",
    "Forward",
    "Winger",
    "Midfielder",
    "Defender",
    "Full-Back",
    "Wing-Back",
    "Attack",
    "Midfield",
    "Defence",
]

POSITION_ALIASES = [
    ("Centre-Forward", ["centre-forward", "center-forward", "striker"]),
    ("Second Striker", ["second striker", "support striker"]),
    ("Right Winger", ["right winger", "right wing"]),
    ("Left Winger", ["left winger", "left wing"]),
    ("Attacking Midfield", ["attacking midfield", "attacking midfielder", "cam"]),
    ("Central Midfield", ["central midfield", "central midfielder", "midfield"]),
    ("Defensive Midfield", ["defensive midfield", "defensive midfielder", "dm"]),
    ("Right Midfield", ["right midfield", "right midfielder"]),
    ("Left Midfield", ["left midfield", "left midfielder"]),
    ("Centre-Back", ["centre-back", "center-back", "centre back", "center back"]),
    ("Right-Back", ["right-back", "right back", "full-back", "right full-back", "right wing-back"]),
    ("Left-Back", ["left-back", "left back", "left full-back", "left wing-back"]),
    ("Goalkeeper", ["goalkeeper", "keeper"]),
    ("Defender", ["defender", "defence"]),
    ("Midfielder", ["midfielder"]),
    ("Forward", ["forward", "attack"]),
]

INVALID_CLUB_LABELS = {
    "Syria",
    "Returnee",
    "New arrival",
    "Without Club",
    "Retired",
    "Career break",
    "Unknown",
    "Winter signing",
}


def load_seen():
    if not SEEN_FILE.exists():
        return set()
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen_ids):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen_ids)), f, ensure_ascii=False, indent=2)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()


def flag_for_country(country):
    flags = {
        "United Arab Emirates": "🇦🇪",
        "Qatar": "🇶🇦",
        "Saudi Arabia": "🇸🇦",
        "Bahrain": "🇧🇭",
        "Jordan": "🇯🇴",
        "Iraq": "🇮🇶",
        "Lebanon": "🇱🇧",
        "Türkiye": "🇹🇷",
        "Germany": "🇩🇪",
        "Sweden": "🇸🇪",
        "Norway": "🇳🇴",
        "Denmark": "🇩🇰",
        "Netherlands": "🇳🇱",
        "Belgium": "🇧🇪",
        "France": "🇫🇷",
        "Spain": "🇪🇸",
        "Italy": "🇮🇹",
        "England": "🏴",
        "Scotland": "🏴",
        "Austria": "🇦🇹",
        "Switzerland": "🇨🇭",
        "Greece": "🇬🇷",
        "Cyprus": "🇨🇾",
        "Romania": "🇷🇴",
        "Bulgaria": "🇧🇬",
        "Armenia": "🇦🇲",
        "Russia": "🇷🇺",
        "United States": "🇺🇸",
        "Canada": "🇨🇦",
        "Australia": "🇦🇺",
        "Haiti": "🇭🇹",
        "Afghanistan": "🇦🇫",
        "Albania": "🇦🇱",
        "Algeria": "🇩🇿",
        "American Samoa": "🇦🇸",
        "American Virgin Islands": "🇻🇮",
        "Andorra": "🇦🇩",
        "Angola": "🇦🇴",
        "Anguilla": "🇦🇮",
        "Antigua and Barbuda": "🇦🇬",
        "Argentina": "🇦🇷",
        "Aruba": "🇦🇼",
        "Azerbaijan": "🇦🇿",
        "Bahamas": "🇧🇸",
        "Bangladesh": "🇧🇩",
        "Barbados": "🇧🇧",
        "Belarus": "🇧🇾",
        "Belize": "🇧🇿",
        "Benin": "🇧🇯",
        "Bermuda": "🇧🇲",
        "Bhutan": "🇧🇹",
        "Bolivia": "🇧🇴",
        "Bonaire": "🇧🇶",
        "Bosnia-Herzegovina": "🇧🇦",
        "Botswana": "🇧🇼",
        "Brazil": "🇧🇷",
        "British India": "🏳️",
        "British Virgin Islands": "🇻🇬",
        "Brunei Darussalam": "🇧🇳",
        "Burkina Faso": "🇧🇫",
        "Burundi": "🇧🇮",
        "Cambodia": "🇰🇭",
        "Cameroon": "🇨🇲",
        "Cape Verde": "🇨🇻",
        "Cayman Islands": "🇰🇾",
        "Central African Republic": "🇨🇫",
        "Chad": "🇹🇩",
        "Chile": "🇨🇱",
        "China": "🇨🇳",
        "Chinese Taipei": "🇹🇼",
        "Christmas Island": "🇨🇽",
        "Colombia": "🇨🇴",
        "Comoros": "🇰🇲",
        "Congo": "🇨🇬",
        "Cookinseln": "🇨🇰",
        "Costa Rica": "🇨🇷",
        "Cote d'Ivoire": "🇨🇮",
        "Crimea": "🏳️",
        "Croatia": "🇭🇷",
        "CSSR": "🏳️",
        "Cuba": "🇨🇺",
        "Curacao": "🇨🇼",
        "Czech Republic": "🇨🇿",
        "Djibouti": "🇩🇯",
        "Dominica": "🇩🇲",
        "Dominican Republic": "🇩🇴",
        "DR Congo": "🇨🇩",
        "East Germany (GDR)": "🏳️",
        "Ecuador": "🇪🇨",
        "Egypt": "🇪🇬",
        "El Salvador": "🇸🇻",
        "Equatorial Guinea": "🇬🇶",
        "Eritrea": "🇪🇷",
        "Estonia": "🇪🇪",
        "Eswatini": "🇸🇿",
        "Ethiopia": "🇪🇹",
        "Falkland Islands": "🇫🇰",
        "Faroe Islands": "🇫🇴",
        "Federated States of Micronesia": "🇫🇲",
        "Fiji": "🇫🇯",
        "Finland": "🇫🇮",
        "French Guiana": "🇬🇫",
        "Gabon": "🇬🇦",
        "Georgia": "🇬🇪",
        "Ghana": "🇬🇭",
        "Gibraltar": "🇬🇮",
        "Greenland": "🇬🇱",
        "Grenada": "🇬🇩",
        "Guadeloupe": "🇬🇵",
        "Guam": "🇬🇺",
        "Guatemala": "🇬🇹",
        "Guernsey": "🇬🇬",
        "Guinea": "🇬🇳",
        "Guinea-Bissau": "🇬🇼",
        "Guyana": "🇬🇾",
        "Honduras": "🇭🇳",
        "Hongkong": "🇭🇰",
        "Hungary": "🇭🇺",
        "Iceland": "🇮🇸",
        "India": "🇮🇳",
        "Indonesia": "🇮🇩",
        "Iran": "🇮🇷",
        "Ireland": "🇮🇪",
        "Isle of Man": "🇮🇲",
        "Israel": "🇮🇱",
        "Jamaica": "🇯🇲",
        "Japan": "🇯🇵",
        "Jersey": "🇯🇪",
        "Jugoslawien (SFR)": "🏳️",
        "Kazakhstan": "🇰🇿",
        "Kenya": "🇰🇪",
        "Kiribati": "🇰🇮",
        "Korea, North": "🇰🇵",
        "Korea, South": "🇰🇷",
        "Kosovo": "🇽🇰",
        "Kuwait": "🇰🇼",
        "Kyrgyzstan": "🇰🇬",
        "Laos": "🇱🇦",
        "Latvia": "🇱🇻",
        "Lesotho": "🇱🇸",
        "Liberia": "🇱🇷",
        "Libya": "🇱🇾",
        "Liechtenstein": "🇱🇮",
        "Lithuania": "🇱🇹",
        "Luxembourg": "🇱🇺",
        "Macao": "🇲🇴",
        "Macedonia": "🇲🇰",
        "Madagascar": "🇲🇬",
        "Malawi": "🇲🇼",
        "Malaysia": "🇲🇾",
        "Maldives": "🇲🇻",
        "Mali": "🇲🇱",
        "Malta": "🇲🇹",
        "Mandate for Palestine": "🏳️",
        "Marshall Islands": "🇲🇭",
        "Martinique": "🇲🇶",
        "Mauritania": "🇲🇷",
        "Mauritius": "🇲🇺",
        "Mayotte": "🇾🇹",
        "Mexico": "🇲🇽",
        "Moldova": "🇲🇩",
        "Monaco": "🇲🇨",
        "Mongolia": "🇲🇳",
        "Montenegro": "🇲🇪",
        "Montserrat": "🇲🇸",
        "Morocco": "🇲🇦",
        "Mozambique": "🇲🇿",
        "Myanmar": "🇲🇲",
        "Namibia": "🇳🇦",
        "Nauru": "🇳🇷",
        "Nepal": "🇳🇵",
        "Netherlands Antilles": "🏳️",
        "Netherlands East India": "🏳️",
        "New Caledonia": "🇳🇨",
        "New Zealand": "🇳🇿",
        "Nicaragua": "🇳🇮",
        "Niger": "🇳🇪",
        "Nigeria": "🇳🇬",
        "Niue": "🇳🇺",
        "North Macedonia": "🇲🇰",
        "Northern Ireland": "🏴",
        "Northern Mariana Islands": "🇲🇵",
        "Oman": "🇴🇲",
        "Pakistan": "🇵🇰",
        "Palau": "🇵🇼",
        "Palestine": "🇵🇸",
        "Panama": "🇵🇦",
        "Papua New Guinea": "🇵🇬",
        "Paraguay": "🇵🇾",
        "People's republic of the Congo": "🏳️",
        "Peru": "🇵🇪",
        "Philippines": "🇵🇭",
        "Poland": "🇵🇱",
        "Portugal": "🇵🇹",
        "Puerto Rico": "🇵🇷",
        "Réunion": "🇷🇪",
        "Rwanda": "🇷🇼",
        "Saarland": "🏳️",
        "Saint-Martin": "🇲🇫",
        "Samoa": "🇼🇸",
        "San Marino": "🇸🇲",
        "Sao Tome and Principe": "🇸🇹",
        "Senegal": "🇸🇳",
        "Serbia": "🇷🇸",
        "Serbia and Montenegro": "🏳️",
        "Seychelles": "🇸🇨",
        "Sierra Leone": "🇸🇱",
        "Singapore": "🇸🇬",
        "Sint Maarten": "🇸🇽",
        "Slovakia": "🇸🇰",
        "Slovenia": "🇸🇮",
        "Solomon Islands": "🇸🇧",
        "Somalia": "🇸🇴",
        "South Africa": "🇿🇦",
        "Southern Sudan": "🇸🇸",
        "Sri Lanka": "🇱🇰",
        "St. Kitts & Nevis": "🇰🇳",
        "St. Lucia": "🇱🇨",
        "St. Vincent & Grenadinen": "🇻🇨",
        "Sudan": "🇸🇩",
        "Suriname": "🇸🇷",
        "Swaziland": "🇸🇿",
        "Syria": "🇸🇾",
        "Tahiti": "🇵🇫",
        "Tajikistan": "🇹🇯",
        "Tanzania": "🇹🇿",
        "Thailand": "🇹🇭",
        "The Gambia": "🇬🇲",
        "Tibet": "🏳️",
        "Timor-Leste": "🇹🇱",
        "Togo": "🇹🇬",
        "Tonga": "🇹🇴",
        "Trinidad and Tobago": "🇹🇹",
        "Tunisia": "🇹🇳",
        "Turkmenistan": "🇹🇲",
        "Turks- and Caicosinseln": "🇹🇨",
        "Tuvalu": "🇹🇻",
        "UdSSR": "🏳️",
        "Uganda": "🇺🇬",
        "Ukraine": "🇺🇦",
        "United Kingdom": "🇬🇧",
        "Uruguay": "🇺🇾",
        "Uzbekistan": "🇺🇿",
        "Vanuatu": "🇻🇺",
        "Vatican": "🇻🇦",
        "Venezuela": "🇻🇪",
        "Vietnam": "🇻🇳",
        "Wales": "🏴",
        "Western Sahara": "🇪🇭",
        "Yemen": "🇾🇪",
        "Yugoslavia (Republic)": "🏳️",
        "Zaire": "🏳️",
        "Zambia": "🇿🇲",
        "Zanzibar": "🏳️",
        "Zimbabwe": "🇿🇼",
    }
    return flags.get(country, "🏳️")


def clean(text):
    return re.sub(r"\s+", " ", text).strip()


def is_valid_club_label(label, href=""):
    if not label:
        return False

    normalized = clean(label)

    if normalized in INVALID_CLUB_LABELS:
        return False

    lowered = normalized.lower()
    if "national team" in lowered:
        return False

    if href:
        href_lower = href.lower()
        if "/nationalmannschaft/" in href_lower:
            return False
        if "/nationalteam/" in href_lower:
            return False

    return True


def build_payload(club_country_id, reason_type):
    payload = {
        "Detailsuche[vorname]": "",
        "Detailsuche[name]": "",
        "Detailsuche[name_anzeige]": "",
        "Detailsuche[passname]": "",
        "Detailsuche[genaue_suche]": "0",
        "Detailsuche[geb_ort]": "",
        "Detailsuche[genaue_suche_geburtsort]": "0",
        "Detailsuche[land_id]": "",
        "Detailsuche[zweites_land_id]": "",
        "Detailsuche[geb_land_id]": "",
        "Detailsuche[kontinent_id]": "",
        "Detailsuche[geburtstag]": "",
        "Detailsuche[geburtsmonat]": "",
        "Detailsuche[geburtsjahr]": "",
        "Detailsuche[minAlter]": "0",
        "Detailsuche[maxAlter]": "150",
        "Detailsuche[age]": "0;150",
        "Detailsuche[minJahrgang]": "1850",
        "Detailsuche[maxJahrgang]": "2015",
        "Detailsuche[jahrgang]": "1850;2015",
        "Detailsuche[minGroesse]": "0",
        "Detailsuche[maxGroesse]": "220",
        "Detailsuche[groesse]": "0;220",
        "Detailsuche[hauptposition_id]": "",
        "Detailsuche[nebenposition_id_1]": "",
        "Detailsuche[nebenposition_id_2]": "",
        "Detailsuche[minMarktwert]": "0",
        "Detailsuche[maxMarktwert]": "200000000",
        "Detailsuche[marktwert]": "0;200000000",
        "Detailsuche[fuss_id]": "",
        "Detailsuche[captain]": "",
        "Detailsuche[rn]": "",
        "Detailsuche[wettbewerb_id]": "",
        "Detailsuche[w_land_id]": str(club_country_id),
        "Detailsuche[minNmSpiele]": "0",
        "Detailsuche[maxNmSpiele]": "300",
        "Detailsuche[nm_spiele]": "0;300",
        "Detailsuche[trans_id]": "0",
        "Detailsuche[aktiv]": "0",
        "Detailsuche[vereinslos]": "0",
        "Detailsuche[leihen]": "0",
        "speichern": "Submit search",
    }

    if reason_type == "birth":
        payload["Detailsuche[geb_land_id]"] = str(SYRIA_ID)
    elif reason_type == "citizenship":
        payload["Detailsuche[land_id]"] = str(SYRIA_ID)
    elif reason_type == "second_citizenship":
        payload["Detailsuche[zweites_land_id]"] = str(SYRIA_ID)

    return payload


def get_position_from_text(text):
    lowered = text.lower()

    for pos in POSSIBLE_POSITIONS:
        if pos.lower() in lowered:
            return pos

    for normalized, aliases in POSITION_ALIASES:
        for alias in aliases:
            if alias in lowered:
                return normalized

    return "Unknown position"


def fetch_player_profile_details(session, profile_url):
    club = ""
    position = "Unknown position"

    try:
        response = session.get(profile_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to load profile {profile_url}: {e}")
        return club, position

    soup = BeautifulSoup(response.text, "lxml")
    page_text = clean(soup.get_text(" ", strip=True))

    position = get_position_from_text(page_text)

    club_selectors = [
        'a[href*="/startseite/verein/"]',
        'a[href*="/verein/"]',
        ".data-header__club a",
        ".data-header__box--small a",
    ]

    for selector in club_selectors:
        links = soup.select(selector)
        for link in links:
            href = link.get("href", "")
            label = clean(link.get_text(" ", strip=True))
            if "/verein/" in href and is_valid_club_label(label, href):
                club = label
                break
        if club:
            break

    return club, position


def parse_players(session, html, club_country_name, reason_text):
    soup = BeautifulSoup(html, "lxml")
    players = []

    rows = soup.select("table.items tbody tr")

    for row in rows:
        profile_link = row.select_one('a[href*="/profil/spieler/"]')
        if not profile_link:
            continue

        href = profile_link.get("href", "")
        if not href:
            continue

        profile_url = "https://www.transfermarkt.com" + href
        match = re.search(r"/spieler/(\d+)", href)
        player_id = match.group(1) if match else profile_url

        name = clean(profile_link.get_text(" ", strip=True))

        club = ""
        club_selectors = [
            'a[href*="/startseite/verein/"]',
            'a[href*="/verein/"]',
        ]
        for selector in club_selectors:
            links = row.select(selector)
            for link in links:
                link_text = clean(link.get_text(" ", strip=True))
                href2 = link.get("href", "")
                if "/verein/" in href2 and link_text != name and is_valid_club_label(link_text, href2):
                    club = link_text
                    break
            if club:
                break

        row_text = clean(row.get_text(" ", strip=True))
        position = get_position_from_text(row_text)

        if not club or position == "Unknown position":
            fallback_club, fallback_position = fetch_player_profile_details(session, profile_url)
            if not club and fallback_club:
                club = fallback_club
            if position == "Unknown position" and fallback_position:
                position = fallback_position
            time.sleep(1)

        players.append({
            "id": player_id,
            "name": name,
            "club": club or "Unknown club",
            "club_country": club_country_name,
            "position": position,
            "reason": reason_text,
            "profile_url": profile_url,
        })

    unique = {}
    for p in players:
        if p["id"] not in unique:
            unique[p["id"]] = p
        else:
            old_reason = unique[p["id"]]["reason"]
            if p["reason"] not in old_reason:
                unique[p["id"]]["reason"] = old_reason + ", " + p["reason"]

    return list(unique.values())


def fetch_search(club_country_id, club_country_name, reason_type, reason_text):
    session = requests.Session()
    session.headers.update(HEADERS)

    session.get(BASE_URL, timeout=30)
    time.sleep(1)

    payload = build_payload(club_country_id, reason_type)
    response = session.post(BASE_URL, data=payload, timeout=60)
    response.raise_for_status()

    return parse_players(session, response.text, club_country_name, reason_text)


def collect_all_matches():
    all_players = {}

    searches = [
        ("birth", "Country of birth: Syria"),
        ("citizenship", "Citizenship: Syria"),
        ("second_citizenship", "Second citizenship: Syria"),
    ]

    for club_country_id, club_country_name in CLUB_COUNTRIES.items():
        for reason_type, reason_text in searches:
            try:
                players = fetch_search(
                    club_country_id,
                    club_country_name,
                    reason_type,
                    reason_text
                )
                print(f"{club_country_name} / {reason_text} -> {len(players)} players")
            except Exception as e:
                print(f"Failed: {club_country_name} / {reason_text} -> {e}")
                continue

            for player in players:
                if player["id"] not in all_players:
                    all_players[player["id"]] = player
                else:
                    existing_reason = all_players[player["id"]]["reason"]
                    if player["reason"] not in existing_reason:
                        all_players[player["id"]]["reason"] = (
                            existing_reason + ", " + player["reason"]
                        )

    return list(all_players.values())


def format_message(player):
    flag = flag_for_country(player["club_country"])
    return (
        "Hey bro! I got a new player for you 😁\n\n"
        f"🏃‍♂️ Player: {player['name']}\n"
        f"🌎 Plays in: {flag} {player['club_country']}\n"
        f"🚩 Club: {player['club'] or 'Unknown club'}\n"
        f"🔄 Position: {player['position']}\n"
        f"🇸🇾 Reason: {player['reason']}\n"
        f"📎 Profile: {player['profile_url']}"
    )


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    seen_ids = load_seen()
    players = collect_all_matches()

    new_players = [p for p in players if p["id"] not in seen_ids]

    print(f"Total matches found: {len(players)}")
    print(f"New players found: {len(new_players)}")

    for player in new_players:
        send_telegram_message(format_message(player))
        seen_ids.add(player["id"])
        time.sleep(2)

    save_seen(seen_ids)


if __name__ == "__main__":
    main()