"""One-time asset preparation. Downloads are checked in; startup never needs network."""
import json
import sys
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.dev-deps'))
from PIL import Image
from fontTools.ttLib import TTFont


def download(url):
    with urlopen(Request(url, headers={'User-Agent': 'BIRGE-student-project/1.1 (asset preparation)'}), timeout=40) as response:
        return response.read()


def main():
    fonts = ROOT / 'static/fonts'
    fonts.mkdir(parents=True, exist_ok=True)
    font_path = fonts / 'NotoSans-Variable.ttf'
    font_path.write_bytes(download('https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/NotoSans%5Bwdth,wght%5D.ttf'))
    (fonts / 'OFL.txt').write_bytes(download('https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/OFL.txt'))
    font = TTFont(font_path)
    sample = 'Қазақша мәтін: Әдемі ғимарат, жаңа мүмкіндік, оқу және білім. ӘәҒғҚқҢңӨөҰұҮүҺһІі'
    assert all(ord(c) in font.getBestCmap() for c in sample), 'Kazakh glyph missing'
    print('Verified all requested Kazakh glyphs in downloaded Noto Sans')
    font.flavor = 'woff2'
    try:
        font.save(fonts / 'NotoSans-Variable.woff2')
    except ImportError:
        pass  # TTF remains the fully verified offline source.

    images = ROOT / 'static/images/food'
    credits = {}
    # Source/license verified on the Commons file page; image stays representative.
    photos = [('Pepperoni pizza.jpg', 'pizza-pepperoni.webp',
               'Jon Sullivan / PDPhoto.org — public domain (CC0)',
               'Representative homemade pepperoni pizza; not a canteen photograph', 'zero/1.0'),
              ('Pizza margherita.png', 'pizza-margherita.webp', 'RanZag — public domain',
               'Representative Margherita pizza; not a canteen photograph', 'zero/1.0'),
              ('Hot dog.jpg', 'hot-dog.webp', 'tednmiki — CC BY-SA 3.0',
               'Representative hot dog with ketchup and mayonnaise; not a canteen photograph', 'by-sa/3.0'),
              ('Kapsalon.jpg', 'kapsalon.webp', 'Incase design; white balance by Takeaway — CC BY 2.0',
               'Representative kapsalon with fries, meat and salad; not a canteen photograph', 'by/2.0')]
    for title, filename, credit, alt, license_slug in photos:
        source = 'https://commons.wikimedia.org/wiki/File:' + quote(title.replace(' ', '_'))
        # File path is the documented Wikimedia MD5-based upload path.
        import hashlib
        normalized = title.replace(' ', '_')
        digest = hashlib.md5(normalized.encode()).hexdigest()
        url = f'https://upload.wikimedia.org/wikipedia/commons/{digest[0]}/{digest[:2]}/{quote(normalized)}'
        try:
            image = Image.open(BytesIO(download(url))).convert('RGB')
            image.thumbnail((960, 720))
            image.save(images / filename, 'WEBP', quality=82, method=6)
            credits[filename] = {'kind': 'representative', 'credit': credit, 'alt': alt,
                                 'source': source, 'license': ('https://creativecommons.org/publicdomain/' if license_slug.startswith('zero') else 'https://creativecommons.org/licenses/') + license_slug + '/',
                                 'changes': 'Resized to at most 960 × 720; converted to WebP'}
            print('Saved', filename)
        except Exception as error:
            print('Photo unavailable; retain explicit placeholder:', title, str(error))
    (images / 'credits.json').write_text(json.dumps(credits, indent=2, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
