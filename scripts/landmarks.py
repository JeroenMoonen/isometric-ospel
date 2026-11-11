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

# Buildings found by an address or point; `pand` is resolved to the 3D BAG building under that point.
BUILDINGS = [
    {
        "name": "Sint-Willibrorduskerk",
        "note": "R.K. zaalkerk uit 1950 naar ontwerp van J. Deltrap",
        "kind": "Kerk · 1950",
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
    {"name": "Voormalige tabaksschuur (ca. 1870)", "at": (192660.0, 377621.0), "kind": "Ca. 1870", "stop": "Tabaksschuur"},
    # The other koningshoeven, from OpenStreetMap (names, BAG building years) and the Rijksmonumenten register.
    {"name": "Emmahoeve", "latlon": (51.42026, 5.89746), "kind": "Koningshoeve · rijksmonument", "stop": "Emmahoeve"},
    {
        "name": "Julianahoeve",
        "latlon": (51.41126, 5.90111),
        "kind": "Koningshoeve · 1910",
        "address": "Soemeersingel 107",
        "text": "Een van de koningshoeven van de Maatschappij Helenaveen, vernoemd naar prinses Juliana. Nu is het Landgoed Julianahoeve, met een camping.",
        "photo": ("Julianahoeve,_voor-_en_linker_zijgevel_-_Helenaveen_-_20107512_-_RCE.jpg", "De Julianahoeve in 1979, Rijksdienst voor het Cultureel Erfgoed, CC BY-SA 4.0"),
        "web": "https://www.landgoed-julianahoeve.nl",
    },
    {
        "name": "Oranjehoeve",
        "latlon": (51.40502, 5.91000),
        "kind": "Koningshoeve · 1912",
        "address": "Soemeersingel 87",
        "text": "Een van de koningshoeven van de Maatschappij Helenaveen, vernoemd naar het Huis van Oranje. Tegenwoordig een groepsaccommodatie.",
        "photo": ("Oranjehoeve_-_Helenaveen_-_20107510_-_RCE.jpg", "De Oranjehoeve in 1979, Rijksdienst voor het Cultureel Erfgoed, CC BY-SA 4.0"),
        "web": "https://www.oranjehoeve.com/",
    },
    {"name": "Willem de Zwijgerhoeve", "latlon": (51.39099, 5.91658), "kind": "Boerderij · 1934"},
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
    {"name": "Oorlogsmonument", "latlon": (51.38868, 5.91955), "kind": "Monument", "stop": "De oude kerk verwoest"},
    {"name": "Beeld: de jager die het zwijn doodde", "latlon": (51.3887, 5.91966), "kind": "Oorlogsmonument", "stop": "De jager die het zwijn doodde"},
    {"name": "Kunstwerk: kiepkarren met turf", "latlon": (51.38868, 5.91982), "kind": "Kunstwerk", "stop": "Kipkarren op het Kerkplein"},
    {"name": "Borstbeeld koningin Juliana", "latlon": (51.38939, 5.91762), "kind": "Beeld", "stop": "Koningin Juliana"},
    {"name": "Speeltuin 't Turfveldje", "latlon": (51.38773, 5.91842), "kind": "Speeltuin"},
    # Aardbeiweg 2 is the Protestant cemetery, Aardbeiweg 4 the Catholic one (rijksmonumenten register, Wikidata).
    {"name": "Protestantse begraafplaats (ca. 1885)", "latlon": (51.38613, 5.91274), "kind": "Rijksmonument", "stop": "Protestantse begraafplaats"},
    {"name": "Katholieke begraafplaats", "latlon": (51.38511, 5.91346), "kind": "Begraafplaats", "stop": "Het katholieke kerkhof"},
    {"name": "Sportpark", "latlon": (51.38566, 5.91100), "kind": "Sport"},
    {"name": "Vindplaats Gouden Helm", "latlon": (51.39051, 5.90431), "kind": "Monument", "stop": "De Gouden Helm"},
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
        "text": "Een van de monumenten 'Sporen die bleven' in de dorpen tussen Maas en Peel, voor de razzia's van het najaar van 1944, toen de bezetter duizenden jongens en mannen wegvoerde voor dwangarbeid in Duitsland.",
    },
    {"name": "Beeld: Hellehond", "latlon": (51.40699, 5.90938), "kind": "Kunstwerk"},
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


def main():
    feats = [json.loads(line) for line in open(RAW / "3dbag.jsonl")]
    rings = []
    for f in feats:
        t = f["transform"]
        V = np.array(f["vertices"], dtype=np.float64) * t["scale"] + t["translate"]
        co = f["CityObjects"][f["id"]]
        rings.append((f["id"], V[co["geometry"][0]["boundaries"][0][0]][:, :2], co["attributes"]))

    out = {"buildings": {}, "places": [], "masts": [], "hotspots": []}
    for b in BUILDINGS:
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
        x, y = wgs_to_rd(*p["latlon"])
        out["places"].append({"name": p["name"], "note": p.get("note"), "x": x, "y": y, "h": 2.0})
        out["hotspots"].append({"name": p["name"], "x": x, "y": y, **{k: p[k] for k in INFO if k in p}})
    for m in MASTS:
        x, y = wgs_to_rd(*m["latlon"])
        out["masts"].append({**{k: v for k, v in m.items() if k != "latlon"}, "x": x, "y": y})
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "landmarks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
