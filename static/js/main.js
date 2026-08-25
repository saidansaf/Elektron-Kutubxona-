document.addEventListener("DOMContentLoaded", function () {
  // Manzil oxirida "#admin" bo'lsa - maxfiy administrator kirish sahifasi.
  if (window.location.hash === "#admin") {
    window.location.replace("/boshqaruv-panel/kirish/");
    return;
  }

  // ----------------------------------------------------------------------
  // Sahifadagi joyni eslab qolish
  //
  // Forma yuborilganda (tema, til, yoqtirish, izoh) server sahifani
  // qaytadan ochadi va brauzer uni TEPASIDAN boshlaydi. Foydalanuvchi
  // pastda turgan bo'lsa, o'sha joyga qaytadan aylantirib tushishi kerak
  // edi. Bu yerda joy saqlanadi va sahifa ochilganda tiklanadi.
  //
  // Manzilda langar bo'lsa (#izoh-12) aralashmaymiz — u yerda brauzerning
  // o'zi kerakli joyga tushadi.
  // ----------------------------------------------------------------------
  var SCROLL_KEY = "scroll:" + window.location.pathname;

  var saveScroll = function () {
    try {
      sessionStorage.setItem(
        SCROLL_KEY,
        JSON.stringify({ y: window.scrollY, at: Date.now() })
      );
    } catch (e) {
      // Yopiq rejimda sessionStorage taqiqlangan bo'lishi mumkin - muhim emas.
    }
  };

  document.addEventListener("submit", saveScroll, true);

  var restoreScroll = function () {
    if (window.location.hash) return;
    try {
      var saved = JSON.parse(sessionStorage.getItem(SCROLL_KEY) || "null");
      sessionStorage.removeItem(SCROLL_KEY);
      // 30 soniyadan eski qiymat boshqa tashrifga tegishli bo'lishi mumkin.
      if (saved && saved.y > 0 && Date.now() - saved.at < 30000) {
        window.scrollTo(0, saved.y);
      }
    } catch (e) {
      /* e'tiborsiz qoldiramiz */
    }
  };

  // ----------------------------------------------------------------------
  // Chap menyu (telefonda yon tomondan chiqadi)
  // ----------------------------------------------------------------------
  var sidebar = document.getElementById("sidebar");
  var sidebarToggle = document.getElementById("sidebarToggle");
  var backdrop = document.getElementById("sidebarBackdrop");

  if (sidebar && sidebarToggle && backdrop) {
    var setSidebar = function (open) {
      sidebar.classList.toggle("open", open);
      backdrop.hidden = !open;
      sidebarToggle.setAttribute("aria-expanded", open ? "true" : "false");
    };

    sidebarToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      setSidebar(!sidebar.classList.contains("open"));
    });
    backdrop.addEventListener("click", function () {
      setSidebar(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") setSidebar(false);
    });
  }

  // Profil (avatar) menyusi
  var btn = document.getElementById("avatarBtn");
  var panel = document.getElementById("userMenu");

  if (btn && panel) {
    var setOpen = function (open) {
      panel.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    };

    // Tema yoki til almashtirilgandan keyin server "#menu" langari bilan
    // qaytaradi - menyu yopilib qolmasligi uchun uni qayta ochamiz.
    if (window.location.hash === "#menu") {
      setOpen(true);
      // Langarni darrov olib tashlaymiz, aks holda `restoreScroll` uni
      // "foydalanuvchi aynan shu joyni so'radi" deb tushunadi va joyni
      // tiklamaydi.
      history.replaceState(null, "", window.location.pathname + window.location.search);
      restoreScroll();
    }

    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      setOpen(!panel.classList.contains("open"));
    });

    // Menyu ichidagi bosishlar uni yopmasin
    panel.addEventListener("click", function (e) {
      e.stopPropagation();
    });

    // Tashqariga bosilganda yopiladi
    document.addEventListener("click", function () {
      setOpen(false);
    });

    // Esc bilan yopiladi
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        setOpen(false);
      }
    });
  }

  restoreScroll();

  // "Javob berish" tugmasi - javob formasini ochib/yopadi.
  document.querySelectorAll(".reply-toggle").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var form = document.getElementById(btn.dataset.target);
      if (!form) return;
      form.hidden = !form.hidden;
      if (!form.hidden) {
        var input = form.querySelector("input[type=text]");
        if (input) input.focus();
      }
    });
  });
});
