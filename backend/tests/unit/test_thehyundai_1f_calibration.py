from pathlib import Path

import pytest

from scripts.transform.calibrate_thehyundai_1f import analyze, regenerate, _load


ROOT = Path(__file__).resolve().parents[3]
CALIBRATION = ROOT / "backend/resources/calibration/thehyundai-seoul/1f.json"


def test_dabeeo_to_svg_robust_fit_is_stable():
    calibration = _load(CALIBRATION)
    report = analyze(calibration)

    fit = report["source_to_svg_px"]
    assert fit["matched"] >= 58
    assert fit["inliers"] >= 55
    assert fit["rmse_inlier_px"] < 1.5
    assert fit["anisotropy_ratio"] < 1.002
    assert report["svg_footprint_bounds"]["ratio"] == pytest.approx(2016 / 1180)


def test_unverified_measurements_cannot_regenerate_production_data():
    calibration = _load(CALIBRATION)
    report = analyze(calibration)

    assert report["physical_scale"]["production_ready"] is False
    with pytest.raises(ValueError, match="production 재생성 거부"):
        regenerate(calibration, report)
