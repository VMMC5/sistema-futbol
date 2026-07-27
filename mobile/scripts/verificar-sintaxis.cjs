// Parseo de sintaxis con el @babel/core del proyecto.
// Uso: node scripts/verificar-sintaxis.cjs App.js src/components/Icono.js ...
const path = require("path");
const babel = require(path.join(process.cwd(), "node_modules", "@babel", "core"));

let malos = 0;
for (const archivo of process.argv.slice(2)) {
  try {
    babel.transformFileSync(archivo, {
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
