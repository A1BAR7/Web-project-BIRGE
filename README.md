# BIRGE — SDU student community

HTML/CSS/JavaScript frontend with a FastAPI backend. Lost & Found, Däm,
SkillQos and Ishimде use PostgreSQL through SQLAlchemy. The API is available
in Swagger, and the frontend requires no build step. Source files use UTF-8.

## Installation and startup

### Quick start on Windows

With Python 3.12 or a current Python 3.10/3.11 patch release installed, double-click
`start.bat`. It creates `.venv` if needed, checks dependencies, runs migrations,
starts the API, and opens the site. The first run without a configured
`DATABASE_URL` downloads PostgreSQL for Windows x64 and initializes a local
database on `127.0.0.1:55432`. Keep `.birge-local/` to retain this database.
Closing the window stops the API. The local PostgreSQL process stays available
for the next launch. A `DATABASE_URL` in the environment or `.env` uses your
existing database instead. Run `start.bat --no-browser` to start from a terminal
without opening a browser. If port 8000 is busy, the launcher chooses a free port
and prints the URLs for the site and Swagger.

### Manual setup

Use Python 3.10+ and a running PostgreSQL server. In `psql`, connect as a
PostgreSQL administrator and create a local role and database:

```sql
CREATE ROLE birge LOGIN;
\password birge
CREATE DATABASE birge OWNER birge;
```

From the project directory:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set `DATABASE_URL` in `.env` to
`postgresql+psycopg://birge:<password>@localhost:5432/birge`. URL-encode
reserved characters in the password. A `DATABASE_URL` set in the environment
takes precedence over `.env`.

```powershell
.venv\Scripts\python -m alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --reload
```

On macOS/Linux use `.venv/bin/python` instead of `.venv\Scripts\python`.
Use `cp .env.example .env` to create the local environment file.

Run `alembic upgrade head` after pulling schema changes. The initial migration
creates all tables and inserts the ten original menu items with their existing
IDs and photo credits. Subsequent edits and deletions persist across restarts.

- Website: http://127.0.0.1:8000/app/
- Swagger UI: http://127.0.0.1:8000/docs
- OpenAPI: http://127.0.0.1:8000/openapi.json

Open the website through FastAPI. Local file/Live Server previews still target
`http://127.0.0.1:8000` for API calls. Fonts and menu images are bundled; startup
does not download assets. Swagger retains its standard CDN-based UI.

## Lost & Found

Existing JSON CRUD and resolve endpoints at `/lost-items` are preserved.
Responses include `images: [{id, url}]`. Announcements without photos return an
empty list.

- `POST /lost-items/{item_id}/images?actor_id=101`: multipart form with repeated
  `files` fields; returns the updated announcement with **201**.
- `DELETE /lost-items/{item_id}/images/{image_id}?actor_id=101`: **204**.
- Deleting an announcement also removes its uploaded images.

Five images per announcement, each at most **5 × 1024 × 1024 bytes**. JPG/JPEG,
PNG and WebP are supported. Pillow verifies and decodes content; extension and
MIME must match. Invalid formats/content/counts return **422**, oversized files
**413**, ownership violations **403**, missing records/images **404**, and disk
failures **500** with a retry message. A 20-megapixel limit bounds decoding memory.
Batches validate before writing; failed writes remove their new files. UUID
filenames ignore user paths. Files live in `uploads/lost_items/`, served from
`/uploads/lost_items/`.

The frontend provides drag/drop, selection, previews, removal before upload,
image counters, validation/loading, galleries, enlarged previews, adding photos
to existing announcements, and confirmation before owner deletions.

## Däm

| Method | Path | Result |
| --- | --- | --- |
| GET | `/food` | List/filter, 200/422 |
| GET | `/food/{food_id}` | Details, 200/404 |
| POST | `/food` | Create, 201/422 |
| PATCH | `/food/{food_id}` | Partial update, 200/404/422 |
| DELETE | `/food/{food_id}` | Delete, 204/404 |

Combine `canteen`, `category`, `search`, `min_price` and `max_price`. Canteen and
category match case-insensitively; search matches the food name. Price bounds
are inclusive and nonnegative; reversed bounds return 422. Example:

```text
/food?canteen=Injoo&category=Main%20Course&search=лағман&max_price=1600
```

Fields: `id`, `name`, `description`, positive finite `price`, `currency` (`KZT`),
`category`, `canteen`, `image_url`, `available`, UTC `created_at`, plus
`image_kind`, `image_alt`, `image_credit`, `image_source` for provenance.
PATCH supports availability changes. Explicit nulls, unknown fields and empty
or whitespace names/categories/canteens are rejected. Image URLs reference
existing local `/static/images/food/` assets. Shared menu assets are retained
when a food record is deleted or its image changes. Duplicate names are allowed;
no artificial uniqueness/409 business rule was introduced. Existing resolve,
like and SkillQos conflicts retain their 409 responses.

`app/menu.py` contains exactly the ten supplied dishes, portions, prices and
canteens. No extra two dishes were invented. Extend this list and provide image
assets/provenance when additional dishes are supplied. Frontend cards fetch
from `/food`, with API search/filtering, local price sorting, availability,
details, loading skeletons, empty/error/retry states and clear filters.

## Existing workflows and storage

SkillQos retains creation, filtering, applications and owner accept/reject.
Ishimде retains anonymous posts and like/unlike. Create a skill with owner 202
in Swagger and apply on the website as actor 101. For owner decisions, create a
request to a skill owned by 101 and use its button on the site.

The frontend uses **demo actor 101**. Actor/owner IDs preserve the existing
ownership model; they are not secure authentication. Food management is also
unauthenticated; an admin/login system was outside the requested scope.

PostgreSQL persists announcements, image metadata, skills, applications,
confessions, likes and menu items. Announcements own images, skills own
applications, and confessions own likes. Foreign keys cascade row deletion,
and database constraints enforce one pending application per applicant per skill
and one like per user per confession. Actor IDs remain numeric demo identifiers.

Back up the database and `uploads/lost_items/` together. Workers serving the same
database must share that upload directory. Upload files and database metadata
use separate storage, so an interruption during a file operation can require
reconciliation. Assignment 5 kept announcements in memory, so there are no
stored announcement rows to import from that version.

## Typography and images

Local variable **Noto Sans** with Cyrillic Extended is primary, with Segoe UI,
Arial and system sans-serif fallbacks. It applies to navigation, cards, forms,
controls and dialogs. The actual TTF character map was checked against:

> Қазақша мәтін: Әдемі ғимарат, жаңа мүмкіндік, оқу және білім.
> Ә ә, Ғ ғ, Қ қ, Ң ң, Ө ө, Ұ ұ, Ү ү, Һ һ, І і.

Its SIL Open Font License is in `static/fonts/OFL.txt`.

Ten photographs supplied in `Photo/` are copied unchanged to local JPG assets.
The user confirmed matching by filename despite differences in pictured contents,
advertised prices, and portions. Menu data remains unchanged; the UI explains this.
`Photo/Logo.jpg` is used in the sidebar, page header and favicon, with preserved proportions.

| Menu dish | Supplied source |
| --- | --- |
| Супер комбо 3 | супер комбо3.jpg |
| Комбо 2 | комбо2.jpg |
| Пицца Маргарита | маргарита.jpg |
| Пицца Пепперони | пепперони.jpg |
| Пиде тауық етімен | пиде.jpg |
| Хот-дог | хот-дог.jpg |
| Капсалон | капсолон.jpg |
| Гуйру лағман | гуйру.jpg |
| Суйру лағман | Суйру.jpg |
| Сет SDU | сет SDU.jpg |

All ten dishes have a supplied photo. Cards use a responsive 4:3 cover with
`object-fit: cover`; an unavailable image falls back to a labeled placeholder.
Sources are recorded in `static/images/food/credits.json`. Older representative
WebP assets remain available for API compatibility with their original attribution.
Do not run `scripts/fetch_assets.py` to replace this supplied-photo manifest.

## Automated verification

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
.venv\Scripts\python scripts/verify_assets.py
```

By default, tests run Alembic against temporary SQLite files with foreign keys
enabled. To run the same API suite against PostgreSQL, set `TEST_DATABASE_URL`
to a dedicated test database using the same URL format as `DATABASE_URL`.
The test role needs permission to create schemas. Tests create and drop a
temporary schema per test and use temporary directories for uploads.

### Test the frontend manually

1. Open `/app/`, select Däm, and confirm ten cards with the correct menu,
   prices, canteens and corresponding supplied photos.
2. Combine canteen/category/search, sort both ways, clear filters, and inspect
   details. Search for an unmatched word to see the empty state. Stop the API,
   reload, then restart and use Retry to check the error state.
3. Create a Lost & Found post with two images through selection or drag/drop.
   Remove a preview, publish, open details, enlarge a photo, add photos, and
   delete one with confirmation. Delete the post; its image URLs should return
   404. Try an invalid type, a >5 MB file and more than five images.
4. Test SkillQos/Ishimде using the workflows above. Use Tab/Enter and Escape;
   verify focus indicators, modal focus trapping/return and dialog dismissal.
5. Inspect at 390 px, 760 px and desktop widths in light/dark mode. All navigation
   sections remain available on mobile. Check wrapping, controls, dialogs and
   Kazakh text. Verify Noto Sans loads using the browser's font inspector.

### Test Swagger manually

1. Open `/docs`; run `GET /food` and combined filters, then food POST/PATCH/DELETE.
   Use price 0 for 422 and a missing ID for 404.
2. Create `/lost-items` with owner 101. In its multipart image upload operation,
   enter the ID and actor 101, select files, and execute. Inspect returned URLs.
   Use actor 202 for 403. Delete images and the announcement as owner 101.
3. Verify `/skills` and `/confessions` still work. Check `/openapi.json` includes
   the food schemas and multipart upload operation.
