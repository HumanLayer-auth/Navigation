#!/usr/bin/env python3
"""Generate an interactive HTML preview for the split navigation map dataset."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path


DEFAULT_DATASET_DIR = Path("thehyundai_indoor_navigation_dataset")
DEFAULT_INPUT = DEFAULT_DATASET_DIR / "navigation_map.json"
DEFAULT_OUTPUT = DEFAULT_DATASET_DIR / "preview.html"


def read_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"navigation map JSON이 없습니다: {path.resolve()}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_navigation_map(path: Path) -> dict:
    data = read_json(path)
    if data.get("format") != "split_navigation_map":
        return data

    merged = {
        "schema_version": data.get("schema_version"),
        "generated_from": data.get("generated_from", {}),
    }
    files = data.get("files") or {}
    for key, value in files.items():
        part_path = Path(value)
        if not part_path.is_absolute():
            part_path = path.parent / part_path
        part_data = read_json(part_path)
        merged[key] = part_data.get(key)
    return merged


def html_document(data: dict) -> str:
    json_blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    background_data_url = background_image_data_url(data)
    title = data.get("building", {}).get("name") or "Indoor Navigation Preview"
    floor = data.get("building", {}).get("floor", {}).get("name") or ""
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape_html(str(title))} {escape_html(str(floor))}</title>
  <style>
    :root {{
      color-scheme: light;
      --panel: #ffffff;
      --line: #d5d9dd;
      --text: #20252b;
      --muted: #68717b;
      --graph: #d34242;
      --corridor: #8fcfb0;
      --store: #d5d7da;
      --poi: #27a870;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      overflow: hidden;
      font: 13px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--text);
      background: #eef1f2;
    }}
    #toolbar {{
      position: fixed;
      left: 14px;
      top: 14px;
      z-index: 10;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      max-width: calc(100vw - 340px);
      padding: 10px 12px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.94);
      box-shadow: 0 8px 24px rgba(20,30,40,.12);
    }}
    #toolbar strong {{ margin-right: 8px; }}
    label {{
      display: inline-flex;
      gap: 5px;
      align-items: center;
      white-space: nowrap;
      color: var(--muted);
    }}
    button {{
      height: 28px;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--text);
      cursor: pointer;
    }}
    button:hover {{ background: #f4f6f7; }}
    #panel {{
      position: fixed;
      right: 14px;
      top: 14px;
      bottom: 14px;
      z-index: 10;
      width: 300px;
      padding: 14px;
      overflow: auto;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.95);
      box-shadow: 0 8px 24px rgba(20,30,40,.12);
    }}
    #panel h1 {{
      margin: 0 0 2px;
      font-size: 16px;
      line-height: 1.25;
    }}
    #panel .sub {{ color: var(--muted); margin-bottom: 12px; }}
    #panel dl {{ display: grid; grid-template-columns: 94px 1fr; gap: 6px 8px; margin: 12px 0; }}
    #panel dt {{ color: var(--muted); }}
    #panel dd {{ margin: 0; word-break: break-word; }}
    #canvas {{
      display: block;
      width: 100vw;
      height: 100vh;
      cursor: grab;
    }}
    #canvas.dragging {{ cursor: grabbing; }}
    #tooltip {{
      position: fixed;
      display: none;
      pointer-events: none;
      z-index: 20;
      max-width: 260px;
      padding: 7px 9px;
      border: 1px solid var(--line);
      background: #fff;
      box-shadow: 0 6px 18px rgba(20,30,40,.15);
      color: var(--text);
    }}
    .hint {{ color: var(--muted); font-size: 12px; }}
  </style>
</head>
<body>
  <div id="toolbar">
    <strong>Overlay</strong>
    <label><input type="checkbox" data-layer="outline" checked>건물 외곽</label>
    <label><input type="checkbox" data-layer="corridors" checked>복도</label>
    <label><input type="checkbox" data-layer="graph" checked>Graph</label>
    <label><input type="checkbox" data-layer="stores" checked>매장</label>
    <label><input type="checkbox" data-layer="ocr" checked>OCR</label>
    <label><input type="checkbox" data-layer="pois" checked>POI</label>
    <button id="fit">Fit</button>
    <button id="zoomIn">+</button>
    <button id="zoomOut">-</button>
  </div>
  <aside id="panel">
    <h1></h1>
    <div class="sub"></div>
    <div id="stats"></div>
    <div id="selection" class="hint">노드를 클릭하거나 매장 위에 마우스를 올리면 상세 정보가 표시됩니다.</div>
  </aside>
  <canvas id="canvas"></canvas>
  <div id="tooltip"></div>
  <script id="navigation-data" type="application/json">{json_blob}</script>
  <script>
  const nav = JSON.parse(document.getElementById('navigation-data').textContent);
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  const tooltip = document.getElementById('tooltip');
  const panel = document.getElementById('panel');
  const layers = Object.fromEntries(Array.from(document.querySelectorAll('[data-layer]')).map(input => [input.dataset.layer, input.checked]));
  const bounds = nav.coordinate_system?.floor_bounds_source || {{min_x: 0, min_y: 0, max_x: 3000, max_y: 3000, width: 3000, height: 3000}};
  const nodeById = new Map((nav.nodes || []).map(node => [node.id, node]));
  const state = {{ scale: 1, offsetX: 0, offsetY: 0, dragging: false, lastX: 0, lastY: 0, hoveredStore: null, selectedNode: null }};
  const backgroundImage = new Image();
  backgroundImage.src = {json.dumps(background_data_url)};
  backgroundImage.onload = () => draw();

  panel.querySelector('h1').textContent = nav.building?.name || 'Indoor Navigation Map';
  panel.querySelector('.sub').textContent = `${{nav.building?.floor?.name || ''}} · ${{nav.schema_version || ''}}`;
  document.getElementById('stats').innerHTML = `
    <dl>
      <dt>Nodes</dt><dd>${{(nav.nodes || []).length}}</dd>
      <dt>Edges</dt><dd>${{(nav.edges || []).length}}</dd>
      <dt>Stores</dt><dd>${{(nav.stores || []).length}}</dd>
      <dt>POI</dt><dd>${{(nav.pois || []).length}}</dd>
      <dt>Review</dt><dd>${{(nav.manual_review_candidates || []).length}}</dd>
    </dl>`;

  function resize() {{
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = `${{window.innerWidth}}px`;
    canvas.style.height = `${{window.innerHeight}}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }}

  function fit() {{
    const rightPanel = 330;
    const margin = 70;
    const availableW = Math.max(320, window.innerWidth - rightPanel - margin * 2);
    const availableH = Math.max(320, window.innerHeight - margin * 2);
    state.scale = Math.min(availableW / bounds.width, availableH / bounds.height);
    state.offsetX = margin;
    state.offsetY = margin;
    draw();
  }}

  function worldToScreen(point) {{
    return {{ x: state.offsetX + (point.x - bounds.min_x) * state.scale, y: state.offsetY + (point.y - bounds.min_y) * state.scale }};
  }}

  function screenToWorld(x, y) {{
    return {{ x: bounds.min_x + (x - state.offsetX) / state.scale, y: bounds.min_y + (y - state.offsetY) / state.scale }};
  }}

  function pathFromSource(points) {{
    const path = new Path2D();
    points.forEach((point, index) => {{
      const screen = worldToScreen(point);
      if (index === 0) path.moveTo(screen.x, screen.y);
      else path.lineTo(screen.x, screen.y);
    }});
    path.closePath();
    return path;
  }}

  function drawPolygon(points, fill, stroke, width = 1) {{
    if (!points || points.length < 2) return;
    const path = pathFromSource(points);
    if (fill) {{
      ctx.fillStyle = fill;
      ctx.fill(path);
    }}
    if (stroke) {{
      ctx.strokeStyle = stroke;
      ctx.lineWidth = width;
      ctx.stroke(path);
    }}
  }}

  function draw() {{
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    ctx.fillStyle = '#eef1f2';
    ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);

    ctx.save();
    drawBackground();
    const topLeft = worldToScreen({{x: bounds.min_x, y: bounds.min_y}});
    const bottomRight = worldToScreen({{x: bounds.max_x, y: bounds.max_y}});
    ctx.fillStyle = '#fff';
    ctx.strokeStyle = '#9ca4aa';
    ctx.lineWidth = 1.5;
    if (!backgroundImage.complete || !backgroundImage.naturalWidth) ctx.fillRect(topLeft.x, topLeft.y, bottomRight.x - topLeft.x, bottomRight.y - topLeft.y);
    ctx.strokeRect(topLeft.x, topLeft.y, bottomRight.x - topLeft.x, bottomRight.y - topLeft.y);

    if (layers.outline) drawOutline();
    if (layers.corridors) drawCorridors();
    if (layers.stores) drawStores();
    if (layers.graph) drawGraph();
    if (layers.pois) drawPois();
    if (layers.ocr) drawOcr();
    ctx.restore();
  }}

  function drawBackground() {{
    if (!backgroundImage.complete || !backgroundImage.naturalWidth) return;
    const preview = nav.preview || {{}};
    const affine = nav.image_analysis?.source_to_image_affine?.matrix;
    if (affine) {{
      const p0 = worldToScreen(imageToSource(0, 0, affine));
      const p1 = worldToScreen(imageToSource(backgroundImage.naturalWidth, 0, affine));
      const p2 = worldToScreen(imageToSource(0, backgroundImage.naturalHeight, affine));
      ctx.save();
      ctx.globalAlpha = 0.82;
      ctx.transform(
        (p1.x - p0.x) / backgroundImage.naturalWidth,
        (p1.y - p0.y) / backgroundImage.naturalWidth,
        (p2.x - p0.x) / backgroundImage.naturalHeight,
        (p2.y - p0.y) / backgroundImage.naturalHeight,
        p0.x,
        p0.y
      );
      ctx.drawImage(backgroundImage, 0, 0);
      ctx.restore();
      return;
    }}
    const bbox = preview.map_bbox_image;
    const imageSize = preview.image_size;
    if (!bbox || !imageSize) return;
    const bboxW = Math.max(1, bbox[2] - bbox[0]);
    const bboxH = Math.max(1, bbox[3] - bbox[1]);
    const worldMinX = bounds.min_x - (bbox[0] / bboxW) * bounds.width;
    const worldMinY = bounds.min_y - (bbox[1] / bboxH) * bounds.height;
    const worldMaxX = bounds.min_x + ((imageSize.width - bbox[0]) / bboxW) * bounds.width;
    const worldMaxY = bounds.min_y + ((imageSize.height - bbox[1]) / bboxH) * bounds.height;
    const a = worldToScreen({{x: worldMinX, y: worldMinY}});
    const b = worldToScreen({{x: worldMaxX, y: worldMaxY}});
    ctx.globalAlpha = 0.82;
    ctx.drawImage(backgroundImage, a.x, a.y, b.x - a.x, b.y - a.y);
    ctx.globalAlpha = 1;
  }}

  function imageToSource(x, y, affine) {{
    const a = affine[0][0], b = affine[0][1], c = affine[0][2];
    const d = affine[1][0], e = affine[1][1], f = affine[1][2];
    const det = a * e - b * d || 1;
    const px = x - c;
    const py = y - f;
    return {{
      x: (e * px - b * py) / det,
      y: (-d * px + a * py) / det
    }};
  }}

  function drawOutline() {{
    const sections = nav.floor_regions?.sections || [];
    sections.forEach(section => drawPolygon(section.polygon?.source || [], 'rgba(235,237,238,.45)', '#8f979d', 1));
  }}

  function drawCorridors() {{
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = 'rgba(94, 184, 135, .28)';
    ctx.lineWidth = Math.max(8, 24 * state.scale);
    (nav.edges || []).forEach(edge => {{
      const a = nodeById.get(edge.from);
      const b = nodeById.get(edge.to);
      if (!a || !b) return;
      const pa = worldToScreen(a.position.source);
      const pb = worldToScreen(b.position.source);
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }});
  }}

  function drawGraph() {{
    ctx.lineCap = 'round';
    ctx.strokeStyle = 'rgba(211,66,66,.82)';
    ctx.lineWidth = 1.5;
    (nav.edges || []).forEach(edge => {{
      const a = nodeById.get(edge.from);
      const b = nodeById.get(edge.to);
      if (!a || !b) return;
      const pa = worldToScreen(a.position.source);
      const pb = worldToScreen(b.position.source);
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }});
    (nav.nodes || []).forEach(node => {{
      const p = worldToScreen(node.position.source);
      ctx.beginPath();
      ctx.fillStyle = colorForNode(node.type);
      ctx.arc(p.x, p.y, node.id === state.selectedNode ? 5 : 3.2, 0, Math.PI * 2);
      ctx.fill();
    }});
  }}

  function drawStores() {{
    (nav.stores || []).forEach(store => {{
      const hovered = state.hoveredStore && state.hoveredStore.id === store.id;
      const fill = hovered ? 'rgba(246,174,45,.70)' : 'rgba(170,174,180,.62)';
      const stroke = hovered ? '#b56f00' : '#ffffff';
      if (store.polygon?.source) drawPolygon(store.polygon.source, fill, stroke, hovered ? 2 : 1);
      const c = worldToScreen(store.centroid.source);
      ctx.fillStyle = '#33383d';
      ctx.font = `${{Math.max(9, 12 * state.scale)}}px sans-serif`;
      if (state.scale > 0.18 || hovered) ctx.fillText(store.name, c.x + 4, c.y - 4);
    }});
  }}

  function drawPois() {{
    (nav.pois || []).forEach(poi => {{
      const p = worldToScreen(poi.centroid.source);
      ctx.beginPath();
      ctx.fillStyle = colorForPoi(poi.type);
      ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = '#1f2a30';
      ctx.font = '11px sans-serif';
      if (state.scale > 0.22) ctx.fillText(poi.name || poi.type, p.x + 6, p.y + 3);
    }});
  }}

  function drawOcr() {{
    (nav.ocr_results || []).forEach(result => {{
      const bbox = result.bbox_source;
      if (!bbox) return;
      const a = worldToScreen({{x: bbox[0], y: bbox[1]}});
      const b = worldToScreen({{x: bbox[2], y: bbox[3]}});
      ctx.strokeStyle = result.confidence >= .65 ? '#238f45' : '#d78928';
      ctx.lineWidth = 1.2;
      ctx.strokeRect(a.x, a.y, b.x - a.x, b.y - a.y);
      if (state.scale > 0.2) {{
        ctx.fillStyle = ctx.strokeStyle;
        ctx.fillText(result.text, a.x, a.y - 3);
      }}
    }});
  }}

  function colorForNode(type) {{
    if (type === 'elevator') return '#178c60';
    if (type === 'escalator') return '#2a75bb';
    if (type === 'store_entrance') return '#f0a51a';
    if (type === 'dead_end') return '#777';
    if (type === 'junction') return '#d34242';
    return '#343a40';
  }}

  function colorForPoi(type) {{
    if (type === 'elevator') return '#178c60';
    if (type === 'escalator') return '#2a75bb';
    if (type === 'exit') return '#7a55c7';
    if (type === 'toilet') return '#159aa2';
    return '#27a870';
  }}

  function hitTestStore(world) {{
    for (const store of nav.stores || []) {{
      const points = store.polygon?.source;
      if (!points || points.length < 3) continue;
      const path = new Path2D();
      points.forEach((point, index) => {{
        if (index === 0) path.moveTo(point.x, point.y);
        else path.lineTo(point.x, point.y);
      }});
      path.closePath();
      if (ctx.isPointInPath(path, world.x, world.y)) return store;
    }}
    return null;
  }}

  function hitTestNode(screenX, screenY) {{
    let best = null;
    let bestDist = 10;
    for (const node of nav.nodes || []) {{
      const p = worldToScreen(node.position.source);
      const dist = Math.hypot(p.x - screenX, p.y - screenY);
      if (dist < bestDist) {{
        bestDist = dist;
        best = node;
      }}
    }}
    return best;
  }}

  function showSelection(item, kind) {{
    const target = document.getElementById('selection');
    if (!item) {{
      target.className = 'hint';
      target.textContent = '노드를 클릭하거나 매장 위에 마우스를 올리면 상세 정보가 표시됩니다.';
      return;
    }}
    target.className = '';
    const confidence = typeof item.confidence === 'number' ? item.confidence.toFixed(2) : '';
    const pos = item.position?.local_m || item.centroid?.local_m;
    target.innerHTML = `<dl>
      <dt>Type</dt><dd>${{kind}}</dd>
      <dt>ID</dt><dd>${{item.id || ''}}</dd>
      <dt>Name</dt><dd>${{item.name || item.type || ''}}</dd>
      <dt>Confidence</dt><dd>${{confidence}}</dd>
      <dt>Local m</dt><dd>${{pos ? `${{pos.x.toFixed(2)}}, ${{pos.y.toFixed(2)}}` : ''}}</dd>
    </dl>`;
  }}

  canvas.addEventListener('mousedown', event => {{
    state.dragging = true;
    state.lastX = event.clientX;
    state.lastY = event.clientY;
    canvas.classList.add('dragging');
  }});
  window.addEventListener('mouseup', () => {{
    state.dragging = false;
    canvas.classList.remove('dragging');
  }});
  canvas.addEventListener('mousemove', event => {{
    if (state.dragging) {{
      state.offsetX += event.clientX - state.lastX;
      state.offsetY += event.clientY - state.lastY;
      state.lastX = event.clientX;
      state.lastY = event.clientY;
      draw();
      return;
    }}
    const world = screenToWorld(event.clientX, event.clientY);
    const store = hitTestStore(world);
    state.hoveredStore = store;
    if (store) {{
      tooltip.style.display = 'block';
      tooltip.style.left = `${{event.clientX + 12}}px`;
      tooltip.style.top = `${{event.clientY + 12}}px`;
      tooltip.textContent = `${{store.name}} · confidence ${{store.confidence.toFixed(2)}}`;
      showSelection(store, 'store');
    }} else {{
      tooltip.style.display = 'none';
      if (!state.selectedNode) showSelection(null);
    }}
    draw();
  }});
  canvas.addEventListener('click', event => {{
    const node = hitTestNode(event.clientX, event.clientY);
    state.selectedNode = node ? node.id : null;
    showSelection(node, 'node');
    draw();
  }});
  canvas.addEventListener('wheel', event => {{
    event.preventDefault();
    const before = screenToWorld(event.clientX, event.clientY);
    const factor = event.deltaY < 0 ? 1.12 : 0.89;
    state.scale = Math.max(0.05, Math.min(4, state.scale * factor));
    const after = worldToScreen(before);
    state.offsetX += event.clientX - after.x;
    state.offsetY += event.clientY - after.y;
    draw();
  }}, {{ passive: false }});

  document.querySelectorAll('[data-layer]').forEach(input => {{
    input.addEventListener('change', () => {{
      layers[input.dataset.layer] = input.checked;
      draw();
    }});
  }});
  document.getElementById('fit').addEventListener('click', fit);
  document.getElementById('zoomIn').addEventListener('click', () => {{ state.scale *= 1.2; draw(); }});
  document.getElementById('zoomOut').addEventListener('click', () => {{ state.scale /= 1.2; draw(); }});
  window.addEventListener('resize', resize);
  resize();
  fit();
  </script>
</body>
</html>
"""


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def background_image_data_url(data: dict) -> str:
    path_value = data.get("preview", {}).get("background_image") or data.get("generated_from", {}).get("floor_image")
    if not path_value:
        return ""
    path = Path(path_value)
    if not path.exists():
        return ""
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    suffix = path.suffix.lower()
    mime = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{encoded}"


def generate_preview(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> Path:
    data = load_navigation_map(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_document(data), encoding="utf-8")
    print(f"Preview 저장: {output_path.resolve()}")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="navigation_map.json을 브라우저 확인용 preview.html로 변환합니다.")
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="입력 navigation_map.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="출력 preview.html")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        generate_preview(Path(args.input), Path(args.output))
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI should print root cause
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
