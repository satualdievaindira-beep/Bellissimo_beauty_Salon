# -*- coding: utf-8 -*-
"""
Автотесты сайта. Запуск из папки проекта:  python test_site.py
Проверяют страницы, цены, ссылки и главное: что запись ведёт в WhatsApp
администратора с правильным текстом.
"""
import sys
import unittest
from datetime import date, timedelta
from urllib.parse import parse_qs, unquote, urlparse

import app as site
import data


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.client = site.app.test_client()
        self.day = (date.today() + timedelta(days=3)).isoformat()

    def post_booking(self, **overrides):
        form = {"service": "cuts-0", "day": self.day, "time": "15:00", "name": "Айгуль", "comment": ""}
        form.update(overrides)
        return self.client.post("/book", data=form)

    # --- страницы ---
    def test_pages_open(self):
        for path in ("/", "/robots.txt", "/static/css/style.css", "/static/js/app.js", "/static/img/logo.png"):
            self.assertEqual(self.client.get(path).status_code, 200, path)
        self.assertEqual(self.client.get("/nope").status_code, 404)

    def test_home_has_contacts_and_logo(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertIn("https://2gis.kg/bishkek/geo/15763234351112671", html)
        self.assertIn("+996 550 402 057", html)
        self.assertIn("https://wa.me/996550402057", html)
        self.assertIn("/static/img/logo.png", html)
        self.assertIn("Bellissimo_beauty_kg", html)

    def test_prices_from_price_list(self):
        html = self.client.get("/").get_data(as_text=True)
        for text in ("Женские стрижки", "800 с", "Сложное окрашивание", "4000 с", "Ноги полностью", "1500 с",
                     "Гигиенический педикюр", "700 с", "800-1000 с", "от 200 с"):
            self.assertIn(text, html)
        self.assertGreaterEqual(html.count("Уточняйте цену"), 4)

    def test_every_service_is_in_the_form(self):
        html = self.client.get("/").get_data(as_text=True)
        for service in site.SERVICES:
            self.assertIn(f'value="{service["id"]}"', html)

    def test_service_preselected_from_link(self):
        html = self.client.get("/?service=laser-11").get_data(as_text=True)
        self.assertRegex(html, r'value="laser-11"[^>]*selected')

    # --- запись через WhatsApp ---
    def test_booking_redirects_to_whatsapp(self):
        response = self.post_booking(comment="хочу  светлый   оттенок")
        self.assertEqual(response.status_code, 303)
        link = urlparse(response.headers["Location"])
        self.assertEqual((link.scheme, link.netloc, link.path), ("https", "wa.me", "/996550402057"))
        text = parse_qs(link.query)["text"][0]
        self.assertIn("Bellissimo Beauty Salon", text)
        self.assertIn("Услуга: Женские стрижки (800 с)", text)
        self.assertIn("Дата: " + site.format_date(date.fromisoformat(self.day)), text)
        self.assertIn("Время: 15:00", text)
        self.assertIn("Имя: Айгуль", text)
        self.assertIn("Комментарий: хочу светлый оттенок", text)

    def test_service_without_price_has_no_empty_brackets(self):
        text = parse_qs(urlparse(self.post_booking(service="color-2").headers["Location"]).query)["text"][0]
        self.assertIn("Услуга: Осветление волос маслами\n", text)
        self.assertNotIn("()", text)

    def test_name_is_optional(self):
        text = parse_qs(urlparse(self.post_booking(name="").headers["Location"]).query)["text"][0]
        self.assertNotIn("Имя:", text)

    def test_link_survives_special_characters(self):
        location = self.post_booking(name="Анна & Ко", comment="a=b&c=d #1").headers["Location"]
        self.assertNotIn(" ", location)
        text = parse_qs(urlparse(location).query)["text"][0]
        self.assertIn("Анна & Ко", text)
        self.assertIn("a=b&c=d #1", text)
        self.assertIn("%0A", location)  # переводы строк закодированы

    # --- проверки формы ---
    def test_validation_errors(self):
        cases = [
            ({"service": ""}, "Выберите услугу."),
            ({"service": "hacker-99"}, "Выберите услугу."),
            ({"day": ""}, "Выберите дату."),
            ({"day": "2020-01-01"}, "прошедшую дату"),
            ({"day": (date.today() + timedelta(days=500)).isoformat()}, "дней вперёд"),
            ({"time": ""}, "Выберите время."),
            ({"time": "03:00"}, "Выберите время."),
        ]
        for override, expected in cases:
            response = self.post_booking(**override)
            self.assertEqual(response.status_code, 400, override)
            self.assertIn(expected, response.get_data(as_text=True), override)

    def test_form_keeps_values_after_error(self):
        html = self.post_booking(time="", name="Мадина").get_data(as_text=True)
        self.assertIn('value="Мадина"', html)

    def test_text_is_escaped(self):
        html = self.post_booking(time="", name="<script>alert(1)</script>").get_data(as_text=True)
        self.assertNotIn("<script>alert(1)</script>", html)

    def test_same_message_as_in_javascript(self):
        # JS-превью и серверный текст обязаны совпадать: сверяем ключевые строки
        js = open("static/js/app.js", encoding="utf-8").read()
        for fragment in ("Здравствуйте! Хочу записаться в ", "'Услуга: '", "'Дата: '", "'Время: '",
                         "'Подтвердите, пожалуйста, запись.'"):
            self.assertIn(fragment, js)

    def test_price_list_is_consistent(self):
        ids = [s["id"] for s in site.SERVICES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(site.SERVICES), sum(len(c["items"]) for c in data.CATEGORIES))


if __name__ == "__main__":
    result = unittest.main(exit=False, verbosity=2).result
    sys.exit(0 if result.wasSuccessful() else 1)
