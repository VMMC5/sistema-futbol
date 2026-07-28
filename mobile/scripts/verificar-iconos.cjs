// Valida los datos de iconos sin React Native ni emulador.
// Uso: node scripts/verificar-iconos.cjs
const ICONOS = require("../src/components/iconos-datos.json");

const ESPERADOS = ["edit", "creditcard", "lock", "logout", "bell"];
const fallos = [];

for (const nombre of ESPERADOS) {
  const def = ICONOS[nombre];
  if (!def) { fallos.push(`falta el icono "${nombre}"`); continue; }
  if (!Array.isArray(def.d) || def.d.length === 0) {
    fallos.push(`"${nombre}": "d" debe ser un array no vacío`);
    continue;
  }
  def.d.forEach((d, i) => {
    if (typeof d !== "string" || !d.trim().startsWith("M")) {
      fallos.push(`"${nombre}"[${i}]: un path SVG debe empezar por "M"`);
    }
    if (/#[0-9a-fA-F]{3,6}/.test(d)) {
      fallos.push(`"${nombre}"[${i}]: color literal incrustado; el color va por prop`);
    }
  });
}

const sobran = Object.keys(ICONOS).filter((k) => !ESPERADOS.includes(k));
if (sobran.length) fallos.push(`iconos no esperados: ${sobran.join(", ")}`);

if (fallos.length) {
  console.error("FALLO:\n" + fallos.map((f) => "  - " + f).join("\n"));
  process.exit(1);
}
console.log(`OK: ${ESPERADOS.length} iconos válidos`);
