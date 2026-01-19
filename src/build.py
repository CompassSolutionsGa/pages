from __future__ import annotations

import datetime as dt
import pathlib
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Tuple, Any

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape
from slugify import slugify

ROOT = pathlib.Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "src" / "templates"
CONTENT_POSTS_DIR = ROOT / "content" / "posts"
DATA_DIR = ROOT / "data"
CONFIG_PATH = ROOT / "site.config.yml"


@dataclass
class Item:
    title: str
    description: str
    url: str
    date: dt.date
    html: str
    canonical: str


def load_config() -> Dict[str, str]:
    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if not cfg.get("site_url"):
        raise ValueError("site_url is required in site.config.yml")
    return cfg


def parse_frontmatter(md_text: str) -> Tuple[Dict[str, str], str]:
    # Supports YAML frontmatter between --- blocks.
    lines = md_text.splitlines()
    if len(lines) >= 3 and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm = "\n".join(lines[1:i])
                body = "\n".join(lines[i + 1 :])
                meta = yaml.safe_load(fm) or {}
                return meta, body
    return {}, md_text


def md_to_html(md_body: str) -> str:
    return markdown.markdown(
        md_body,
        extensions=[
            "fenced_code",
            "tables",
            "toc",
        ],
    )


def ensure_dir(path: pathlib.Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_csv_list(path: pathlib.Path) -> List[str]:
    if not path.exists():
        return []
    items: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        items.append(s)
    return items


def get_app_url(cfg: Dict[str, str]) -> str:
    # Always return a usable URL for CTAs
    return (cfg.get("app_url") or "https://formhuntsman.com").rstrip("/")


def load_industry_fields() -> Dict[str, Any]:
    """
    Optional file:
      data/industry_fields.yml

    Expected structure (keyed by industry slug):
      roofing:
        fields:
          - ...
        questions:
          - ...
        tests:
          - ...
    """
    path = DATA_DIR / "industry_fields.yml"
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def build_posts(cfg: Dict[str, str], env: Environment) -> List[Item]:
    items: List[Item] = []
    app_url = get_app_url(cfg)

    for md_file in sorted(CONTENT_POSTS_DIR.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(raw)

        title = str(meta.get("title") or md_file.stem)
        description = str(meta.get("description") or "")
        date_str = str(meta.get("date") or dt.date.today().isoformat())
        date = dt.date.fromisoformat(date_str)

        slug = str(meta.get("slug") or slugify(title))
        url = f"/blog/{slug}/"
        canonical = cfg["site_url"].rstrip("/") + url

        content_html = md_to_html(body)

        post_t = env.get_template("post.html")
        body_html = post_t.render(
            title=title,
            date=date.isoformat(),
            content=content_html,
            cta_url=meta.get("cta_url") or app_url,
            cta_text=meta.get("cta_text") or "Run unlimited form experiments in minutes.",
        )

        base_t = env.get_template("base.html")
        full = base_t.render(
            lang=cfg.get("language", "en"),
            title=f"{title} | {cfg['site_name']}",
            description=description or title,
            canonical=canonical,
            base_url=cfg["site_url"].rstrip("/"),
            site_name=cfg["site_name"],
            tagline="A lightweight library of A/B form tests and templates.",
            year=dt.date.today().year,
            author=cfg.get("author", cfg["site_name"]),
            body=body_html,
        )

        items.append(Item(title, description or title, url, date, full, canonical))

    # newest first
    items.sort(key=lambda x: x.date, reverse=True)
    return items


def build_pseo(cfg: Dict[str, str], env: Environment) -> List[Item]:
    industries = load_csv_list(DATA_DIR / "industries.txt")
    use_cases = load_csv_list(DATA_DIR / "use_cases.txt")

    industry_meta = load_industry_fields()

    pages: List[Item] = []
    today = dt.date.today()
    app_url = get_app_url(cfg)

    for industry in industries:
        title = f"{industry} form templates"
        description = (
            f"Browse {industry}-specific form templates with field suggestions, example questions, "
            "and A/B test ideas you can run in FormHuntsman."
        )
        slug = slugify(industry)
        url = f"/templates/{slug}/"
        canonical = cfg["site_url"].rstrip("/") + url

        # Pull richer content if present
        meta = industry_meta.get(slug, {}) if isinstance(industry_meta, dict) else {}
        fields = meta.get("fields", []) if isinstance(meta, dict) else []
        questions = meta.get("questions", []) if isinstance(meta, dict) else []
        tests = meta.get("tests", []) if isinstance(meta, dict) else []

        # Fallbacks so pages are never empty
        if not fields:
            fields = [
                "Name",
                "Email or phone",
                "Service needed",
                "Location / ZIP code",
                "Best time to contact",
            ]

        if not questions:
            questions = [
                "What are you trying to accomplish?",
                "When do you need this done?",
                "Any special requirements or constraints?",
            ]

        if not tests:
            # Use your use_cases list as a generic fallback for test ideas
            if use_cases:
                tests = use_cases[:6]
            else:
                tests = [
                    "Test a shorter form vs a longer form",
                    "Test CTA text: “Get a quote” vs “Request pricing”",
                    "Test phone-first vs email-first ordering",
                ]

        fields_md = "\n".join([f"- {f}" for f in fields])
        questions_md = "\n".join([f"- {q}" for q in questions])
        tests_md = "\n".join([f"- {t}" for t in tests])

        md_body = f"""
## What this page includes

Use this as a quick starting point for building a higher-converting **{industry}** lead form: the best fields to ask for, example questions, and simple tests that improve conversion without redesigning your whole site.

## Recommended form fields

{fields_md}

## Example questions to include

{questions_md}

## A/B test ideas worth trying

{tests_md}

## Run these tests with FormHuntsman

FormHuntsman helps you **scan existing pages**, **track form changes over time**, and **ship experiments faster** without rebuilding your site.
""".strip()

        content_html = md_to_html(md_body)

        post_t = env.get_template("post.html")
        body_html = post_t.render(
            title=title,
            date=today.isoformat(),
            content=content_html,
            cta_url=app_url,  # ✅ always goes to the app
            cta_text="Open FormHuntsman and launch a form experiment.",
        )

        base_t = env.get_template("base.html")
        full = base_t.render(
            lang=cfg.get("language", "en"),
            title=f"{title} | {cfg['site_name']}",
            description=description,
            canonical=canonical,
            base_url=cfg["site_url"].rstrip("/"),
            site_name=cfg["site_name"],
            tagline="A lightweight library of A/B form tests and templates.",
            year=today.year,
            author=cfg.get("author", cfg["site_name"]),
            body=body_html,
        )

        pages.append(Item(title, description, url, today, full, canonical))

    return pages


def write_item(out_dir: pathlib.Path, item: Item) -> None:
    dest = out_dir / item.url.strip("/") / "index.html"
    ensure_dir(dest.parent)
    dest.write_text(item.html, encoding="utf-8")


def write_index(cfg: Dict[str, str], env: Environment, posts: List[Item], pseo_pages: List[Item], out_dir: pathlib.Path) -> None:
    index_t = env.get_template("index.html")
    body = index_t.render(
        posts=[
            {"title": p.title, "description": p.description, "url": p.url, "date": p.date.isoformat()}
            for p in posts[:10]
        ],
        pseo_pages=[{"title": x.title, "url": x.url} for x in pseo_pages[:30]],
        base_url=cfg["site_url"].rstrip("/"),
    )

    base_t = env.get_template("base.html")
    canonical = cfg["site_url"].rstrip("/") + "/"
    full = base_t.render(
        lang=cfg.get("language", "en"),
        title=f"{cfg['site_name']} | Form experimentation made simple",
        description="A library of form tests, templates, and conversion ideas you can ship fast.",
        canonical=canonical,
        base_url=cfg["site_url"].rstrip("/"),
        site_name=cfg["site_name"],
        tagline="A lightweight library of A/B form tests and templates.",
        year=dt.date.today().year,
        author=cfg.get("author", cfg["site_name"]),
        body=body,
    )

    (out_dir / "index.html").write_text(full, encoding="utf-8")


def write_robots(out_dir: pathlib.Path) -> None:
    (out_dir / "robots.txt").write_text(
        "User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n",
        encoding="utf-8",
    )


def write_sitemap(cfg: Dict[str, str], items: List[Item], out_dir: pathlib.Path) -> None:
    urlset = ET.Element("urlset", attrib={"xmlns": "http://www.sitemaps.org/schemas/sitemap/0.9"})
    for it in items:
        u = ET.SubElement(urlset, "url")
        ET.SubElement(u, "loc").text = it.canonical
        ET.SubElement(u, "lastmod").text = it.date.isoformat()

    tree = ET.ElementTree(urlset)
    tree.write(out_dir / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def write_rss(cfg: Dict[str, str], items: List[Item], out_dir: pathlib.Path) -> None:
    base = cfg["site_url"].rstrip("/")

    rss = ET.Element("rss", attrib={"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = cfg.get("rss_title", cfg["site_name"])
    ET.SubElement(channel, "link").text = base + "/"
    ET.SubElement(channel, "description").text = cfg.get("rss_description", "")

    for it in sorted(items, key=lambda x: x.date, reverse=True)[:30]:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = it.title
        ET.SubElement(item, "link").text = it.canonical
        ET.SubElement(item, "guid").text = it.canonical
        ET.SubElement(item, "pubDate").text = dt.datetime.combine(it.date, dt.time()).strftime("%a, %d %b %Y %H:%M:%S GMT")
        ET.SubElement(item, "description").text = it.description

    ET.ElementTree(rss).write(out_dir / "rss.xml", encoding="utf-8", xml_declaration=True)


def copy_static(out_dir: pathlib.Path) -> None:
    static_dir = ROOT / "static"
    if not static_dir.exists():
        return
    for p in static_dir.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(static_dir)
        dest = out_dir / rel
        ensure_dir(dest.parent)
        shutil.copy2(p, dest)


def clean_out(out_dir: pathlib.Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def main() -> None:
    cfg = load_config()
    out_dir = ROOT / cfg.get("output_dir", "_site")

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    clean_out(out_dir)

    posts = build_posts(cfg, env)
    pseo_pages = build_pseo(cfg, env)

    for it in posts + pseo_pages:
        write_item(out_dir, it)

    write_index(cfg, env, posts, pseo_pages, out_dir)
    write_robots(out_dir)
    write_sitemap(cfg, [*posts, *pseo_pages], out_dir)
    write_rss(cfg, [*posts, *pseo_pages], out_dir)
    copy_static(out_dir)

    print(f"Built {len(posts)} posts and {len(pseo_pages)} landing pages -> {out_dir}")


if __name__ == "__main__":
    main()
