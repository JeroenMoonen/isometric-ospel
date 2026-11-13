"""Ospel van toen: a guided tour along the village's history, as an overlay for the viewer.

Texts are written for this map from Wikipedia (nl) and the rijksmonumenten register; every stop links to its source.
Photos are from the Rijksdienst voor het Cultureel Erfgoed (CC BY-SA 4.0) and other Commons files with an open license;
they are downloaded once and published with the site, with credits.

Output: data/build/history.json and data/build/history/*.jpg
"""

import hashlib
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request

from config import BUILD, CX, CY
from geo import wgs_to_rd

RCE = "Rijksdienst voor het Cultureel Erfgoed, CC BY-SA 4.0"
NAHM = "https://natuurtijdschriften.nl/pub/"
WP = "https://nl.wikipedia.org/wiki/"

CHURCH = (182698, 367724)

STOPS = [
    {
        "year": "ca. 1840",
        "title": "Een buurtschap in de Peel",
        "at": CHURCH,
        "text": "Ospel ligt op hoge, zandige grond die als een schiereiland in de moerassen van de Peel uitstak. In 1840 was Ospel nog een buurtschap met 176 inwoners.",
        "source": ("Wikipedia: Ospel", WP + "Ospel"),
        "more": WP + "Ospel",
    },
    {
        "year": "1864-1867",
        "title": "Een eigen parochie",
        "at": CHURCH,
        "text": "In 1864 werd Ospel een eigen parochie, en een dorp waar ook de buurtschappen eromheen naar de kerk, de school en de winkel kwamen. Pierre Cuypers, de architect van het Rijksmuseum, ontwierp de kerk: een bakstenen neogotische kruisbasiliek, gebouwd in 1866 en 1867.",
        "photos": [("Exterieur + overzicht - Ospel - 20177811 - RCE.jpg", f"De kerk in 1971, H.P.R. Rosenberg, {RCE}")],
        "source": ("Wikipedia: Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk", WP + "Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk_(Ospel)"),
    },
    {
        "year": "1944-1954",
        "title": "De toren valt",
        "at": (182679, 367720),
        "h": 30,
        "text": "In 1944 werd de kerktoren opgeblazen en stortten de kruisribgewelven in. Die werden in 1946 en 1947 deels hersteld; in 1953 en 1954 kwam er een nieuwe toren, met een achtkante spits tussen vier hoektorentjes en een zeskante traptoren ernaast. In 1956 kwam er een nieuw Vermeulen-orgel.",
        "photos": [("Overzicht noordwestgevel met kerktoren - Ospel - 20354362 - RCE.jpg", f"De toren in 2001, J.P. de Koning, {RCE}")],
        "source": ("Wikipedia: Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk", WP + "Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk_(Ospel)"),
    },
    {
        "year": "1944",
        "title": "Oktober 1944",
        "at": (184026, 368646),
        "text": "Op 27 oktober 1944 heroverden Duitse troepen bij een verrassingsaanval Meijel en Ospel op de Amerikaanse 7e Pantserdivisie. Begin november namen de Amerikanen Ospel terug; de divisie verloor hier 54 doden en ruim 300 gewonden. Aan de Plattepeeldijk staat sinds 2007 het monument voor de Amerikaanse bevrijders.",
        "source": ("Liberation Route Europe", "https://www.europeremembers.com/pois/747/monument-for-the-american-liberators"),
    },
    {
        "year": "1926",
        "title": "Het Heilig Hartbeeld",
        "latlon": (51.29839, 5.78512),
        "text": "Bij het graf van pastoor H. Caris, die in 1926 overleed, staat een Heilig Hartgroep van Albert Verschuuren. Op een foto uit 1935 staat de groep op een bordes, met een lantaarn aan elk eind van de muur en op de sokkel: Ziet uw koning.",
        "photos": [
            ("Heilig Hartbeeld Ospel in 1935.jpg", "Het Heilig Hartbeeld in 1935, publiek domein"),
            ("Overzicht Heilig Hartgroep op het kerkhof - Ospel - 20354363 - RCE.jpg", f"Het beeld op het kerkhof in 2001, J.P. de Koning, {RCE}"),
        ],
        "source": ("Wikipedia: Heilig Hartbeeld (Ospel)", WP + "Heilig_Hartbeeld_(Ospel)"),
    },
    {
        "year": "1861-1993",
        "title": "Scholen en een klooster",
        "latlon": (51.30007, 5.78436),
        "text": "Kinderen uit Kreijel gingen vanaf 1829 naar een primitief schooltje; in 1861 kreeg Ospel een openbare lagere school, later de Heilig Hartschool. In 1910 kwamen Franciscanessen uit Heythuysen met een klooster en een meisjesschool, de Sint-Annaschool. De laatste zuster vertrok in 1959 en het klooster werd een gemeenschapshuis. In 1993 werden de twee scholen samen De Schrank.",
        "source": ("Wikipedia: Ospel", WP + "Ospel"),
    },
    {
        "year": "1840",
        "title": "Molen Sint-Joseph",
        "latlon": (51.28915, 5.77109),
        "text": "Negentien boeren en Breukers lieten in Kreijel een beltmolen bouwen, elk voor een twintigste deel. Rond 1900 kwam er een zuiggasmotor in, zodat hij ook bij windstilte kon draaien. Rond 1970 was hij in slechte staat; in 1979 is hij gerestaureerd.",
        "photos": [("Ronde stenen beltmolen schuin van voren gefotografeerd - Kreijel - 20127681 - RCE.jpg", f"Molen Sint-Joseph, datum onbekend, {RCE}")],
        "source": ("Molendatabase: Sint Joseph", "https://www.molendatabase.nl/molens/ten-bruggencate-nr-02807"),
    },
    {
        "year": "1869",
        "title": "De Korenbloem",
        "latlon": (51.29967, 5.78027),
        "text": "Het jonge dorp kreeg in 1869 een eigen korenmolen. De Korenbloem maalde tot 1948 en raakte daarna in verval; in 1970 werd hij onttakeld. De gemeente kocht hem in 1972 en liet hem in 1990 restaureren. Nu malen vrijwilligers er weer graan.",
        "photos": [
            ("Korenmolen \"De Korenbloem\", in verval - Ospel - 20177814 - RCE.jpg", f"De Korenbloem in verval, 1966, W.A. Korpershoek, {RCE}"),
            ("De Korenbloem Ospel.jpg", "De Korenbloem in 2013, A. Ansems, CC0"),
        ],
        "source": ("Molendatabase: De Korenbloem", "https://www.molendatabase.nl/molens/ten-bruggencate-nr-02809"),
    },
    {
        "year": "1893-1907",
        "title": "Van melkfabriekje tot kapel",
        "latlon": (51.29346, 5.77026),
        "text": "In 1893 begonnen boeren aan de Klaarstraat een coöperatief melkfabriekje, met de hand bediend, onder de leuze Eendracht maakt macht. Toen de stoomzuivelfabriek Sint-Isidorus het werk in 1906 overnam, werd het gebouwtje een kapel voor Onze Lieve Vrouw van Altijddurende Bijstand, in 1907 ingezegend.",
        "photos": [
            ("Kapel Klaarstraatzijweg Ospel.jpg", "De kapel in 2009, A. Ansems, publiek domein"),
            ("Kapel Klaarstraatzijweg Ospel interieur.jpg", "Het blauwe interieur in 2012, A. Ansems, CC BY-SA 3.0 NL"),
        ],
        "source": ("Wikipedia: Onze-Lieve-Vrouw-van-Altijddurende-Bijstandkapel", WP + "Onze-Lieve-Vrouw-van-Altijddurende-Bijstandkapel_(Ospel)"),
    },
    {
        "year": "Franse tijd",
        "title": "De Noordervaart",
        "at": (184625, 367280),
        "text": "In de Franse tijd liet Napoleon een kanaal graven van de Schelde naar de Maas en de Rijn, het Grand Canal du Nord. Toen Holland in 1810 bij Frankrijk werd ingelijfd, was het niet meer nodig: het werk stopte en duizenden arbeiders stonden op straat, voor het kanaal diep genoeg was. Pas rond 1853 werd de Noordervaart op diepte gebracht, zodat Peelwater weg kon en turf werd afgevoerd.",
        "source": ("Staatsbosbeheer: Fietsroute De Groote Peel", "https://www.staatsbosbeheer.nl/-/media/de-pelen/fietsroute-de-groote-peel.pdf"),
    },
    {
        "year": "1954",
        "title": "Ospeldijk",
        "latlon": (51.3203, 5.8136),
        "text": "Langs de dijk van Meijel naar Ospel groeide een lint van boerderijen, op de grond die op de Peel was ontgonnen. In 1954 werd Ospeldijk een kerkdorp. De kerk van 1958 ging in 2007 dicht en werd een jaar later gesloopt; de toren bleef staan. De school van 1952 sloot in 2012.",
        "source": ("Wikipedia: Ospeldijk", WP + "Ospeldijk"),
    },
    {
        "year": "1937-1966",
        "title": "Een peelreservaat",
        "latlon": (51.32786, 5.80172),
        "text": "In 1937 werd gevraagd om een peelreservaat op de grens van Brabant en Limburg; in 1951 kocht Staatsbosbeheer de eerste gronden. Aan Limburgse kant was de grond zo versnipperd dat voor 875 hectare ruim 500 aktes nodig waren. Het bezoekerscentrum Mijl op Zeven, een kopie van een peelboerderij, ging in 1966 open.",
        "source": ("Natuurhistorisch Maandblad, 1969", NAHM + "1007186/NAHM1969058006008.pdf"),
        "photos": [('Ontginning, grondbewerking, egaliseren, bezanden, overzichten, Ospelse Peel, Bestanddeelnr 159-0085.jpg', 'Ontginning van de Ospelse Peel in 1952, Nationaal Archief, CC0')],
    },
    {
        "year": "1993",
        "title": "De Groote Peel",
        "latlon": (51.3258, 5.80157),
        "text": "Eeuwenlang staken mensen hier turf, met twee man: één in de veenput, één die de turf op de moostwagen legde. Bole turf was om aan te maken, zwarte turf de beste brandstof, rietturf voor de handel. Wat bleef, met zijn vennen, is sinds 1993 Nationaal Park De Groote Peel. Bij Buitencentrum De Pelen beginnen de wandelingen; een stalen zuil herdenkt de vliegtuigbemanningen die hier in de oorlog omkwamen.",
        "source": ("Natuurhistorisch Maandblad, 1969: Zo was het in Ospel", NAHM + "1007185/NAHM1969058006007.pdf"),
    },
    {
        "year": "Nu",
        "title": "Ospel nu",
        "latlon": (51.29804, 5.80813),
        "text": "Ospel heeft ruim vierduizend inwoners. Sinds 1986 is er elk eerste weekend van mei het bluesfestival Moulin Blues, nu op het terrein aan de Stenenbrug, gemaakt door ruim vijfhonderd vrijwilligers; B.B. King en Buddy Guy speelden er. Einde van de rondleiding.",
        "source": ("Wikipedia: Moulin Blues", WP + "Moulin_Blues"),
    },
]


def commons_thumb(name, width=960):  # Wikimedia only serves a fixed set of thumbnail widths
    name = name.replace(" ", "_")  # Commons hashes the name with underscores
    h = hashlib.md5(name.encode()).hexdigest()
    q = urllib.parse.quote(name)
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{width}px-{q}"


def download(url, tries=6):
    """Wikimedia rate-limits bursts of thumbnail requests; wait politely and retry."""
    req = urllib.request.Request(url, headers={"User-Agent": "isometric-ospel/0.1 (personal map)"})
    for attempt in range(tries):
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
            time.sleep(3)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 404 and "/thumb/" in url:  # no thumbnail wider than the original: take the original
                return download(url.replace("/thumb/", "/").rsplit("/", 1)[0], tries)
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(15 * (attempt + 1))


def route_order(stops):
    """Visit the stops as a route over the map instead of by date: the first and last stay put, the rest is a
    nearest-neighbour path tidied with 2-opt, so dots that lie together come one after another. Stops on the same
    spot (the old and the new church) keep their chronological order."""
    if len(stops) < 3:
        return stops
    first, last, middle = stops[0], stops[-1], stops[1:-1]
    dist = lambda a, b: ((a["x"] - b["x"]) ** 2 + (a["y"] - b["y"]) ** 2) ** 0.5
    path, todo = [first], middle[:]
    while todo:
        nxt = min(todo, key=lambda s: (dist(path[-1], s), stops.index(s)))
        path.append(nxt)
        todo.remove(nxt)
    path.append(last)
    improved = True
    while improved:
        improved = False
        for i in range(1, len(path) - 2):
            for j in range(i + 1, len(path) - 1):
                before = dist(path[i - 1], path[i]) + dist(path[j], path[j + 1])
                after = dist(path[i - 1], path[j]) + dist(path[i], path[j + 1])
                if after < before - 0.01:
                    path[i : j + 1] = path[i : j + 1][::-1]
                    improved = True
    # Places within 40 m of each other (church, parsonage, Sunday school) in chronological order.
    i = 0
    while i < len(path):
        j = i
        while j + 1 < len(path) - 1 and i > 0 and dist(path[j + 1], path[i]) < 40:
            j += 1
        year = lambda st: int(m.group()) if (m := re.search(r"\d{4}", st["year"])) else 9999
        path[i : j + 1] = sorted(path[i : j + 1], key=lambda st: (year(st), stops.index(st)))
        i = j + 1
    return path


def main():
    out_dir = BUILD / "history"
    out_dir.mkdir(parents=True, exist_ok=True)
    stops = []
    for i, s in enumerate(STOPS, start=1):
        x, y = s["at"] if "at" in s else wgs_to_rd(*s["latlon"])
        stop = {"n": i, "year": s["year"], "title": s["title"], "text": s["text"], "x": round(x, 1), "y": round(y, 1),
                "h": s.get("h", 0), "zoom": s.get("zoom", 1.2),
                "source": {"label": s["source"][0], "url": s["source"][1]}, "more": s.get("more")}
        stop["photos"] = []
        for k, (name, credit) in enumerate(s.get("photos", [])):
            dst = out_dir / f"{i:02d}_{k}.jpg"
            if not dst.exists():
                dst.write_bytes(download(commons_thumb(name)))
                subprocess.run(["magick", str(dst), "-resize", "640x640>", "-quality", "82", str(dst)], check=True)
            stop["photos"].append({"src": f"history/{dst.name}", "credit": credit,
                                   "url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(name)}"})
        stops.append(stop)
    stops = route_order(stops)
    for n, stop in enumerate(stops, start=1):
        stop["n"] = n
    # A version in every photo URL, so browsers never show a cached photo that has since been replaced.
    version = hashlib.md5(b"".join(f.read_bytes() for f in sorted(out_dir.glob("*.jpg")))).hexdigest()[:8]
    for stop in stops:
        for ph in stop["photos"]:
            ph["src"] += f"?v={version}"
    (BUILD / "history.json").write_text(json.dumps({"stops": stops}, ensure_ascii=False, indent=1))
    print(f"{len(stops)} stops, {sum(len(s['photos']) for s in stops)} photos on {sum(bool(s['photos']) for s in stops)} stops")


if __name__ == "__main__":
    main()
