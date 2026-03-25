#!/usr/bin/env python3
"""
Generate europe-countries.json: break down European first-pro-destination players by country.
"""

import json
import sqlite3
import os

DB_PATH = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/data/d1_basketball.db"
OUTPUT_PATH = "/Users/rjb/Desktop/Hoop Research/d1-basketball-outcomes/website/public/data/europe-countries.json"

# ---------------------------------------------------------------------------
# European team keywords (from generate-sankey-data.py)
# ---------------------------------------------------------------------------
EUROPEAN_KEYWORDS = [
    "BC", "KK", "Barca", "Real Madrid", "Zalgiris", "ALBA", "Bayern",
    "Fenerbahce", "Galatasaray", "Olympiacos", "Panathinaikos", "Partizan",
    "CSKA", "Khimki", "Zenit", "Milan", "Bologna", "Cremona", "Varese",
    "Trento", "Sassari", "Trieste", "Leicester", "Sheffield", "Cheshire",
    "London Lions", "Plymouth", "Glasgow", "Caledonia", "MHP Riesen",
    "Towers Hamburg", "Telekom Baskets", "Goettingen", "Bayreuth", "Vechta",
    "Baskets", "Leuven", "Antwerp", "Hapoel", "Maccabi", "Ironi", "Bnei",
    "Nymburk", "Horsens", "FOG", "Naestved", "Lavrio", "Aris", "PAOK",
    "Promitheas", "Kolossos", "Limoges", "Boulogne", "Strasbourg", "Chorale",
    "Nanterre", "Gran Canaria", "Fuenlabrada", "Joventut", "Valencia Basket",
    "Zaragoza", "Badalona", "Turk Telekom", "Besiktas", "Bursaspor", "Banvit",
    "Warszawa", "Wroclaw", "Gdynia", "Bydgoszcz", "Golden Eagle", "Riders",
    "Netherlands", "Germany", "Serbia", "Lithuania", "Spain", "France",
    "Greece", "Great Britain", "Croatia", "Italy", "Turkey", "Israel",
    "Poland", "Czech", "Belgium", "Denmark", "Finland", "Sweden", "Norway",
    "Hungary", "Romania", "Bulgaria", "Slovenia", "Latvia", "Estonia",
    "Montenegro", "Bosnia", "Portugal", "Switzerland", "Austria", "Ukraine",
    "Russia", "Georgia", "Iceland", "Cyprus", "Kosovo", "Albania",
    "North Macedonia", "Slovakia",
    "Ulm", "Bamberg", "Bonn", "Frankfurt", "Berlin", "Wurzburg",
    "Ludwigsburg", "Braunschweig", "Treviso", "Reggio", "Brescia", "Napoli",
    "Pesaro", "Pau", "Roanne", "Dijon", "Nancy", "Orleans",
    "Le Mans", "Gravelines", "Murcia", "Malaga", "Tenerife", "Manresa",
    "Burgos", "Bilbao", "Andorra", "Porto", "Sporting", "Benfica",
    "Oliveirense", "Elan Chalon", "Saint-Quentin", "Fos-sur-Mer", "JDA",
    "Den Bosch", "Leiden", "Groningen", "Donar", "Bakken", "Aarhus",
    "Helsinki", "Korihait", "Kauhajoki", "Svitavy", "Opava", "USK Praha",
    "Cibona", "Cedevita", "Split", "FMP", "Mega", "Buducnost",
    "SC Rasta", "Phoenix Hagen", "Mitteldeutscher", "Fraport", "Skyliners",
    "Artland", "Brose", "EWE", "BBC Bayreuth", "Walter Tigers", "Crailsheim",
    "Giessen", "Gottingen", "Oettinger Rockets", "s.Oliver", "Eisbaren",
    "ratiopharm", "MBC", "Niners", "Hamburg", "Rostock", "Ehingen", "Trier",
    "Jena", "Tubingen", "Legia", "Trefl", "Anwil", "Stelmet", "Czarni",
    "Rosa", "Asseco", "Turów", "Enea", "Spojnia", "Dekorglass", "Lublin",
    "Grodno", "Minsk", "Rilski", "Levski", "Lukoil", "Beroe", "Yambol",
    "Lokomotiv", "Primorska", "Krka", "Rogaska", "Helios", "Olimpija",
    "Sigal", "Rahoveci", "Trepca", "Kalaja", "Peja", "Shkupi", "MZT",
    "Pelister", "Mornar", "Sutjeska", "Igokea", "Borac", "Sloga", "Brno",
    "Decin", "Pardubice", "Prosek", "Prostejov", "Olomouc", "Sluneta",
    "Sokolov", "Kolin", "Hradec", "Chartres", "Fos",
    "Rouen", "Blois", "Vichy", "Poitiers", "Denain", "Aix", "Le Portel",
    "Antibes", "Quimper", "Hyeres", "Challans", "Nantes", "Bourg", "Evreux",
    "Prienai", "Lietkabelis", "Neptunas", "Juventus", "Pieno", "Rytas",
    "Siauliai", "BC Wolves", "Kalev", "Ventspils", "VEF",
    "Ogre", "Tartu", "Rapla", "Parnu", "Valga", "Bisons", "Szolnok",
    "Falco", "Koermend", "Sopron", "Szeged", "Alba Fehervar", "Paks",
    "Debrecen", "Alytus", "Nevezis", "Carolo", "Le Havre", "Saint-Chamond",
    "Aix-Maurienne", "Union Tarbes", "Champagne", "Caen",
]
EUROPEAN_KEYWORDS_LOWER = [kw.lower() for kw in EUROPEAN_KEYWORDS]


def is_european_team(team_name):
    team_lower = team_name.lower()
    for kw in EUROPEAN_KEYWORDS_LOWER:
        if kw in team_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# Country classification keywords (case-insensitive substring match)
# Order matters: more specific keywords should be checked before generic ones.
# ---------------------------------------------------------------------------
COUNTRY_KEYWORDS = {
    "Spain": [
        "Gran Canaria", "Fuenlabrada", "Joventut", "Valencia Basket",
        "Zaragoza", "Badalona", "Barca", "Real Madrid", "Murcia", "Malaga",
        "Tenerife", "Manresa", "Burgos", "Bilbao", "Andorra", "Estudiantes",
        "Unicaja", "Obradoiro", "Breogan", "Spain",
    ],
    "Germany": [
        "MHP Riesen", "Towers Hamburg", "Telekom Baskets", "Goettingen",
        "Bayreuth", "Vechta", "ALBA Berlin", "Bamberg", "Bonn", "Frankfurt",
        "Wurzburg", "Ludwigsburg", "Braunschweig", "Ulm", "ratiopharm",
        "s.Oliver", "Crailsheim", "Giessen", "Baskets Bonn", "Bayern Munich",
        "Mitteldeutscher", "Fraport Skyliners", "SC Rasta", "Brose", "EWE",
        "Niners", "Hamburg Towers", "Rostock", "Tubingen", "Trier",
        "BG Goettingen", "Phoenix Hagen", "Germany", "Gottingen",
        "BBC Bayreuth", "Walter Tigers", "Oettinger Rockets", "Eisbaren",
        "MBC", "Hamburg", "Ehingen", "Jena", "Artland",
    ],
    "Italy": [
        "Milan", "Bologna", "Cremona", "Varese", "Trento", "Sassari",
        "Trieste", "Treviso", "Reggio", "Brescia", "Napoli", "Pesaro",
        "Brindisi", "Pistoia", "Fortitudo", "Virtus", "AX Armani", "Italy",
    ],
    "France": [
        "Limoges", "Boulogne", "Strasbourg", "Chorale", "Nanterre", "Pau",
        "Roanne", "Dijon", "Nancy", "Orleans", "Le Mans", "Gravelines",
        "Elan Chalon", "Saint-Quentin", "Fos-sur-Mer", "JDA", "Le Portel",
        "Antibes", "Monaco", "ASVEL", "Metropolitans", "Chalons", "Bourg",
        "Le Havre", "France", "Chartres", "Fos", "Rouen", "Blois", "Vichy",
        "Poitiers", "Denain", "Aix", "Quimper", "Hyeres", "Challans",
        "Nantes", "Evreux", "Carolo", "Saint-Chamond", "Aix-Maurienne",
        "Union Tarbes", "Champagne", "Caen",
    ],
    "Turkey": [
        "Fenerbahce", "Galatasaray", "Turk Telekom", "Besiktas", "Bursaspor",
        "Banvit", "Darussafaka", "Efes", "Bahcesehir", "Tofas", "Pinar",
        "Turkey",
    ],
    "Greece": [
        "Olympiacos", "Panathinaikos", "PAOK", "Aris", "GS Lavrio",
        "Promitheas", "Kolossos", "AEK Athens", "Peristeri", "Iraklis",
        "Greece", "Lavrio",
    ],
    "Israel": [
        "Hapoel", "Maccabi", "Ironi", "Bnei", "Israel",
    ],
    "UK": [
        "Leicester", "Sheffield", "Cheshire", "London Lions", "Plymouth",
        "Glasgow", "Caledonia", "Bristol", "Surrey", "Manchester", "Newcastle",
        "Worcester", "Sharks", "Riders", "Phoenix", "Flyers", "Scorchers",
        "Great Britain",
    ],
    "Lithuania": [
        "Zalgiris", "Lietkabelis", "Neptunas", "Juventus", "Rytas", "Pieno",
        "Prienai", "Lithuania", "Siauliai", "BC Wolves", "Alytus", "Nevezis",
    ],
    "Serbia": [
        "KK Partizan", "Partizan", "FMP", "Mega", "Crvena Zvezda", "Serbia",
    ],
    "Belgium": [
        "Leuven", "Antwerp", "Mons", "Charleroi", "Limburg", "Mechelen",
        "Oostende", "Giants", "Belgium",
    ],
    "Netherlands": [
        "Den Bosch", "Leiden", "Groningen", "Donar", "Heroes", "ZZ Leiden",
        "Netherlands",
    ],
    "Denmark": [
        "Horsens", "FOG Naestved", "Bakken", "Aarhus", "Svendborg", "Denmark",
        "FOG", "Naestved",
    ],
    "Croatia": [
        "Cibona", "Cedevita", "Split", "Zadar", "Croatia",
    ],
    "Poland": [
        "Warszawa", "Wroclaw", "Gdynia", "Bydgoszcz", "Legia", "Trefl",
        "Anwil", "Stelmet", "Czarni", "Poland", "Rosa", "Asseco", "Turów",
        "Enea", "Spojnia", "Dekorglass", "Lublin",
    ],
    "Russia/CIS": [
        "CSKA", "Khimki", "Zenit", "Lokomotiv Kuban", "UNICS", "Parma",
        "Avtodor", "Russia", "Lokomotiv",
    ],
    "Finland": [
        "Helsinki", "Korihait", "Kauhajoki", "Finland",
    ],
    "Czech Republic": [
        "Nymburk", "Czech", "Svitavy", "Opava", "USK Praha", "Brno",
        "Decin", "Pardubice", "Prosek", "Prostejov", "Olomouc", "Sluneta",
        "Sokolov", "Kolin", "Hradec",
    ],
    "Montenegro": [
        "Buducnost", "Mornar", "Sutjeska", "Montenegro",
    ],
    "Bosnia": [
        "Igokea", "Borac", "Sloga", "Bosnia",
    ],
    "Slovenia": [
        "Primorska", "Krka", "Rogaska", "Helios", "Olimpija", "Slovenia",
    ],
    "Hungary": [
        "Szolnok", "Falco", "Koermend", "Sopron", "Szeged", "Alba Fehervar",
        "Paks", "Debrecen", "Hungary",
    ],
    "Portugal": [
        "Porto", "Sporting", "Benfica", "Oliveirense", "Portugal",
    ],
    "Kosovo": [
        "Sigal", "Rahoveci", "Trepca", "Kalaja", "Peja", "Kosovo",
    ],
    "North Macedonia": [
        "Shkupi", "MZT", "Pelister", "North Macedonia",
    ],
    "Latvia/Estonia": [
        "Kalev", "Ventspils", "VEF", "Ogre", "Tartu", "Rapla", "Parnu",
        "Valga", "Latvia", "Estonia",
    ],
    "Belarus": [
        "Grodno", "Minsk",
    ],
    "Bulgaria": [
        "Rilski", "Levski", "Lukoil", "Beroe", "Yambol", "Bulgaria",
    ],
    "Sweden": ["Sweden"],
    "Norway": ["Norway"],
    "Romania": ["Romania"],
    "Ukraine": ["Ukraine"],
    "Georgia": ["Georgia"],
    "Iceland": ["Iceland"],
    "Cyprus": ["Cyprus"],
    "Albania": ["Albania"],
    "Slovakia": ["Slovakia"],
    "Austria": ["Austria"],
    "Switzerland": ["Switzerland"],
}

# Pre-compute lowercase keyword lists per country
COUNTRY_KEYWORDS_LOWER = {
    country: [kw.lower() for kw in kws]
    for country, kws in COUNTRY_KEYWORDS.items()
}


def classify_country(team_name):
    """Classify a European team name to a country. Returns country or None."""
    team_lower = team_name.lower()
    for country, keywords in COUNTRY_KEYWORDS_LOWER.items():
        for kw in keywords:
            if kw in team_lower:
                return country
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all rows grouped by player
    cursor.execute("""
        SELECT realgm_id, season, level, teams, section_types
        FROM realgm_timeline
        ORDER BY realgm_id, season
    """)

    rows = cursor.fetchall()
    conn.close()

    # Group by player
    from collections import defaultdict
    players = defaultdict(list)
    for realgm_id, season, level, teams_json, section_types_json in rows:
        teams = json.loads(teams_json) if teams_json else []
        section_types = json.loads(section_types_json) if section_types_json else []
        players[realgm_id].append({
            "season": season,
            "level": level,
            "teams": teams,
            "section_types": section_types,
        })

    # For each player, find their first international season and check if Europe
    country_counts = defaultdict(int)
    europe_total = 0

    for pid, seasons in players.items():
        # Sort by season
        seasons.sort(key=lambda s: s["season"])

        # Find first international season (level = "intl" or section_types contain international indicators)
        # The existing script checks for "International" in section_types
        intl_seasons = [
            s for s in seasons
            if s["level"] == "international"
        ]

        if not intl_seasons:
            continue

        first_intl = intl_seasons[0]
        teams = first_intl["teams"]

        # Check if any team is European
        is_europe = False
        for team in teams:
            if isinstance(team, str) and is_european_team(team):
                is_europe = True
                break

        if not is_europe:
            continue

        europe_total += 1

        # Now classify the country from the first matching European team
        country_found = None
        for team in teams:
            if isinstance(team, str):
                country_found = classify_country(team)
                if country_found:
                    break

        if country_found:
            country_counts[country_found] += 1
        else:
            country_counts["Other Europe"] += 1

    # Sort by count descending
    sorted_countries = sorted(country_counts.items(), key=lambda x: -x[1])

    # Build output: top countries individually, rest grouped into "Other European Leagues"
    top_countries = []
    other_count = 0
    for country, count in sorted_countries:
        if count >= 20 and country != "Other Europe":
            top_countries.append((country, count))
        else:
            other_count += count

    # Keep top 10 max
    if len(top_countries) > 10:
        for country, count in top_countries[10:]:
            other_count += count
        top_countries = top_countries[:10]

    # Build nodes and links
    nodes = [{"id": "eu_all", "label": "Europe Players", "count": europe_total}]
    links = []

    for country, count in top_countries:
        cid = "eu_" + country.lower().replace(" ", "_").replace("/", "_")
        pct = f"{100.0 * count / europe_total:.1f}%"
        nodes.append({"id": cid, "label": country, "count": count, "pct": pct})
        links.append({"source": "eu_all", "target": cid, "value": count})

    if other_count > 0:
        pct = f"{100.0 * other_count / europe_total:.1f}%"
        nodes.append({"id": "eu_other", "label": "Other European Leagues", "count": other_count, "pct": pct})
        links.append({"source": "eu_all", "target": "eu_other", "value": other_count})

    output = {"nodes": nodes, "links": links}

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    # Print summary
    print(f"Total Europe players: {europe_total}")
    print(f"\nCountry breakdown (top countries):")
    for country, count in top_countries:
        pct = 100.0 * count / europe_total
        print(f"  {country:25s} {count:5d}  ({pct:.1f}%)")
    if other_count > 0:
        pct = 100.0 * other_count / europe_total
        print(f"  {'Other European Leagues':25s} {other_count:5d}  ({pct:.1f}%)")

    print(f"\nAll country counts:")
    for country, count in sorted_countries:
        print(f"  {country:25s} {count:5d}")

    print(f"\nOutput written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
