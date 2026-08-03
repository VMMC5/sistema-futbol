// Comportamiento del panel. Va en un archivo externo (no inline) porque la CSP
// es estricta: script-src 'self' bloquea los manejadores inline (onchange,
// onsubmit). Aquí se enlazan por data-atributos.
document.addEventListener("DOMContentLoaded", function () {
  // Filtros que se envían solos al cambiar el <select> (antes: onchange="this.form.submit()").
  document.querySelectorAll("select[data-autosubmit]").forEach(function (sel) {
    sel.addEventListener("change", function () {
      if (sel.form) sel.form.submit();
    });
  });

  // Formularios que piden confirmación antes de enviarse (antes: onsubmit="return confirm(...)").
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (evento) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        evento.preventDefault();
      }
    });
  });
});

// Toggle VER/OCULTAR de la contraseña del login (CSP: nada de onClick inline).
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll("button[data-toggle-password]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var input = document.getElementById(btn.getAttribute("data-toggle-password"));
      if (!input) return;
      var oculta = input.type === "password";
      input.type = oculta ? "text" : "password";
      btn.textContent = oculta ? "OCULTAR" : "VER";
    });
  });
});
