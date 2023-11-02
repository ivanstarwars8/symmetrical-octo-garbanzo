from datetime import datetime, timedelta
from typing import Optional
import os

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from tgbot.db.db_api import subs, trial, files

from tgbot.services.get_trial_image import get_trial_image_filename

from tgbot.keyboards.inline import (
    support_keyboard,
    settings_keyboard,
)
from tgbot.keyboards.reply import choose_plan_keyboard

trial_router = Router()


@trial_router.message(F.text.in_({"Тариф 'Trial' ⏱ (Пробный период на 1 день)"}))
async def process_pay(query: Message):
    user_id: int = query.from_user.id
    date: datetime = datetime.now()

    sub: Optional[dict] = await subs.find_one(
        filter={"user_id": user_id, "end_date": {"$gt": date}}
    )

    if sub:
        sub_flag = sub.get("client_id")
        if len(sub_flag) > 10:
            await query.answer(
                text="Извините! Вы уже воспользовались пробным периодом 😪"
                "Акция доступна только один раз",
                reply_markup=choose_plan_keyboard,
            )
        else:
            await query.answer(
                text="✅ Вы уже оформили подписку\n"
                "Акция доступна только новым пользователям",
                reply_markup=choose_plan_keyboard,
            )
    else:
        image_filename = ""
        client_id = ""
        pk = ""

        async for image in get_trial_image_filename():
            image_filename = image
            break

        try:
            pk = image_filename.split("/")[2].split(".")[0]
            client_id = "Client_№" + pk + "_(trial)"

        except Exception as e:
            print(e)

        if not os.path.exists(image_filename):
            await query.answer(
                text="Извините! Лимит на бесплатные подписки закончился 😪\n"
                "Ждите анонса новой акции в наших соц сетях 🙈",
                reply_markup=support_keyboard,
            )
        else:
            end_date = date + timedelta(days=2)

            await trial.insert_one(
                {
                    "user_id": user_id,
                    "trial_flag": "on",
                    "start_date": date,
                    "end_date": end_date,
                }
            )

            await subs.insert_one(
                document={
                    "user_id": user_id,
                    "start_date": date,
                    "end_date": end_date,
                    "client_id": client_id,
                }
            )

            image_from_pc = FSInputFile(image_filename)

            end_date_str: str = end_date.strftime("%d.%m.%Y")

            result = await query.answer_photo(
                photo=image_from_pc,
                caption=f"✅  Подписка успешно оформлена!!! \n\n\n"
                f"Ваш QR - код для подключения ⤴️ \n\n"
                f"<b>Срок действия пробного периода:</b> до {end_date_str}\n\n"
                f"Перейдите в меню настроек для подключения",
                reply_markup=settings_keyboard,
            )

            await files.insert_one(
                {"user_id": user_id, "photo_id": result.photo[-1].file_id, "pk": pk}
            )

            os.remove(image_filename)
