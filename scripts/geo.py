"""RD New <-> WGS84 (the usual polynomial approximation, about a meter off) and map projections."""

import math

from config import CX, CY


def wgs_to_rd(lat, lon):
    dp, dl = 0.36 * (lat - 52.15517440), 0.36 * (lon - 5.38720621)
    x = (155000 + 190094.945 * dl - 11832.228 * dp * dl - 114.221 * dp**2 * dl - 32.391 * dl**3 - 0.705 * dp
         - 2.340 * dp**3 * dl - 0.608 * dp * dl**3 - 0.008 * dl**2 + 0.148 * dp**2 * dl**3)
    y = (463000 + 309056.544 * dp + 3638.893 * dl**2 + 73.077 * dp**2 - 157.984 * dp * dl**2 + 59.788 * dp**3
         + 0.433 * dl - 6.439 * dp**2 * dl**2 - 0.032 * dp * dl + 0.092 * dl**4 - 0.054 * dp * dl**4)
    return x, y


def rd_to_image(x, y, scale=4, width=16971, height_m=0.0):
    """Pixel position in the full isometric render of an RD point at a height above ground."""
    lx, lz = x - CX, CY - y
    u = (lx + lz) / math.sqrt(2)
    v = (lx - lz) / (2 * math.sqrt(2)) + height_m * math.cos(math.radians(30))
    top = 1500 * math.sqrt(2) * 0.5 + 32
    return u * scale + width / 2, (top - v) * scale
