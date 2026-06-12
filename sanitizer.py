import nh3

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
    "*": {"class",  "style"},
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
    "table": {"style", "border"},
    "tr": {"style"},
    "td": {"style"},
    "th": {"style"},
    "tbody": {"style"},
}

def sanitize(raw_html: str) -> str:
    cleaned = nh3.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip_comments=True,
        link_rel="noopener noreferrer",
        url_schemes={"http", "https"},
    )
    return cleaned