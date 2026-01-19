# FormHuntsman: zero-cost, automated growth repo

This is a **GitHub Pages + GitHub Actions** project that:
- Builds a static site from Markdown (`content/posts/*.md`)
- Generates "programmatic SEO" landing pages from simple lists (`data/*.txt`)
- Publishes automatically (daily + on push)
- Generates `sitemap.xml`, `rss.xml`, and `robots.txt`

## What you change (manual)
You only need to edit:
- `site.config.yml` (set your real `site_url`)
- `data/industries.txt` and `data/usecases.txt` (add more long-tail coverage)
- Add new posts in `content/posts/`

Everything else is automated.

## How to go live (GitHub Pages)
1. Create a new GitHub repo and upload this project.
2. In your repo: **Settings → Pages**
   - Source: **GitHub Actions**
3. Commit/push. The workflow will build and deploy.

After the first deploy, your site will be live at a `*.github.io` URL.

## Hooking up formhuntsman.com (Namecheap)
Recommended: keep your main domain on your existing app, and point a subdomain to GitHub Pages, e.g.:
- `pages.formhuntsman.com` → GitHub Pages (this static SEO/blog site)

Steps:
1. In `site.config.yml`, set `site_url` to `https://pages.formhuntsman.com`
2. Create a `CNAME` file in repo root with:
   - `pages.formhuntsman.com`
3. In Namecheap DNS:
   - Add `CNAME` record for host `pages` pointing to `<your-github-username>.github.io`
4. In GitHub repo Settings → Pages, add the custom domain.

## Local build
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/build.py
```
Output goes to `/_site`.

## Automation schedule
`.github/workflows/pages.yml` runs:
- On every push to `main`
- Daily (so new programmatic pages and fresh `sitemap.xml` are always published)

## Notes on SEO safety
This approach avoids risky automation (spam posting, link farms, scraping with aggressive bots). It focuses on:
- Helpful long-tail landing pages
- Clean internal linking
- Sitemaps + RSS
- Consistent publishing cadence

