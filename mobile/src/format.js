// Pequeñas utilidades para mostrar fechas de forma legible.
const MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const DIAS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

function _parse(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  return isNaN(d.getTime()) ? null : d;
}

// "Sáb 31 May · 18:00"
export function fechaHora(iso) {
  const d = _parse(iso);
  if (!d) return "Por definir";
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${DIAS[d.getDay()]} ${d.getDate()} ${MESES[d.getMonth()]} · ${hh}:${mm}`;
}

// "31 May 2026"
export function fecha(iso) {
  const d = _parse(iso);
  if (!d) return "Por definir";
  return `${d.getDate()} ${MESES[d.getMonth()]} ${d.getFullYear()}`;
}
