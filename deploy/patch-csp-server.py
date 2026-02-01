#!/usr/bin/env python3
"""Patch production.py CSP on server: add R2/storage_origin and base.html CDNs."""

path = "/var/www/footycollect-demo/config/settings/production.py"
with open(path) as f:
    content = f.read()

# script-src: add cdn.jsdelivr.net, code.jquery.com, unpkg.com and storage_origin
old1 = """        "script-src": _csp_sources(
            "DJANGO_CSP_SCRIPT_SRC",
            "'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com",
        ),"""
new1 = """        "script-src": _csp_sources(
            "DJANGO_CSP_SCRIPT_SRC",
            "'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net "
            "https://code.jquery.com https://unpkg.com " + storage_origin,
        ),"""

# style-src: add cdn.jsdelivr.net and storage_origin
old2 = """        "style-src": _csp_sources(
            "DJANGO_CSP_STYLE_SRC",
            "'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
        ),"""
new2 = """        "style-src": _csp_sources(
            "DJANGO_CSP_STYLE_SRC",
            "'self' 'unsafe-inline' "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://fonts.googleapis.com " + storage_origin,
        ),"""

# font-src: add data: and cdn.jsdelivr.net and storage_origin
old3 = """        "font-src": _csp_sources(
            "DJANGO_CSP_FONT_SRC",
            "'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com",
        ),"""
new3 = """        "font-src": _csp_sources(
            "DJANGO_CSP_FONT_SRC",
            "'self' data: "
            "https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://fonts.gstatic.com " + storage_origin,
        ),"""

# connect-src: add storage_origin (for R2/fetch)
old4 = '"connect-src": _csp_sources("DJANGO_CSP_CONNECT_SRC", "\'self\'"),'
new4 = '"connect-src": _csp_sources("DJANGO_CSP_CONNECT_SRC", "\'self\' " + storage_origin),'

for old, new in [(old1, new1), (old2, new2), (old3, new3), (old4, new4)]:
    if old in content:
        content = content.replace(old, new, 1)
        print("Patched one directive")
    else:
        print("Pattern not found (may already be patched):", old[:60] + "...")

with open(path, "w") as f:
    f.write(content)
print("Done. Restart gunicorn: systemctl restart footycollect-demo")
