// Comprueba que todo nombre= usado con <Icono> exista en iconos-datos.json.
// Una errata no lanza error en ejecucion: pinta un hueco vacio. Esto lo caza.
// Uso: node scripts/verificar-nombres-iconos.cjs   (o npm run verificar-nombres)
const fs = require("fs");
const path = require("path");

const RAIZ = path.join(__dirname, "..");
const iconos = new Set(Object.keys(require(path.join(RAIZ, "src/components/iconos-datos.json"))));

const archivos = [];
(function recorrer(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) recorrer(p);
    else if (p.endsWith(".js")) archivos.push(p);
  }
})(path.join(RAIZ, "src"));
archivos.push(path.join(RAIZ, "App.js"));

let malos = 0;
for (const archivo of archivos) {
  const txt = fs.readFileSync(archivo, "utf8");
  for (const m of txt.matchAll(/nombre="([a-z]+)"/g)) {
    if (!iconos.has(m[1])) {
      console.log(`FALLO ${path.relative(RAIZ, archivo)}: nombre="${m[1]}" no existe en iconos-datos.json`);
      malos++;
    }
  }
}
console.log(malos ? `${malos} nombres inválidos` : "OK: todos los nombres de icono existen");
process.exit(malos ? 1 : 0);
