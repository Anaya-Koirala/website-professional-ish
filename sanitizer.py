import re

import nh3

# Block high-risk JS constructs
_DANGEROUS_JS = re.compile(
    r"(?<!\w)(eval\s*\(|new\s+Function\s*\(|document\.write\s*\(|document\.writeln\s*\(|document\.cookie)",
    re.IGNORECASE,
)

# Remove inline on* handlers from non-script tags
_ON_ATTR_RE = re.compile(
    r"\s+on\w+\s*=\s*(?:\"[^\"]*\"|'[^']*'|[^>\s]+)", re.IGNORECASE
)

ALLOWED_TAGS = set(nh3.ALLOWED_TAGS) | {
    "video",
    "audio",
    "source",
    "iframe",
    "canvas",
    "font",
    "center",
}

ALLOWED_ATTRS = {
    "*": {"class", "id", "style"},
    "a": {"href", "title", "target", "rel"},
    "img": {"src", "alt", "width", "height", "style"},
    "iframe": {
        "src",
        "width",
        "height",
        "frameborder",
        "allowfullscreen",
        "sandbox",
        "style",
    },
    "audio": {
        "src",
        "controls",
        "autoplay",
        "loop",
        "muted",
        "style",
    },
    "video": {
        "src",
        "controls",
        "width",
        "height",
        "autoplay",
        "muted",
        "loop",
        "style",
        "crossorigin",
    },
    "source": {"src", "type"},
    "canvas": {"width", "height", "id", "style"},
    "font": {"style"},
    "center": {"style"},
}


# Strip on* attributes from non-script tags
def _remove_inline_handlers(html_text: str) -> str:
    def repl(m):
        tag = m.group(1)
        attrs = m.group(2) or ""
        cleaned = _ON_ATTR_RE.sub("", attrs)
        return f"<{tag}{cleaned}>"

    return re.sub(
        r"<(?!script\b)([a-zA-Z0-9]+)\b([^>]*)>", repl, html_text, flags=re.IGNORECASE
    )


# Replace javascript: URLs with a safe placeholder.
def _strip_js_protocols(html_text: str) -> str:
    return re.sub(
        r'(?i)(href|src)\s*=\s*["\']?\s*javascript:',
        r'\1="#" data-blocked="true"',
        html_text,
    )


"""Sanitize HTML while preserving and post-processing <script>, <style>, and <canvas>.
Strategy:
1. Extract <style>, <canvas>, and <script> blocks and replace them with placeholders.
2. Run nh3.clean on the remainder (avoid custom tag sets to prevent panics).
3. Post-process cleaned HTML: remove inline handlers, strip javascript: URLs.
4. Re-insert sanitized <style>, <canvas>, and <script> blocks.
"""


def sanitize(raw_html: str) -> str:
    # 1) Extract <style> blocks
    style_pattern = re.compile(
        r"(<style\b[^>]*>)(.*?)</style>", re.IGNORECASE | re.DOTALL
    )
    styles = []  # list of (open_tag, body)

    def _extract_style(m):
        open_tag = m.group(1)
        body = m.group(2)
        idx = len(styles)
        styles.append((open_tag, body))
        return f"__NH3_STYLE_PLACEHOLDER_{idx}__"

    interim = style_pattern.sub(_extract_style, raw_html)

    # 1b) Extract <canvas> blocks from interim (preserve content and attrs)
    canvas_pattern = re.compile(
        r"(<canvas\b[^>]*>)(.*?)</canvas>", re.IGNORECASE | re.DOTALL
    )
    canvases = []  # list of (open_tag, body)

    def _extract_canvas(m):
        open_tag = m.group(1)
        body = m.group(2)
        idx = len(canvases)
        canvases.append((open_tag, body))
        return f"__NH3_CANVAS_PLACEHOLDER_{idx}__"

    interim2 = canvas_pattern.sub(_extract_canvas, interim)

    # 1c) Extract <script> blocks from interim2
    script_pattern = re.compile(
        r"(<script\b[^>]*>)(.*?)</script>", re.IGNORECASE | re.DOTALL
    )
    scripts = []  # list of (open_tag, body)

    def _extract_script(m):
        open_tag = m.group(1)
        body = m.group(2)
        idx = len(scripts)
        scripts.append((open_tag, body))
        return f"__NH3_SCRIPT_PLACEHOLDER_{idx}__"

    placeholder_html = script_pattern.sub(_extract_script, interim2)

    # 2) Clean the placeholder html with nh3. Pass attribute whitelist (no tags)
    # to preserve IDs/styles while avoiding tag conflicts. Fall back to simple
    # clean() if nh3 raises.
    try:
        cleaned = nh3.clean(
            placeholder_html,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRS,
            strip_comments=True,
            link_rel=None,
        )
    except Exception:
        try:
            cleaned = nh3.clean(placeholder_html)
        except Exception:
            cleaned = ""

    # 3) Remove inline handlers and javascript: protocols
    cleaned = _remove_inline_handlers(cleaned)
    cleaned = _strip_js_protocols(cleaned)

    # helper to sanitize style bodies (block @import and javascript: urls)
    _DANGEROUS_CSS = re.compile(
        r"@import\s+[^;]+;|url\s*\(\s*['\"]?\s*javascript:[^)]+\)", re.IGNORECASE
    )

    # 4) Re-insert styles first
    for i, (open_tag, body) in enumerate(styles):
        m = re.match(r"<style\b([^>]*)>", open_tag, re.IGNORECASE)
        attrs = m.group(1) if m else ""
        # remove on* handlers in attrs (unlikely on <style>) and strip js: in attrs
        attrs = _ON_ATTR_RE.sub("", attrs)
        attrs = re.sub(
            r'(?i)(src|href)\s*=\s*["\']?\s*javascript:',
            r'\1="#" data-blocked="true"',
            attrs,
        )

        safe_body = _DANGEROUS_CSS.sub("/* [blocked] */", body or "")
        style_tag = f"<style{attrs}>{safe_body}</style>"
        placeholder = f"__NH3_STYLE_PLACEHOLDER_{i}__"
        cleaned = cleaned.replace(placeholder, style_tag)

    # 4b) Re-insert canvases
    for i, (open_tag, body) in enumerate(canvases):
        m = re.match(r"<canvas\b([^>]*)>", open_tag, re.IGNORECASE)
        attrs = m.group(1) if m else ""
        # remove inline handlers and strip js: in attrs
        attrs = _ON_ATTR_RE.sub("", attrs)
        attrs = re.sub(
            r'(?i)(src|href)\s*=\s*["\']?\s*javascript:',
            r'\1="#" data-blocked="true"',
            attrs,
        )

        # canvas body preserved
        canvas_tag = f"<canvas{attrs}>{body or ''}</canvas>"
        placeholder = f"__NH3_CANVAS_PLACEHOLDER_{i}__"
        cleaned = cleaned.replace(placeholder, canvas_tag)

    # 4c) Re-insert scripts
    for i, (open_tag, body) in enumerate(scripts):
        m = re.match(r"<script\b([^>]*)>", open_tag, re.IGNORECASE)
        attrs = m.group(1) if m else ""
        attrs = _ON_ATTR_RE.sub("", attrs)
        attrs = re.sub(
            r'(?i)(src|href)\s*=\s*["\']?\s*javascript:',
            r'\1="#" data-blocked="true"',
            attrs,
        )

        safe_body = _DANGEROUS_JS.sub("/* [blocked] */", body or "")
        script_tag = f"<script{attrs}>{safe_body}</script>"
        placeholder = f"__NH3_SCRIPT_PLACEHOLDER_{i}__"
        cleaned = cleaned.replace(placeholder, script_tag)
    return cleaned

print(
    sanitize("""""")
)