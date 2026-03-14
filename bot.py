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
MAX_MESSAGES_PER_RUN = 50
MESSAGE_DELAY_SECONDS = 4

CLUB_COUNTRIES = {
    3: "Albania",
    4: "Algeria",
    5: "Andorra",
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
    159: "South Africa",
    262: "Southern Sudan",
    157: "Spain",
    158: "Sri Lanka",
    160: "Sudan",
    161: "Suriname",
    147: "Sweden",
    148: "Switzerland",
    165: "Tajikistan",
    167: "Thailand",
    173: "Tunisia",
    174: "Türkiye",
    175: "Turkmenistan",
    226: "Turks- and Caicosinseln",
    221: "UdSSR",
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
        return {}
    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {player_id: {"id": player_id} for player_id in data}
            if isinstance(data, dict):
                return data
            return {}
    except Exception:
        return {}


def save_seen(seen_data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen_data, f, ensure_ascii=False, indent=2, sort_keys=True)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    max_attempts = 5

    for _ in range(max_attempts):
        response = requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )

        if response.status_code == 429:
            retry_after = 10
            try:
                data = response.json()
                retry_after = int(data.get("parameters", {}).get("retry_after", 10))
            except Exception:
                pass

            wait_time = retry_after + 2
            print(f"Telegram rate limit hit. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue

        response.raise_for_status()
        return

    raise RuntimeError("Failed to send Telegram message after multiple retries.")


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
        "Afghanistan": "🇦🇫",
        "Albania": "🇦🇱",
        "Algeria": "🇩🇿",
        "Argentina": "🇦🇷",
        "Azerbaijan": "🇦🇿",
        "Belarus": "🇧🇾",
        "Benin": "🇧🇯",
        "Bermuda": "🇧🇲",
        "Bhutan": "🇧🇹",
        "Bolivia": "🇧🇴",
        "Bonaire": "🇧🇶",
        "Bosnia-Herzegovina": "🇧🇦",
        "Botswana": "🇧🇼",
        "Brazil": "🇧🇷",
        "Cameroon": "🇨🇲",
        "Cape Verde": "🇨🇻",
        "Chad": "🇹🇩",
        "Chile": "🇨🇱",
        "China": "🇨🇳",
        "Chinese Taipei": "🇹🇼",
        "Colombia": "🇨🇴",
        "Congo": "🇨🇬",
        "Costa Rica": "🇨🇷",
        "Cote d'Ivoire": "🇨🇮",
        "Croatia": "🇭🇷",
        "Cuba": "🇨🇺",
        "Cyprus": "🇨🇾",
        "Czech Republic": "🇨🇿",
        "Denmark": "🇩🇰",
        "Dominica": "🇩🇲",
        "Dominican Republic": "🇩🇴",
        "DR Congo": "🇨🇩",
        "Ecuador": "🇪🇨",
        "Egypt": "🇪🇬",
        "El Salvador": "🇸🇻",
        "England": "🏴",
        "Estonia": "🇪🇪",
        "Ethiopia": "🇪🇹",
        "Finland": "🇫🇮",
        "France": "🇫🇷",
        "Gabon": "🇬🇦",
        "Georgia": "🇬🇪",
        "Germany": "🇩🇪",
        "Ghana": "🇬🇭",
        "Greece": "🇬🇷",
        "Honduras": "🇭🇳",
        "Hongkong": "🇭🇰",
        "Hungary": "🇭🇺",
        "Iceland": "🇮🇸",
        "India": "🇮🇳",
        "Indonesia": "🇮🇩",
        "Iran": "🇮🇷",
        "Iraq": "🇮🇶",
        "Ireland": "🇮🇪",
        "Israel": "🇮🇱",
        "Italy": "🇮🇹",
        "Jamaica": "🇯🇲",
        "Japan": "🇯🇵",
        "Jordan": "🇯🇴",
        "Kazakhstan": "🇰🇿",
        "Kenya": "🇰🇪",
        "Korea, North": "🇰🇵",
        "Korea, South": "🇰🇷",
        "Kosovo": "🇽🇰",
        "Kuwait": "🇰🇼",
        "Kyrgyzstan": "🇰🇬",
        "Latvia": "🇱🇻",
        "Lebanon": "🇱🇧",
        "Libya": "🇱🇾",
        "Lithuania": "🇱🇹",
        "Luxembourg": "🇱🇺",
        "Malaysia": "🇲🇾",
        "Maldives": "🇲🇻",
        "Mali": "🇲🇱",
        "Malta": "🇲🇹",
        "Mauritania": "🇲🇷",
        "Mexico": "🇲🇽",
        "Moldova": "🇲🇩",
        "Monaco": "🇲🇨",
        "Montenegro": "🇲🇪",
        "Morocco": "🇲🇦",
        "Netherlands": "🇳🇱",
        "New Zealand": "🇳🇿",
        "Nicaragua": "🇳🇮",
        "Niger": "🇳🇪",
        "Nigeria": "🇳🇬",
        "North Macedonia": "🇲🇰",
        "Northern Ireland": "🏴",
        "Norway": "🇳🇴",
        "Oman": "🇴🇲",
        "Palestine": "🇵🇸",
        "Panama": "🇵🇦",
        "Paraguay": "🇵🇾",
        "Peru": "🇵🇪",
        "Philippines": "🇵🇭",
        "Poland": "🇵🇱",
        "Portugal": "🇵🇹",
        "Puerto Rico": "🇵🇷",
        "Qatar": "🇶🇦",
        "Romania": "🇷🇴",
        "Russia": "🇷🇺",
        "Saudi Arabia": "🇸🇦",
        "Scotland": "🏴",
        "Senegal": "🇸🇳",
        "Serbia": "🇷🇸",
        "Singapore": "🇸🇬",
        "Slovakia": "🇸🇰",
        "Slovenia": "🇸🇮",
        "South Africa": "🇿🇦",
        "Southern Sudan": "🇸🇸",
        "Spain": "🇪🇸",
        "Sri Lanka": "🇱🇰",
        "Sudan": "🇸🇩",
        "Suriname": "🇸🇷",
        "Sweden": "🇸🇪",
        "Switzerland": "🇨🇭",
        "Syria": "🇸🇾",
        "Tajikistan": "🇹🇯",
        "Thailand": "🇹🇭",
        "Tunisia": "🇹🇳",
        "Türkiye": "🇹🇷",
        "Turkmenistan": "🇹🇲",
        "Ukraine": "🇺🇦",
        "United Arab Emirates": "🇦🇪",
        "United Kingdom": "🇬🇧",
        "United States": "🇺🇸",
        "Uruguay": "🇺🇾",
        "Uzbekistan": "🇺🇿",
        "Venezuela": "🇻🇪",
        "Vietnam": "🇻🇳",
        "Wales": "🏴",
        "Yemen": "🇾🇪",
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


def determine_without_club(club_name):
    if not club_name:
        return True
    return clean(club_name) in {"Unknown club", "Without Club"}


def extract_national_team(soup):
    selectors = [
        'a[href*="/nationalmannschaft/"]',
        'a[href*="/nationalteam/"]',
        '.data-header__details a[href*="/national"]',
        '.data-header__box--small a[href*="/national"]',
    ]

    candidates = []

    for selector in selectors:
        for link in soup.select(selector):
            href = link.get("href", "")
            label = clean(link.get_text(" ", strip=True))
            if not label:
                continue
            href_lower = href.lower()
            if "/nationalmannschaft/" in href_lower or "/nationalteam/" in href_lower:
                candidates.append(label)

    for candidate in candidates:
        lowered = candidate.lower()
        if lowered in {"current international", "international", "national player"}:
            continue
        return candidate

    full_text = clean(soup.get_text(" ", strip=True))
    match = re.search(r"Current international:\s*([A-Za-zÀ-ÿ0-9\s\-\.\(\)&']+)", full_text, re.IGNORECASE)
    if match:
        value = clean(match.group(1))
        if value:
            return value

    return ""


def fetch_player_profile_details(session, profile_url):
    club = ""
    position = "Unknown position"
    national_team = ""

    try:
        response = session.get(profile_url, timeout=30)
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to load profile {profile_url}: {e}")
        return club, position, national_team

    soup = BeautifulSoup(response.text, "lxml")
    page_text = clean(soup.get_text(" ", strip=True))

    position = get_position_from_text(page_text)
    national_team = extract_national_team(soup)

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

    return club, position, national_team


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
        national_team = ""

        if not club or position == "Unknown position" or not national_team:
            fallback_club, fallback_position, fallback_national_team = fetch_player_profile_details(session, profile_url)
            if not club and fallback_club:
                club = fallback_club
            if position == "Unknown position" and fallback_position:
                position = fallback_position
            if fallback_national_team:
                national_team = fallback_national_team
            time.sleep(1)

        player = {
            "id": player_id,
            "name": name,
            "club": club or "Unknown club",
            "club_country": club_country_name,
            "position": position,
            "reason": reason_text,
            "profile_url": profile_url,
            "national_team": national_team or "",
        }
        player["is_without_club"] = determine_without_club(player["club"])

        players.append(player)

    unique = {}
    for p in players:
        if p["id"] not in unique:
            unique[p["id"]] = p
        else:
            old_reason = unique[p["id"]]["reason"]
            if p["reason"] not in old_reason:
                unique[p["id"]]["reason"] = old_reason + ", " + p["reason"]

            if not unique[p["id"]].get("national_team") and p.get("national_team"):
                unique[p["id"]]["national_team"] = p["national_team"]

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
                        all_players[player["id"]]["reason"] = existing_reason + ", " + player["reason"]

                    if not all_players[player["id"]].get("national_team") and player.get("national_team"):
                        all_players[player["id"]]["national_team"] = player["national_team"]

    return list(all_players.values())


def snapshot_player(player):
    return {
        "id": player["id"],
        "name": player["name"],
        "club": player["club"],
        "club_country": player["club_country"],
        "position": player["position"],
        "reason": player["reason"],
        "profile_url": player["profile_url"],
        "is_without_club": player["is_without_club"],
        "national_team": player.get("national_team", ""),
    }


def detect_events(old_player, new_player):
    events = []

    if old_player is None:
        events.append("new_player")
        return events

    old_club = old_player.get("club", "Unknown club")
    new_club = new_player.get("club", "Unknown club")

    old_country = old_player.get("club_country", "")
    new_country = new_player.get("club_country", "")

    old_without_club = bool(old_player.get("is_without_club", determine_without_club(old_club)))
    new_without_club = bool(new_player.get("is_without_club", determine_without_club(new_club)))

    old_national_team = clean(old_player.get("national_team", ""))
    new_national_team = clean(new_player.get("national_team", ""))

    if old_without_club and not new_without_club:
        events.append("signed_with_club")
    elif not old_without_club and new_without_club:
        events.append("became_without_club")
    elif not old_without_club and not new_without_club and old_club != new_club:
        events.append("club_changed")

    if old_country and new_country and old_country != new_country:
        events.append("country_changed")

    if not old_national_team and new_national_team:
        events.append("joined_national_team")
    elif old_national_team and not new_national_team:
        events.append("left_national_team")
    elif old_national_team and new_national_team and old_national_team != new_national_team:
        events.append("changed_national_team")

    return events


def format_new_player_message(player):
    flag = flag_for_country(player["club_country"])
    extra_nt = ""
    if player.get("national_team"):
        extra_nt = f"\n🏟️ National team: {player['national_team']}"

    return (
        "Hey bro! I got a new player for you 😁\n\n"
        f"🏃‍♂️ Player: {player['name']}\n"
        f"🌎 Plays in: {flag} {player['club_country']}\n"
        f"🚩 Club: {player['club'] or 'Unknown club'}\n"
        f"🔄 Position: {player['position']}"
        f"{extra_nt}\n"
        f"🇸🇾 Reason: {player['reason']}\n"
        f"📎 Profile: {player['profile_url']}"
    )


def format_update_message(old_player, new_player, events):
    parts = []
    flag = flag_for_country(new_player["club_country"])

    if "signed_with_club" in events:
        parts.append("Reason: Signed with a club")
        parts.append(f"Previous status: {old_player.get('club', 'Without club')}")
        parts.append(f"New club: {new_player['club']}")

    elif "became_without_club" in events:
        parts.append("Reason: Became without club")
        parts.append(f"Previous club: {old_player.get('club', 'Unknown club')}")
        parts.append(f"Current status: {new_player['club']}")

    elif "club_changed" in events:
        parts.append("Reason: Club changed")
        parts.append(f"Old club: {old_player.get('club', 'Unknown club')}")
        parts.append(f"New club: {new_player['club']}")

    if "country_changed" in events:
        parts.append(f"Old country of play: {old_player.get('club_country', 'Unknown')}")
        parts.append(f"New country of play: {new_player['club_country']}")

    if "joined_national_team" in events:
        parts.append("Reason: Joined national team")
        parts.append(f"National team: {new_player.get('national_team', 'Unknown')}")

    elif "left_national_team" in events:
        parts.append("Reason: Left national team")
        parts.append(f"Previous national team: {old_player.get('national_team', 'Unknown')}")

    elif "changed_national_team" in events:
        parts.append("Reason: National team changed")
        parts.append(f"Old national team: {old_player.get('national_team', 'Unknown')}")
        parts.append(f"New national team: {new_player.get('national_team', 'Unknown')}")

    return (
        "Hey bro! I got an update for you 😁\n\n"
        f"🏃‍♂️ Player: {new_player['name']}\n"
        f"🌎 Plays in: {flag} {new_player['club_country']}\n"
        f"🚩 Club: {new_player['club'] or 'Unknown club'}\n"
        f"🔄 Position: {new_player['position']}\n"
        + "\n".join(parts) + "\n"
        + f"📎 Profile: {new_player['profile_url']}"
    )


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    seen_data = load_seen()
    players = collect_all_matches()

    print(f"Total matches found: {len(players)}")

    outbound_messages = []

    for player in players:
        old_player = seen_data.get(player["id"])
        events = detect_events(old_player, player)

        if not events:
            seen_data[player["id"]] = snapshot_player(player)
            continue

        if "new_player" in events:
            message = format_new_player_message(player)
        else:
            message = format_update_message(old_player, player, events)

        outbound_messages.append((player["id"], message, snapshot_player(player), events))

    print(f"Messages to send: {len(outbound_messages)}")

    outbound_messages = outbound_messages[:MAX_MESSAGES_PER_RUN]

    for player_id, message, snapshot, events in outbound_messages:
        print(f"Sending alert for {player_id}: {', '.join(events)}")
        send_telegram_message(message)
        seen_data[player_id] = snapshot
        save_seen(seen_data)
        time.sleep(MESSAGE_DELAY_SECONDS)

    for player in players:
        if player["id"] not in seen_data:
            seen_data[player["id"]] = snapshot_player(player)

    save_seen(seen_data)


if __name__ == "__main__":
    main()
