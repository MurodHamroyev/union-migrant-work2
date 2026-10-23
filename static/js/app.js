(function () {
  // окна, показать пароль, закрытие
  document.addEventListener('click', function (e) {
    var o = e.target.closest('[data-open]');
    if (o) { var d = document.getElementById(o.dataset.open); if (d) d.showModal(); return; }
    if (e.target.closest('[data-close]')) { e.target.closest('dialog').close(); return; }
    var eye = e.target.closest('[data-eye]');
    if (eye) {
      var i = eye.parentElement.querySelector('input'), show = i.type === 'password';
      i.type = show ? 'text' : 'password'; eye.classList.toggle('on', show); return;
    }
    if (e.target.tagName === 'DIALOG') {
      var r = e.target.getBoundingClientRect();
      if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) e.target.close();
    }
    document.querySelectorAll('details.lang[open]').forEach(function (d) { if (!d.contains(e.target)) d.open = false; });
  });

  // имя выбранного файла
  document.addEventListener('change', function (e) {
    var i = e.target;
    if (!i.matches || !i.matches('input[type=file][data-fname]')) return;
    var l = i.closest('.drop').querySelector('.fname');
    l.textContent = i.files.length > 1 ? i.files.length + ' files' : (i.files[0] ? i.files[0].name : '');
  });

  // выбор страны и код телефона
  var hid = document.getElementById('country');
  if (hid) {
    var list = document.getElementById('clist'), flag = document.getElementById('cflag'),
        name = document.getElementById('cname'), dial = document.getElementById('dial');
    var pick = function (b) {
      hid.value = b.dataset.iso; flag.textContent = b.dataset.flag;
      name.textContent = b.dataset.name; dial.textContent = b.dataset.dial;
    };
    pick(list.querySelector('[data-iso="' + hid.value + '"]') || list.querySelector('button'));
    list.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      pick(b); document.getElementById('cdlg').close();
    });
    document.getElementById('csearch').addEventListener('input', function (e) {
      var q = e.target.value.toLowerCase();
      list.querySelectorAll('li').forEach(function (li) { li.hidden = li.textContent.toLowerCase().indexOf(q) < 0; });
    });
  }

  // проверка возраста 18+ при вводе даты рождения
  var bd = document.getElementById('birth');
  if (bd) {
    var warn = document.getElementById('agewarn'), btn = document.getElementById('regbtn');
    var check = function () {
      if (!bd.value) { warn.hidden = true; btn.disabled = false; return; }
      var b = new Date(bd.value), t = new Date(), a = t.getFullYear() - b.getFullYear(), m = t.getMonth() - b.getMonth();
      if (m < 0 || (m === 0 && t.getDate() < b.getDate())) a--;
      warn.hidden = a >= 18; btn.disabled = a < 18;
    };
    bd.addEventListener('input', check); check();
  }

  // обратный отсчёт 10 часов между отметками смены
  document.querySelectorAll('[data-countdown]').forEach(function (el) {
    var s = parseInt(el.dataset.countdown, 10), f = function (n) { return String(n).padStart(2, '0'); };
    var tick = function () {
      if (s <= 0) { location.reload(); return; }
      el.textContent = f(Math.floor(s / 3600)) + ':' + f(Math.floor(s % 3600 / 60)) + ':' + f(s % 60); s--;
    };
    tick(); setInterval(tick, 1000);
  });
})();
