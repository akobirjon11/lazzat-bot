import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

ADMIN_CHAT_ID = config.ADMIN_ID

# ─── Holatlar (FSM) ───────────────────────────────────────────────────────────

class MijozState(StatesGroup):
    mahsulot_tanlash = State()
    miqdor_kiritish = State()
    qayta_tovar_tavsif = State()

# ─── Mahsulotlar ro'yxati ─────────────────────────────────────────────────────

MAHSULOTLAR = [
    "Kichik qaymoq",
    "Katta qaymoq",
    "Ko'k smetana",
    "Sariq 15% smetana",
    "Smetana sariq",
    "Ko'za qaymoq",
    "Kefir kattasi",
    "Kefir maydasi",
    "Chakka",
]

# ─── Klaviaturalar ────────────────────────────────────────────────────────────

def asosiy_menyu_mijoz():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 Buyurtma berish")],
            [KeyboardButton(text="↩️ Qaytarish tovari haqida xabar")],
        ],
        resize_keyboard=True
    )

def asosiy_menyu_yetkazuvchi():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Ertaga kerak mahsulotlarni so'rash")],
        ],
        resize_keyboard=True
    )

def mahsulotlar_klaviatura():
    buttons = []
    for i, m in enumerate(MAHSULOTLAR):
        buttons.append([InlineKeyboardButton(text=m, callback_data=f"mah_{i}")])
    buttons.append([InlineKeyboardButton(text="✅ Buyurtmani yuborish", callback_data="yuborish")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bekor")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def rol_tanlash_klaviatura():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👤 Mijoz"), KeyboardButton(text="🚚 Yetkazib beruvchi")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# ─── Ma'lumotlar (xotira) ─────────────────────────────────────────────────────

foydalanuvchilar = {}
buyurtmalar = {}

# ─── Yordamchi: yetkazuvchilarga xabar yuborish ───────────────────────────────

async def yetkazuvchilarga_yuborish(xabar: str) -> int:
    yuborildi = 0
    try:
        await bot.send_message(ADMIN_CHAT_ID, xabar, parse_mode="HTML")
        yuborildi += 1
    except Exception as e:
        logger.error(f"Adminga yuborishda xato: {e}")
    for uid, info in foydalanuvchilar.items():
        if info["rol"] == "yetkazuvchi" and uid != ADMIN_CHAT_ID:
            try:
                await bot.send_message(uid, xabar, parse_mode="HTML")
                yuborildi += 1
            except Exception as e:
                logger.error(f"Yetkazuvchiga yuborishda xato: {e}")
    return yuborildi

# ─── Start ───────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    ism = message.from_user.first_name
    await message.answer(
        f"🥛 Assalomu alaykum, <b>{ism}</b>!\n\n"
        f"<b>Lazzat M.Ch.J</b> botiga xush kelibsiz!\n\n"
        f"Iltimos, rolingizni tanlang:",
        parse_mode="HTML",
        reply_markup=rol_tanlash_klaviatura()
    )

# ─── Rol tanlash ─────────────────────────────────────────────────────────────

@dp.message(F.text == "👤 Mijoz")
async def mijoz_rol(message: Message, state: FSMContext):
    await state.clear()
    foydalanuvchilar[message.from_user.id] = {"rol": "mijoz", "ism": message.from_user.first_name}
    await message.answer(
        "✅ Siz <b>Mijoz</b> sifatida tanlandingiz.\n\nQuyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=asosiy_menyu_mijoz()
    )

@dp.message(F.text == "🚚 Yetkazib beruvchi")
async def yetkazuvchi_rol(message: Message, state: FSMContext):
    await state.clear()
    foydalanuvchilar[message.from_user.id] = {"rol": "yetkazuvchi", "ism": message.from_user.first_name}
    await message.answer(
        "✅ Siz <b>Yetkazib beruvchi</b> sifatida tanlandingiz.\n\nQuyidagi amallardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=asosiy_menyu_yetkazuvchi()
    )

# ═══════════════════════════════════════════════════════════════════════════════
#   MIJOZ — BUYURTMA
# ═══════════════════════════════════════════════════════════════════════════════

@dp.message(F.text == "🛒 Buyurtma berish")
async def buyurtma_boshlash(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in foydalanuvchilar or foydalanuvchilar[user_id]["rol"] != "mijoz":
        await message.answer("❗ Iltimos, avval /start orqali rolingizni tanlang.")
        return
    buyurtmalar[user_id] = {}
    await state.set_state(MijozState.mahsulot_tanlash)
    await message.answer(
        "📦 <b>Buyurtma berish</b>\n\n"
        "Mahsulotni bosing, keyin miqdorini kiriting.\n"
        "Tugagach <b>✅ Buyurtmani yuborish</b>ni bosing.",
        parse_mode="HTML",
        reply_markup=mahsulotlar_klaviatura()
    )

@dp.callback_query(F.data.startswith("mah_"), MijozState.mahsulot_tanlash)
async def mahsulot_tanlandi(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split("_")[1])
    mahsulot = MAHSULOTLAR[idx]
    await state.update_data(joriy_mahsulot=mahsulot)
    await state.set_state(MijozState.miqdor_kiritish)
    await callback.message.answer(
        f"📝 <b>{mahsulot}</b> uchun miqdorni kiriting:\n<i>(Masalan: 5 dona, 20 ta, 2 kg)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()

@dp.message(MijozState.miqdor_kiritish)
async def miqdor_kiritildi(message: Message, state: FSMContext):
    user_id = message.from_user.id
    miqdor = message.text.strip()
    data = await state.get_data()
    mahsulot = data.get("joriy_mahsulot", "Noma'lum")
    if user_id not in buyurtmalar:
        buyurtmalar[user_id] = {}
    buyurtmalar[user_id][mahsulot] = miqdor
    await state.set_state(MijozState.mahsulot_tanlash)
    savat_text = "🛒 <b>Joriy buyurtma:</b>\n"
    for m, q in buyurtmalar[user_id].items():
        savat_text += f"  • {m} — <b>{q}</b>\n"
    await message.answer(
        f"✅ <b>{mahsulot}</b> qo'shildi: {miqdor}\n\n" + savat_text +
        "\nYana mahsulot tanlang yoki buyurtmani yuboring:",
        parse_mode="HTML",
        reply_markup=mahsulotlar_klaviatura()
    )

@dp.callback_query(F.data == "yuborish", MijozState.mahsulot_tanlash)
async def buyurtma_yuborish(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    ism = foydalanuvchilar.get(user_id, {}).get("ism", "Mijoz")
    if user_id not in buyurtmalar or not buyurtmalar[user_id]:
        await callback.answer("⚠️ Savat bo'sh! Avval mahsulot tanlang.", show_alert=True)
        return
    xabar = (
        f"📦 <b>YANGI BUYURTMA!</b>\n"
        f"👤 Mijoz: <b>{ism}</b>\n"
        f"🆔 ID: {user_id}\n\n"
        f"🛒 <b>Buyurtma:</b>\n"
    )
    for m, q in buyurtmalar[user_id].items():
        xabar += f"  • {m} — <b>{q}</b>\n"
    xabar += "\n⏰ Ertaga yetkazilishi kerak!"
    yuborildi = await yetkazuvchilarga_yuborish(xabar)
    tasdiq = f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n\n📋 <b>Sizning buyurtmangiz:</b>\n"
    for m, q in buyurtmalar[user_id].items():
        tasdiq += f"  • {m} — {q}\n"
    tasdiq += "\n🚚 Yetkazib beruvchiga xabar yuborildi." if yuborildi > 0 else "\n⚠️ Hozircha faol yetkazuvchi yo'q."
    await callback.message.answer(tasdiq, parse_mode="HTML", reply_markup=asosiy_menyu_mijoz())
    buyurtmalar[user_id] = {}
    await state.clear()
    await callback.answer("✅ Yuborildi!")

@dp.callback_query(F.data == "bekor")
async def bekor_qilish(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    buyurtmalar[user_id] = {}
    await state.clear()
    await callback.message.answer("❌ Buyurtma bekor qilindi.", reply_markup=asosiy_menyu_mijoz())
    await callback.answer()

# ═══════════════════════════════════════════════════════════════════════════════
#   MIJOZ — QAYTARISH
# ═══════════════════════════════════════════════════════════════════════════════

@dp.message(F.text == "↩️ Qaytarish tovari haqida xabar")
async def qaytarish_boshlash(message: Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in foydalanuvchilar or foydalanuvchilar[user_id]["rol"] != "mijoz":
        await message.answer("❗ Iltimos, avval /start orqali rolingizni tanlang.")
        return
    await state.set_state(MijozState.qayta_tovar_tavsif)
    await message.answer(
        "↩️ <b>Qaytarish tovari</b>\n\n"
        "Qaytarmoqchi bo'lgan tovar va sabab haqida yozing:\n\n"
        "<i>Namuna: Vazvrat tovar bor 2 ta mayda qaymoq, ertaga almashtiring.</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(MijozState.qayta_tovar_tavsif)
async def qaytarish_xabari(message: Message, state: FSMContext):
    user_id = message.from_user.id
    ism = foydalanuvchilar.get(user_id, {}).get("ism", "Mijoz")
    xabar = (
        f"↩️ <b>QAYTARISH XABARI!</b>\n"
        f"👤 Mijoz: <b>{ism}</b>\n"
        f"🆔 ID: {user_id}\n\n"
        f"📝 <b>Xabar:</b>\n{message.text.strip()}"
    )
    yuborildi = await yetkazuvchilarga_yuborish(xabar)
    tasdiq = "✅ <b>Qaytarish xabaringiz yetkazuvchiga yuborildi!</b>"
    if yuborildi == 0:
        tasdiq = "⚠️ Xabar saqlandi, lekin hozircha faol yetkazuvchi yo'q."
    await message.answer(tasdiq, parse_mode="HTML", reply_markup=asosiy_menyu_mijoz())
    await state.clear()

# ═══════════════════════════════════════════════════════════════════════════════
#   YETKAZIB BERUVCHI
# ═══════════════════════════════════════════════════════════════════════════════

@dp.message(F.text == "📋 Ertaga kerak mahsulotlarni so'rash")
async def sorash_boshlash(message: Message, state: FSMContext):
    user_id = message.from_user.id
    info = foydalanuvchilar.get(user_id)
    if info and info["rol"] != "yetkazuvchi":
        await message.answer("❗ Bu funksiya faqat yetkazuvchilar uchun.")
        return
    ism = foydalanuvchilar.get(user_id, {}).get("ism", "Yetkazuvchi")
    sorov_xabari = (
        f"📋 <b>Yetkazib beruvchidan so'rov!</b>\n\n"
        f"🚚 {ism} so'raydi:\n\n"
        f"<b>Sizga ertaga qanday va qancha mahsulot kerak?</b>\n\n"
        f"<i>🛒 Buyurtma berish tugmasini bosib yuboring.</i>"
    )
    yuborildi = 0
    for uid, inf in foydalanuvchilar.items():
        if inf["rol"] == "mijoz":
            try:
                await bot.send_message(uid, sorov_xabari, parse_mode="HTML")
                yuborildi += 1
            except Exception as e:
                logger.error(f"Mijozga yuborishda xato: {e}")
    if yuborildi > 0:
        await message.answer(
            f"✅ So'rov {yuborildi} ta mijozga yuborildi!\nUlar javob berganida siz ko'rasiz.",
            parse_mode="HTML",
            reply_markup=asosiy_menyu_yetkazuvchi()
        )
    else:
        await message.answer("⚠️ Hozircha ro'yxatdan o'tgan mijoz yo'q.", reply_markup=asosiy_menyu_yetkazuvchi())

# ─── Umumiy xabar ─────────────────────────────────────────────────────────────

@dp.message()
async def umumiy_xabar(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()
    if user_id in foydalanuvchilar and current_state is None:
        rol = foydalanuvchilar[user_id]["rol"]
        if rol == "mijoz":
            await message.answer("Quyidagi amallardan birini tanlang:", reply_markup=asosiy_menyu_mijoz())
        elif rol == "yetkazuvchi":
            await message.answer("Quyidagi amallardan birini tanlang:", reply_markup=asosiy_menyu_yetkazuvchi())
    else:
        await message.answer("👋 Boshlash uchun /start ni bosing.")

# ─── Ishga tushirish ──────────────────────────────────────────────────────────

async def main():
    logger.info("🥛 Lazzat M.Ch.J boti ishga tushmoqda...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
