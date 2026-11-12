# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy"]
# ///
"""Named places of Ospel: style overrides and extra geometry for buildings, plus the viewer's place list.

Sources: Wikipedia (nl), the rijksmonumentenregister, photos on Wikimedia Commons, OpenStreetMap, and AHN for the
church tower.

Output: data/build/landmarks.json
"""

import json

import numpy as np

from config import BUILD, RAW
from geo import wgs_to_rd

WP = "https://nl.wikipedia.org/wiki/"

# Buildings found by an address or point; `pand` is resolved to the 3D BAG building under that point.
BUILDINGS = [
    {
        "name": "Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk",
        "note": "Neogotische kruisbasiliek van Pierre Cuypers, rijksmonument",
        "kind": "Rijksmonument · 1868",
        "address": "Onze Lieve Vrouwestraat 38",
        "text": "Kort nadat Ospel in 1864 een eigen parochie werd, ontwierp Pierre Cuypers deze bakstenen kruisbasiliek; in 1868 werd ze ingewijd. In 1944 werd de toren opgeblazen en raakten de gewelven verwoest. De nieuwe toren van 1954 heeft een leien spits tussen vier hoektorentjes.",
        "more": WP + "Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk_(Ospel)",
        "photo": ("Ospel, kerk in straatzicht foto2 2011-03-20 15.36.JPG", "De kerk in 2011, Michielverbeek, CC BY-SA 3.0"),
        "latlon": (51.29824, 5.78438),
        "style": "church",
        "wall": (150, 80, 62),
        "roof": (70, 72, 80),
        # Tower from AHN: about 8 m square on the west end, the spire 50 m to the top of the cross.
        "tower": {"x": 182679.2, "y": 367720.0, "w": 8.0, "body": 27.0, "top": 50.0, "cross": True},
    },
    {
        "name": "Molen De Korenbloem",
        "note": "Beltmolen uit 1870, rijksmonument",
        "kind": "Rijksmonument · 1870",
        "address": "Korenbloemstraat 3",
        "text": "Een beltmolen uit 1870, op een plek waar nog nooit een molen had gestaan. Hij maalde tot 1948, werd in 1970 onttakeld en in 1972 door de gemeente gekocht. Sinds de restauratie van 1990 malen vrijwilligers er weer graan, met twee koppels stenen.",
        "more": WP + "De_Korenbloem_(Ospel)",
        "photo": ("De Korenbloem Ospel.jpg", "De Korenbloem in 2013, A. Ansems, CC0"),
        "latlon": (51.29967, 5.78027),
    },
    {
        "name": "Molen Sint-Joseph",
        "note": "Beltmolen uit 1840 in Kreijel, rijksmonument",
        "kind": "Rijksmonument · 1840",
        "text": "Twintig boeren lieten deze beltmolen in 1840 bouwen. Rond 1900 kwam er een zuiggasmotor in, om ook bij windstilte te kunnen malen. Tot rond 1970 was hij als korenmolen in bedrijf; in 1979 is hij gerestaureerd. De roeden zijn 25 meter lang.",
        "more": WP + "Sint-Joseph_(molen)",
        "latlon": (51.28915, 5.77109),
    },
    {
        "name": "Kapel Klaarstraat",
        "note": "Onze-Lieve-Vrouw-van-Altijddurende-Bijstandkapel, rijksmonument",
        "kind": "Rijksmonument · 1907",
        "address": "Klaarstraatzijweg 1",
        "text": "In 1893 stond hier een coöperatief melkfabriekje, met de hand bediend, onder de leuze Eendracht maakt macht. Toen de stoomzuivelfabriek het werk in 1906 overnam, werd het fabriekje verbouwd tot kapel; in 1907 werd die ingezegend. Binnen zijn het houten gewelf en de banken blauw geschilderd.",
        "more": WP + "Onze-Lieve-Vrouw-van-Altijddurende-Bijstandkapel_(Ospel)",
        "photo": ("Kapel Klaarstraatzijweg Ospel.jpg", "De kapel in 2009, A. Ansems, publiek domein"),
        "latlon": (51.29346, 5.77026),
    },
    {
        "name": "Basisschool De Schrank",
        "kind": "Basisschool",
        "address": "Siebenstraat 14",
        "text": "In 1993 gingen de Heilig Hartschool en de Sint-Annaschool samen in De Schrank. De Heilig Hartschool begon in 1861 als openbare lagere school; de meisjesschool hoorde bij het Sint-Annaklooster van de Franciscanessen uit Heythuysen, dat er van 1910 tot 1959 stond.",
        "web": "https://www.schrank.nl",
        "latlon": (51.30007, 5.78436),
    },
    {
        "name": "Gemeenschapshuis Haaze-Hoof",
        "kind": "Gemeenschapshuis",
        "address": "Aerthijsplein 3",
        "web": "https://www.haaze-hoof.nl/",
        "latlon": (51.29862, 5.78166),
    },
    {
        "name": "Buitencentrum De Pelen",
        "note": "Bezoekerscentrum van Nationaal Park De Groote Peel",
        "kind": "Bezoekerscentrum · 2000",
        "address": "Moostdijk 15",
        "text": "De hoofdingang van Nationaal Park De Groote Peel, vroeger Mijl op Zeven geheten: informatie, een terras en het begin van de wandelingen het hoogveen in. De Groote Peel is sinds 1993 een nationaal park.",
        "web": "https://www.np-degrootepeel.nl/",
        "latlon": (51.3258, 5.80157),
    },
    {"name": "Peelboerderij", "kind": "Boerderij · 1965", "latlon": (51.32786, 5.80172)},
    {
        "name": "Thomashuis Ospeldijk",
        "kind": "Voormalige school · 1952",
        "address": "Moostdijk 1",
        "text": "Hier stond de lagere school van Ospeldijk, eerst de Heilige Geestschool, later 't Kienhout. In 2012 ging de school dicht omdat er te weinig kinderen waren; nu is het een Thomashuis.",
        "latlon": (51.31985, 5.81452),
    },
    {"name": "De Dorpsherberg", "kind": "Restaurant", "address": "Casseweg 1A", "web": "https://www.dedorpsherberg.nl/", "latlon": (51.31065, 5.78687)},
]

# Points without a building of their own.
POINTS = [
    {
        "name": "Heilig Hartbeeld",
        "latlon": (51.29839, 5.78512),
        "kind": "Monument · 1926",
        "text": "Pastoor Carels vierde in 1924 zijn zilveren jubileum in Ospel en nam het initiatief voor dit beeld van Albert Verschuuren. Christus zegent met zijn rechterhand; naast hem knielen een vrouw met kind en een man met een zak op zijn schouder. Het parkje waarin het in 1926 kwam, hoort nu bij het kerkhof.",
        "more": WP + "Heilig_Hartbeeld_(Ospel)",
        "photo": ("Heilig Hartbeeld Ospel in 1935.jpg", "Het Heilig Hartbeeld in 1935, publiek domein"),
    },
    {"name": "Kerkhof", "latlon": (51.29823, 5.78463), "kind": "Begraafplaats"},
    {
        "name": "Monument voor de vliegtuigbemanningen",
        "latlon": (51.32801, 5.80214),
        "kind": "Oorlogsmonument",
        "text": "Een driekante zuil van roestvrij staal bij het bezoekerscentrum, ter nagedachtenis aan de vliegtuigbemanningen die in de Tweede Wereldoorlog in de Peel omkwamen.",
    },
    {
        "name": "Raatakker Gebleektendijk",
        "latlon": (51.2884, 5.80443),
        "kind": "Archeologie",
        "text": "Een celtic field: de sporen van een prehistorisch akkersysteem, kleine vierkante akkers met lage wallen eromheen, aangelegd tussen de late bronstijd en de Romeinse tijd.",
    },
    {"name": "Sportpark De Houwakker", "latlon": (51.304075, 5.78596), "kind": "Sport", "text": "Het sportpark van RKSVO, de voetbalclub van Ospel, opgericht in 1948."},
    {"name": "Vrienden van de Peel", "kind": "Restaurant in Haaze-Hoof", "address": "Aerthijsplein 3", "web": "https://vriendenvandepeel.nl/", "latlon": (51.2985, 5.78189)},
    {"name": "Kampeerderij De Kaaiewaaier", "latlon": (51.29537, 5.79165), "kind": "Camping", "web": "https://kampeerderijdekaaiewaaier.nl/"},
    {"name": "Camperplaats Anselberg", "latlon": (51.32372, 5.81544), "kind": "Camperplaats", "web": "https://www.anselberg.nl/"},
]

# Series in the viewer's panel: a walk past these places, starting with the one nearest the village.
CATEGORIES = [
    ("monumenten", "Monumenten", [
        "Onze-Lieve-Vrouw-Onbevlekt-Ontvangenkerk", "Molen De Korenbloem", "Molen Sint-Joseph", "Kapel Klaarstraat", "Heilig Hartbeeld",
    ]),
    ("peel", "De Groote Peel", ["Buitencentrum De Pelen", "Peelboerderij", "Monument voor de vliegtuigbemanningen", "Thomashuis Ospeldijk"]),
    ("bedrijven", "Eten en slapen", ["Vrienden van de Peel", "De Dorpsherberg", "Kampeerderij De Kaaiewaaier", "Camperplaats Anselberg"]),
]

# What the viewer shows when a place is clicked; the rest of an entry is for the render.
INFO = ("note", "kind", "text", "address", "web", "more", "photo", "stop")

# A steel lattice telecom mast next to the A67 (three antenna entries in OSM, one structure in AHN).
MASTS = []


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
        ADDRESSES = {label.split(", ")[0]: (x, y) for x, y, label in json.loads((RAW / "addresses.json").read_text())}
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
