""" HTML layout for the e-mails sent by notify_mobiles

    A plain module, not an app. Do not add it to apps.yaml.

    Use:  from email_template import render_email
          html, text = render_email('Dryer', 'The dryer is finished.', level='info')

    All text is escaped. No images, no web fonts, no external requests.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.0"

import html as _html
import re
from string import Template
from typing import Dict, Optional, Tuple

# Credit line in the footer. Change name, link or wording here.
AUTHOR_NAME = 'Automagisk Hus'
AUTHOR_URL = 'https://automagisk-hus.no'
FOOTER_TEXT = {
    'en': 'Sent by your smart home. Apps by {author}.',
    'no': 'Sendt fra smarthuset ditt. Apper fra {author}.',
}

FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

# Neutral stone base with a deep teal accent. Warning and alert are status tones
# of the same muted strength. Every text colour is at least 4.5:1 on its background.
PALETTE = {
    'light': {
        'page': '#f2f1ee',
        'card': '#ffffff',
        'border': '#e2e0db',
        'text': '#1d2125',
        'muted': '#5b6066',
        'link': '#0b6660',
        'info': '#0f6e68',
        'warning': '#9a5b00',
        'alert': '#b42318',
    },
    'dark': {
        'page': '#121416',
        'card': '#1c1f22',
        'border': '#2e3236',
        'text': '#e7e5e0',
        'muted': '#a4a9ae',
        'link': '#6ccbc0',
        'info': '#5cc2b7',
        'warning': '#e3a948',
        'alert': '#f07b70',
    },
}

# Level mark: the character and shape carry the meaning, not only the colour.
LEVELS = {
    'info': {'glyph': 'i', 'radius': '50%', 'filled': False},
    'warning': {'glyph': '!', 'radius': '4px', 'filled': False},
    'alert': {'glyph': '!', 'radius': '4px', 'filled': True},
}

PREHEADER_LENGTH = 110

_HTML = Template("""<!DOCTYPE html>
<html lang="$lang">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="x-apple-disable-message-reformatting">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>$title_text</title>
<style>
:root{color-scheme:light dark;supported-color-schemes:light dark}
body{margin:0;padding:0;-webkit-text-size-adjust:100%;text-size-adjust:100%}
@media (max-width:480px){.em-outer{padding:16px 8px !important}.em-pad{padding:24px 20px 28px !important}}
@media (prefers-color-scheme:dark){
.em-page{background-color:$d_page !important}
.em-card{background-color:$d_card !important;border-color:$d_border !important}
.em-text{color:$d_text !important}
.em-muted{color:$d_muted !important}
.em-link{color:$d_link !important}
.em-bar{background-color:$d_accent !important}
.em-mark{color:$d_accent !important;border-color:$d_accent !important}
.em-mark-fill{background-color:$d_accent !important;border-color:$d_accent !important;color:$d_card !important}
}
</style>
<!--[if mso]><style>body,table,td,h1,p,a{font-family:'Segoe UI',Arial,sans-serif !important}</style><![endif]-->
</head>
<body class="em-page" style="margin:0;padding:0;background-color:$page;">
<div style="display:none;max-height:0;max-width:0;overflow:hidden;opacity:0;mso-hide:all;font-size:1px;line-height:1px;color:$page;">$preheader$preheader_spacer</div>
<table role="presentation" class="em-page" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;background-color:$page;">
<tr><td class="em-outer" align="center" style="padding:32px 16px;">
<!--[if mso]><table role="presentation" width="560" align="center" cellpadding="0" cellspacing="0" border="0"><tr><td><![endif]-->
<table role="presentation" class="em-card" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:560px;background-color:$card;border:1px solid $border;border-radius:12px;border-collapse:separate;">
<tr><td class="em-bar" height="4" style="height:4px;line-height:4px;font-size:4px;background-color:$accent;border-radius:11px 11px 0 0;">&nbsp;</td></tr>
<tr><td class="em-pad" align="left" style="padding:28px 32px 32px;text-align:left;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="width:100%;">
<tr><td width="36" valign="top" aria-hidden="true" style="width:36px;padding-top:2px;">$mark</td>
<td valign="top"><h1 class="em-text" style="margin:0;font-family:$font;font-size:22px;line-height:28px;font-weight:600;color:$text;">$title</h1></td></tr>
</table>
$body</td></tr>
</table>
<!--[if mso]></td></tr></table><![endif]-->
$footer</td></tr>
</table>
</body>
</html>
""")

_MARK = Template(
    '<table role="presentation" aria-hidden="true" cellpadding="0" cellspacing="0" border="0"><tr>'
    '<td class="$css_class" align="center" valign="middle" width="20" height="20" '
    'style="width:20px;height:20px;border:2px solid $accent;border-radius:$radius;${fill}'
    'font-family:$font;font-size:13px;line-height:20px;font-weight:700;text-align:center;">$glyph</td>'
    '</tr></table>'
)

_PARAGRAPH = Template(
    '<p class="em-text" style="margin:16px 0 0;font-family:$font;font-size:16px;line-height:24px;'
    'color:$text;overflow-wrap:break-word;word-wrap:break-word;">$content</p>\n'
)

_FOOTER = Template(
    '<p class="em-muted" style="margin:20px 0 0;padding:0 16px;font-family:$font;font-size:13px;'
    'line-height:20px;color:$muted;text-align:center;">$before'
    '<a class="em-link" href="$url" style="color:$link;text-decoration:underline;">$author</a>$after</p>\n'
)

# Keeps mail clients from filling the inbox preview with the rest of the mail.
_PREHEADER_SPACER = '&#847;&zwnj;&nbsp;' * 30

_LANG_RE = re.compile(r'[A-Za-z]{2,3}(-[A-Za-z0-9]{1,8})*$')


def _escape(text: str) -> str:
    return _html.escape(text, quote=True)


def _palette(theme: Optional[Dict[str, Dict[str, str]]]) -> Dict[str, Dict[str, str]]:
    colours = {mode: dict(values) for mode, values in PALETTE.items()}
    for mode, values in (theme or {}).items():
        if mode in colours and isinstance(values, dict):
            colours[mode].update(values)
    return colours


def _paragraphs(message: str):
    """Split the message into paragraphs on blank lines, each a list of lines."""
    lines = message.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    paragraphs, current = [], []
    for line in lines:
        line = line.rstrip()
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(current)
            current = []
    if current:
        paragraphs.append(current)
    return paragraphs


def _footer_parts(lang: str) -> Tuple[str, str]:
    language = lang.lower().split('-')[0]
    if language in ('nb', 'nn'):
        language = 'no'
    before, _, after = FOOTER_TEXT.get(language, FOOTER_TEXT['en']).partition('{author}')
    return before, after


def _preheader(message: str) -> str:
    text = ' '.join(message.split())
    if len(text) <= PREHEADER_LENGTH:
        return text
    cut = text[:PREHEADER_LENGTH].rsplit(' ', 1)[0]
    return cut.rstrip(' ,.;:') + '…'


def render_email(title, message, *, level: str = 'info', footer: bool = True, lang: str = 'en',
                 preheader: Optional[str] = None,
                 theme: Optional[Dict[str, Dict[str, str]]] = None) -> Tuple[str, str]:
    """Return ``(html, plain_text)`` for a short notification e-mail.

    Parameters
    ----------
    title : str
        Shown as the heading.
    message : str
        One or more lines. A newline is a line break, a blank line starts a new paragraph.
    level : str
        ``info``, ``warning`` or ``alert``. Changes the accent bar and the mark. Unknown values give ``info``.
    footer : bool
        Show the credit line at the bottom.
    lang : str
        Language code for the ``lang`` attribute and the footer wording.
    preheader : str, optional
        Inbox preview text. Defaults to the start of the message.
    theme : dict, optional
        ``{'light': {...}, 'dark': {...}}`` with colours that replace those in ``PALETTE``.
    """
    title = '' if title is None else str(title).strip()
    message = '' if message is None else str(message).strip()
    lang = str(lang) if lang and _LANG_RE.match(str(lang)) else 'en'
    level_name = str(level).lower()
    if level_name not in LEVELS:
        level_name = 'info'
    level_style = LEVELS[level_name]
    colours = _palette(theme)
    light, dark = colours['light'], colours['dark']
    accent = light[level_name]

    if level_style['filled']:
        mark_class = 'em-mark-fill'
        fill = f"background-color:{accent};color:{light['card']};"
    else:
        mark_class = 'em-mark'
        fill = f"color:{accent};"
    mark = _MARK.substitute(
        css_class=mark_class, accent=accent, radius=level_style['radius'], fill=fill,
        font=FONT_STACK, glyph=level_style['glyph'],
    )

    paragraphs = _paragraphs(message)
    body = ''.join(
        _PARAGRAPH.substitute(
            font=FONT_STACK, text=light['text'],
            content='<br>\n'.join(_escape(line) for line in lines),
        )
        for lines in paragraphs
    )

    footer_html = ''
    footer_plain = ''
    if footer:
        before, after = _footer_parts(lang)
        footer_html = _FOOTER.substitute(
            font=FONT_STACK, muted=light['muted'], link=light['link'],
            before=_escape(before), after=_escape(after),
            url=_escape(AUTHOR_URL), author=_escape(AUTHOR_NAME),
        )
        footer_plain = f"{before}{AUTHOR_NAME} ({AUTHOR_URL}){after}"

    if preheader is None:
        preheader = _preheader(message)

    html = _HTML.substitute(
        lang=lang,
        title_text=_escape(title),
        title=_escape(title),
        preheader=_escape(str(preheader)),
        preheader_spacer=_PREHEADER_SPACER,
        mark=mark,
        body=body,
        footer=footer_html,
        font=FONT_STACK,
        accent=accent,
        d_accent=dark[level_name],
        page=light['page'], card=light['card'], border=light['border'], text=light['text'],
        d_page=dark['page'], d_card=dark['card'], d_border=dark['border'], d_text=dark['text'],
        d_muted=dark['muted'], d_link=dark['link'],
    )

    plain_parts = [title]
    if paragraphs:
        plain_parts.append('\n\n'.join('\n'.join(lines) for lines in paragraphs))
    if footer_plain:
        plain_parts.append(footer_plain)
    plain = '\n\n'.join(part for part in plain_parts if part) + '\n'
    return html, plain
