# 📚 BookBot - Telegram Kitob Boti

Bu bot orqali siz kitob rasmlarini yuborib, ularni avtomatik ravishda Telegram kanaliga joylashtirishingiz mumkin. Bot OCR texnologiyasi yordamida rasmda yozilgan matnlarni o'qiydi va belgilangan formatda kanalga joylashtiradi.

## ✨ Xususiyatlar

- 📸 **Rasm qayta ishlash**: Kitob rasmlarini qabul qiladi va OCR yordamida matn o'qiydi
- 🤖 **Avtomatik formatlash**: Matnlarni belgilangan formatda kanalga joylashtiradi
- 🔄 **Avtomatik qayta joylashtirish**: 1 hafta ichida sotilmagan kitoblar avtomatik ravishda qayta joylashtiriladi
- 💾 **Ma'lumotlar bazasi**: Barcha postlar SQLite ma'lumotlar bazasida saqlanadi
- ✏️ **Qo'lda tahrirlash**: OCR natijalarini qo'lda tahrirlash imkoniyati

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

### 3. Tesseract OCR o'rnatish

#### Windows:
1. [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) ni yuklab oling
2. Standart joyga o'rnating: `C:\Program Files\Tesseract-OCR\`
3. O'zbek tili paketini yuklab oling (ixtiyoriy)

#### Linux:
```bash
sudo apt-get install tesseract-ocr tesseract-ocr-uzb
```

#### macOS:
```bash
brew install tesseract tesseract-lang
```

### 4. Bot token va kanal ID ni o'rnatish

`.env` faylini tahrirlang:
```env
BOT_TOKEN=your_bot_token_here
CHANNEL_ID=@your_channel_username
TESSERACT_PATH=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 5. Botni ishga tushirish
```bash
python bookbot.py
```

## 📖 Foydalanish

### Bot buyruqlari:
- `/start` - Botni ishga tushirish
- `/help` - Yordam olish

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

### Ma'lumotlar bazasi
Bot SQLite ma'lumotlar bazasidan foydalanadi (`bookbot.db`). Barcha postlar va ularning holati saqlanadi.

### Qayta joylashtirish
- Kitoblar 1 hafta (7 kun) dan keyin avtomatik ravishda qayta joylashtiriladi
- Eski post o'chiriladi va yangisi yuboriladi
- Qayta joylashtirish sanasi ma'lumotlar bazasida saqlanadi

### Rasm saqlash
Barcha rasm fayllar `images/` papkasida saqlanadi.

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
