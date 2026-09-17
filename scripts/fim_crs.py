#!/usr/bin/env python3
"""
Minimal projected-CRS support shared by fim_fetch_streets.py and fim_georef.py: any UTM zone on WGS84 / NAD83 /
ETRS89 (EPSG 326xx, 327xx, 269xx, 258xx) with numpy only; anything else through pyproj if it is installed.
Formulas: Snyder, Map Projections — A Working Manual (1987), 8-9..8-25. Error vs pyproj < 1 mm inside a zone.
"""
from __future__ import annotations

import math
import re

import numpy as np

_ELLIPSOIDS = {"WGS 84": (6378137.0, 1 / 298.257223563), "GRS 1980": (6378137.0, 1 / 298.257222101)}


def utm_params(epsg: int) -> dict | None:
    """zone, hemisphere, ellipsoid, datum name for the UTM EPSG ranges we handle without pyproj; None otherwise."""
    if 32601 <= epsg <= 32660:
        return {"zone": epsg - 32600, "north": True, "ellipsoid": "WGS 84", "datum": "WGS 84"}
    if 32701 <= epsg <= 32760:
        return {"zone": epsg - 32700, "north": False, "ellipsoid": "WGS 84", "datum": "WGS 84"}
    if 26901 <= epsg <= 26923:
        return {"zone": epsg - 26900, "north": True, "ellipsoid": "GRS 1980", "datum": "NAD83"}
    if 25828 <= epsg <= 25838:
        return {"zone": epsg - 25800, "north": True, "ellipsoid": "GRS 1980", "datum": "ETRS89"}
    return None


def utm_epsg_for(lon: float, lat: float, datum: str = "WGS 84") -> int:
    zone = int((lon + 180) // 6) + 1
    if datum == "NAD83":
        return 26900 + zone
    return (32600 if lat >= 0 else 32700) + zone


def pad_bbox_km(bbox_swne, km: float) -> tuple[float, float, float, float]:
    """Grow a WGS84 S,W,N,E box by km on every side (equirectangular; fine for the few km used here)."""
    s, w, n, e = (float(v) for v in bbox_swne)
    if km <= 0:
        return s, w, n, e
    dlat = km / 111.32
    dlon = km / (111.32 * max(math.cos(math.radians((s + n) / 2)), 1e-6))
    return max(s - dlat, -90.0), w - dlon, min(n + dlat, 90.0), e + dlon


def bbox_union(boxes) -> tuple[float, float, float, float]:
    """Smallest S,W,N,E box containing every given S,W,N,E box."""
    arr = np.array([[float(v) for v in b] for b in boxes], float)
    if arr.ndim != 2 or arr.shape[1] != 4 or len(arr) == 0:
        raise ValueError("bbox_union needs one or more S,W,N,E boxes")
    return float(arr[:, 0].min()), float(arr[:, 1].min()), float(arr[:, 2].max()), float(arr[:, 3].max())


def parse_epsg(crs_member) -> int | None:
    """GeoJSON 'crs' member ({'type':'name','properties':{'name':'EPSG:26910' | 'urn:ogc:def:crs:EPSG::26910'}}) -> 26910."""
    if not crs_member:
        return None
    name = str(crs_member.get("properties", {}).get("name", "")) if isinstance(crs_member, dict) else str(crs_member)
    if re.search(r"CRS84|4326$", name):
        return 4326
    m = re.search(r"EPSG:{1,2}(\d+)", name)
    return int(m.group(1)) if m else None


class CRS:
    """to_wgs84(x, y) -> (lon, lat) and from_wgs84(lon, lat) -> (x, y), arrays in, arrays out."""

    def __init__(self, epsg: int):
        self.epsg = epsg
        self.utm = utm_params(epsg)
        self._pj = None
        if self.utm is None and epsg != 4326:
            try:
                from pyproj import Transformer  # optional

                self._pj = (Transformer.from_crs(epsg, 4326, always_xy=True), Transformer.from_crs(4326, epsg, always_xy=True))
            except Exception as e:  # noqa: BLE001
                raise SystemExit(f"EPSG:{epsg} is not a UTM zone this script handles natively and pyproj is not available ({e}). Re-fetch the streets in a UTM zone (fim_fetch_streets.py does this by default) or pip install pyproj.")

    # -- public
    def to_wgs84(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        if self.epsg == 4326:
            return x, y
        if self._pj:
            return self._pj[0].transform(x, y)
        return self._tm_inverse(x, y)

    def from_wgs84(self, lon, lat):
        lon, lat = np.asarray(lon, float), np.asarray(lat, float)
        if self.epsg == 4326:
            return lon, lat
        if self._pj:
            return self._pj[1].transform(lon, lat)
        return self._tm_forward(lon, lat)

    def name(self) -> str:
        if self.utm:
            return f"{self.utm['datum']} / UTM zone {self.utm['zone']}{'N' if self.utm['north'] else 'S'}"
        return f"EPSG:{self.epsg}"

    def wkt(self) -> str:
        """WKT1 for a QGIS .points header (pyproj's if available, else a UTM template)."""
        if self._pj:
            from pyproj import CRS as _C

            return _C.from_epsg(self.epsg).to_wkt(version="WKT1_GDAL").replace("\n", "")
        u = self.utm
        a, f = _ELLIPSOIDS[u["ellipsoid"]]
        geog = {"WGS 84": 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4326"]]',
                "NAD83": 'GEOGCS["NAD83",DATUM["North_American_Datum_1983",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],AUTHORITY["EPSG","6269"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4269"]]',
                "ETRS89": 'GEOGCS["ETRS89",DATUM["European_Terrestrial_Reference_System_1989",SPHEROID["GRS 1980",6378137,298.257222101,AUTHORITY["EPSG","7019"]],AUTHORITY["EPSG","6258"]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433],AUTHORITY["EPSG","4258"]]'}[u["datum"]]
        return (f'PROJCS["{self.name()}",{geog},PROJECTION["Transverse_Mercator"],PARAMETER["latitude_of_origin",0],PARAMETER["central_meridian",{self._lon0_deg()}],'
                f'PARAMETER["scale_factor",0.9996],PARAMETER["false_easting",500000],PARAMETER["false_northing",{0 if u["north"] else 10000000}],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AUTHORITY["EPSG","{self.epsg}"]]')

    # -- Transverse Mercator on the ellipsoid
    def _lon0_deg(self) -> float:
        return -183.0 + 6 * self.utm["zone"]

    def _consts(self):
        a, f = _ELLIPSOIDS[self.utm["ellipsoid"]]
        e2 = f * (2 - f)
        return a, e2, e2 / (1 - e2), 0.9996, math.radians(self._lon0_deg()), 0.0 if self.utm["north"] else 10000000.0

    def _tm_forward(self, lon, lat):
        a, e2, ep2, k0, lon0, fn = self._consts()
        phi, lam = np.radians(lat), np.radians(lon)
        s, c, t = np.sin(phi), np.cos(phi), np.tan(phi)
        N = a / np.sqrt(1 - e2 * s**2)
        T = t**2
        C = ep2 * c**2
        A = (lam - lon0) * c
        M = a * ((1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256) * phi - (3 * e2 / 8 + 3 * e2**2 / 32 + 45 * e2**3 / 1024) * np.sin(2 * phi) + (15 * e2**2 / 256 + 45 * e2**3 / 1024) * np.sin(4 * phi) - (35 * e2**3 / 3072) * np.sin(6 * phi))
        x = k0 * N * (A + (1 - T + C) * A**3 / 6 + (5 - 18 * T + T**2 + 72 * C - 58 * ep2) * A**5 / 120) + 500000.0
        y = k0 * (M + N * t * (A**2 / 2 + (5 - T + 9 * C + 4 * C**2) * A**4 / 24 + (61 - 58 * T + T**2 + 600 * C - 330 * ep2) * A**6 / 720)) + fn
        return x, y

    def _tm_inverse(self, x, y):
        a, e2, ep2, k0, lon0, fn = self._consts()
        x = x - 500000.0
        M = (y - fn) / k0
        mu = M / (a * (1 - e2 / 4 - 3 * e2**2 / 64 - 5 * e2**3 / 256))
        e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
        phi1 = mu + (3 * e1 / 2 - 27 * e1**3 / 32) * np.sin(2 * mu) + (21 * e1**2 / 16 - 55 * e1**4 / 32) * np.sin(4 * mu) + (151 * e1**3 / 96) * np.sin(6 * mu) + (1097 * e1**4 / 512) * np.sin(8 * mu)
        s, c, t = np.sin(phi1), np.cos(phi1), np.tan(phi1)
        N1 = a / np.sqrt(1 - e2 * s**2)
        T1 = t**2
        C1 = ep2 * c**2
        R1 = a * (1 - e2) / (1 - e2 * s**2) ** 1.5
        D = x / (N1 * k0)
        lat = phi1 - (N1 * t / R1) * (D**2 / 2 - (5 + 3 * T1 + 10 * C1 - 4 * C1**2 - 9 * ep2) * D**4 / 24 + (61 + 90 * T1 + 298 * C1 + 45 * T1**2 - 252 * ep2 - 3 * C1**2) * D**6 / 720)
        lon = lon0 + (D - (1 + 2 * T1 + C1) * D**3 / 6 + (5 - 2 * C1 + 28 * T1 - 3 * C1**2 + 8 * ep2 + 24 * T1**2) * D**5 / 120) / c
        return np.degrees(lon), np.degrees(lat)
