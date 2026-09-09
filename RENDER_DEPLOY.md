# Render.com'ga deploy qilish (Flask webhook rejimi)

Bot endi **Flask webhook** orqali ishlaydi: aiogram polling o'rniga,
Telegram yangiliklari (update) `/webhook/<secret>` manziliga POST
so'rov sifatida keladi va Flask uni qabul qiladi. Bot logikasi
(handler'lar, middleware'lar, baza) o'zgarishsiz qoldi — faqat update
qabul qilish usuli o'zgardi.

## Nima o'zgardi

- `main.py` — endi `flask_app` nomli Flask ilova eksport qiladi.
  - `GET /health` — health-check
  - `POST /webhook/<WEBHOOK_SECRET_PATH>` — Telegram yangiliklari shu yerga keladi
  - aiogram dispatcher/bot fon (background) thread'dagi asosiy event loop'da ishlaydi
- `Dockerfile` / `container_entrypoint.py` — `python main.py` o'rniga
  `gunicorn ... main:flask_app` bilan ishga tushadi.
- `services/http/health_server.py` olib tashlandi — endi kerak emas
  (uning vazifasini `main.py`dagi Flask app bajaradi).

**MUHIM: `gunicorn --workers 1`.** Bot holati (aiogram Bot, Dispatcher,
DB engine, event loop) modul darajasida bitta marta yaratiladi. Agar
worker soni 1 dan ko'p bo'lsa, har bir worker o'z nusxasini yaratadi va
Telegram webhook'ni faqat bittasiga yuboradi — qolganlari ishlamay
qoladi yoki DB ulanishlari ikki marta ochiladi. Shuning uchun
`--workers 1 --threads 8` ishlatilgan (bitta process, ko'p thread —
Flask so'rovlarni parallel qabul qiladi, aiogram esa o'z event loop'ida
ishlaydi).

## 1-usul: Blueprint orqali (tavsiya etiladi)

1. Kodni GitHub/GitLab repo'ga push qiling (`render.yaml` bilan birga).
2. Render dashboard → **New** → **Blueprint** → repo'ni tanlang.
3. Quyidagilar avtomatik yaratiladi:
   - `downloader-bot` — Web Service (Docker, gunicorn)
   - `downloader-bot-db` — PostgreSQL 17
4. Deploy paytida qo'lda kiritish so'raladigan qiymatlar
   (`sync: false`):
   - `BOT_TOKEN`
   - `ADMIN_ID`
   - `CUSTOM_API_URL`
   - `WEBHOOK_URL` — **birinchi deploy'da bo'sh qoldiring** (pastga qarang)
5. `WEBHOOK_SECRET_PATH` va `WEBHOOK_SECRET_TOKEN` Render tomonidan
   avtomatik generatsiya qilinadi (`generateValue: true`) — qo'lda
   kiritish shart emas.
6. **Create New Resources** tugmasini bosing va birinchi deploy
   tugashini kuting.

### WEBHOOK_URL'ni sozlash (ikkinchi qadam, majburiy)

Render domenini oldindan bilib bo'lmaydi, shuning uchun ikki bosqichli:

1. Birinchi deploy tugagach, Render sizga xizmat manzilini beradi:
   `https://downloader-bot-xxxx.onrender.com`
2. Shu manzilni **to'liq nusxalab**, Environment sozlamalarida
   `WEBHOOK_URL` qiymatiga joylashtiring (oxirida `/` bo'lmasin).
3. **Manual Deploy → Deploy latest commit** yoki shunchaki "Save
   Changes" qiling — bot qayta ishga tushib, Telegram'ga to'g'ri
   webhook manzilini ro'yxatdan o'tkazadi.
4. Loglarda `webhook_set` va `webhook_mode_ready` event'larini
   qidiring — bular webhook muvaffaqiyatli o'rnatilganini bildiradi.

Agar `WEBHOOK_URL` bo'sh qolsa, bot ishga tushadi lekin Telegram
webhook'ni ro'yxatdan o'tkazmaydi (`webhook_url_missing` logi chiqadi)
va hech qanday xabar kelmaydi.

## 2-usul: Qo'lda (Blueprint ishlatmasdan)

1. Render dashboard → **New** → **Web Service** → repo'ni ulang →
   **Runtime: Docker**.
2. **Health Check Path**: `/health`
3. Environment → majburiy o'zgaruvchilar:

   | Key | Qiymat |
   |---|---|
   | `BOT_TOKEN` | BotFather tokeningiz |
   | `ADMIN_ID` | Sizning Telegram user ID |
   | `CUSTOM_API_URL` | Bot API server manzili |
   | `DATABASE_URL` | Postgres connection string |
   | `HTTP_HEALTH_HOST` | `0.0.0.0` |
   | `HTTP_HEALTH_PORT` | `8080` |
   | `PORT` | `8080` |
   | `WEBHOOK_SECRET_PATH` | o'zingiz generatsiya qiling (masalan `openssl rand -hex 20`) |
   | `WEBHOOK_SECRET_TOKEN` | o'zingiz generatsiya qiling |
   | `WEBHOOK_URL` | birinchi deploy'dan keyin Render bergan manzil |

4. Alohida **PostgreSQL** instance yarating, uning **Internal
   Connection String**'ini `DATABASE_URL`ga qo'ying.
5. Birinchi deploy'dan keyin `WEBHOOK_URL`ni to'ldirib, qayta deploy
   qiling (yuqoridagi izohga qarang).

## Ixtiyoriy environment o'zgaruvchilar

- `MEASUREMENT_ID`, `API_SECRET` — Google Analytics (GA4)
- `CHANNEL_ID` — majburiy obuna kanali
- `COBALT_API_URL`, `COBALT_API_KEY` — Cobalt media API (https va
  public IP talab qilinadi, kod tekshiradi)
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_MARKET`

## Webhookni tekshirish

Deploy'dan keyin brauzerda yoki curl bilan:

```
https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo
```

`"url"` maydonida sizning Render manzilingiz + `/webhook/...` ko'rinishi
kerak, `"last_error_message"` bo'sh bo'lishi kerak.

## Muhim eslatmalar

- **Disk**: `/app/downloads` uchun 1GB disk ulangan (`plan: starter`
  kerak, chunki Free tarif diskni qo'llab-quvvatlamaydi). Kerak
  bo'lmasa `render.yaml`dan `disk:` blokini olib tashlang.
- **Bitta instance**: `Number of Instances = 1` bo'lishi shart —
  bir nechta instance bo'lsa, har biri Telegram webhook'ni bir-biridan
  qayta yozib, tasodifiy ishlamay qolishi mumkin.
- Agar avval polling rejimida ishlatgan bo'lsangiz va eski webhook
  qoldiqlari bo'lsa, bot ishga tushganda avtomatik ravishda yangi
  webhook bilan almashtiradi (`drop_pending_updates=True`).
