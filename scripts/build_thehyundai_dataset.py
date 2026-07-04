#!/usr/bin/env python3
"""Build the The Hyundai Seoul demo map dataset end to end."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from extract_ehyundai_floor_assets import DEFAULT_URL, extract_ehyundai_floor_assets, has_resource_keyword
from extract_thehyundai_building import extract_thehyundai_building


DEFAULT_OUTPUT_DIR = Path("thehyundai_indoor_navigation_dataset")
DATASET_SUMMARY_NAME = "thehyundai_dataset_summary.json"


def candidate_floor_assets(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for resource in manifest.get("resources", []):
        saved_path = resource.get("saved_path")
        if not saved_path:
            continue

        url = str(resource.get("url", ""))
        content_type = str(resource.get("content_type", ""))
        category = str(resource.get("category", ""))
        parsed = urlsplit(url)
        keyword_text = unquote(parsed.path).lower()

        saved_lower = Path(str(saved_path)).name.lower()
        has_floor_keyword = has_resource_keyword(keyword_text) or has_resource_keyword(saved_lower)

        if has_floor_keyword:
            candidates.append(
                {
                    "url": url,
                    "content_type": content_type,
                    "category": category,
                    "size_bytes": resource.get("size_bytes", 0),
                    "saved_path": saved_path,
                }
            )
    return candidates


def build_thehyundai_dataset(
    shp_path: str | None = None,
    url: str = DEFAULT_URL,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    headed: bool = False,
) -> dict[str, Any]:
    output_base = Path(output_dir)
    output_base.mkdir(parents=True, exist_ok=True)

    print("1/2 VWorld SHP에서 더현대서울 건물 외곽을 추출합니다.")
    building_summary = extract_thehyundai_building(shp_path=shp_path, output_dir=output_base)

    print("2/2 현대백화점 층별 안내도 리소스를 추출합니다.")
    floor_manifest = extract_ehyundai_floor_assets(
        url=url,
        output_dir=output_base / "floor_assets",
        headless=not headed,
    )

    summary_path = output_base / DATASET_SUMMARY_NAME
    screenshots = list(floor_manifest.get("screenshots", {}).values())
    notes = []
    notes.extend(building_summary.get("notes", []))
    notes.extend(floor_manifest.get("notes", []))
    notes.append(f"네트워크 response {floor_manifest.get('network_response_count', 0)}개를 기록했습니다.")

    summary = {
        "building_geojson": building_summary.get("building_geojson"),
        "building_summary": building_summary.get("building_summary"),
        "floor_asset_manifest": str((output_base / "floor_assets" / "manifest.json").resolve()),
        "screenshots": screenshots,
        "candidate_floor_assets": candidate_floor_assets(floor_manifest),
        "notes": notes,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Dataset summary 저장: {summary_path.resolve()}")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="더현대서울 실내 내비게이션 데모용 지도 데이터셋을 구축합니다.")
    parser.add_argument("--shp", help="VWorld SHP 경로. 생략하면 기본 파일명을 자동 검색합니다.")
    parser.add_argument("--url", default=DEFAULT_URL, help="현대백화점 모바일 층별 안내도 URL")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="결과 저장 디렉토리")
    parser.add_argument("--headed", action="store_true", help="리소스 추출 브라우저를 화면에 표시합니다.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        build_thehyundai_dataset(
            shp_path=args.shp,
            url=args.url,
            output_dir=args.output_dir,
            headed=args.headed,
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should print clear root cause
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
