"""The DOV texture -> Rosetta chain, offline (dovwms faked with its real dict shape)."""

import sys
import types

import pytest

from simplesoilprofile import profile_from_dov
from simplesoilprofile.swap import soilhydrfunc_table


def fake_dov(x, y, fetch_elevation=False, crs="EPSG:31370"):
    layers = []
    for name, top, bottom, sand, silt, clay in [
        ("Layer_0-30cm", 0, 30, 72.0, 22.0, 6.0),
        ("Layer_30-60cm", 30, 60, 70.0, 23.0, 7.0),
        ("Layer_60-100cm", 60, 100, 75.0, 19.0, 6.0),
        ("Layer_100-150cm", 100, 150, 80.0, 15.0, 5.0),
    ]:
        layers.append({
            "name": name, "layer_top": top, "layer_bottom": bottom,
            "sand_content": sand, "silt_content": silt, "clay_content": clay,
            "metadata": {k: {"source": "DOV WMS", "uncertainty": 5.0} for k in ("sand_content", "silt_content", "clay_content")},
        })
    out = {"layers": layers}
    if fetch_elevation:
        out["elevation"] = {"elevation": 33.2}
    return out


def test_dov_profile_feeds_rosetta(monkeypatch):
    monkeypatch.setitem(sys.modules, "dovwms", types.SimpleNamespace(get_profile_from_dov=fake_dov))
    p = profile_from_dov(247172.56, 204590.58, fetch_elevation=True)
    assert p.elevation == 33.2 and p.x == 247172.56
    assert [h.bottom for h in p.horizons] == [0.3, 0.6, 1.0, 1.5]
    assert p.horizons[0].material.metadata["sand_content"].source == "DOV WMS"

    for i, h in p.present:
        p = p.with_material(i, h.material.with_rosetta(version=2).with_(bulk_density=1.5))
    assert all(1.1 < h.material.n < 2.5 for h in p.horizons)
    assert len(soilhydrfunc_table(p)) == 4


def test_dov_extra_missing(monkeypatch):
    monkeypatch.setitem(sys.modules, "dovwms", None)
    with pytest.raises(ImportError, match="simplesoilprofile\\[dov\\]"):
        profile_from_dov(0.0, 0.0)
