// Genera las entradas de iconos-datos.json desde sus dos fuentes:
//   - el macro Jinja de la web (web/app/templates/_iconos.html), para que movil
//     y web pinten el mismo path del mismo concepto
//   - el paquete npm reicon, descargado aparte (NO es dependencia del proyecto)
//
// Uso:  node scripts/generar-iconos.cjs <dir-del-paquete-reicon>
// Ej.:  node scripts/generar-iconos.cjs /tmp/reicon-gen/package
//
// Imprime el JSON por stdout. No escribe nada: revisa y redirige tu mismo.
//
// Los datos actuales de iconos-datos.json se generaron con reicon@1.1.103.
// Re-ejecutar este script con otra version del paquete puede cambiar los
// paths en silencio (verificar-iconos.cjs solo comprueba que no esten
// vacios, que empiecen por "M" y que no lleven color hex: no detecta un
// cambio de version). Si regeneras, deja constancia de la version usada.
const fs = require("fs");
const path = require("path");

const RAIZ_REPO = path.join(__dirname, "..", "..");
const dirReicon = process.argv[2];
if (!dirReicon) {
  console.error("Falta el directorio del paquete reicon. Ver la cabecera del script.");
  process.exit(1);
}

// Del macro de la web: mismo concepto, mismo path que el panel.
const DESDE_WEB = ["cuptrophy", "chart", "calendar", "people", "football", "transfer"];
// De reicon: clave en el JSON -> nombre del archivo del paquete.
const DESDE_REICON = {
  home: "Home",
  user: "User",
  history: "History",
  clipboardlist: "ClipboardList",
  docadd: "DocAdd",
  location: "Pin",   // el "location" del macro web usa circle/line/g: no vale aqui
  envelope: "Envelope",
  paperclip: "Paperclip",
};

function paths(svg) {
  return [...svg.matchAll(/\sd="([^"]+)"/g)].map((m) => m[1]);
}

function entrada(svg) {
  const e = { d: paths(svg) };
  if (svg.includes('stroke="currentColor"') || svg.includes('stroke="#')) e.trazo = true;
  if (svg.includes('fill-rule="evenodd"')) e.parImpar = true;
  return e;
}

// Iconos cuyo dato NO se puede extraer de la fuente porque no es un <path>.
// El "tarjeta" del macro web es <rect x="6" y="2.5" width="12" height="19" rx="2.2"/>.
// A diferencia de "location" (que mezcla circle/line/g y por eso se tomó de reicon),
// un rectangulo redondeado se expresa EXACTAMENTE como path, sin perdida:
// esquinas (6,2.5)-(18,21.5) y radio 2.2 en las cuatro.
const LITERALES = {
  tarjeta: {
    d: ["M8.2 2.5 H15.8 A2.2 2.2 0 0 1 18 4.7 V19.3 A2.2 2.2 0 0 1 15.8 21.5 H8.2 A2.2 2.2 0 0 1 6 19.3 V4.7 A2.2 2.2 0 0 1 8.2 2.5 Z"],
  },
};

const macro = fs.readFileSync(path.join(RAIZ_REPO, "web/app/templates/_iconos.html"), "utf8");
const salida = {};

for (const nombre of DESDE_WEB) {
  const m = macro.match(new RegExp(`"${nombre}": "(.*?)",\\n`, "s"));
  if (!m) { console.error(`No encontre "${nombre}" en el macro web`); process.exit(1); }
  salida[nombre] = entrada(m[1].replace(/\\"/g, '"'));
}

for (const [clave, archivo] of Object.entries(DESDE_REICON)) {
  const src = fs.readFileSync(path.join(dirReicon, "icons", `${archivo}.js`), "utf8");
  const b64 = src.match(/base64,([A-Za-z0-9+/=]*)/);
  if (!b64) { console.error(`No encontre el SVG de ${archivo}`); process.exit(1); }
  salida[clave] = entrada(Buffer.from(b64[1], "base64").toString("utf8"));
}

Object.assign(salida, LITERALES);

console.log(JSON.stringify(salida, null, 2));
