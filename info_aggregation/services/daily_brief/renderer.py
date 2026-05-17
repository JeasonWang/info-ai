"""Render daily brief to Markdown, HTML and plain text."""
import html as html_lib


def render_markdown(brief: dict) -> str:
    """Render brief to Markdown format."""
    parts = [f"# {brief.get('headline', '每日情报简报')}"]
    brief_text = brief.get("brief_text", "")
    if brief_text:
        # Strip duplicate top-level heading if brief_text starts with #
        stripped = brief_text.lstrip()
        if stripped.startswith("# "):
            first_newline = stripped.find(chr(10))
            if first_newline >= 0:
                parts.append(stripped[first_newline + 1:].strip())
            else:
                parts.append("")
        else:
            parts.append(brief_text)
    else:
        for idx, ev in enumerate(brief.get("events", []), 1):
            parts.append(f"{chr(10)}## {idx}. {ev.get('title', '')}{chr(10)}")
            parts.append(f"**判断**: {ev.get('judgment', '')}{chr(10)}")
            parts.append(f"{ev.get('detail', '')}{chr(10)}")
    return chr(10).join(parts)


def render_html(brief: dict) -> str:
    """Render brief to HTML suitable for WeChat public account (inline styles, no external CSS)."""
    headline = html_lib.escape(brief.get("headline", "每日情报简报"))
    events = brief.get("events", [])

    event_items = []
    for idx, ev in enumerate(events, 1):
        title = html_lib.escape(ev.get("title", ""))
        judgment = html_lib.escape(ev.get("judgment", ""))
        detail = html_lib.escape(ev.get("detail", ""))
        event_items.append(
            '<div style="margin-bottom:20px;padding:12px 16px;'
            'background:#f7f8fa;border-radius:8px;">'
            f'<h3 style="margin:0 0 8px 0;font-size:16px;color:#1a1a1a;">'
            f'{idx}. {title}</h3>'
            f'<p style="margin:0 0 6px 0;font-size:14px;color:#1890ff;">'
            f'<strong>判断：</strong>{judgment}</p>'
            f'<p style="margin:0;font-size:14px;color:#333;line-height:1.8;">'
            f'{detail}</p></div>'
        )

    events_html = chr(10).join(event_items)
    return (
        '<div style="max-width:680px;margin:0 auto;font-family:-apple-system,'
        'BlinkMacSystemFont,\'Segoe Wall\',Roboto,\'Helvetica Neue\',Arial,sans-serif;">'
        f'<h1 style="text-align:center;font-size:22px;color:#1a1a1a;'
        f'border-bottom:2px solid #1890ff;padding-bottom:12px;margin-bottom:20px;">'
        f'{headline}</h1>'
        f'{events_html}'
        f'</div>'
    )


def render_text(brief: dict) -> str:
    """Render brief to plain text format."""
    lines = [brief.get("headline", "每日情报简报")]
    lines.append("")
    for idx, ev in enumerate(brief.get("events", []), 1):
        lines.append(f"{idx}. {ev.get('title', '')}")
        lines.append(f"   判断: {ev.get('judgment', '')}")
        lines.append(f"   {ev.get('detail', '')}")
        lines.append("")
    return chr(10).join(lines)