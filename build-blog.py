#!/usr/bin/env python3
"""
SystemShift Blog Builder
Converts Markdown posts in /blog/posts/ to SEO-optimized HTML pages.
Also generates blog index page and sitemap.xml.

Usage: python build-blog.py
Run before deploy: ./deploy.sh automatically calls this.

Post format (Markdown with YAML frontmatter):
---
title: Your Blog Post Title
description: Meta description under 160 chars with primary keyword in first 80 chars
slug: your-url-slug
date: 2026-03-09
category: Automation
tags: [CRM, lead generation, automation]
cover: images/blog/your-cover.png
author: Rock
---

Your markdown content here...
"""

import os
import re
import glob
import json
from datetime import datetime
from pathlib import Path

SITE_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(SITE_DIR, 'blog', 'posts')
BLOG_OUTPUT_DIR = os.path.join(SITE_DIR, 'blog')
SITE_URL = 'https://systemshifthq.com'

# ── Minimal Markdown parser (no dependencies) ──

def parse_frontmatter(content):
    """Extract YAML-like frontmatter and body from markdown."""
    if not content.startswith('---'):
        return {}, content
    end = content.find('---', 3)
    if end == -1:
        return {}, content
    fm_text = content[3:end].strip()
    body = content[end + 3:].strip()
    meta = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, val = line.split(':', 1)
            key = key.strip()
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                val = [v.strip().strip('"').strip("'") for v in val[1:-1].split(',')]
            elif val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            meta[key] = val
    return meta, body


def md_to_html(md):
    """Convert markdown to HTML. Handles headers, bold, italic, links, lists, code, blockquotes, images."""
    lines = md.split('\n')
    html_lines = []
    in_list = False
    in_ol = False
    in_code = False
    in_blockquote = False

    for line in lines:
        stripped = line.strip()

        # Code blocks
        if stripped.startswith('```'):
            if in_code:
                html_lines.append('</code></pre>')
                in_code = False
            else:
                lang = stripped[3:].strip()
                html_lines.append(f'<pre><code class="lang-{lang}">' if lang else '<pre><code>')
                in_code = True
            continue

        if in_code:
            html_lines.append(line.replace('<', '&lt;').replace('>', '&gt;'))
            continue

        # Close open lists if needed
        if in_list and not stripped.startswith('- ') and not stripped.startswith('* '):
            html_lines.append('</ul>')
            in_list = False

        if in_ol and not re.match(r'^\d+\.\s', stripped):
            html_lines.append('</ol>')
            in_ol = False

        # Blockquote
        if stripped.startswith('> '):
            if not in_blockquote:
                html_lines.append('<blockquote>')
                in_blockquote = True
            html_lines.append(f'<p>{inline_format(stripped[2:])}</p>')
            continue
        elif in_blockquote:
            html_lines.append('</blockquote>')
            in_blockquote = False

        # Headers
        if stripped.startswith('######'):
            html_lines.append(f'<h6>{inline_format(stripped[6:].strip())}</h6>')
        elif stripped.startswith('#####'):
            html_lines.append(f'<h5>{inline_format(stripped[5:].strip())}</h5>')
        elif stripped.startswith('####'):
            html_lines.append(f'<h4>{inline_format(stripped[4:].strip())}</h4>')
        elif stripped.startswith('###'):
            html_lines.append(f'<h3>{inline_format(stripped[3:].strip())}</h3>')
        elif stripped.startswith('##'):
            html_lines.append(f'<h2>{inline_format(stripped[2:].strip())}</h2>')
        elif stripped.startswith('#'):
            # Skip h1 -- we use the title from frontmatter
            pass
        # Horizontal rule
        elif stripped in ('---', '***', '___'):
            html_lines.append('<hr>')
        # Unordered list
        elif stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{inline_format(stripped[2:])}</li>')
        # Ordered list
        elif re.match(r'^\d+\.\s', stripped):
            if not in_ol:
                html_lines.append('<ol>')
                in_ol = True
            text = re.sub(r'^\d+\.\s', '', stripped)
            html_lines.append(f'<li>{inline_format(text)}</li>')
        # Image
        elif re.match(r'^!\[.*?\]\(.*?\)$', stripped):
            m = re.match(r'^!\[(.*?)\]\((.*?)\)$', stripped)
            html_lines.append(f'<img src="{m.group(2)}" alt="{m.group(1)}" loading="lazy">')
        # Empty line
        elif stripped == '':
            html_lines.append('')
        # Paragraph
        else:
            html_lines.append(f'<p>{inline_format(stripped)}</p>')

    # Close any open tags
    if in_list:
        html_lines.append('</ul>')
    if in_ol:
        html_lines.append('</ol>')
    if in_blockquote:
        html_lines.append('</blockquote>')
    if in_code:
        html_lines.append('</code></pre>')

    return '\n'.join(html_lines)


def inline_format(text):
    """Handle inline markdown: bold, italic, links, inline code."""
    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    # Bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', text)
    return text


def estimate_read_time(text):
    """Estimate reading time in minutes."""
    words = len(text.split())
    return max(1, round(words / 200))


def build_post_html(meta, body_html, read_time):
    """Generate full HTML page for a blog post."""
    title = meta.get('title', 'Untitled')
    description = meta.get('description', '')
    slug = meta.get('slug', 'untitled')
    date = meta.get('date', '')
    category = meta.get('category', '')
    tags = meta.get('tags', [])
    cover = meta.get('cover', '')
    author = meta.get('author', 'Rock')

    # Format date
    try:
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_display = date_obj.strftime('%B %d, %Y')
        date_iso = date_obj.strftime('%Y-%m-%dT00:00:00-05:00')
    except (ValueError, TypeError):
        date_display = date
        date_iso = date

    tags_html = ''.join(f'<span class="blog-tag">{t}</span>' for t in tags) if isinstance(tags, list) else ''

    cover_html = f'''
    <div class="blog-cover">
      <img src="../{cover}" alt="{title}" loading="lazy">
    </div>''' if cover else ''

    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": title,
        "description": description,
        "author": {"@type": "Person", "name": author},
        "publisher": {
            "@type": "Organization",
            "name": "SystemShift HQ",
            "url": SITE_URL
        },
        "datePublished": date_iso,
        "dateModified": date_iso,
        "image": f"{SITE_URL}/{cover}" if cover else "",
        "mainEntityOfPage": f"{SITE_URL}/blog/{slug}.html",
        "articleSection": category,
        "keywords": ', '.join(tags) if isinstance(tags, list) else tags
    }, indent=2)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | SystemShift HQ Blog</title>
  <meta name="description" content="{description}">
  <link rel="canonical" href="{SITE_URL}/blog/{slug}.html">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{SITE_URL}/blog/{slug}.html">
  {"<meta property='og:image' content='" + SITE_URL + "/" + cover + "'>" if cover else ""}
  <meta property="article:published_time" content="{date_iso}">
  <meta property="article:section" content="{category}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,400;0,8..60,600;0,8..60,700;0,8..60,900;1,8..60,400&family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="../css/styles.css">
  <script type="application/ld+json">
  {schema}
  </script>
  <style>
    .blog-post-hero {{
      padding: 140px 0 40px;
      background: var(--bg-dark);
    }}

    .blog-post-meta {{
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 20px;
      flex-wrap: wrap;
    }}

    .blog-category {{
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--turquoise);
      background: var(--turquoise-dim);
      padding: 4px 12px;
      border-radius: 100px;
    }}

    .blog-date {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .blog-read-time {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .blog-post-hero h1 {{
      font-family: var(--serif);
      font-size: clamp(2rem, 4vw, 3rem);
      font-weight: 900;
      line-height: 1.15;
      color: #fff;
      max-width: 800px;
      margin-bottom: 16px;
    }}

    .blog-post-hero .blog-desc {{
      font-size: 1.1rem;
      color: var(--text-secondary);
      line-height: 1.7;
      max-width: 700px;
    }}

    .blog-tags {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 20px;
    }}

    .blog-tag {{
      font-size: 0.72rem;
      padding: 4px 12px;
      border-radius: 100px;
      border: 1px solid var(--border);
      color: var(--text-muted);
    }}

    .blog-cover {{
      margin: 40px 0;
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--border);
    }}

    .blog-cover img {{
      width: 100%;
      height: auto;
      display: block;
    }}

    .blog-content {{
      padding: 0 0 100px;
      background: var(--bg-dark);
    }}

    .blog-body {{
      max-width: 720px;
      margin: 0 auto;
      font-size: 1.05rem;
      line-height: 1.8;
      color: var(--text-secondary);
    }}

    .blog-body h2 {{
      font-family: var(--serif);
      font-size: 1.6rem;
      font-weight: 700;
      color: #fff;
      margin: 48px 0 16px;
    }}

    .blog-body h3 {{
      font-family: var(--serif);
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      margin: 36px 0 12px;
    }}

    .blog-body p {{
      margin-bottom: 20px;
    }}

    .blog-body strong {{
      color: #fff;
    }}

    .blog-body a {{
      color: var(--turquoise);
      text-decoration: underline;
      text-underline-offset: 3px;
    }}

    .blog-body ul, .blog-body ol {{
      margin: 16px 0 24px 24px;
    }}

    .blog-body li {{
      margin-bottom: 8px;
    }}

    .blog-body blockquote {{
      border-left: 3px solid var(--turquoise);
      padding: 16px 24px;
      margin: 32px 0;
      background: rgba(255,255,255,0.02);
      border-radius: 0 8px 8px 0;
      font-style: italic;
    }}

    .blog-body blockquote p {{
      margin-bottom: 0;
      color: var(--text-primary);
    }}

    .blog-body pre {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px 24px;
      overflow-x: auto;
      margin: 24px 0;
      font-size: 0.9rem;
    }}

    .blog-body code {{
      font-size: 0.9em;
      background: var(--bg-card);
      padding: 2px 6px;
      border-radius: 4px;
    }}

    .blog-body pre code {{
      background: none;
      padding: 0;
    }}

    .blog-body img {{
      max-width: 100%;
      border-radius: 12px;
      margin: 24px 0;
    }}

    .blog-body hr {{
      border: none;
      border-top: 1px solid var(--border);
      margin: 40px 0;
    }}

    .blog-cta {{
      max-width: 720px;
      margin: 0 auto;
      padding: 40px;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      text-align: center;
    }}

    .blog-cta h3 {{
      font-family: var(--serif);
      font-size: 1.3rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 12px;
    }}

    .blog-cta p {{
      color: var(--text-secondary);
      margin-bottom: 20px;
      font-size: 0.95rem;
    }}

    .blog-back {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--turquoise);
      font-size: 0.9rem;
      font-weight: 500;
      margin-bottom: 24px;
    }}

    .blog-back:hover {{ text-decoration: underline; }}

    @media (max-width: 768px) {{
      .blog-post-hero {{ padding: 120px 0 32px; }}
      .blog-body {{ font-size: 1rem; }}
      .blog-cta {{ padding: 28px 20px; }}
    }}
  </style>
</head>
<body>

  <header class="site-header">
    <div class="header-inner">
      <a href="../index.html" class="header-logo"><img src="../images/logo-white.png" alt="SystemShift HQ"></a>
      <nav class="header-nav">
        <a href="../index.html">Home</a>
        <div class="nav-dropdown">
          <a href="../services.html">Services <svg class="dropdown-arrow" viewBox="0 0 12 12"><polyline points="2 4 6 8 10 4"/></svg></a>
          <div class="dropdown-menu">
            <a href="../service-crm.html">CRM Build + Management</a>
            <a href="../custom-ai-solutions.html">Custom AI Solutions</a>
            <a href="../service-voice.html">AI Voice &amp; Chat Agents</a>
            <a href="../service-funnels.html">Landing Pages &amp; Funnels</a>
            <a href="../service-social.html">Social Media Automation</a>
            <a href="../service-linkedin.html">LinkedIn Brand Management</a>
            <a href="../service-consulting.html">AI + Automation Consulting</a>
            <a href="../service-apps.html">Integrator Services</a>
            <a href="../service-app-design.html">App Design</a>
            <a href="../service-cao.html">Fractional CAO</a>
            <a href="../service-ghl.html">GHL Implementation</a>
          </div>
        </div>
        <a href="../blog.html" class="active">Blog</a>
        <a href="https://www.youtube.com/@rockurbusiness" target="_blank" rel="noopener">Education</a>
        <a href="../contact.html">Contact</a>
        <div class="header-cta"><a href="../contact.html" class="btn btn-primary btn-sm">Book a Call</a></div>
      </nav>
      <button class="mobile-toggle" aria-label="Menu"><span></span><span></span><span></span></button>
    </div>
  </header>

  <main class="page-top">
    <section class="blog-post-hero">
      <div class="container">
        <a href="../blog.html" class="blog-back">&larr; Back to Blog</a>
        <div class="blog-post-meta">
          <span class="blog-category">{category}</span>
          <span class="blog-date">{date_display}</span>
          <span class="blog-read-time">{read_time} min read</span>
        </div>
        <h1>{title}</h1>
        <p class="blog-desc">{description}</p>
        <div class="blog-tags">{tags_html}</div>
      </div>
    </section>

    <section class="blog-content">
      <div class="container">
        {cover_html}
        <div class="blog-body">
          {body_html}
        </div>
        <div class="blog-cta">
          <h3>Ready to Automate Your Business?</h3>
          <p>Book a free strategy call and we'll map out exactly what to build first.</p>
          <a href="../contact.html" class="btn btn-primary">Book Your Call</a>
        </div>
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div class="footer-brand">
          <a href="../index.html" class="header-logo"><img src="../images/logo-white.png" alt="SystemShift HQ"></a>
          <p>We build AI and automation systems for businesses ready to scale without the busywork.</p>
          <div class="footer-contact">
            <a href="mailto:support@systemshifthq.com">support@systemshifthq.com</a>
            <a href="tel:3365688504">336-568-8504</a>
            <a href="#">3980 Premier Dr, High Point, NC 27265</a>
          </div>
        </div>
        <div class="footer-col"><h4>Pages</h4><a href="../index.html">Home</a><a href="../services.html">Services</a><a href="../blog.html">Blog</a><a href="../about.html">About</a><a href="../contact.html">Contact Us</a></div>
        <div class="footer-col"><h4>Resources</h4><a href="https://www.youtube.com/@rockurbusiness" target="_blank">Education</a><a href="../case-studies.html">Case Studies</a><a href="../contact.html">Book a Call</a></div>
        <div class="footer-col"><h4>Legal</h4><a href="../privacy-policy.html">Privacy Policy</a><a href="../terms.html">Terms of Service</a></div>
      </div>
      <div class="footer-bottom">
        <span>&copy; 2026 SystemShift HQ. All rights reserved.</span>
        <div class="footer-legal"><a href="../privacy-policy.html">Privacy</a><a href="../terms.html">Terms</a></div>
      </div>
    </div>
  </footer>

  <script src="../js/main.js"></script>
</body>
</html>'''


def build_index_html(posts):
    """Generate blog index page."""
    cards_html = ''
    for p in posts:
        meta = p['meta']
        tags_html = ''.join(f'<span class="blog-card-tag">{t}</span>' for t in (meta.get('tags', []) if isinstance(meta.get('tags', []), list) else []))
        cover = meta.get('cover', '')
        cover_img = f'<img src="{cover}" alt="{meta.get("title", "")}" class="blog-card-img" loading="lazy">' if cover else '<div class="blog-card-img blog-card-placeholder"></div>'

        try:
            date_obj = datetime.strptime(meta.get('date', ''), '%Y-%m-%d')
            date_display = date_obj.strftime('%B %d, %Y')
        except (ValueError, TypeError):
            date_display = meta.get('date', '')

        cards_html += f'''
        <a href="blog/{meta.get('slug', 'untitled')}.html" class="blog-card fade-up">
          {cover_img}
          <div class="blog-card-content">
            <div class="blog-card-meta">
              <span class="blog-category">{meta.get('category', '')}</span>
              <span class="blog-date">{date_display}</span>
              <span class="blog-read-time">{p['read_time']} min read</span>
            </div>
            <h2>{meta.get('title', 'Untitled')}</h2>
            <p>{meta.get('description', '')}</p>
            <div class="blog-card-tags">{tags_html}</div>
          </div>
        </a>
'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog | AI & Automation Insights | SystemShift HQ</title>
  <meta name="description" content="Actionable insights on AI automation, CRM systems, lead generation, and scaling your business. Written by Rock at SystemShift HQ.">
  <link rel="canonical" href="{SITE_URL}/blog.html">
  <meta property="og:title" content="Blog | SystemShift HQ">
  <meta property="og:description" content="Actionable insights on AI automation, CRM systems, and scaling your business.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{SITE_URL}/blog.html">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;600;700;900&family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="css/styles.css">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Blog",
    "name": "SystemShift HQ Blog",
    "description": "Actionable insights on AI automation, CRM systems, lead generation, and scaling your business.",
    "url": "{SITE_URL}/blog.html",
    "publisher": {{
      "@type": "Organization",
      "name": "SystemShift HQ",
      "url": "{SITE_URL}"
    }}
  }}
  </script>
  <style>
    .blog-hero {{
      padding: 160px 0 80px;
      text-align: center;
      background: var(--bg-dark);
    }}

    .blog-hero h1 {{
      font-family: var(--serif);
      font-size: clamp(2.4rem, 5vw, 3.6rem);
      font-weight: 900;
      color: #fff;
      margin-bottom: 16px;
    }}

    .blog-hero p {{
      font-size: 1.1rem;
      color: var(--text-secondary);
      max-width: 600px;
      margin: 0 auto;
      line-height: 1.7;
    }}

    .blog-grid-section {{
      padding: 60px 0 100px;
      background: var(--bg-dark);
    }}

    .blog-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 32px;
      max-width: 1000px;
      margin: 0 auto;
    }}

    .blog-card {{
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      transition: all 0.3s ease;
      display: block;
      color: inherit;
      text-decoration: none;
    }}

    .blog-card:hover {{
      border-color: rgba(15,223,216,0.3);
      transform: translateY(-4px);
      box-shadow: 0 12px 48px rgba(0,0,0,0.4);
    }}

    .blog-card-img {{
      width: 100%;
      height: 220px;
      object-fit: cover;
      display: block;
    }}

    .blog-card-placeholder {{
      background: linear-gradient(135deg, #1a1a2e, #16213e);
    }}

    .blog-card-content {{
      padding: 24px 28px 28px;
    }}

    .blog-card-meta {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }}

    .blog-category {{
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: var(--turquoise);
      background: var(--turquoise-dim);
      padding: 4px 12px;
      border-radius: 100px;
    }}

    .blog-date, .blog-read-time {{
      font-size: 0.8rem;
      color: var(--text-muted);
    }}

    .blog-card h2 {{
      font-family: var(--serif);
      font-size: 1.25rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 8px;
      line-height: 1.3;
    }}

    .blog-card p {{
      font-size: 0.9rem;
      color: var(--text-secondary);
      line-height: 1.6;
      margin-bottom: 16px;
    }}

    .blog-card-tags {{
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }}

    .blog-card-tag {{
      font-size: 0.68rem;
      padding: 3px 10px;
      border-radius: 100px;
      border: 1px solid var(--border);
      color: var(--text-muted);
    }}

    .blog-empty {{
      text-align: center;
      padding: 80px 0;
      color: var(--text-muted);
      font-size: 1.1rem;
    }}

    @media (max-width: 700px) {{
      .blog-grid {{ grid-template-columns: 1fr; }}
      .blog-hero {{ padding: 120px 0 60px; }}
    }}
  </style>
</head>
<body>

  <header class="site-header">
    <div class="header-inner">
      <a href="index.html" class="header-logo"><img src="images/logo-white.png" alt="SystemShift HQ"></a>
      <nav class="header-nav">
        <a href="index.html">Home</a>
        <div class="nav-dropdown">
          <a href="services.html">Services <svg class="dropdown-arrow" viewBox="0 0 12 12"><polyline points="2 4 6 8 10 4"/></svg></a>
          <div class="dropdown-menu">
            <a href="service-crm.html">CRM Build + Management</a>
            <a href="custom-ai-solutions.html">Custom AI Solutions</a>
            <a href="service-voice.html">AI Voice &amp; Chat Agents</a>
            <a href="service-funnels.html">Landing Pages &amp; Funnels</a>
            <a href="service-social.html">Social Media Automation</a>
            <a href="service-linkedin.html">LinkedIn Brand Management</a>
            <a href="service-consulting.html">AI + Automation Consulting</a>
            <a href="service-apps.html">Integrator Services</a>
            <a href="service-app-design.html">App Design</a>
            <a href="service-cao.html">Fractional CAO</a>
            <a href="service-ghl.html">GHL Implementation</a>
          </div>
        </div>
        <a href="blog.html" class="active">Blog</a>
        <a href="https://www.youtube.com/@rockurbusiness" target="_blank" rel="noopener">Education</a>
        <a href="contact.html">Contact</a>
        <div class="header-cta"><a href="contact.html" class="btn btn-primary btn-sm">Book a Call</a></div>
      </nav>
      <button class="mobile-toggle" aria-label="Menu"><span></span><span></span><span></span></button>
    </div>
  </header>

  <main class="page-top">
    <section class="blog-hero">
      <div class="container">
        <span class="section-eyebrow fade-up">Blog</span>
        <h1 class="fade-up">Systems That Scale</h1>
        <p class="fade-up">Frameworks, breakdowns, and real talk on automating your business. No fluff. No theory. Just what works.</p>
      </div>
    </section>

    <section class="blog-grid-section">
      <div class="container">
        {"<div class='blog-grid'>" + cards_html + "</div>" if cards_html else "<p class='blog-empty'>New posts coming soon. Check back shortly.</p>"}
      </div>
    </section>
  </main>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div class="footer-brand">
          <a href="index.html" class="header-logo"><img src="images/logo-white.png" alt="SystemShift HQ"></a>
          <p>We build AI and automation systems for businesses ready to scale without the busywork.</p>
          <div class="footer-contact">
            <a href="mailto:support@systemshifthq.com">support@systemshifthq.com</a>
            <a href="tel:3365688504">336-568-8504</a>
            <a href="#">3980 Premier Dr, High Point, NC 27265</a>
          </div>
        </div>
        <div class="footer-col"><h4>Pages</h4><a href="index.html">Home</a><a href="services.html">Services</a><a href="blog.html">Blog</a><a href="about.html">About</a><a href="contact.html">Contact Us</a></div>
        <div class="footer-col"><h4>Resources</h4><a href="https://www.youtube.com/@rockurbusiness" target="_blank">Education</a><a href="case-studies.html">Case Studies</a><a href="contact.html">Book a Call</a></div>
        <div class="footer-col"><h4>Legal</h4><a href="privacy-policy.html">Privacy Policy</a><a href="terms.html">Terms of Service</a></div>
      </div>
      <div class="footer-bottom">
        <span>&copy; 2026 SystemShift HQ. All rights reserved.</span>
        <div class="footer-legal"><a href="privacy-policy.html">Privacy</a><a href="terms.html">Terms</a></div>
      </div>
    </div>
  </footer>

  <script src="js/main.js"></script>
</body>
</html>'''


def build_sitemap(posts, pages):
    """Generate sitemap.xml."""
    today = datetime.now().strftime('%Y-%m-%d')
    entries = ''

    # Static pages
    for page in pages:
        priority = '1.0' if page == 'index.html' else '0.8'
        freq = 'weekly' if page in ('index.html', 'blog.html') else 'monthly'
        entries += f'''  <url>
    <loc>{SITE_URL}/{page}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>{freq}</changefreq>
    <priority>{priority}</priority>
  </url>
'''

    # Blog posts
    for p in posts:
        meta = p['meta']
        entries += f'''  <url>
    <loc>{SITE_URL}/blog/{meta.get('slug', 'untitled')}.html</loc>
    <lastmod>{meta.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
'''

    return f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{entries}</urlset>'''


def build_llms_txt():
    """Generate llms.txt for AI crawler optimization (GEO)."""
    return f"""# SystemShift HQ

> SystemShift HQ is an AI automation agency based in High Point, NC that builds custom automation systems, CRM implementations, AI agents, and custom apps for service businesses ready to scale without the busywork.

## Services

- [CRM Build + Management]({SITE_URL}/service-crm.html): Full CRM setup, pipeline automation, and ongoing management
- [Custom AI Solutions]({SITE_URL}/custom-ai-solutions.html): AI agents, chatbots, and intelligent automation
- [AI Voice & Chat Agents]({SITE_URL}/service-voice.html): Conversational AI for phone, chat, and SMS
- [Landing Pages & Funnels]({SITE_URL}/service-funnels.html): High-converting landing pages and sales funnels
- [Social Media Automation]({SITE_URL}/service-social.html): Automated posting, engagement, and analytics
- [LinkedIn Brand Management]({SITE_URL}/service-linkedin.html): Profile optimization, content, and outreach
- [AI + Automation Consulting]({SITE_URL}/service-consulting.html): Strategy sessions and systems audits
- [Integrator Services]({SITE_URL}/service-apps.html): Connect your tech stack with custom integrations
- [App Design & Development]({SITE_URL}/service-app-design.html): Custom business apps, portals, and dashboards
- [Fractional CAO]({SITE_URL}/service-cao.html): On-demand automation leadership
- [GHL Implementation]({SITE_URL}/service-ghl.html): GoHighLevel setup and optimization

## Key Pages

- [Home]({SITE_URL}/): Main landing page
- [Services]({SITE_URL}/services.html): All services overview
- [Blog]({SITE_URL}/blog.html): Insights on automation, AI, and scaling
- [Case Studies]({SITE_URL}/case-studies.html): Real client results
- [About]({SITE_URL}/about.html): Our story and mission
- [Contact]({SITE_URL}/contact.html): Book a free strategy call

## Location

SystemShift HQ is located at 3980 Premier Dr, High Point, NC 27265. We serve businesses across the Triad (Greensboro, Winston-Salem, High Point) and nationwide.

## Contact

- Email: support@systemshifthq.com
- Phone: 336-568-8504
- Book a Call: {SITE_URL}/contact.html
"""


def main():
    # Collect all markdown posts
    posts = []
    md_files = glob.glob(os.path.join(POSTS_DIR, '*.md'))

    for md_path in md_files:
        with open(md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        meta, body = parse_frontmatter(content)
        body_html = md_to_html(body)
        read_time = estimate_read_time(body)

        posts.append({
            'meta': meta,
            'body_html': body_html,
            'read_time': read_time,
            'source': md_path
        })

    # Sort by date descending
    posts.sort(key=lambda p: p['meta'].get('date', ''), reverse=True)

    # Build individual post pages
    for p in posts:
        slug = p['meta'].get('slug', 'untitled')
        html = build_post_html(p['meta'], p['body_html'], p['read_time'])
        out_path = os.path.join(BLOG_OUTPUT_DIR, f'{slug}.html')
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  Built: blog/{slug}.html')

    # Build blog index
    index_html = build_index_html(posts)
    with open(os.path.join(SITE_DIR, 'blog.html'), 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f'  Built: blog.html ({len(posts)} posts)')

    # Collect all static pages for sitemap
    static_pages = sorted([
        f for f in os.listdir(SITE_DIR)
        if f.endswith('.html') and f != 'blog.html' and not f.startswith('components')
    ])
    static_pages.insert(0, 'blog.html')

    # Build sitemap
    sitemap = build_sitemap(posts, static_pages)
    with open(os.path.join(SITE_DIR, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap)
    print(f'  Built: sitemap.xml ({len(static_pages) + len(posts)} URLs)')

    # Build llms.txt
    llms = build_llms_txt()
    with open(os.path.join(SITE_DIR, 'llms.txt'), 'w', encoding='utf-8') as f:
        f.write(llms)
    print(f'  Built: llms.txt')

    # Build robots.txt
    robots = f"""User-agent: *
Allow: /

# AI Crawlers
User-agent: GPTBot
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Bingbot
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
    with open(os.path.join(SITE_DIR, 'robots.txt'), 'w', encoding='utf-8') as f:
        f.write(robots)
    print(f'  Built: robots.txt')

    print(f'\nBlog build complete! {len(posts)} posts processed.')


if __name__ == '__main__':
    main()
