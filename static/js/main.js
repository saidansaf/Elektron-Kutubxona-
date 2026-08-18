document.addEventListener("DOMContentLoaded", function () {
  // Manzil oxirida "#admin" bo'lsa - maxfiy administrator kirish sahifasi.
  if (window.location.hash === "#admin") {
    window.location.replace("/boshqaruv-panel/kirish/");
    return;
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
      history.replaceState(null, "", window.location.pathname + window.location.search);
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
