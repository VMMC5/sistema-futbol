// Geometría de las formaciones: líneas de la defensa al ataque y sus huecos
// (coordenadas x,y en fracción 0..1 sobre la cancha). Fuente única compartida
// entre LineupScreen (entrenador) y LineupPitch (árbitro).

// Cada formación se describe por líneas, de la defensa al ataque.
export const FORMACIONES = {
  "4-4-2": [["POR"], ["DEF", "DEF", "DEF", "DEF"], ["MED", "MED", "MED", "MED"], ["DEL", "DEL"]],
  "4-3-3": [["POR"], ["DEF", "DEF", "DEF", "DEF"], ["MED", "MED", "MED"], ["DEL", "DEL", "DEL"]],
  "3-5-2": [["POR"], ["DEF", "DEF", "DEF"], ["MED", "MED", "MED", "MED", "MED"], ["DEL", "DEL"]],
};

// Convierte la formación en huecos con coordenadas (x,y en fracción 0..1).
export function huecos(formacion) {
  const lineas = FORMACIONES[formacion];
  const slots = [];
  let orden = 0;
  const n = lineas.length;
  lineas.forEach((linea, r) => {
    // r=0 (POR) abajo; última línea (DEL) arriba
    const y = 0.9 - (r * 0.78) / (n - 1);
    linea.forEach((label, i) => {
      const x = (i + 1) / (linea.length + 1);
      slots.push({ orden, x, y, label });
      orden += 1;
    });
  });
  return slots;
}
