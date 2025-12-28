# 📚 BookBot - Telegram Kitob Boti

Bu bot orqali siz kitob rasmlarini yuborib, ularni avtomatik ravishda Telegram kanaliga joylashtirishingiz mumkin. Bot OCR texnologiyasi yordamida rasmda yozilgan matnlarni o'qiydi va belgilangan formatda kanalga joylashtiradi.

## ✨ Xususiyatlar

- 📸 **Rasm qayta ishlash**: Kitob rasmlarini qabul qiladi va avtomatik ravishda kanalga joylashtiradi
- 🤖 **Avtomatik formatlash**: Matnlarni belgilangan formatda kanalga joylashtiradi
- 🔄 **Avtomatik qayta joylashtirish**: Belgilangan kunlardan keyin sotilmagan kitoblar avtomatik ravishda qayta joylashtiriladi
- 📅 **Sanaga bo'yicha qayta joylashtirish**: Admin foydalanuvchilar ma'lum sanadan kitoblarni qayta joylashtirishlari mumkin
- 💾 **Ma'lumotlar bazasi**: Barcha postlar SQLite yoki PostgreSQL ma'lumotlar bazasida saqlanadi
- 🚀 **Async operatsiyalar**: Event loop blokiravchi operatsiyalar yo'q, Railway ga optimal
- 🔁 **Intelligent Reposting**: O'chirilgan postlarni qayta joylashtirmaydi, xatoliklarni to'g'ri boshqaradi
- ⏱️ **Rate-limit xavfsizligi**: Telegram rate-limitlarini hurmat qiladi, eksponensial backoff ishlatadi

## 🚀 O'rnatish

### 1. Loyihani klonlash
```bash
git clone <repository-url>
cd telegram-bot
```

### 2. Python paketlarini o'rnatish
```bash
python setup.py
```

Yoki qo'lda:
```bash
pip install -r requirements.txt
```

**Windows (PowerShell)**: run the helper script which creates a `.venv`, installs dependencies, copies `.env` from `env.example` (if missing) and initializes the DB:

```powershell
.\setup_env.ps1
```

See `SETUP_WINDOWS.md` for details.

### 3. .env faylini sozlash

`.env` faylini tahrirlang (env.example-dan nusxa oling):
```env
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_username
ADMIN_IDS=123456789,987654321
REPOST_INTERVAL_DAYS=7
```

### 4. Botni ishga tushirish
```bash
python bookbot.py
```

**Railway-da deployment:**
```bash
railway login
railway link
railway variables set BOT_TOKEN=... CHANNEL_ID=... ADMIN_IDS=...
railway up
```

## 📖 Foydalanish

### Bot buyruqlari:
- `/start` - Botni ishga tushirish
- `/help` - Yordam olish
- `/status` - Bot statusini ko'rish
- `/reposttest` - Qayta joylashtiriladigan postlarni ko'rish (sinov)
- `/repostnow` - Hoziroq qayta joylashtirish tekshirivini boshlash
- `/repost_now dd.mm.yyyy` - **ADMIN**: Ma'lum sanadan kitoblarni qayta joylashtirish (masalan: `/repost_now 11.12.2025`)
- `/addadmin` - Admin foydalanuvchi qo'shish (faqat adminlar uchun)

### Kitob yuborish:
1. Kitob rasmini yuboring
2. Bot avtomatik ravishda matnni o'qiydi
3. Matnni tekshiring va kerak bo'lsa tahrirlang
4. "Kanalga joylashtirish" tugmasini bosing

### Matn formati:
Bot quyidagi formatda matn kutadi (har bir qator alohida):
```
Kitob nomi
Muallif
Betlar soni
Holati
Muqova
Nashr yili
Qo'shimcha ma'lumot
Narx
```

### Kanal post formati:
```
#kitob 
📜Nomi: {kitob_nomi}
👥Muallifi: {muallif}
📖Beti: {betlar_soni}
🕵‍♂Holati: {holati}
📚Muqovasi: {muqova}
🗓Nashr etilgan yili: {yil}
📝Qo'shimcha ma'lumot: {qoshimcha}
🎭Murojaat uchun: @Yollovchi
💰Narxi: {narx} 000 soʻm
```

## 🔧 Sozlash

### Environment variables (.env fayli)
```env
# Majburiy sozlamalar
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_username

# Ixtiyoriy sozlamalar
ADMIN_IDS=123456789,987654321          # Admin foydalanuvchilar (vergul bilan ajratilgan)
REPOST_INTERVAL_DAYS=7                 # Qayta joylashtirish oralig'i kunlarda (standart: 7)
DATABASE_URL=postgresql://...          # PostgreSQL URL (yo'q bo'lsa SQLite ishlatiladi)
```

### Ma'lumotlar bazasi
Bot sukut bo'yicha SQLite ma'lumotlar bazasidan foydalanadi (`bookbot.db`). Railway-da deployment uchun `DATABASE_URL` o'rnatib PostgreSQL-dan foydalanishni tavsiya qilamiz.

**PostgreSQL o'rnatish** (Railway):
```
railway link
# Keyin DATABASE_URL avtomatik o'rnatiladi
```

### Qayta joylashtirish

**Avtomatik qayta joylashtirish:**
- Kitoblar `REPOST_INTERVAL_DAYS` kundan keyin (standart: 7 kun) avtomatik ravishda qayta joylashtiriladi
- Eski post o'chiriladi va yangisi yuboriladi
- O'chirilgan postlar qayta joylashtirilmaydi
- Xatoliklarni to'g'ri boshqaradi va logs-da kayid qiladi

**Qo'lda qayta joylashtirish:**
```
Admin: /repost_now 11.12.2025
Bot: Barcha 2025-12-11 kunida yaratilgan kitoblarni qayta joylashtiradi (Tashkent vaqti)
```

### Xatolik boshqaruvi

**V2.0+ jadavallari:**
- ✅ Media-group xatolari to'g'ri qayd qilinadi (error log ko'rsatiladi, lekin DB ga yozilmaydi)
- ✅ O'chirilgan postlar aniqlaniadi va o'tkazilib yuboriladi
- ✅ Telegram rate-limit-larini hurmat qiladi (eksponensial backoff)
- ✅ Async DB operatsiyalar event loop-ni blokiramaydi

## 📁 Loyiha tuzilishi

```
telegram-bot/
├── bookbot.py          # Asosiy bot fayli
├── config.py           # Sozlash fayli
├── setup.py            # O'rnatish skripti
├── requirements.txt    # Python paketlari
├── README.md          # Hujjat
├── .env               # Muxfiyda saqlanadigan sozlamalar
├── bookbot.db         # Ma'lumotlar bazasi (avtomatik yaratiladi)
└── images/            # Rasm fayllari papkasi
```

## 🛠 Rivojlantirish

### Importing existing channel posts
If you need to reset the database and import existing messages from your channel (e.g., after deleting `bookbot.db`):

- Reset local DB: `python db_manager.py reset` (type `yes` to confirm)
- Import channel messages: set `TELETHON_API_ID`, `TELETHON_API_HASH` and `CHANNEL_ID` in `.env`, then run:

```bash
pip install -r requirements.txt
python import_channel.py
```

Note: Import uses a Telethon MTProto client to read channel history (the Bot API cannot read arbitrary historical messages).


### Xatoliklarni tekshirish
```bash
python -m py_compile bookbot.py
```

### Ma'lumotlar bazasini ko'rish
SQLite ma'lumotlar bazasini ko'rish uchun:
```bash
sqlite3 bookbot.db
.tables
SELECT * FROM posts;
```

## 🐛 V2.0 Xatolik Tuzatishlari va Yaxshilanishlari

### Problem 1: O'chirilgan postlarni qayta joylashtirish
**Muammo**: Bot ba'zida kanaldan o'chirilgan postlarni qayta joylashtirar edi.
**Yechim**: Bot endi o'chirilgan postlarni aniqlaydi va o'tkazib yuboradi (xatolik logli qo'shiladi).

### Problem 2: Media xatoliklari DB-ga yozilmasligi
**Muammo**: Media yuborishdagi xatolik logs-ga ko'rinishiga qaramay DB-da "reposted" sifatida belgilana edi.
**Yechim**: Endi xatoliklarni to'g'ri boshqaradi, faqat muvaffaqiyatli yuborishdagina DB-ga yozadi.

### Problem 3: Sanaga bo'yicha qayta joylashtirish
**Yechim**: `/repost_now dd.mm.yyyy` buyrug'i qo'shildi (Tashkent vaqti). Masalan: `/repost_now 11.12.2025`

### V2.0 Texnik Yaxshilanishlari
- ✅ Async DB wrapper-lar (event loop blokiravchi operatsiyalar yo'q)
- ✅ Telegram rate-limit handling (eksponensial backoff)
- ✅ Specific exception handling (xatoliklar to'liq qayd qilinadi)
- ✅ PostgreSQL qo'llab-quvvatlash (Railway-da cheklangan DB uchun)

## 📝 Litsenziya

Bu loyiha MIT litsenziyasi ostida tarqatiladi.

## 🤝 Hissa qo'shish

1. Loyihani fork qiling
2. Yangi branch yarating (`git checkout -b feature/amazing-feature`)
3. O'zgarishlarni commit qiling (`git commit -m 'Add amazing feature'`)
4. Branch'ni push qiling (`git push origin feature/amazing-feature`)
5. Pull Request yarating

## 📞 Yordam

Agar muammo yuz bersa, issue yarating yoki @Yollovchi ga murojaat qiling.

## 🔄 Yangilanishlar

### v1.0.0
- Asosiy funksionallik
- OCR matn o'qish
- Avtomatik kanalga joylashtirish
- Haftalik qayta joylashtirish
- Ma'lumotlar bazasi
