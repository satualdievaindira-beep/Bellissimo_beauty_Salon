#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bellissimo_beauty_kg: сайт салона Bellissimo Beauty Salon (Бишкек).

Что умеет:
  * показывает услуги и цены из прайс-листа (файл data.py)
  * онлайн-запись: клиент выбирает услугу, дату и время, нажимает кнопку,
    и его перекидывает в WhatsApp администратора с готовым сообщением
  * кнопка "Мы на карте" ведёт на точку салона в 2ГИС

Запуск:
    pip install flask
    python app.py
Откройте http://127.0.0.1:5000
"""

import os
from datetime import date, datetime, timedelta
from urllib.parse import quote

from flask import Flask, Response, redirect, render_template, request

import data

# ---------------------------------------------------------------------------
# НАСТРОЙКИ: контакты и ссылки меняются здесь
# ---------------------------------------------------------------------------
SITE_NAME = "Bellissimo_beauty_kg"
SALON_NAME = "Bellissimo Beauty Salon"
CITY = "Бишкек"

# Ссылка на логотип. Если оставить пустой, берётся файл static/img/logo.png
LOGO_URL = ""

# Точка салона в 2ГИС
MAP_URL = "https://2gis.kg/bishkek/geo/15763234351112671"

# WhatsApp администратора: цифры с кодом страны, без плюса и пробелов
WHATSAPP_DIGITS = "996550402057"
WHATSAPP_DISPLAY = "+996 550 402 057"

# Какое время предлагать клиенту в форме записи (в минутах от полуночи).
# Значения примерные: поставьте реальные часы работы салона.
SLOT_START = 10 * 60
SLOT_END = 20 * 60
SLOT_STEP = 30

BOOK_DAYS_AHEAD = 60  # на сколько дней вперёд можно записаться

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
          "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

app = Flask(__name__)

SERVICES = data.all_services()
SERVICES_BY_ID = {s["id"]: s for s in SERVICES}


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------
def time_options():
    """Список времён для выпадающего списка: '10:00', '10:30', ..."""
    return [f"{m // 60:02d}:{m % 60:02d}" for m in range(SLOT_START, SLOT_END + 1, SLOT_STEP)]


def format_date(d):
    """15 октября, среда"""
    return f"{d.day} {MONTHS[d.month - 1]}, {WEEKDAYS[d.weekday()]}"


def clean(text, limit):
    return " ".join((text or "").split())[:limit]


def build_message(service, day, time_str, name="", comment=""):
    """Текст, который клиент отправит администратору в WhatsApp."""
    price = f" ({service['price']})" if service["price"] else ""
    lines = [
        f"Здравствуйте! Хочу записаться в {SALON_NAME}.",
        f"Услуга: {service['name']}{price}",
        f"Дата: {format_date(day)}",
        f"Время: {time_str}",
    ]
    if name:
        lines.append(f"Имя: {name}")
    if comment:
        lines.append(f"Комментарий: {comment}")
    lines.append("Подтвердите, пожалуйста, запись.")
    return "\n".join(lines)


def whatsapp_link(text=""):
    base = f"https://wa.me/{WHATSAPP_DIGITS}"
    return f"{base}?text={quote(text)}" if text else base


def validate_booking(form):
    """Проверяет форму записи. Возвращает (данные, список ошибок)."""
    errors = []
    service = SERVICES_BY_ID.get(form.get("service", ""))
    if not service:
        errors.append("Выберите услугу.")

    day = None
    try:
        day = date.fromisoformat(form.get("day", ""))
    except ValueError:
        errors.append("Выберите дату.")
    else:
        today = date.today()
        if day < today:
            errors.append("Нельзя записаться на прошедшую дату.")
        elif day > today + timedelta(days=BOOK_DAYS_AHEAD):
            errors.append(f"Запись открыта на {BOOK_DAYS_AHEAD} дней вперёд.")

    time_str = form.get("time", "")
    if time_str not in time_options():
        errors.append("Выберите время.")
    elif day == date.today():
        hour, minute = map(int, time_str.split(":"))
        if datetime.combine(day, datetime.min.time()) + timedelta(hours=hour, minutes=minute) < datetime.now():
            errors.append("Это время уже прошло. Выберите более позднее.")

    return {"service": service, "day": day, "time": time_str}, errors


@app.context_processor
def inject_globals():
    return {
        "site_name": SITE_NAME,
        "salon_name": SALON_NAME,
        "city": CITY,
        "map_url": MAP_URL,
        "logo_url": LOGO_URL or "/static/img/logo.png",
        "wa_display": WHATSAPP_DISPLAY,
        "wa_link": whatsapp_link(f"Здравствуйте! Хочу уточнить по услугам {SALON_NAME}."),
        "tel_link": "tel:+" + WHATSAPP_DIGITS,
    }


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "same-origin"
    # form-action намеренно не ограничиваем: после записи форма перекидывает в WhatsApp
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data: https:; "
        "connect-src 'self'; frame-ancestors 'none'"
    )
    return resp


# ---------------------------------------------------------------------------
# Страницы
# ---------------------------------------------------------------------------
def render_home(form=None, errors=None, status=200):
    today = date.today()
    form = form or {"service": request.args.get("service", ""), "day": "", "time": "", "name": "", "comment": ""}
    return render_template(
        "index.html",
        categories=data.CATEGORIES,
        services=SERVICES,
        times=time_options(),
        form=form,
        errors=errors or [],
        min_day=today.isoformat(),
        max_day=(today + timedelta(days=BOOK_DAYS_AHEAD)).isoformat(),
    ), status


@app.route("/")
def index():
    return render_home()


@app.route("/book", methods=["POST"])
def book():
    """Принимает форму записи и перекидывает клиента в WhatsApp с готовым сообщением."""
    form = {
        "service": request.form.get("service", ""),
        "day": request.form.get("day", ""),
        "time": request.form.get("time", ""),
        "name": clean(request.form.get("name"), 60),
        "comment": clean(request.form.get("comment"), 200),
    }
    booking, errors = validate_booking(form)
    if errors:
        return render_home(form, errors, 400)
    message = build_message(booking["service"], booking["day"], booking["time"], form["name"], form["comment"])
    return redirect(whatsapp_link(message), code=303)


@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nAllow: /\n", mimetype="text/plain")


@app.errorhandler(404)
def not_found(_err):
    return render_template("error.html", code=404, title="Страница не найдена",
                           text="Такой страницы нет. Вернитесь на главную."), 404


@app.errorhandler(500)
def server_error(_err):
    return render_template("error.html", code=500, title="Ошибка на нашей стороне",
                           text="Попробуйте обновить страницу через минуту."), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")
