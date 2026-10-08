/* ==========================================================================
   Bellissimo_beauty_kg: интерактив сайта.
   Без этого файла сайт работает: форма записи отправляется обычным способом
   и перекидывает в WhatsApp, а все услуги видны сразу.
   ========================================================================== */
(function () {
  'use strict';

  var html = document.documentElement;
  html.classList.remove('no-js');
  html.classList.add('js');

  /* ----- Меню на телефоне ------------------------------------------------- */
  var toggle = document.querySelector('.nav-toggle');
  var nav = document.getElementById('nav');
  function closeMenu() {
    if (!nav || !toggle) return;
    nav.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  }
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('open');
      toggle.setAttribute('aria-expanded', String(open));
    });
    nav.addEventListener('click', function (e) { if (e.target.closest('a')) closeMenu(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeMenu(); });
  }

  /* ----- Фильтр услуг по направлениям ------------------------------------- */
  var chips = document.querySelectorAll('.chip[data-filter]');
  var blocks = document.querySelectorAll('.price-block');
  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      var key = chip.getAttribute('data-filter');
      chips.forEach(function (c) { c.classList.toggle('active', c === chip); });
      blocks.forEach(function (b) { b.hidden = key !== 'all' && b.getAttribute('data-cat') !== key; });
    });
  });

  /* ----- Форма записи ------------------------------------------------------ */
  var form = document.getElementById('booking-form');
  if (!form) return;

  var service = document.getElementById('service');
  var day = document.getElementById('day');
  var time = document.getElementById('time');
  var nameInput = document.getElementById('name');
  var comment = document.getElementById('comment');
  var preview = document.getElementById('preview');
  var salon = form.getAttribute('data-salon') || '';

  var MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'];
  var WEEKDAYS = ['воскресенье', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота'];

  function formatDate(value) {
    var p = value.split('-');
    if (p.length !== 3) return '';
    var d = new Date(Number(p[0]), Number(p[1]) - 1, Number(p[2]));
    if (isNaN(d.getTime())) return '';
    return d.getDate() + ' ' + MONTHS[d.getMonth()] + ', ' + WEEKDAYS[d.getDay()];
  }

  // Текст сообщения. Формат совпадает с тем, что собирает сервер (app.py, build_message).
  function updatePreview() {
    var opt = service.options[service.selectedIndex];
    if (!service.value && !day.value && !time.value) {
      preview.textContent = 'Выберите услугу, дату и время.';
      return;
    }
    var price = opt && opt.getAttribute('data-price') ? ' (' + opt.getAttribute('data-price') + ')' : '';
    var lines = [
      'Здравствуйте! Хочу записаться в ' + salon + '.',
      'Услуга: ' + (service.value ? opt.getAttribute('data-name') + price : '...'),
      'Дата: ' + (formatDate(day.value) || '...'),
      'Время: ' + (time.value || '...')
    ];
    var n = nameInput.value.trim().replace(/\s+/g, ' ');
    var c = comment.value.trim().replace(/\s+/g, ' ');
    if (n) lines.push('Имя: ' + n);
    if (c) lines.push('Комментарий: ' + c);
    lines.push('Подтвердите, пожалуйста, запись.');
    preview.textContent = lines.join('\n');
  }

  [service, day, time, nameInput, comment].forEach(function (el) {
    el.addEventListener('input', updatePreview);
    el.addEventListener('change', updatePreview);
  });

  // Кнопка "Записаться" у услуги: выбираем услугу и плавно едем к форме
  document.querySelectorAll('.pick[data-service]').forEach(function (link) {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      service.value = link.getAttribute('data-service');
      updatePreview();
      var target = document.getElementById('booking');
      var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      window.setTimeout(function () { (day.value ? time : day).focus({ preventScroll: true }); }, 450);
    });
  });

  // Проверка перед отправкой: подсказываем, чего не хватает
  form.addEventListener('submit', function (e) {
    var problem = '';
    if (!service.value) problem = 'Выберите услугу.';
    else if (!day.value) problem = 'Выберите дату.';
    else if (!time.value) problem = 'Выберите время.';
    if (!problem) return;
    e.preventDefault();
    var box = form.querySelector('.errors');
    if (!box) {
      box = document.createElement('div');
      box.className = 'errors';
      box.setAttribute('role', 'alert');
      form.insertBefore(box, form.firstChild);
    }
    box.textContent = '';
    var p = document.createElement('p');
    p.textContent = problem;
    box.appendChild(p);
    box.scrollIntoView({ behavior: 'smooth', block: 'center' });
  });

  updatePreview();
})();
