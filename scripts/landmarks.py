# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Named places of Helenaveen: style overrides and extra geometry for buildings, plus the viewer's place list.

Sources: Monumenten in Nederland, Noord-Brabant (1997), Rijksmonumenten photos on Wikimedia Commons,
OpenStreetMap, and AHN for tower positions and heights.

Output: data/build/landmarks.json
"""

import json

import numpy as np

from config import BUILD, RAW
from geo import wgs_to_rd

HVT = "https://www.helenaveenvantoen.nl/"  # Het Helenaveen van toen, the village's own history site

# Buildings found by an address or point; `pand` is resolved to the 3D BAG building under that point.
BUILDINGS = [
    {
        "name": "Sint-Willibrorduskerk",
        "note": "Zaalkerk uit 1950 van J. Deltrap, sinds 2024 woningen",
        "kind": "Voormalige kerk · 1950",
        "stop": "Sint-Willibrorduskerk",
        "at": (192080, 377790),
        "style": "church",
        "wall": (146, 80, 62),
        "roof": (70, 72, 80),
        # Tower from AHN: about 4 m square near the north-west corner, 26 m to the top.
        "tower": {"x": 192090.0, "y": 377807.4, "w": 4.6, "body": 19.0, "top": 25.5, "cross": True},
    },
    {
        "name": "Protestantse kerk (1867)",
        "note": "Neoclassicistisch zaalkerkje met dakruiter, rijksmonument",
        "kind": "Rijksmonument · 1867",
        "stop": "Protestantse kerk",
        "at": (191907.3, 378307.1),
        "style": "church",
        "wall": (234, 230, 218),
        "roof": (78, 80, 88),
        # Dakruiter on the front, seen in AHN as a spike over the canal-side end of the ridge.
        "turret": {"x": 191911.2, "y": 378298.7, "r": 1.0, "base": 9.4, "body": 12.6, "top": 16.8},
    },
    {
        "name": "Zondagsschool (ca. 1880)",
        "kind": "Ca. 1880",
        "stop": "Zondagsschool",
        "at": (191920.1, 378300.0),
        "style": "house",
        "wall": (152, 86, 66),
        "roof": (82, 84, 90),
        "frame": (236, 234, 226),
    },
    {
        "name": "Pastorie (1867)",
        "note": "Predikantenwoning, rijksmonument",
        "kind": "Rijksmonument · 1867",
        "stop": "Pastorie en kazemat",
        "at": (191902.6, 378289.2),
        "style": "house",
        "wall": (150, 90, 70),
        "roof": (66, 68, 74),
        "frame": (240, 238, 230),
    },
    {
        "name": "Basisschool De Peelparel",
        "note": "Dorpsschool met zes lokalen uit ca. 1930",
        "kind": "Basisschool",
        "address": "Oude Peelstraat 10",
        "web": "https://www.peelparel.nl",
        "stop": "Dorpsschool De Peelparel",
        "at": (191907.0, 377855.0),
        "style": "school",
        "wall": (176, 112, 96),
        "roof": (186, 90, 60),
        "bell": True,
    },
    {
        "name": "Hoeve Willem III",
        "note": "Kop-rompboerderij uit 1913, rijksmonument, nu ijsboerderij",
        "kind": "Koningshoeve · 1913",
        "address": "Soemeersingel 127",
        "stop": "Willem III-hoeve",
        "at": (190290.0, 381292.0),
        "style": "house",
        "wall": (126, 70, 56),
        "roof": (74, 76, 82),
        "frame": (238, 236, 228),
    },
    {
        "name": "Wilhelminahoeve",
        "note": "Kop-rompboerderij uit 1908, rijksmonument",
        "kind": "Koningshoeve · 1908",
        "stop": "Wilhelminahoeve",
        "at": (191131.0, 380087.0),
        "style": "house",
        "wall": (130, 72, 58),
        "roof": (78, 80, 86),
        "frame": (238, 236, 228),
    },
    {
        "name": "Gemeenschapshuis De Gouden Helm",
        "latlon": (51.38802, 5.91843),
        "address": "Oude Peelstraat 3",
        "web": "https://www.degoudenhelm.nl",
        "stop": "Gemeenschapshuis De Gouden Helm",
    },
    {
        "name": "Hotel Eetcafé In d'Ouwe Peel",
        "latlon": (51.38892, 5.91938),
        "kind": "Hotel en eetcafé",
        "address": "Oude Peelstraat 2",
        "text": "Hotel en eetcafé midden in het dorp, tegenover de kerk.",
        "web": "https://www.indouwepeel.nl",
    },
    {"name": "Voormalige tabaksschuur (ca. 1870)", "addrs": ["Geldersestraat 10", "Geldersestraat 12"], "kind": "Tabaksschuur · ca. 1870", "address": "Geldersestraat 10 en 12", "stop": "Tabaksschuur"},
    # From Het Helenaveen van toen; the 3D BAG building years agree that these still stand.
    {
        "name": "Tabaksschuur Waldeck-Hoeve",
        "addrs": ["Geldersestraat 3", "Geldersestraat 5"],
        "kind": "Tabaksschuur",
        "address": "Geldersestraat 3 en 5",
        "text": "Een van de grote tabaksschuren aan de Geldersestraat, toen nog de Geldersche Laan. Een tijd stond de naam Waldeck-Hoeve op de zijgevel; nu zijn het twee huizen. Op de kaart van 1889 is de omgeving geel van de tabaksvelden.",
        "more": HVT + "de-kaar-van-deel-1",
    },
    {
        "name": "Tabaksschuur Geldersestraat 4 en 6",
        "addrs": ["Geldersestraat 4", "Geldersestraat 6"],
        "kind": "Tabaksschuur",
        "address": "Geldersestraat 4 en 6",
        "text": "Schuin tegenover de Waldeck-Hoeve staat de volgende grote tabaksschuur van de Geldersestraat, uit de tijd dat hier tabak werd geteeld.",
        "more": HVT + "de-kaar-van-deel-1",
    },
    {
        "name": "Woonhuis van Jules de Corte",
        "addrs": ["Geldersestraat 9"],
        "kind": "Woonhuis",
        "address": "Geldersestraat 9",
        "text": "Zanger, pianist en liedjesschrijver Jules de Corte (1924-1996) woonde hier vanaf 1973 tot zijn dood, en werkte er vaak tot diep in de nacht aan zijn liedjes. Hij schreef er ruim 4000, waaronder Ik zou wel eens willen weten en Koning Onbenul.",
        "more": HVT + "jules-de-corte",
    },
    {
        "name": "Zuivelfabriekje De Fuke",
        "addrs": ["Helenastraat 18"],
        "kind": "Ca. 1896",
        "address": "Helenastraat 18",
        "text": "Martinus van de Mortel, Tinus de Fauts, begon hier een fabriekje voor roomboter, De Fuke. Het was niet rendabel genoeg en ging al snel weer dicht. Het gebouw staat er nog en is nu een woonhuis.",
        "more": HVT + "geschiedenis-in-jaartallen",
    },
    # The other koningshoeven, from OpenStreetMap (names, BAG building years) and the Rijksmonumenten register.
    {"name": "Emmahoeve", "latlon": (51.42026, 5.89746), "kind": "Koningshoeve · rijksmonument", "stop": "Emmahoeve"},
    {
        "name": "Julianahoeve",
        "latlon": (51.41126, 5.90111),
        "kind": "Koningshoeve · 1910",
        "address": "Soemeersingel 107",
        "text": "In 1910 bouwde de Maatschappij twee koningshoeven die bijna elkaars evenbeeld zijn: de Emmahoeve en deze Julianahoeve, die in 1911 klaar was. De eerste pachter was Johannes Dekker uit Noord-Holland. Nu is het Landgoed Julianahoeve, met een camping.",
        "more": HVT + "de-juliana-hoeve",
        "photo": ("Julianahoeve,_voor-_en_linker_zijgevel_-_Helenaveen_-_20107512_-_RCE.jpg", "De Julianahoeve in 1979, Rijksdienst voor het Cultureel Erfgoed, CC BY-SA 4.0"),
        "web": "https://www.landgoed-julianahoeve.nl",
    },
    {
        "name": "Oranjehoeve",
        "latlon": (51.40502, 5.91000),
        "kind": "Koningshoeve · 1912",
        "address": "Soemeersingel 87",
        "text": "De Maatschappij Helenaveen bouwde deze koningshoeve in 1912, aan de Helenavaart bij het drooggelegde Soemeer, op de plek van een huis dat er in 1889 al stond. Tegenwoordig een groepsaccommodatie.",
        "more": HVT + "de-kaar-van-deel-1",
        "photo": ("Oranjehoeve_-_Helenaveen_-_20107510_-_RCE.jpg", "De Oranjehoeve in 1979, Rijksdienst voor het Cultureel Erfgoed, CC BY-SA 4.0"),
        "web": "https://www.oranjehoeve.com/",
    },
    {
        "name": "Jeugdgebouw De Wiek",
        "addrs": ["Soemeersingel 31"],
        "kind": "Voormalige school",
        "address": "Soemeersingel 31",
        "text": "Tot 1982 was dit de openbare lagere school De Zonnedauw, die er kwam toen de andere school van het dorp katholiek werd. Sinds 21 mei 1983 is het jeugdgebouw De Wiek, genoemd naar de wijken: de zijtakken van de peelkanalen waar turfschepen konden keren of aanleggen. Op de gevel zit een keramisch reliëf van de Deurnese kunstenaar Frans Jacobs, gemaakt bij De Porceleyne Fles.",
        "more": HVT + "monumenten-en-kunst",
    },
    # Casemate 206S of the Peel-Raamstelling (OpenStreetMap way 949470200, BAG building from 1938).
    {
        "name": "Kazemat 206",
        "at": (191902.8, 378260.3),
        "kind": "Kazemat · 1938",
        "text": "Een betonnen kazemat van de Peel-Raamstelling, van het type dat stekelvarken heet. Aan deze kant van de vaart stonden er drie, tussen de protestantse kerk en de Geldersestraat, bemand door soldaten van het 30ste Regiment Infanterie. Alleen nummer 206 staat er nog.",
        "more": HVT + "de-peel-onder-vuur",
    },
    {"name": "Willem de Zwijgerhoeve", "latlon": (51.39099, 5.91658), "kind": "Boerderij · 1934"},
    {"name": "Wehrmachthuisje", "at": (191577.0, 379760.0), "address": "Koolweg 40", "stop": "Het Wehrmachthuisje aan de Koolweg"},
    {"name": "Keuterboerderij", "at": (191630.7, 379389.2), "kind": "Rijksmonument", "address": "Soemeersingel 75", "stop": "Keuterboerderij aan de Soemeersingel"},
    # Businesses, from OpenStreetMap.
    {
        "name": "Cafetaria Van Veen",
        "latlon": (51.38962, 5.91891),
        "kind": "Cafetaria",
        "address": "Dominee Swaluestraat 1",
        "text": "De snackbar van het dorp: friet om mee te nemen, of op het terras.",
    },
    {
        "name": "Esso Helenaveen",
        "latlon": (51.37943, 5.90877),
        "kind": "Tankstation",
        "address": "Zinkskesweg 1",
        "text": "Tankstation aan de A67, met een Spar express.",
    },
]

# Points without a building of their own.
POINTS = [
    {
        "name": "Monument voor de burgerslachtoffers",
        "latlon": (51.38868, 5.91955),
        "kind": "Oorlogsmonument · 1985",
        "text": "Voor de inwoners die door deportatie of oorlogsgeweld omkwamen, onthuld op 4 mei 1985. Twee muurtjes staan voor de fundamenten van het dorp, die de oorlog doorstonden; daartegen rust een driehoekige steen als een dak, met 22 namen.",
        "more": HVT + "monumenten-en-kunst",
    },
    {"name": "Beeld: de jager die het zwijn doodde", "latlon": (51.3887, 5.91966), "kind": "Oorlogsmonument · 1956", "stop": "De jager die het zwijn doodde"},
    {"name": "Kunstwerk: kiepkarren met turf", "latlon": (51.38868, 5.91982), "kind": "Kunstwerk · 1978", "stop": "Kipkarren op het Kerkplein"},
    {"name": "Borstbeeld koningin Juliana", "latlon": (51.38939, 5.91762), "kind": "Beeld", "stop": "Koningin Juliana"},
    # The BGT art object on the corner of the green next to the church; AHN shows a 6 m tall structure there.
    {
        "name": "Jules de Corte-carillon",
        "at": (192040.6, 377827.6),
        "kind": "Carillon · 1975",
        "address": "Hannes Joostenplein",
        "text": "Op het grasveld naast de kerk hangt een carillon met 23 klokken van Eijsbouts uit Asten, betaald door het Koning Willem III-fonds. Bij de opening op 6 december 1975 begeleidde Jules de Corte de dorpsjeugd bij Hertog Jan: zijn debuut als beiaardier. Sinds 1996 draagt het carillon zijn naam, met op een bronzen plaat zijn regel: In de oude toren zingt het carillon.",
        "more": HVT + "monumenten-en-kunst",
    },
    # The only BGT art object along the Pastoor Kerssemakersstraat.
    {
        "name": "Kunstwerk: Vierzijdige Driehoek",
        "at": (191844.4, 377965.9),
        "kind": "Kunstwerk · 1990",
        "address": "Pastoor Kerssemakersstraat",
        "text": "Stalen balken in rood, blauw en geel, van de Bredase kunstenaar Norbert Veeger. Burgemeester Van Genabeek onthulde het op 23 januari 1990.",
        "more": HVT + "monumenten-en-kunst",
    },
    {"name": "Speeltuin 't Turfveldje", "latlon": (51.38773, 5.91842), "kind": "Speeltuin"},
    # Aardbeiweg 2 is the Protestant cemetery, Aardbeiweg 4 the Catholic one (rijksmonumenten register, Wikidata).
    {"name": "Protestantse begraafplaats (ca. 1885)", "latlon": (51.38613, 5.91274), "kind": "Rijksmonument", "stop": "Protestantse begraafplaats"},
    {"name": "Katholieke begraafplaats", "latlon": (51.38511, 5.91346), "kind": "Begraafplaats", "stop": "Het katholieke kerkhof"},
    {"name": "Sportpark", "latlon": (51.38566, 5.91100), "kind": "Sport"},
    {
        "name": "Romeins tempeltje",
        "latlon": (51.39051, 5.90431),
        "kind": "Monument · 1998",
        "text": "Op de vindplaats van de Gouden Helm, die hier in 1910 uit het veen kwam. Joep Coppens maakte het tempeltje van basaltlava, brons en baksteen. In de gevel staat E PALUDE EMERGO: ik kwam boven uit het veen.",
        "more": HVT + "monumenten-en-kunst",
        "stop": "De Gouden Helm",
    },
    {"name": "Eijndepaal", "latlon": (51.38475, 5.93129), "kind": "Grenspaal"},
    {"name": "Paal tussen Broemeer en Soemeer", "latlon": (51.40279, 5.91580), "kind": "Grenspaal"},
    {"name": "Zendmast", "latlon": (51.37999, 5.90874), "kind": "Telecommast"},
    {"name": "Camping De Peelkant", "latlon": (51.39878, 5.8964), "kind": "Camping", "address": "Centurioweg 7", "web": "https://www.peelkant.com/"},
    {"name": "Camping de Peelweide", "latlon": (51.37558, 5.93315), "kind": "Camping", "address": "Spiesberg 23", "web": "https://www.peelweide.nl"},
    {"name": "Camperplaats De Oude Hoeven", "latlon": (51.40924, 5.90605), "kind": "Camperplaats"},
    {"name": "Brug Spiesberg", "latlon": (51.37756, 5.93492), "kind": "Brug"},
    # Komoot's description of the monument, from its makers.
    {
        "name": "Herrezen uit de vergetelheid",
        "latlon": (51.40615, 5.91761),
        "kind": "Monument · 2021",
        "text": "Voor de 21 mannen die tussen 1940 en 1954 omkwamen bij vijf vliegtuigcrashes in de Peel. Het monument geeft namen aan slachtoffers die lang anoniem bleven. Een initiatief van Piet Snellen en Sjaar Huijs, ontworpen door Ruud van der Beele en onthuld in oktober 2021.",
    },
    {
        "name": "Sporen die bleven",
        "latlon": (51.40314, 5.91352),
        "kind": "Oorlogsmonument · 1944-2004",
        "text": "Voor de kerkrazzia van 8 oktober 1944. Uit Helenaveen werden 143 mensen weggevoerd; 26 mannen overleefden de oorlog niet. Het hoort bij een reeks die in 2004 in 45 dorpen tussen Maas en Peel werd geplaatst; kunstsmid Thijs van de Manakker maakte de smeedijzeren standaard.",
        "more": HVT + "monumenten-en-kunst",
    },
    {
        "name": "Mijmerplek met de Hellehond",
        "latlon": (51.40699, 5.90938),
        "kind": "Kunstwerk",
        "text": "Hier stond een Koningswoning, in 1888 gebouwd met een schenking van koning Willem III en in 1921 verwoest door een grote veenbrand. Op initiatief van Jan van Woezik is de oude huisput weer uitgegraven, met de Hellehond van de Helenaveense kunstenaar Dirk Verberne.",
        "more": HVT + "monumenten-en-kunst",
    },
    {
        "name": "Mijnenongeluk 1945",
        "latlon": (51.38751, 5.91419),
        "kind": "Oorlog",
        "text": "Op 19 mei 1945 ruimden Frans van den Eijnden uit Liessel en korporaal Meindert Postma uit Drachten hier mijnen, waar de Lagebrugweg en de Oude Peelstraat samenkomen. Een springmijn ging af en beiden kwamen om.",
        "more": HVT + "mijnenruimen-aan-de-lagebrugweg",
    },
    # Places that are gone.
    {
        "name": "Eerste school van Helenaveen",
        "latlon": (51.38540, 5.92277),
        "kind": "1861",
        "text": "In 1861 stelde de Maatschappij hier, op de hoek van de Geldersestraat en de Jan Deckersstraat, een gebouwtje beschikbaar als eerste school. Aan de overkant lag de scheepstimmerwerf. Het was maar een tijdelijke oplossing: al snel kwam er een nieuwe school.",
        "more": HVT + "scholen",
    },
    {
        "name": "Eerste noodkerk en kerkhof",
        "addr": "Fruitweg 2",
        "kind": "1857",
        "text": "Aan de Fruitweg werd in 1857 een katholieke noodkerk ingericht in de omgebouwde stal van een boerderij. Erbij lag het eerste kerkhof van Helenaveen, zo'n 20 bij 25 meter, waar 35 mensen werden begraven.",
        "more": HVT + "kerkhof",
    },
    {"name": "Turfstrooiselfabriek", "at": (191854.0, 378594.0), "kind": "Rijksmonument, afgebrand in 2025", "stop": "Turfstrooiselfabriek"},
    {"name": "Kunstwerk: Verleden Veen", "at": (192068.0, 377892.0), "kind": "Kunstwerk · 2006", "stop": "Verleden Veen"},
    {"name": "Kunstwerk: Peeltroef", "at": (190176.0, 381262.0), "kind": "Kunstwerk · 2014", "stop": "Peeltroef"},
]

# Series in the viewer's panel: a walk past these places, starting with the one nearest the village.
CATEGORIES = [
    ("koningshoeven", "Koningshoeven", ["Wilhelminahoeve", "Emmahoeve", "Julianahoeve", "Oranjehoeve", "Hoeve Willem III"]),
    ("historisch", "Historische gebouwen", [
        "Protestantse kerk (1867)", "Pastorie (1867)", "Zondagsschool (ca. 1880)", "Voormalige tabaksschuur (ca. 1870)",
        "Keuterboerderij", "Basisschool De Peelparel", "Sint-Willibrorduskerk", "Protestantse begraafplaats (ca. 1885)",
        "Tabaksschuur Waldeck-Hoeve", "Tabaksschuur Geldersestraat 4 en 6", "Woonhuis van Jules de Corte", "Zuivelfabriekje De Fuke",
        "Jeugdgebouw De Wiek",
    ]),
    ("oorlog", "Oorlog en herdenking", [
        "Monument voor de burgerslachtoffers", "Beeld: de jager die het zwijn doodde", "Mijnenongeluk 1945", "Wehrmachthuisje",
        "Sporen die bleven", "Herrezen uit de vergetelheid", "Kazemat 206",
    ]),
    ("kunst", "Kunst", [
        "Kunstwerk: kiepkarren met turf", "Beeld: de jager die het zwijn doodde", "Borstbeeld koningin Juliana", "Kunstwerk: Verleden Veen",
        "Kunstwerk: Peeltroef", "Mijmerplek met de Hellehond", "Romeins tempeltje", "Jules de Corte-carillon",
        "Kunstwerk: Vierzijdige Driehoek",
    ]),
    ("verdwenen", "Verdwenen", ["Eerste school van Helenaveen", "Eerste noodkerk en kerkhof", "Turfstrooiselfabriek"]),
    ("bedrijven", "Bedrijven", [
        "Hotel Eetcafé In d'Ouwe Peel", "Cafetaria Van Veen", "Hoeve Willem III", "Oranjehoeve", "Julianahoeve", "Camping De Peelkant",
        "Camping de Peelweide", "Camperplaats De Oude Hoeven", "Esso Helenaveen",
    ]),
]

# What the viewer shows when a place is clicked; the rest of an entry is for the render.
INFO = ("note", "kind", "text", "address", "web", "more", "photo", "stop")

# A steel lattice telecom mast next to the A67 (three antenna entries in OSM, one structure in AHN).
MASTS = [{"latlon": (51.37999, 5.90874), "height": 32.0, "base": 2.6, "tip": 0.7}]


def point_in_ring(x, y, ring):
    inside = False
    for (x1, y1), (x2, y2) in zip(ring, np.roll(ring, -1, axis=0)):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


ADDRESSES = None


def address_xy(name):
    """RD position of a BAG address such as "Geldersestraat 3" (data/raw/addresses.json, from scripts/fetch.py)."""
    global ADDRESSES
    if ADDRESSES is None:
        ADDRESSES = {label.replace(", Helenaveen", "").split(", ")[0]: (x, y) for x, y, label in json.loads((RAW / "addresses.json").read_text())}
    return ADDRESSES[name]


def building_at(rings, x, y):
    for rid, ring, a in rings:
        if point_in_ring(x, y, ring):
            return rid, a
    return None, None


def main():
    feats = [json.loads(line) for line in open(RAW / "3dbag.jsonl")]
    rings = []
    for f in feats:
        t = f["transform"]
        V = np.array(f["vertices"], dtype=np.float64) * t["scale"] + t["translate"]
        co = f["CityObjects"][f["id"]]
        rings.append((f["id"], V[co["geometry"][0]["boundaries"][0][0]][:, :2], co["attributes"]))

    out = {"buildings": {}, "places": [], "masts": [], "hotspots": [], "categories": []}
    for b in BUILDINGS:
        if "addrs" in b:
            pts = [address_xy(a) for a in b["addrs"]]
            pids = [building_at(rings, *pt)[0] for pt in pts]
            assert all(pids), f"{b['name']}: no building at {b['addrs']}"
            x, y = np.mean(pts, axis=0)
            out["places"].append({"name": b["name"], "note": b.get("note"), "x": x, "y": y, "h": 4.0})
            out["hotspots"].append({"name": b["name"], "pids": pids, "x": x, "y": y, **{k: b[k] for k in INFO if k in b}})
            print(f"{b['name']}: {', '.join(pids)}")
            continue
        x, y = b["at"] if "at" in b else wgs_to_rd(*b["latlon"])
        pid, attrs = None, None
        for rid, ring, a in rings:
            if point_in_ring(x, y, ring):
                pid, attrs = rid, a
                break
        if pid is None:
            d = [(np.hypot(*(ring.mean(0) - (x, y))), rid, a) for rid, ring, a in rings]
            dist, pid, attrs = min(d, key=lambda t: t[0])
            if dist > 20:
                pid = None
        height = ((attrs or {}).get("b3_h_dak_max") or 0) - ((attrs or {}).get("b3_h_maaiveld") or 0)
        if "tower" in b:
            height = b["tower"]["top"]
        elif "turret" in b:
            height = b["turret"]["top"]
        out["places"].append({"name": b["name"], "note": b.get("note"), "x": x, "y": y, "h": round(height, 1)})
        if pid and "style" in b:
            out["buildings"][pid] = {k: v for k, v in b.items() if k not in ("at", "latlon", *INFO)}
        if pid:
            out["hotspots"].append({"name": b["name"], "pid": pid, "x": x, "y": y, **{k: b[k] for k in INFO if k in b}})
        print(f"{b['name']}: {pid or 'no building'}")
    for p in POINTS:
        x, y = p["at"] if "at" in p else address_xy(p["addr"]) if "addr" in p else wgs_to_rd(*p["latlon"])
        out["places"].append({"name": p["name"], "note": p.get("note"), "x": x, "y": y, "h": 2.0})
        out["hotspots"].append({"name": p["name"], "x": x, "y": y, **{k: p[k] for k in INFO if k in p}})
    for m in MASTS:
        x, y = wgs_to_rd(*m["latlon"])
        out["masts"].append({**{k: v for k, v in m.items() if k != "latlon"}, "x": x, "y": y})
    names = {h["name"] for h in out["hotspots"]}
    for key, label, members in CATEGORIES:
        missing = [n for n in members if n not in names]
        assert not missing, f"{label}: no hotspot for {missing}"
        out["categories"].append({"key": key, "label": label, "names": members})
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "landmarks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
