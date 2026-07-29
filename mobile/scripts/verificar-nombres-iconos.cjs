// Comprueba que todo nombre de icono usado exista en iconos-datos.json.
// Una errata no lanza error en ejecucion: pinta un hueco vacio. Esto lo caza.
// Uso: node scripts/verificar-nombres-iconos.cjs   (o npm run verificar-nombres)
//
// Reconoce tres formas, que juntas cubren todos los usos literales del proyecto:
//   <Icono nombre="football">      render directo
//   <OpcionMenu icono="edit">      prop que otro componente pasa a <Icono>
//   { icono: "people", ... }       clave de objeto (ACCIONES, ICONO de eventos)
// La primera va acotada a <Icono> a proposito: <Avatar> tiene una prop `nombre`
// que no es un icono, y sin acotar daria falsos positivos.
//
// El patron acepta letras y digitos ([a-z0-9]+): hoy ningun icono del catalogo
// lleva digito, pero reicon tiene nombres como Home2 o User4, y si alguno asi
// entra al catalogo su uso quedaria sin verificar en silencio con un patron
// mas estrecho. Por eso: si alguna vez se vuelve a estrechar el patron, los
// nombres de prueba usados para comprobar este script NO deben llevar digitos,
// o la prueba dara verde aunque el detector este roto.
//
// Limite que PERMANECE: un valor calculado en tiempo de ejecucion sigue siendo
// invisible. Esto cubre lo literal, que es todo lo que el proyecto usa hoy.
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

const PATRONES = [
  [/<Icono\b[^>]*?\snombre="([a-z0-9]+)"/g, 'nombre='],
  [/\sicono="([a-z0-9]+)"/g, 'icono='],
  [/\bicono:\s*"([a-z0-9]+)"/g, 'icono:'],
];

let malos = 0;
let vistos = 0;
for (const archivo of archivos) {
  const txt = fs.readFileSync(archivo, "utf8");
  for (const [patron, etiqueta] of PATRONES) {
    for (const m of txt.matchAll(patron)) {
      vistos++;
      if (!iconos.has(m[1])) {
        console.log(`FALLO ${path.relative(RAIZ, archivo)}: ${etiqueta}"${m[1]}" no existe en iconos-datos.json`);
        malos++;
      }
    }
  }
}
console.log(malos ? `${malos} nombres inválidos` : `OK: ${vistos} usos de icono, todos existen`);
process.exit(malos ? 1 : 0);
