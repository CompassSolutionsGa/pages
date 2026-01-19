from __future__ import annotations

import datetime as dt
import pathlib
import random
import re
import sys
from typing import Dict, Any, List, Tuple

import yaml
from slugify import slugify


ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "site.config.yml"
POSTS_DIR = ROOT / "content" / "posts"
INDUSTRY_YML = ROOT / "data" / "industry_fields.yml"


ANGLES: List[Tuple[str, str]] = [
    ("conversion", "How to improve {industry} form conversion (without redesigning your site)"),
    ("fields", "The best fields to include on a {industry} lead form"),
    ("mistakes", "Common {industry} form mistakes that reduce leads (and quick fixes)"),
    ("speed", "Make your {industry} lead form faster to complete: practical changes to test"),
    ("trust", "Trust signals that help {industry} forms convert more leads"),
    ("cta", "CTA ideas for {industry} forms: what to test and why it matters"),
]


def load_config() -> Dict[str, Any]:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return cfg


def read_yaml(path: pathlib.Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def existing_slugs() -> set[str]:
    slugs = set()
    for p in POSTS_DIR.glob("*.md"):
        slugs.add(p.stem)
    return slugs


def pick_industry(industry_meta: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
    # industry_meta keys are slugs (e.g. "roofing"), but we need a nice display name.
    # Prefer mapping from industries.txt if you have it; otherwise title-case the slug.
    items = []
    for slug, meta in industry_meta.items():
        if not isinstance(meta, dict):
            continue
        display = slug.replace("-", " ").title()
        items.append((display, slug, meta))
    if not items:
        raise RuntimeError("No industries found in data/industry_fields.yml")
    return random.choice(items)


def limit_list(x: List[str], n: int) -> List[str]:
    return [s.strip() for s in x if str(s).strip()][:n]


def safe_text(s: str) -> str:
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_post(cfg: Dict[str, Any], industry_name: str, industry_slug: str, meta: Dict[str, Any]) -> Tuple[str, str]:
    app_url = (cfg.get("app_url") or "https://formhuntsman.com/").rstrip("/") + "/"

    fields = limit_list(meta.get("fields", []) or [], 8)
    questions = limit_list(meta.get("questions", []) or [], 6)
    tests = limit_list(meta.get("tests", []) or [], 6)

    angle_key, angle_title_tmpl = random.choice(ANGLES)
    title = angle_title_tmpl.format(industry=industry_name)

    # Make a deterministic-ish slug so duplicates are unlikely
    date = dt.date.today().isoformat()
    base_slug = slugify(f"{industry_name}-{angle_key}-{date}")
    slug = base_slug

    # Ensure unique filename
    slugs = existing_slugs()
    i = 2
    while slug in slugs:
        slug = f"{base_slug}-{i}"
        i += 1

    description = safe_text(
        f"Practical {industry_name.lower()} form tips: suggested fields, example questions, and A/B tests you can run in FormHuntsman."
    )

    # Small variations so posts don’t look identical
    intro_lines = [
        f"If you rely on inbound leads, your {industry_name.lower()} contact form is one of your highest-impact pages.",
        f"A great {industry_name.lower()} service page can still underperform if the lead form creates friction.",
        f"Most {industry_name.lower()} sites don’t need a redesign to get more leads, they need clearer forms and better testing.",
    ]
    intro = random.choice(intro_lines)

    body = f"""---
title: {title}
date: {date}
description: {description}
cta_url: {app_url}
cta_text: Start scanning and testing forms in minutes.
---

{intro}

## Recommended form fields for {industry_name}
{chr(10).join([f"- {f}" for f in (fields or ["Name", "Phone", "Email (optional)", "Service needed", "ZIP code"])])}

## Example questions to include
{chr(10).join([f"- {q}" for q in (questions or ["What do you need help with?", "When do you need this?", "Where are you located?"])])}

## A/B tests worth running
{chr(10).join([f"- {t}" for t in (tests or ["Short form vs long form", "CTA wording variations", "Phone-first vs email-first"])])}

## Quick setup
1. Open FormHuntsman
2. Add your domain
3. Run a scan and pick one small test to launch

## Next steps
Run one experiment, measure results, then iterate. Small wins compound fast when you keep a simple testing rhythm.
"""

    return slug, body


def main() -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    industry_meta = read_yaml(INDUSTRY_YML)

    industry_name, industry_slug, meta = pick_industry(industry_meta)
    slug, md = build_post(cfg, industry_name, industry_slug, meta)

    out_path = POSTS_DIR / f"{slug}.md"
    out_path.write_text(md, encoding="utf-8")

    print(f"Created: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"autopost failed: {e}", file=sys.stderr)
        sys.exit(1)
