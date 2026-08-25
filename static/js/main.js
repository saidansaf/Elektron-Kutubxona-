// Brauzer o'zi tiklaydigan joyni o'chiramiz — biz o'zimiz boshqaramiz.
if ("scrollRestoration" in history) {
  history.scrollRestoration = "manual";
}

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
        // `behavior: "instant"` majburiy: CSS'da `scroll-behavior: smooth`
        // turibdi va usiz sahifa tepadan pastga sirg'alib tushardi —
        // foydalanuvchiga bu "sayt sekin" bo'lib ko'rinadi.
        window.scrollTo({ top: saved.y, left: 0, behavior: "instant" });
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


  // ----------------------------------------------------------------------
  // AI yordamchi: yon oyna
  //
  // Ilgari tugma alohida sahifaga olib borardi va foydalanuvchi turgan
  // joyini yo'qotardi. Endi suhbat shu sahifaning ustida ochiladi.
  // ----------------------------------------------------------------------
  var aiFab = document.getElementById("aiFab");
  var aiPanel = document.getElementById("aiPanel");

  if (aiFab && aiPanel) {
    var aiBody = document.getElementById("aiPanelBody");
    var aiForm = document.getElementById("aiPanelForm");
    var aiInput = document.getElementById("aiPanelInput");
    var aiClose = document.getElementById("aiPanelClose");
    var aiSendBtn = aiForm.querySelector("button[type=submit]");

    var aiOpen = function (open) {
      aiPanel.hidden = !open;
      aiFab.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) aiInput.focus();
    };

    var aiAdd = function (text, kind) {
      var el = document.createElement("div");
      el.className = "ai-msg " + kind;
      el.textContent = text;
      aiBody.appendChild(el);
      aiBody.scrollTop = aiBody.scrollHeight;
      return el;
    };

    var aiTyping = function () {
      var el = document.createElement("div");
      el.className = "ai-msg bot";
      el.innerHTML = '<span class="ai-typing"><i></i><i></i><i></i></span>';
      aiBody.appendChild(el);
      aiBody.scrollTop = aiBody.scrollHeight;
      return el;
    };

    aiFab.addEventListener("click", function () {
      aiOpen(aiPanel.hidden);
    });
    aiClose.addEventListener("click", function () {
      aiOpen(false);
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !aiPanel.hidden) aiOpen(false);
    });

    aiForm.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = aiInput.value.trim();
      if (!text) return;

      aiAdd(text, "me");
      aiInput.value = "";
      aiSendBtn.disabled = true;
      var waiting = aiTyping();

      var token = aiForm.querySelector("[name=csrfmiddlewaretoken]").value;

      fetch(aiForm.dataset.sendUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": token },
        body: JSON.stringify({ message: text })
      })
        .then(function (r) {
          return r.json().then(function (data) {
            return { ok: r.ok, data: data };
          });
        })
        .then(function (res) {
          waiting.remove();
          if (res.ok && res.data.answer) {
            aiAdd(res.data.answer, "bot");
          } else {
            aiAdd(res.data.error || aiForm.dataset.error, "error");
          }
        })
        .catch(function () {
          waiting.remove();
          aiAdd(aiForm.dataset.error, "error");
        })
        .finally(function () {
          aiSendBtn.disabled = false;
          aiInput.focus();
        });
    });
  }

  // ----------------------------------------------------------------------
  // Sahifalarni oldindan yuklash — ATAYLAB OLIB TASHLANGAN
  //
  // Bu yerda "sichqoncha havolaga tekkanda sahifani oldindan yuklab
  // qo'yamiz" degan kod turgan edi. Kuchli serverda u sahifani darrov
  // ochilgandek qiladi. Bizniki esa Render'ning bepul tarifida ishlaydi:
  // atigi 0.1 protsessor va bitta ishchi.
  //
  // Natija teskari bo'ldi. Sichqonchani chap menyu ustidan bir marta
  // yurgizish 8-10 ta HAQIQIY sahifa so'rovini tug'dirardi — server
  // ularning hammasini chizishga majbur bo'lardi va foydalanuvchi
  // haqiqatan bosgan havola navbatning oxirida qolardi. Ya'ni tezlashtirish
  // uchun qo'shilgan narsa saytni o'zi sekinlashtirardi.
  //
  // Xulosa: kuchsiz serverda kerak bo'lmagan so'rov yubormaslik eng yaxshi
  // optimallashtirishdir. Shuning uchun bu kod qaytarilmaydi.
  // ----------------------------------------------------------------------

  // ----------------------------------------------------------------------
  // Ilova qilib o'rnatish (PWA)
  //
  // Brauzer saytni telefon ekraniga yorliq qilib qo'yishi mumkin. U holda
  // sayt oddiy ilovadek — o'z belgisi bilan, manzil satrisiz — ochiladi.
  // Play Market kerak emas, pul to'lanmaydi.
  //
  // Brauzer o'rnatish mumkinligini o'zi bildiradi (`beforeinstallprompt`).
  // Shu paytgacha tugma yashirin turadi: bosilganda hech narsa
  // bo'lmaydigan tugmadan ko'ra ko'rinmagani afzal.
  // ----------------------------------------------------------------------
  if ("serviceWorker" in navigator) {
    // Sahifa to'liq yuklangach ro'yxatdan o'tkazamiz — birinchi ochilishni
    // sekinlashtirmasin.
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () {
        // O'rnatish imkoni bo'lmasa sayt oddiy holicha ishlayveradi.
      });
    });
  }

  var installBtn = document.getElementById("installBtn");
  var installHelp = document.getElementById("installHelp");
  var installEvent = null;

  window.addEventListener("beforeinstallprompt", function (e) {
    // Brauzerning o'z taklifini to'xtatamiz - uni tugma bosilganda
    // o'zimiz ochamiz.
    e.preventDefault();
    installEvent = e;
  });

  if (installBtn) {
    installBtn.addEventListener("click", function () {
      if (installEvent) {
        installEvent.prompt();
        installEvent.userChoice.finally(function () {
          // Taklifni ikkinchi marta ishlatib bo'lmaydi.
          installEvent = null;
        });
        return;
      }
      // Safari va Firefox bunday taklif bermaydi - qo'lda o'rnatish
      // yo'riqnomasini ko'rsatamiz.
      if (installHelp) installHelp.hidden = false;
    });
  }

  if (installHelp) {
    var closeHelp = function () {
      installHelp.hidden = true;
    };
    document.getElementById("installHelpClose").addEventListener("click", closeHelp);
    installHelp.addEventListener("click", function (e) {
      if (e.target === installHelp) closeHelp();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeHelp();
    });
  }

  // O'rnatilgach tugma keraksiz.
  window.addEventListener("appinstalled", function () {
    installEvent = null;
    if (installBtn) installBtn.hidden = true;
  });

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
