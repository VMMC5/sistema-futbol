// Parseo de sintaxis con el @babel/core del proyecto.
// Uso (desde cualquier directorio): node mobile/scripts/verificar-sintaxis.cjs App.js src/components/Icono.js ...
// O bien, desde mobile/: npm run verificar -- App.js src/components/Icono.js ...
// Los argumentos de archivos se resuelven contra el cwd (como espera Node), pero
// @babel/core y "babel-preset-expo" se resuelven contra la ubicación del propio
// script (mobile/), no contra el cwd del proceso, para que funcione igual se
// lance desde donde se lance.
const path = require("path");
const RAIZ_MOBILE = path.join(__dirname, "..");
const babel = require(path.join(RAIZ_MOBILE, "node_modules", "@babel", "core"));

let malos = 0;
for (const archivo of process.argv.slice(2)) {
  try {
    babel.transformFileSync(archivo, {
      cwd: RAIZ_MOBILE,
      presets: ["babel-preset-expo"],
      babelrc: false,
      configFile: false,
    });
    console.log("OK    " + archivo);
  } catch (e) {
    console.log("FALLO " + archivo + " -> " + e.message.split("\n")[0]);
    malos++;
  }
}
process.exit(malos ? 1 : 0);
