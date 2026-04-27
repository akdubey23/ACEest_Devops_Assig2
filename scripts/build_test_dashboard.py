#!/usr/bin/env python3
"""
Build test-results/dashboard.html from test-results/junit.xml.
Cucumber-style summary: pie chart (pass/fail/skip) + per-feature table.
No third-party deps (stdlib only).
"""

from __future__ import annotations

import html
import math
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
import re


def _feature_label(classname: str) -> str:
    """Turn tests.test_api_features.TestDiscoveryAndHealth into 'Discovery And Health'."""
    if not classname:
        return "tests"
    short = classname.split(".")[-1]
    if short.startswith("Test"):
        short = short[4:]
    # CamelCase -> words
    spaced = re.sub(r"([a-z])([A-Z])", r"\1 \2", short)
    return spaced.strip() or short


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    junit_path = os.path.join(root, "test-results", "junit.xml")
    out_dir = os.path.join(root, "test-results")
    out_path = os.path.join(out_dir, "dashboard.html")

    if not os.path.isfile(junit_path):
        print(f"skip: no {junit_path}", file=sys.stderr)
        return 0

    tree = ET.parse(junit_path)
    root_el = tree.getroot()

    # pytest may emit <testsuites> or single <testsuite>
    suites: list[ET.Element] = []
    if root_el.tag == "testsuites":
        suites = list(root_el.findall("testsuite"))
    elif root_el.tag == "testsuite":
        suites = [root_el]

    features: dict[str, dict[str, int]] = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0})
    total_p = total_f = total_s = 0

    for suite in suites:
        feature = suite.get("name") or "tests"
        if feature == "pytest":
            feature = "All tests"
        for case in suite.findall("testcase"):
            cname = case.get("classname") or ""
            key = _feature_label(cname) if cname else feature
            failed = case.find("failure") is not None or case.find("error") is not None
            skipped = case.find("skipped") is not None
            if failed:
                features[key]["failed"] += 1
                total_f += 1
            elif skipped:
                features[key]["skipped"] += 1
                total_s += 1
            else:
                features[key]["passed"] += 1
                total_p += 1

    n = total_p + total_f + total_s
    if n == 0:
        print("skip: no test cases in junit", file=sys.stderr)
        return 0

    # SVG donut (pass=green, fail=red, skip=gray)
    def arc(cx, cy, r, w, start_deg, end_deg):
        r_in = r - w
        a0, a1 = math.radians(start_deg), math.radians(end_deg)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        xi0, yi0 = cx + r_in * math.cos(a0), cy + r_in * math.sin(a0)
        xi1, yi1 = cx + r_in * math.cos(a1), cy + r_in * math.sin(a1)
        large = 1 if (end_deg - start_deg) > 180 else 0
        return (
            f"M {x0:.2f},{y0:.2f} A {r},{r} 0 {large},1 {x1:.2f},{y1:.2f} "
            f"L {xi1:.2f},{yi1:.2f} A {r_in},{r_in} 0 {large},0 {xi0:.2f},{yi0:.2f} Z"
        )

    cx, cy, r, w = 120, 120, 90, 36
    parts = []
    if total_p > 0:
        parts.append((total_p / n * 360, "#27ae60"))
    if total_f > 0:
        parts.append((total_f / n * 360, "#c0392b"))
    if total_s > 0:
        parts.append((total_s / n * 360, "#95a5a6"))
    paths = []
    angle = -90
    for span, color in parts:
        if span <= 0:
            continue
        d = arc(cx, cy, r, w, angle, angle + span)
        paths.append(f'<path d="{d}" fill="{color}" stroke="#fff" stroke-width="1"/>')
        angle += span

    pie_svg = "\n".join(paths) if paths else f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#bdc3c7"/>'

    rows = []
    for fname in sorted(features.keys()):
        st = features[fname]
        tot = st["passed"] + st["failed"] + st["skipped"]
        rows.append(
            f"<tr><td>{html.escape(fname)}</td>"
            f"<td>{st['passed']}</td><td>{st['failed']}</td><td>{st['skipped']}</td>"
            f"<td>{tot}</td></tr>"
        )

    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>ACEest API — test dashboard</title>
  <style>
    body {{ font-family: Segoe UI, system-ui, sans-serif; margin: 24px; background: #f8f9fa; color: #2c3e50; }}
    h1 {{ font-size: 1.35rem; }}
    .card {{ background: #fff; border-radius: 8px; padding: 20px 24px; margin-bottom: 20px;
             box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
    .row {{ display: flex; flex-wrap: wrap; gap: 32px; align-items: center; }}
    .legend span {{ display: inline-block; margin-right: 16px; font-size: 0.9rem; }}
    .dot {{ width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 720px; }}
    th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #ecf0f1; }}
    th {{ background: #34495e; color: #fff; }}
    .muted {{ color: #7f8c8d; font-size: 0.85rem; }}
  </style>
</head>
<body>
  <h1>ACEest Fitness API — test report</h1>
  <p class="muted">Generated {html.escape(when)} · Feature-style groups from test class names (similar to Cucumber features)</p>
  <div class="card">
    <div class="row">
      <svg width="240" height="240" viewBox="0 0 240 240" aria-label="Results pie chart">
        {pie_svg}
        <text x="{cx}" y="{cy + 6}" text-anchor="middle" font-size="18" font-weight="600" fill="#2c3e50">{n}</text>
        <text x="{cx}" y="{cy + 24}" text-anchor="middle" font-size="11" fill="#7f8c8d">tests</text>
      </svg>
      <div>
        <p><strong>Summary</strong></p>
        <p class="legend">
          <span><i class="dot" style="background:#27ae60"></i>Passed: {total_p}</span>
          <span><i class="dot" style="background:#c0392b"></i>Failed: {total_f}</span>
          <span><i class="dot" style="background:#95a5a6"></i>Skipped: {total_s}</span>
        </p>
      </div>
    </div>
  </div>
  <div class="card">
    <h2 style="margin-top:0;font-size:1.1rem;">By feature (test module / class)</h2>
    <table>
      <thead><tr><th>Feature</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Total</th></tr></thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
  </div>
</body>
</html>
"""

    os.makedirs(out_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
