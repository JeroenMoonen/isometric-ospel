"""Walking routes for the viewer: the junction network (wandelknooppunten) and long-distance paths from OpenStreetMap.

Lines are in the render's screen meters at ground level (see build_hotspots.py). Output: data/build/routes.json
"""

import json
import math

from config import BUILD, CX, CY, RAW, XMAX, XMIN, YMAX, YMIN
from geo import wgs_to_rd


def screen(lat, lon):
    x, y = wgs_to_rd(lat, lon)
    lx, lz = x - CX, CY - y
    return [round((lx + lz) / math.sqrt(2), 2), round((lx - lz) / (2 * math.sqrt(2)), 2)], XMIN <= x <= XMAX and YMIN <= y <= YMAX


def main():
    path = RAW / "osm_routes.json"
    routes, nodes = [], []
    if path.exists():
        for el in json.loads(path.read_text())["elements"]:
            t = el.get("tags", {})
            if el["type"] == "relation":
                lines = []
                for m in el.get("members", []):
                    if m.get("type") != "way" or not m.get("geometry"):
                        continue
                    pts = [screen(p["lat"], p["lon"]) for p in m["geometry"]]
                    if any(inside for _, inside in pts):
                        lines.append([p for p, _ in pts])
                if lines:
                    network = t.get("network", "")
                    name = t.get("name") or (f"Knooppunt {t['ref'].replace('-', ' naar ')}" if t.get("ref") else "Wandelroute")
                    routes.append({"name": name, "kind": "long" if network in ("nwn", "iwn") else "junction", "ref": t.get("ref"), "lines": lines})
            elif el["type"] == "node" and t.get("rwn_ref"):
                p, inside = screen(el["lat"], el["lon"])
                if inside:
                    nodes.append({"ref": t["rwn_ref"], "at": p})
    (BUILD / "routes.json").write_text(json.dumps({"routes": routes, "nodes": nodes}, ensure_ascii=False))
    print(f"{len(routes)} routes, {len(nodes)} junctions")


if __name__ == "__main__":
    main()
