from itertools import count
from datetime import datetime, timezone
from app.menu import MENU

class Store:
    def __init__(self):
        self.lost = {}
        self.skills = {}
        self.requests = {}
        self.confessions = {}
        self.likes = set()
        self.ids = count(1)
        self.food = {}
        self.food_ids = count(10011)
        # Separate seed IDs preserve the existing modules' ID sequence.
        for index, (name, price, description, canteen, category, slug) in enumerate(MENU, 10001):
            self.food[index] = {
                'id': index, 'name': name, 'description': description, 'price': price,
                'currency': 'KZT', 'category': category, 'canteen': canteen,
                'image_url': f'/static/images/food/{slug}.svg', 'available': True,
                'created_at': datetime.now(timezone.utc), 'image_kind': 'placeholder',
                'image_alt': f'{name} — photo unavailable / Фото жоқ',
                'image_credit': '', 'image_source': '',
            }
        # Prefer supplied menu photos; retain SVG placeholders when unavailable.
        import json
        from pathlib import Path
        folder = Path(__file__).resolve().parent.parent / 'static/images/food'
        manifest = folder / 'credits.json'
        credits = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
        for item in self.food.values():
            filename = item['image_url'].rsplit('/', 1)[-1].replace('.svg', '.jpg')
            if filename in credits and (folder / filename).is_file():
                info = credits[filename]
                item.update(image_url='/static/images/food/' + filename,
                            image_kind=info['kind'], image_alt=info['alt'],
                            image_credit=info['credit'], image_source=info['source'])

    def new_id(self):
        return next(self.ids)

store = Store()
