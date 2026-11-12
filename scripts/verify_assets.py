"""Verify offline assets, image provenance, UTF-8 and actual Kazakh font glyphs."""
import json
from pathlib import Path
from PIL import Image
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def verify():
    sample = 'Қазақша мәтін: Әдемі ғимарат, жаңа мүмкіндік, оқу және білім. ӘәҒғҚқҢңӨөҰұҮүҺһІі'
    font = TTFont(ROOT / 'static/fonts/NotoSans-Variable.ttf')
    missing = sorted({c for c in sample if ord(c) not in font.getBestCmap()})
    assert not missing, f'Missing glyphs: {missing}'
    font.close()
    folder = ROOT / 'static/images/food'
    manifest = json.loads((folder / 'credits.json').read_text(encoding='utf-8'))
    for filename, info in manifest.items():
        with Image.open(folder / filename) as image:
            image.verify()
        assert info['kind'] in {'representative', 'authentic'}
        assert all(info.get(key) for key in ('credit', 'source', 'license', 'alt', 'changes'))
    for directory in ('app', 'frontend'):
        for path in (ROOT / directory).rglob('*'):
            if path.suffix in {'.py', '.html', '.js', '.css'}:
                text = path.read_text(encoding='utf-8')
                assert '\ufffd' not in text, f'Encoding replacement character: {path}'
    with Image.open(ROOT / 'static/images/logo.jpg') as image:
        image.verify()
    print(f'Kazakh glyphs verified; {len(manifest)} local photographs and logo decoded; source files UTF-8.')


if __name__ == '__main__':
    verify()
