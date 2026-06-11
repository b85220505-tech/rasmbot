# 📸 Takroriy Rasm Topuvchi Telegram Bot

Telegram botini ishga tushirish uchun quyidagi qadamlarni bajaring.

---

## 🚀 O'rnatish

### 1. Bot tokeni olish

1. Telegramda **@BotFather** ga yozing
2. `/newbot` buyrug'ini yuboring
3. Bot nomini kiriting (masalan: `DuplicatePhotoBot`)
4. Username kiriting (masalan: `my_duplicate_photo_bot`)
5. BotFather sizga token beradi — uni saqlang

---

### 2. Kutubxonalarni o'rnatish

```bash
pip install -r requirements.txt
```

---

### 3. Botni ishga tushirish

```bash
# Token o'rnatish
export BOT_TOKEN="sizning_tokeningiz_bu_yerga"

# Botni ishga tushirish
python bot.py
```

**Windows da:**
```cmd
set BOT_TOKEN=sizning_tokeningiz_bu_yerga
python bot.py
```

---

## 🎮 Foydalanish

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Botni qayta ishga tushirish |
| `/stats` | Saqlangan rasmlar soni |
| `/clear` | Barcha rasmlarni tozalash |

### Rasm yuborish
- Oddiy rasm (siqilgan) yuborsa ham topadi
- Fayl sifatida yuborsa ham topadi (Document)

### Natija ko'rinishi
```
⚠️ Takroriy rasm topildi!

🔴 Aynan bir xil — o'xshashlik: ~100%
   📎 Xabar: #42

🟡 Juda o'xshash — o'xshashlik: ~94%
   📎 Xabar: #38
```

---

## 🔍 Qanday ishlaydi?

Bot ikki xil usulda solishtiadi:

1. **Exact Hash (MD5)** — Aynan bir xil fayllarni topadi
2. **Perceptual Hash (pHash)** — O'xshash rasmlarni topadi:
   - Crop qilingan
   - Filtr qo'yilgan
   - Biroz siqilgan
   - Rang o'zgartirilgan

---

## ⚙️ Sozlamalar

`bot.py` faylida `THRESHOLD` qiymatini o'zgartirishingiz mumkin:

```python
THRESHOLD = 10   # Standart: 10
# 0  = faqat aynan bir xillar
# 5  = juda o'xshashlar
# 10 = o'xshashlar (tavsiya etilgan)
# 20 = uzoq o'xshashlar ham
```

---

## ⚠️ Eslatma

Bot rasmlarni xotirada saqlaydi. Bot qayta ishga tushirilsa, barcha ma'lumotlar o'chib ketadi. Doimiy saqlash uchun SQLite yoki boshqa ma'lumotlar bazasi qo'shish kerak bo'ladi.
