// Cancha de UN equipo para la vista de alineaciones del árbitro: coloca a
// los titulares del plan sobre la formación (misma geometría que LineupScreen)
// con foto, dorsal y distintivos de eventos (goles/tarjetas/cambios) tomados
// del resumen por jugador. Si no hay plan o titulares, avisa que no se
// registró alineación.
import React, { useMemo } from "react";
import { Text, View } from "react-native";
import { lp } from "../publicTheme";
import Avatar from "./Avatar";
import { huecos } from "../formaciones";
import Icono from "./Icono";

// Deriva los distintivos visuales de un jugador a partir del resumen del
// partido: { goles, asistencias, amarillas, rojas, salio, entro }.
function badgesDe(resumen, jugadorId) {
  const r = resumen ? resumen[String(jugadorId)] : null;
  if (!r) return [];
  const out = [];
  if (r.goles) out.push({ key: "goles", icono: "football", veces: r.goles });
  if (r.asistencias) out.push({ key: "asist", letra: "A", veces: r.asistencias });
  if (r.amarillas) out.push({ key: "amarilla", icono: "tarjeta", color: lp.amarilla, veces: r.amarillas });
  if (r.rojas) out.push({ key: "roja", icono: "tarjeta", color: lp.rojaClara, veces: r.rojas });
  if (r.salio) out.push({ key: "sale", texto: "↓" });
  if (r.entro) out.push({ key: "entra", texto: "↑" });
  return out;
}

// `tinte` es el color base para distintivos sin color propio (flechas, "A",
// balón): blanco sobre la cancha oscura, lp.textDark sobre la banca clara.
// Los colores propios de la tarjeta (b.color: amarilla/rojaClara) siempre
// mandan porque se distinguen en ambos fondos. La sombra de texto solo tiene
// sentido cuando el tinte es claro (texto oscuro sobre banca clara ensucia
// la sombra negra); sobre la cancha el tinte es blanco y sí la necesita.
function Distintivos({ badges, tinte = "#fff", enCancha = false }) {
  if (!badges.length) return null;
  return (
    <View style={enCancha ? estilos.badgesFilaCancha : estilos.badgesFila}>
      {badges.map((b) => (
        <View key={b.key} style={estilos.badge}>
          {b.icono
            ? <Icono nombre={b.icono} size={11} color={b.color || tinte} />
            : <Text style={[estilos.badgeTexto, { color: b.color || tinte }, enCancha && estilos.badgeTextoSombra]}>{b.letra || b.texto}</Text>}
          {b.veces > 1 && <Text style={[estilos.badgeTexto, { color: b.color || tinte }, enCancha && estilos.badgeTextoSombra]}>×{b.veces}</Text>}
        </View>
      ))}
    </View>
  );
}

export default function LineupPitch({ equipoId, plan, resumen }) {
  const formacion = plan?.formacion || "4-4-2";
  const slots = useMemo(() => huecos(formacion), [formacion]);
  const titulares = (plan?.jugadores || []).filter((j) => j.jugador_id != null);
  const suplentes = (plan?.suplentes || []).filter((j) => j.jugador_id != null);

  if (!plan || titulares.length === 0) {
    return (
      <View style={[estilos.campo, { alignItems: "center", justifyContent: "center" }]}>
        <Text style={estilos.avisoTexto}>Alineación no registrada</Text>
      </View>
    );
  }

  const porOrden = {};
  titulares.forEach((j) => { porOrden[j.orden] = j; });

  return (
    <View>
      <View style={estilos.campo}>
        <View style={estilos.lineaMedia} />
        <View style={estilos.circuloCentral} />
        {slots.map((s) => {
          const jug = porOrden[s.orden];
          return (
            <View
              key={s.orden}
              style={[estilos.slot, { left: `${s.x * 100}%`, top: `${s.y * 100}%` }, !jug && estilos.slotVacio]}
            >
              {jug ? (
                <>
                  <Avatar usuarioId={jug.jugador_id} nombre={jug.nombre} size={40} />
                  <Text style={estilos.slotEtiqueta} numberOfLines={1}>
                    {jug.dorsal != null ? `#${jug.dorsal} ` : ""}{jug.nombre}
                  </Text>
                  <Distintivos badges={badgesDe(resumen, jug.jugador_id)} tinte="#fff" enCancha />
                </>
              ) : null}
            </View>
          );
        })}
      </View>

      {suplentes.length > 0 && (
        <View style={estilos.banca}>
          <Text style={estilos.bancaTitulo}>Banca</Text>
          {suplentes.map((j) => {
            const badges = badgesDe(resumen, j.jugador_id);
            return (
              <View key={j.jugador_id} style={estilos.bancaFila}>
                <Avatar usuarioId={j.jugador_id} nombre={j.nombre} size={30} />
                <Text style={estilos.bancaNombre} numberOfLines={1}>
                  {j.dorsal != null ? `#${j.dorsal} ` : ""}{j.nombre}
                </Text>
                <Distintivos badges={badges} tinte={lp.textDark} />
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

const estilos = {
  campo: {
    width: "100%", aspectRatio: 0.66, backgroundColor: "#1C6B3A", borderRadius: 14,
    borderWidth: 2, borderColor: "rgba(255,255,255,0.35)", position: "relative", overflow: "hidden",
  },
  lineaMedia: { position: "absolute", top: "50%", left: 0, right: 0, height: 2, backgroundColor: "rgba(255,255,255,0.35)" },
  circuloCentral: {
    position: "absolute", top: "50%", left: "50%", width: 70, height: 70, borderRadius: 35,
    borderWidth: 2, borderColor: "rgba(255,255,255,0.35)", transform: [{ translateX: -35 }, { translateY: -35 }],
  },
  slot: {
    position: "absolute", width: 36, height: 36, borderRadius: 18, alignItems: "center", justifyContent: "center",
    transform: [{ translateX: -18 }, { translateY: -18 }],
  },
  slotVacio: {
    borderWidth: 2, borderColor: "rgba(255,255,255,0.5)", borderStyle: "dashed", backgroundColor: "rgba(0,0,0,0.15)",
  },
  slotEtiqueta: {
    position: "absolute", top: 44, left: -18, width: 72, textAlign: "center",
    color: "#fff", fontWeight: "700", fontSize: 10,
    textShadowColor: "rgba(0,0,0,0.7)", textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 2,
  },
  // Banca: los distintivos fluyen dentro de bancaFila (fila normal, no
  // absoluta) a la derecha del nombre.
  badgesFila: {
    flexDirection: "row", flexWrap: "wrap", alignItems: "center", justifyContent: "center",
  },
  // Cancha: coordenadas absolutas pensadas para el hueco de 36px del slot,
  // debajo de slotEtiqueta. Solo tiene sentido ahí, nunca en la banca.
  badgesFilaCancha: {
    position: "absolute", top: 58, left: -24, width: 84, flexDirection: "row", flexWrap: "wrap",
    justifyContent: "center",
  },
  badge: { flexDirection: "row", alignItems: "center", marginHorizontal: 1 },
  badgeTexto: { fontSize: 11, fontWeight: "700" },
  // Solo se aplica sobre la cancha (tinte claro/blanco): sobre la banca clara
  // una sombra negra alrededor de texto oscuro se ve sucia.
  badgeTextoSombra: {
    textShadowColor: "rgba(0,0,0,0.7)", textShadowOffset: { width: 0, height: 1 }, textShadowRadius: 2,
  },
  avisoTexto: { color: "#fff", fontWeight: "700", fontSize: 14 },
  banca: {
    marginTop: 14, backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1,
    borderRadius: 12, padding: 12,
  },
  bancaTitulo: {
    color: lp.textDark, fontSize: 12, fontWeight: "800", letterSpacing: 1, textTransform: "uppercase", marginBottom: 8,
  },
  bancaFila: { flexDirection: "row", alignItems: "center", marginBottom: 8 },
  bancaNombre: { color: lp.textDark, fontWeight: "700", fontSize: 13, marginLeft: 10, flex: 1 },
};
