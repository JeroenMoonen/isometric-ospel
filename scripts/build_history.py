"""Helenaveen van toen: a guided tour along the village's history, as an overlay for the viewer.

Texts are written for this map from: Het Helenaveen van toen (helenaveenvantoen.nl, every stop links to its story
there), Monumenten in Nederland, Noord-Brabant (1997, via DBNL), the Rijksmonumenten register and Wikimedia Commons. Photos are from the Rijksdienst voor het Cultureel Erfgoed (CC BY-SA 4.0) and
other Commons files with an open license; they are downloaded once and published with the site, with credits.

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
        "photos": [
            ("Coll_AV-014_Helena_JM01.jpg", "Helena Panis, de vrouw van Jan van de Griendt, naar wie het dorp heet (publiek domein)"),
            ("Hulpkaart_75_DNE00_H_detail_Helenaveen_1861.jpg", "Kadastrale hulpkaart van Helenaveen, 1861 (CC0)"),
        ],
        "source": MONUMENTEN,
        "more": HVT + "ontstaan-helenaveen",
    },
    {
        "year": "1853",
        "title": "De Helenavaart",
        "at": (191975, 378255),
        "text": "Om de turf af te voeren laat Van de Griendt een eigen kanaal graven, van de Noordervaart bij Meijel tot in de Peel. Het graven begint in juni 1853; in januari 1854 bereiken de kanaalgravers de plek van het dorp. Ze komen van overal: uit de omgeving, uit de veenkoloniën in het noorden, en als seizoenarbeiders uit de buurt van Hannover.",
        "photos": [
            ("Karakteristieke_landschappen,_water,_Helenavaart,_Peel,_Deurne,_Bestanddeelnr_164-0184.jpg", "De Helenavaart in 1957, Nationaal Archief, Nederlandse Heidemaatschappij (CC0)"),
            ("Helenavaart_P1040905.JPG", "De Helenavaart tussen Griendtsveen en Helenaveen, 2010 (publiek domein)"),
        ],
        "source": ("Het Helenaveen van toen", HVT),
        "more": HVT,
    },
    {
        "year": "1867",
        "title": "Protestantse kerk",
        "at": (191907.3, 378307.1),
        "h": 12,
        "text": "Een eenvoudig neoclassicistisch zaalkerkje voor de protestantse veenarbeiders, met een fronton en een dakruiter op de voorgevel. In 1883 kreeg de gevel een gedenksteen bij het overlijden van predikant Swalue. Het is een rijksmonument.",
        "photos": [
            ("Prot.Kerk_-_Helenaveen_-_20107504_-_RCE.jpg", f"Protestantse kerk in 1979, {RCE}"),
            ("Coll_AV-020_Swalue_domineeHveen.jpg", "Dominee E.B. Swalue, predikant in Helenaveen van 1867 tot 1883 (publiek domein)"),
            ("SOEMEERSINGEL_HELENAVEEN_DEURNE_protestantse_kerk_interieur_130718_-_protestant_chruch_interior.jpg", "Het interieur in 2013, Peter Bankers, CC BY-SA 4.0"),
        ],
        "source": MONUMENTEN,
        "more": HVT + "page1-3",
    },
    {
        "year": "1867",
        "title": "Pastorie en kazemat",
        "at": (191902.6, 378289.2),
        "h": 8,
        "text": "De predikantenwoning, Soemeersingel 25, is net zo oud als de kerk ernaast. In de voortuin staat een S-kazemat, een bunkertje van de Peel-Raamstelling. In mei 1940 werd er in Helenaveen gevochten.",
        "photos": [
            ("Pastorie,_voorgevel_-_Helenaveen_-_20107503_-_RCE.jpg", f"De pastorie in 1979, {RCE}"),
            ("Soemeersingel_25.jpg", "De pastorie in 2007 (publiek domein)"),
        ],
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
        "photos": [("Voormalige_tabaksschuur_ca._1870_Helenaveen.jpg", "De voormalige tabaksschuur in 2021, Sil Bouwmans, CC BY-SA 4.0")],
        "more": HVT + "tabakstelersrs-uit-gelderland",
    },
    {
        "year": "ca. 1880",
        "title": "Zondagsschool",
        "at": (191920.1, 378300.0),
        "h": 7,
        "text": "Rechts tegen de kerk kwam rond 1880 een zondagsschool, in 1900 verbouwd. Samen met kerk en pastorie vormt hij het protestantse complex aan de Helenavaart.",
        "photos": [("Overzicht_westgevel_met_voorgevels_zondagsschool_en_predikantenwoning_-_Helenaveen_-_20348335_-_RCE.jpg", f"Kerk, zondagsschool en pastorie vanaf de overkant van de vaart, 1997, {RCE}")],
        "source": MONUMENTEN,
        "more": HVT + "page1-3",
    },
    {
        "year": "1881",
        "title": "Turfstrooiselfabriek",
        "at": (191854, 378594),
        "h": 6,
        "text": "De bovenste, lichte laag veen, het grauwveen, brandde slecht en werd eerst gewoon teruggegooid. Toen men ontdekte dat het een goed strooisel voor stallen was, bouwde de Maatschappij Helenaveen hier een turfstrooiselfabriek, met woningen voor het personeel ertegenaan. Het rijksmonument aan de Rector Nuijtsstraat ging op 4 mei 2025 verloren bij een grote brand.",
        "source": MONUMENTEN,
        "photos": [
            ("Helenaveen_-_Rector_Nuijtsstraat_13a_-_Voormalig_turfstrooiselfabriek_met_aangebouwde_dienstwoningen.JPG", "De voormalige fabriek met de dienstwoningen, 2013, John Scholte, CC BY-SA 3.0 NL"),
        ],
        "more": HVT + "turfstrooiselfabriek",
    },
    {
        "year": "ca. 1885",
        "title": "Protestantse begraafplaats",
        "latlon": (51.38613, 5.91274),
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
        "photos": [
            ("Wilhelminahoeve,_voorgevel_-_Helenaveen_-_20107511_-_RCE.jpg", f"De Wilhelminahoeve in 1979, {RCE}"),
            ("Julianahoeve,_voor-_en_linker_zijgevel_-_Helenaveen_-_20107512_-_RCE.jpg", f"De Julianahoeve in 1979, {RCE}"),
            ("Nassauhoeve,_voor-_en_rechter_zijgevel_-_Helenaveen_-_20107508_-_RCE.jpg", f"De Nassauhoeve in 1979, {RCE}"),
            ("Oranjehoeve_-_Helenaveen_-_20107510_-_RCE.jpg", f"De Oranjehoeve in 1979, {RCE}"),
            ("Hendrikhoeve_-_Helenaveen_-_20107502_-_RCE.jpg", f"De Hendrikhoeve in 1979, {RCE}"),
        ],
        "source": ("Het Helenaveen van toen: de koningshoeven", HVT + "wilhelminahoeve"),
        "more": HVT + "wilhelminahoeve",
    },
    {
        "year": "na 1908",
        "title": "Emmahoeve",
        "at": (190481, 381355),
        "h": 8,
        "text": "Nog een van de koningshoeven, aan de Kaasweg, vernoemd naar koningin Emma. Net als de andere hoeven is het een kop-rompboerderij: een woonhuis met daarachter een grote schuur.",
        "photos": [
            ("Emmahoeve_-_Helenaveen_-_20107501_-_RCE.jpg", f"De Emmahoeve in 1979, {RCE}"),
            ("Helenaveen_-_Kaasweg_bij_2_Boerderij_Emma_Hoeve_met_varkensstal.JPG", "De Emmahoeve met varkensstal, 2013, John Scholte, CC BY-SA 3.0 NL"),
        ],
        "source": ("Het Helenaveen van toen: de koningshoeven", HVT + "wilhelminahoeve"),
        "more": HVT + "wilhelminahoeve",
    },
    {
        "year": "1910",
        "title": "De Gouden Helm",
        "latlon": (51.39051, 5.90431),
        "h": 2,
        "text": "In het veen bij Helenaveen werd in 1910 een vergulde helm van een Romeinse officier gevonden, de Gouden Helm van Deurne. Het gemeenschapshuis in het dorp is ernaar vernoemd; op de vindplaats staat een gedenkteken.",
        "photos": [
            ("Roman_cavalry_helmet_of_Deurne.jpg", "De helm in het Rijksmuseum van Oudheden, Michiel (Wiki Loves Art), CC BY-SA 2.0"),
        ],
        "source": ("Het Helenaveen van toen", HVT + "een-romein-komt-om-in-de-peel"),
        "more": HVT + "een-romein-komt-om-in-de-peel",
    },
    {
        "year": "1913",
        "title": "Willem III-hoeve",
        "at": (190290, 381292),
        "h": 8,
        "text": "De noordelijkste koningshoeve, met het jaartal en de naam in de trapgevel. Een rijksmonument, en tegenwoordig een ijsboerderij met terras.",
        "photos": [
            ("Willem_III_hoeve,_voor-_en_rechter_zijgevel_-_Helenaveen_-_20107513_-_RCE.jpg", f"De Willem III-hoeve in 1979, {RCE}"),
            ("Overzicht_met_voorgevel_boerderij_met_sloot_op_de_voorgrond_-_Helenaveen_-_20348354_-_RCE.jpg", f"De Willem III-hoeve in 1997, {RCE}"),
        ],
        "source": MONUMENTEN,
        "more": HVT + "wilhelminahoeve",
    },
    {
        "year": "1915",
        "title": "Het veen is op",
        "at": (192750, 378900),
        "text": "In 1915 stopt de grote turfwinning en wordt er vooral ontgonnen tot land- en tuinbouwgrond. Wat je hier ziet is wat er van het hoogveen over is: heide, vennen en bos, nu natuur in de Deurnsche Peel.",
        "photos": [("Mariapeel_Helenaveen_-_panoramio.jpg", "Hoogveen in de Mariapeel bij Helenaveen, Aat van den Heuvel, CC BY 3.0")],
        "source": MONUMENTEN,
        "more": HVT + "turfgraven",
    },
    {
        "year": "ca. 1930",
        "title": "Dorpsschool De Peelparel",
        "at": (191907.0, 377855.0),
        "h": 9,
        "text": "Een gaaf bewaarde dorpsschool met zes lokalen, met een klokkentorentje op het dak. Nog altijd de basisschool van Helenaveen.",
        "photos": [("Bassisschool_de_Peelparel_Helenaveen_8-025.jpg", "De Peelparel in 2001, publiek domein")],
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
        "at": (191577, 379760),
        "h": 4,
        "text": "Tegen de bosrand aan de Koolweg bouwden de Duitsers een huisje voor de bemanning van een zoeklicht. Het hoorde bij de Kammhuberlinie, de luchtverdediging tegen Britse bommenwerpers op weg naar het Ruhrgebied. Het staat achter Koolweg 42 tegen de bosrand, op nummer 40 denk ik.",
        "source": ("Het Helenaveen van toen", HVT + "wehrmachtshuisje"),
        "more": HVT + "wehrmachtshuisje",
    },
    {
        "year": "1944",
        "title": "De oude kerk verwoest",
        "at": (192080, 377790),
        "h": 14,
        "text": "In de oorlog ging de rooms-katholieke kerk uit 1857 verloren, een vroeg werk van de beroemde architect P.J.H. Cuypers. Op 8 oktober 1944 hielden de Duitsers bij de kerk een razzia en voerden mannen uit het dorp weg. Het oorlogsmonument aan de Oude Peelstraat kwam er op initiatief van wie terugkeerde.",
        "photos": [
            ("Helenaveen_Monument_Oude_Peelstraat.jpg", "Het oorlogsmonument aan de Oude Peelstraat, WoodenSpoon, CC BY-SA 4.0"),
            ("Gedenkteken_uit_2004_van_de_razzia_in_Helenaveen_in_1944_Soemeersingel_foto_aug_2014.jpg", "Gedenkteken uit 2004 voor de razzia van 1944, Peter Bankers, CC BY-SA 4.0"),
        ],
        "source": MONUMENTEN,
        "more": HVT + "gedeporteerden-kerkrazzia",
    },
    {
        "year": "1950",
        "title": "Sint-Willibrorduskerk",
        "at": (192080, 377790),
        "h": 25,
        "text": "Op dezelfde plek bouwde J. Deltrap een nieuwe kerk: een eenvoudige zaalkerk in traditionele vormen, met een klokkentoren die met 26 meter boven het dorp uitsteekt. Eind 2023 werd de kerk met een afscheidsviering gesloten; nu zijn er veertien woningen in, en een Mariakapel die open blijft voor gebed.",
        "photos": [
            ("Sint-Willibroduskerk_(Helenaveen).jpg", "De Sint-Willibrorduskerk in 2022, ACABJULIA, CC BY-SA 4.0"),
            ("Helenaveen_St.Willibrordus_Frans_Tuinstra.jpg", "Reliëf van Sint-Willibrord door Frans Tuinstra, WoodenSpoon, CC BY-SA 4.0"),
        ],
        "source": MONUMENTEN,
        "more": HVT + "rectoraat",
    },
    {
        "year": "2006",
        "title": "Verleden Veen",
        "at": (192068, 377892),
        "h": 2,
        "text": "Op de hoek van de Soemeersingel en de Sevenumseweg staat Verleden Veen van Jan Ros, gemaakt voor 150 jaar Helenaveen, dat in 2003 werd gevierd.",
        "photos": [("Helenaveen_Verleden_Veen_Jan_Ros.jpg", "Verleden Veen van Jan Ros, WoodenSpoon, CC BY-SA 4.0")],
        "source": ("Kunstwacht Deurne", "https://deurne.kunstwacht.nl/kunstwerken/pdf/3589-verleden-veen"),
    },
    {
        "year": "2014",
        "title": "Peeltroef",
        "at": (190176, 381262),
        "h": 3,
        "text": "Aan de Soemeersingel, bij de Willem III-hoeve, staat Peeltroef van Dirk Verberne: twee peelbanken en een zuil die laat zien hoe hoog het veen hier stond voordat het werd afgegraven.",
        "photos": [("Helenaveen_Peeltroef_(2014)_Dirk_Verberne.jpg", "Peeltroef van Dirk Verberne, WoodenSpoon, CC BY-SA 4.0")],
        "source": ("Wikimedia Commons", "https://commons.wikimedia.org/wiki/File:Helenaveen_Peeltroef_(2014)_Dirk_Verberne.jpg"),
    },
    {
        "year": "nu",
        "title": "Het katholieke kerkhof",
        "latlon": (51.38511, 5.91346),
        "h": 2,
        "text": "Op het katholieke kerkhof aan de Aardbeiweg zetten vrijwilligers van Memori zich in om de oude graven te bewaren, en daarmee de verhalen van de mensen die het dorp opbouwden. Er liggen ook Nederlandse oorlogsgraven.",
        "photos": [
            ("Rk_begraafplaats_Helenaveen.jpg", "De katholieke begraafplaats in 2005 (publiek domein)"),
            ("Coll_AV-004_Kerkhof_RK.JPG", "Oude graven op de katholieke begraafplaats (publiek domein)"),
        ],
        "source": ("Het Helenaveen van toen", HVT + "memori"),
        "more": HVT + "memori",
    },
    {
        "year": "rijksmonument",
        "title": "Keuterboerderij aan de Soemeersingel",
        "latlon": (51.40246, 5.91362),
        "h": 5,
        "text": "Een kleine boerderij met een schuurtje en karschop, Soemeersingel 75. Zo woonden de keuterboeren die naast hun werk in het veen een paar hectare grond bewerkten, een wereld van verschil met de grote koningshoeven verderop.",
        "photos": [("Soemeersingel_75.jpg", "Soemeersingel 75 in 2007 (publiek domein)")],
        "source": ("Rijksmonumentenregister via Wikidata", "https://www.wikidata.org/wiki/Special:Search?search=Keuterboerderij+Soemeersingel+75"),
    },
    {
        "year": "1939",
        "title": "Peelkanaal",
        "latlon": (51.41008, 5.93252),
        "text": "Het Peelkanaal bij Evertsoord is een rijksmonument van de Peel-Raamstelling, de verdedigingslinie van 1939 en 1940. Het kanaal diende als gracht tegen tanks; langs de linie stonden kazematten zoals die in de pastorietuin.",
        "source": ("Rijksmonumentenregister via Wikidata", "https://www.wikidata.org/wiki/Special:Search?search=Peelkanaal+bij+Evertsoord"),
        "more": HVT + "verslag-kapitein",
    },
    {
        "year": "1956",
        "title": "De jager die het zwijn doodde",
        "latlon": (51.3887, 5.91966),
        "h": 2,
        "text": "Een beeld van Niel Steenbergen uit 1956, nu een gemeentelijk monument: een jager met het wilde zwijn dat hij heeft gedood.",
        "photos": [("Helenaveen_Jager_die_het_zwijn_doodde_Niel_Steenbergen.jpg", "De jager die het zwijn doodde, WoodenSpoon, CC BY-SA 4.0")],
        "source": ("Wikimedia Commons", "https://commons.wikimedia.org/wiki/File:Helenaveen_Jager_die_het_zwijn_doodde_Niel_Steenbergen.jpg"),
    },
    {
        "year": "beeld",
        "title": "Koningin Juliana",
        "latlon": (51.38939, 5.91762),
        "h": 2,
        "text": "Een borstbeeld van koningin Juliana door Jesualda Kwanten, aan de Dominee Swaluestraat. Het koningshuis is van oudsher verbonden met Helenaveen, via het Fonds Koning Willem III en de koningshoeven.",
        "photos": [("Helenaveen_Koningin_Juliana_Jesualda_Kwanten.jpg", "Borstbeeld van koningin Juliana, WoodenSpoon, CC BY-SA 4.0")],
        "source": ("Wikimedia Commons", "https://commons.wikimedia.org/wiki/File:Helenaveen_Koningin_Juliana_Jesualda_Kwanten.jpg"),
    },
    {
        "year": "dorpshuis",
        "title": "Gemeenschapshuis De Gouden Helm",
        "latlon": (51.38802, 5.91843),
        "h": 6,
        "text": "Het dorpshuis draagt de naam van de vergulde Romeinse helm die in 1910 in het veen bij Helenaveen werd gevonden.",
        "source": ("Het Helenaveen van toen", HVT + "een-romein-komt-om-in-de-peel"),
        "more": HVT + "een-romein-komt-om-in-de-peel",
    },
    {
        "year": "20e eeuw",
        "title": "De kassen",
        "at": (192280, 377570),
        "h": 5,
        "zoom": 0.6,
        "text": "Na het veen kwam de tuinbouw. Groente ging eerst per stoomtram naar Venlo; tegenwoordig bepalen grote kassen het beeld ten oosten van het dorp.",
        "source": ("Het Helenaveen van toen", HVT + "kassen-in-helenaveen"),
        "more": HVT + "kassen-in-helenaveen",
    },
    {
        "year": "nu",
        "title": "Helenaveen nu",
        "at": (191850, 377850),
        "zoom": 0.3,
        "text": "Vanwege de bijzondere geschiedenis als veenkolonie is Helenaveen sinds 1999 een beschermd dorpsgezicht. Einde van de rondleiding. Veel meer verhalen, foto's en kaarten staan op Het Helenaveen van toen.",
        "photos": [("Soemeersingel_Helenaveen_zonsondergang_november_2014.jpg", "Zonsondergang aan de Soemeersingel, 2014, Peter Bankers, CC BY-SA 4.0")],
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


def route_order(stops):
    """Visit the stops as a route over the map instead of by date: the first and last stay put, the rest is a
    nearest-neighbour path tidied with 2-opt, so dots that lie together come one after another. Stops on the same
    spot (the old and the new church) keep their chronological order."""
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
