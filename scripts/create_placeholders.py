"""Create explicit, original SVG placeholders; never masquerade as photographs."""
from html import escape
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.menu import MENU


def make_placeholder(name):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="440" viewBox="0 0 720 440">
<rect width="720" height="440" fill="#edf2ec"/>
<circle cx="360" cy="165" r="65" fill="none" stroke="#b5c8b4" stroke-width="6"/>
<path d="M325 165h70m-35-35v70" stroke="#729076" stroke-width="5"/>
<text x="360" y="280" text-anchor="middle" fill="#355840" font-family="sans-serif" font-size="25">{escape(name)}</text>
<text x="360" y="325" text-anchor="middle" fill="#617664" font-family="sans-serif" font-size="20">Фото жоқ · Photo unavailable</text>
</svg>'''


if __name__ == '__main__':
    folder = ROOT / 'static/images/food'
    folder.mkdir(parents=True, exist_ok=True)
    for name, _, _, _, _, slug in MENU:
        (folder / f'{slug}.svg').write_text(make_placeholder(name), encoding='utf-8')
    (folder / 'placeholder.svg').write_text(make_placeholder('BIRGE · Däm'), encoding='utf-8')
