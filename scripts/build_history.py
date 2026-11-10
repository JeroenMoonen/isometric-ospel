"""Helenaveen van toen: a guided tour along the village's history, as an overlay for the viewer.

Texts are written for this map from: Het Helenaveen van toen (helenaveenvantoen.nl, every stop links to its story
there), Monumenten in Nederland, Noord-Brabant (1997, via DBNL), the Rijksmonumenten register and Wikimedia Commons. Photos are from the Rijksdienst voor het Cultureel Erfgoed (CC BY-SA 4.0) and
other Commons files with an open license; they are downloaded once and published with the site, with credits.

Output: data/build/history.json and data/build/history/*.jpg
"""

import hashlib
import json
import subprocess
import time
import urllib.parse
import urllib.request

from config import BUILD, CX, CY
from geo import wgs_to_rd

MONUMENTEN = ("Monumenten in Nederland: Noord-Brabant", "https://www.dbnl.org/tekst/sten009monu02_01/sten009monu02_01_0081.php")
RCE = "Rijksdienst voor het Cultureel Erfgoed, CC BY-SA 4.0"
HVT = "https://www.helenaveenvantoen.nl/"  # Het Helenaveen van toen: the village's own history site

STOPS = [
    {
        "year": "1853",
        "title": "Helenaveen begint",
        "at": (191850, 377850),
        "zoom": 0.25,
        "text": "Jan en Nicolaas van de Griendt kopen hier 610 hectare hoogveen om af te graven en daarna te ontginnen tot landbouwgrond. Het dorp dat in de zuidoosthoek ontstaat, noemen ze naar Helena, de vrouw van Jan.",
        "photo": ("Hulpkaart_75_DNE00_H_detail_Helenaveen_1861.jpg", "Kadastrale hulpkaart van Helenaveen, 1861 (CC0)"),
        "source": MONUMENTEN,
        "more": HVT + "ontstaan-helenaveen",
    },
    {
        "year": "1853",
        "title": "De Helenavaart",
        "at": (191975, 378255),
        "text": "Om de turf af te voeren laat Van de Griendt een eigen kanaal graven, van de Noordervaart bij Meijel tot in de Peel. Het graven begint in juni 1853; in januari 1854 bereiken de kanaalgravers de plek van het dorp. Ze komen van overal: uit de omgeving, uit de veenkoloniën in het noorden, en als seizoenarbeiders uit de buurt van Hannover.",
        "source": ("Het Helenaveen van toen", HVT),
        "more": HVT,
    },
    {
        "year": "1867",
        "title": "Protestantse kerk",
        "at": (191907.3, 378307.1),
        "h": 12,
        "text": "Een eenvoudig neoclassicistisch zaalkerkje voor de protestantse veenarbeiders, met een fronton en een dakruiter op de voorgevel. In 1883 kreeg de gevel een gedenksteen bij het overlijden van predikant Swalue. Het is een rijksmonument.",
        "photo": ("Prot.Kerk_-_Helenaveen_-_20107504_-_RCE.jpg", f"Protestantse kerk in 1979, {RCE}"),
        "source": MONUMENTEN,
        "more": HVT + "page1-3",
    },
    {
        "year": "1867",
        "title": "Pastorie en kazemat",
        "at": (191902.6, 378289.2),
        "h": 8,
        "text": "De predikantenwoning, Soemeersingel 25, is net zo oud als de kerk ernaast. In de voortuin staat een S-kazemat, een bunkertje van de Peel-Raamstelling. In mei 1940 werd er in Helenaveen gevochten.",
        "photo": ("Pastorie,_voorgevel_-_Helenaveen_-_20107503_-_RCE.jpg", f"De pastorie in 1979, {RCE}"),
        "source": MONUMENTEN,
        "more": HVT + "verslag-kapitein",
    },
    {
        "year": "ca. 1870",
        "title": "Tabaksschuur",
        "at": (192660, 377621),
        "h": 6,
        "text": "Uit Gelderland kwamen tabakstelers naar Helenaveen. De Maatschappij Helenaveen liet hier een schuur bouwen om de tabak te drogen; al rond 1880 werd die verdeeld in twee boerderijen.",
        "source": MONUMENTEN,
        "more": HVT + "tabakstelersrs-uit-gelderland",
    },
    {
        "year": "ca. 1880",
        "title": "Zondagsschool",
        "at": (191920.1, 378300.0),
        "h": 7,
        "text": "Rechts tegen de kerk kwam rond 1880 een zondagsschool, in 1900 verbouwd. Samen met kerk en pastorie vormt hij het protestantse complex aan de Helenavaart.",
        "photo": ("Overzicht_westgevel_met_voorgevels_zondagsschool_en_predikantenwoning_-_Helenaveen_-_20348335_-_RCE.jpg", f"Kerk, zondagsschool en pastorie vanaf de overkant van de vaart, 1997, {RCE}"),
        "source": MONUMENTEN,
        "more": HVT + "page1-3",
    },
    {
        "year": "1881",
        "title": "Turfstrooiselfabriek",
        "at": (191854, 378594),
        "h": 6,
        "text": "De bovenste, lichte laag veen, het grauwveen, brandde slecht en werd eerst gewoon teruggegooid. Toen men ontdekte dat het een goed strooisel voor stallen was, bouwde de Maatschappij Helenaveen hier een turfstrooiselfabriek, met woningen voor het personeel ertegenaan.",
        "source": MONUMENTEN,
        "more": HVT + "turfstrooiselfabriek",
    },
    {
        "year": "ca. 1885",
        "title": "Hervormde begraafplaats",
        "latlon": (51.3851, 5.91358),
        "h": 2,
        "text": "Aan de Aardbeiweg liggen veenarbeiders begraven die van ver kwamen: uit de hoogveengebieden in het noorden van Nederland en uit Duitsland.",
        "source": MONUMENTEN,
    },
    {
        "year": "1908",
        "title": "Wilhelminahoeve",
        "at": (191131, 380087),
        "h": 8,
        "text": "De eerste van elf grote boerderijen die de Maatschappij Helenaveen vanaf 1908 bouwde, onder directeur Adrianus Bos. Ze heten koningshoeven naar leden van het koningshuis; dat het Fonds Koning Willem III ze bouwde is een misvatting, het droeg alleen bij aan een paar ervan.",
        "photo": ("Wilhelminahoeve,_voorgevel_-_Helenaveen_-_20107511_-_RCE.jpg", f"De Wilhelminahoeve in 1979, {RCE}"),
        "source": ("Het Helenaveen van toen: de koningshoeven", HVT + "wilhelminahoeve"),
        "more": HVT + "wilhelminahoeve",
    },
    {
        "year": "na 1908",
        "title": "Emmahoeve",
        "at": (190481, 381355),
        "h": 8,
        "text": "Nog een van de koningshoeven, aan de Kaasweg, vernoemd naar koningin Emma. Net als de andere hoeven is het een kop-rompboerderij: een woonhuis met daarachter een grote schuur.",
        "source": ("Het Helenaveen van toen: de koningshoeven", HVT + "wilhelminahoeve"),
        "more": HVT + "wilhelminahoeve",
    },
    {
        "year": "1910",
        "title": "De Gouden Helm",
        "latlon": (51.39051, 5.90431),
        "h": 2,
        "text": "In het veen bij Helenaveen werd in 1910 een vergulde helm van een Romeinse officier gevonden, de Gouden Helm van Deurne. Het gemeenschapshuis in het dorp is ernaar vernoemd; op de vindplaats staat een gedenkteken.",
        "source": ("Het Helenaveen van toen", HVT + "een-romein-komt-om-in-de-peel"),
        "more": HVT + "een-romein-komt-om-in-de-peel",
    },
    {
        "year": "1913",
        "title": "Willem III-hoeve",
        "at": (190290, 381292),
        "h": 8,
        "text": "De noordelijkste koningshoeve, met het jaartal en de naam in de trapgevel. Een rijksmonument, en tegenwoordig een ijsboerderij met terras.",
        "photo": ("Willem_III_hoeve,_voor-_en_rechter_zijgevel_-_Helenaveen_-_20107513_-_RCE.jpg", f"De Willem III-hoeve in 1979, {RCE}"),
        "source": MONUMENTEN,
        "more": HVT + "wilhelminahoeve",
    },
    {
        "year": "1915",
        "title": "Het veen is op",
        "at": (192750, 378900),
        "text": "In 1915 stopt de grote turfwinning en wordt er vooral ontgonnen tot land- en tuinbouwgrond. Wat je hier ziet is wat er van het hoogveen over is: heide, vennen en bos, nu natuur in de Deurnsche Peel.",
        "source": MONUMENTEN,
        "more": HVT + "turfgraven",
    },
    {
        "year": "ca. 1930",
        "title": "Dorpsschool De Peelparel",
        "at": (191907.0, 377855.0),
        "h": 9,
        "text": "Een gaaf bewaarde dorpsschool met zes lokalen, met een klokkentorentje op het dak. Nog altijd de basisschool van Helenaveen.",
        "photo": ("Bassisschool_de_Peelparel_Helenaveen_8-025.jpg", "De Peelparel in 2001, publiek domein"),
        "source": MONUMENTEN,
        "more": HVT + "page1-3",
    },
    {
        "year": "1937",
        "title": "Kipkarren op het Kerkplein",
        "latlon": (51.38868, 5.91982),
        "h": 2,
        "text": "Na het vervenen moest de grond nog ontgonnen worden, vanaf 1937 ook door werklozen in de werkverschaffing. Met kipkarren legden ze wegen aan, groeven sloten en dempten oude turfvaarten. De karren op het Kerkplein herinneren daaraan; met turfsteken hadden ze niets te maken.",
        "source": ("Het Helenaveen van toen", HVT + "zinkske-ss-kamp"),
        "more": HVT + "zinkske-ss-kamp",
    },
    {
        "year": "1941",
        "title": "Het Wehrmachthuisje aan de Koolweg",
        "at": (191828, 379144),
        "text": "Tegen de bosrand aan de Koolweg bouwden de Duitsers een huisje voor de bemanning van een zoeklicht. Het hoorde bij de Kammhuberlinie, de luchtverdediging tegen Britse bommenwerpers op weg naar het Ruhrgebied. De stip staat midden op de Koolweg; de precieze plek ken ik niet.",
        "source": ("Het Helenaveen van toen", HVT + "wehrmachtshuisje"),
        "more": HVT + "wehrmachtshuisje",
    },
    {
        "year": "1944",
        "title": "De oude kerk verwoest",
        "at": (192080, 377790),
        "h": 14,
        "text": "In de oorlog ging de rooms-katholieke kerk uit 1857 verloren, een vroeg werk van de beroemde architect P.J.H. Cuypers. Het oorlogsmonument bij de kerk herinnert aan deze tijd.",
        "source": MONUMENTEN,
        "more": HVT + "oorlog-1",
    },
    {
        "year": "1950",
        "title": "Sint-Willibrorduskerk",
        "at": (192080, 377790),
        "h": 25,
        "text": "Op dezelfde plek bouwde J. Deltrap een nieuwe kerk: een eenvoudige zaalkerk in traditionele vormen, met een klokkentoren die met 26 meter boven het dorp uitsteekt.",
        "source": MONUMENTEN,
        "more": HVT + "rectoraat",
    },
    {
        "year": "nu",
        "title": "Het katholieke kerkhof",
        "latlon": (51.38615, 5.91274),
        "h": 2,
        "text": "Op het kerkhof van Helenaveen zetten vrijwilligers van Memori zich in om de oude graven te bewaren, en daarmee de verhalen van de mensen die het dorp opbouwden.",
        "source": ("Het Helenaveen van toen", HVT + "memori"),
        "more": HVT + "memori",
    },
    {
        "year": "1999",
        "title": "Beschermd dorpsgezicht",
        "at": (191850, 377850),
        "zoom": 0.3,
        "text": "Vanwege de bijzondere geschiedenis als veenkolonie werd Helenaveen in 1999 een beschermd dorpsgezicht. Einde van de rondleiding. Veel meer verhalen, foto's en kaarten staan op Het Helenaveen van toen.",
        "source": ("Land van de Peel", "https://www.landvandepeel.nl/en/locations/459373849/protected-rural-area-helenaveen"),
        "more": HVT,
    },
]


def commons_thumb(name, width=960):  # Wikimedia only serves a fixed set of thumbnail widths
    h = hashlib.md5(name.encode()).hexdigest()
    q = urllib.parse.quote(name)
    return f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{width}px-{q}"


def download(url, tries=6):
    """Wikimedia rate-limits bursts of thumbnail requests; wait politely and retry."""
    req = urllib.request.Request(url, headers={"User-Agent": "isometric-helenaveen/0.1 (personal map)"})
    for attempt in range(tries):
        try:
            data = urllib.request.urlopen(req, timeout=60).read()
            time.sleep(3)
            return data
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == tries - 1:
                raise
            time.sleep(15 * (attempt + 1))


def main():
    out_dir = BUILD / "history"
    out_dir.mkdir(parents=True, exist_ok=True)
    stops = []
    for i, s in enumerate(STOPS, start=1):
        x, y = s["at"] if "at" in s else wgs_to_rd(*s["latlon"])
        stop = {"n": i, "year": s["year"], "title": s["title"], "text": s["text"], "x": round(x, 1), "y": round(y, 1),
                "h": s.get("h", 0), "zoom": s.get("zoom", 1.2),
                "source": {"label": s["source"][0], "url": s["source"][1]}, "more": s.get("more")}
        if "photo" in s:
            name, credit = s["photo"]
            dst = out_dir / f"{i:02d}.jpg"
            if not dst.exists():
                dst.write_bytes(download(commons_thumb(name)))
                subprocess.run(["magick", str(dst), "-resize", "640x640>", "-quality", "82", str(dst)], check=True)
            stop["photo"] = {"src": f"history/{dst.name}", "credit": credit,
                             "url": f"https://commons.wikimedia.org/wiki/File:{urllib.parse.quote(name)}"}
        stops.append(stop)
    (BUILD / "history.json").write_text(json.dumps({"stops": stops}, ensure_ascii=False, indent=1))
    print(f"{len(stops)} stops, {sum('photo' in s for s in stops)} photos")


if __name__ == "__main__":
    main()
