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
        "at": (191907.3, 378307.1),
        "style": "church",
        "wall": (234, 230, 218),
        "roof": (78, 80, 88),
        # Dakruiter on the front, seen in AHN as a spike over the canal-side end of the ridge.
        "turret": {"x": 191911.2, "y": 378298.7, "r": 1.0, "base": 9.4, "body": 12.6, "top": 16.8},
    },
    {
        "name": "Zondagsschool (ca. 1880)",
        "at": (191920.1, 378300.0),
        "style": "house",
        "wall": (152, 86, 66),
        "roof": (82, 84, 90),
        "frame": (236, 234, 226),
    },
    {
        "name": "Pastorie (1867)",
        "note": "Predikantenwoning, rijksmonument",
        "at": (191902.6, 378289.2),
        "style": "house",
        "wall": (150, 90, 70),
        "roof": (66, 68, 74),
        "frame": (240, 238, 230),
    },
    {
        "name": "Basisschool De Peelparel",
        "note": "Dorpsschool met zes lokalen uit ca. 1930",
        "at": (191907.0, 377855.0),
        "style": "school",
        "wall": (176, 112, 96),
        "roof": (186, 90, 60),
        "bell": True,
    },
    {"name": "Gemeenschapshuis De Gouden Helm", "latlon": (51.38802, 5.91843)},
    {"name": "Hotel Eetcafé In d'Ouwe Peel", "latlon": (51.38892, 5.91938)},
    {"name": "Voormalige tabaksschuur (ca. 1870)", "at": (192660.0, 377621.0)},
]

# Points without a building of their own.
POINTS = [
    {"name": "Oorlogsmonument", "latlon": (51.38868, 5.91955)},
    {"name": "Beeld: de jager die het zwijn doodde", "latlon": (51.3887, 5.91966)},
    {"name": "Kunstwerk: kiepkarren met turf", "latlon": (51.38868, 5.91982)},
    {"name": "Borstbeeld koningin Juliana", "latlon": (51.38939, 5.91762)},
    {"name": "Speeltuin 't Turfveldje", "latlon": (51.38773, 5.91842)},
    {"name": "Kerkhof Helenaveen", "latlon": (51.38615, 5.91274)},
    {"name": "Hervormde begraafplaats (ca. 1885)", "latlon": (51.3851, 5.91358)},
    {"name": "Sportpark", "latlon": (51.38566, 5.91100)},
    {"name": "Vindplaats Gouden Helm", "latlon": (51.39051, 5.90431)},
    {"name": "Eijndepaal", "latlon": (51.38475, 5.93129)},
    {"name": "Esso Helenaveen", "latlon": (51.37943, 5.90877)},
    {"name": "Zendmast", "latlon": (51.37999, 5.90874)},
    {"name": "Camping De Peelkant", "latlon": (51.39878, 5.8964)},
    {"name": "Camping de Peelweide", "latlon": (51.37558, 5.93315)},
    {"name": "Brug Spiesberg", "latlon": (51.37756, 5.93492)},
]

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

    out = {"buildings": {}, "places": [], "masts": []}
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
            out["buildings"][pid] = {k: v for k, v in b.items() if k not in ("at", "latlon", "note")}
        print(f"{b['name']}: {pid or 'no building'}")
    for p in POINTS:
        x, y = wgs_to_rd(*p["latlon"])
        out["places"].append({"name": p["name"], "x": x, "y": y, "h": 2.0})
    for m in MASTS:
        x, y = wgs_to_rd(*m["latlon"])
        out["masts"].append({**{k: v for k, v in m.items() if k != "latlon"}, "x": x, "y": y})
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "landmarks.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
