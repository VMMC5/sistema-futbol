// Tema CLARO para las pantallas públicas (estilo del mockup): fondo crema,
// tarjetas verde oscuro, acento verde medio.
import { StyleSheet } from "react-native";

export const lp = {
  bg: "#EDEAE1",
  surface: "#FBFAF6",
  surfaceBorder: "#E3DFD3",
  green: "#123D2A",      // tarjetas "feature" (verde oscuro)
  greenText: "#F2F0E8",
  accent: "#2E7D52",     // pestañas/badges activos
  textDark: "#1A2A20",
  textMuted: "#7C887E",
  white: "#FFFFFF",
  danger: "#c0392b",
};

export const ls = StyleSheet.create({
  screen: { flex: 1, backgroundColor: lp.bg },
  content: { padding: 16, paddingBottom: 30 },

  sectionTitle: { color: lp.textDark, fontSize: 13, fontWeight: "800", letterSpacing: 1, textTransform: "uppercase", marginBottom: 10, marginTop: 6 },
  muted: { color: lp.textMuted, fontSize: 14 },

  // Tarjeta verde oscuro tipo "PRÓXIMO PARTIDO" / cabecera de torneo
  feature: { backgroundColor: lp.green, borderRadius: 14, padding: 18, marginBottom: 14 },
  featureLabel: { color: lp.greenText, opacity: 0.7, fontSize: 12, fontWeight: "800", letterSpacing: 1.5, textTransform: "uppercase" },
  featureMeta: { color: lp.greenText, opacity: 0.85, fontSize: 13, marginTop: 8 },
  matchRow: { flexDirection: "row", alignItems: "center", justifyContent: "center", marginTop: 14 },
  teamName: { color: lp.greenText, fontSize: 16, fontWeight: "700" },
  vs: { color: lp.greenText, opacity: 0.5, fontSize: 13, marginHorizontal: 12 },

  // Fila de lista (blanca)
  row: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 10, flexDirection: "row", alignItems: "center" },
  rowTitle: { color: lp.textDark, fontSize: 15, fontWeight: "700" },
  rowSub: { color: lp.textMuted, fontSize: 13, marginTop: 2 },

  iconCircle: { width: 40, height: 40, borderRadius: 20, backgroundColor: lp.green, alignItems: "center", justifyContent: "center", marginRight: 12 },
  iconText: { color: lp.greenText, fontSize: 18 },

  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 6, fontSize: 11, fontWeight: "800", letterSpacing: 0.5, overflow: "hidden" },
  badgeOn: { backgroundColor: lp.accent, color: lp.white },
  badgeNext: { borderColor: lp.accent, borderWidth: 1, color: lp.accent },

  // Pestañas internas (Activos/Próximos, Tabla/Partidos/Goleo)
  tabs: { flexDirection: "row", backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, padding: 4, marginBottom: 16 },
  tab: { flex: 1, paddingVertical: 9, borderRadius: 8, alignItems: "center" },
  tabActive: { backgroundColor: lp.accent },
  tabText: { color: lp.textMuted, fontWeight: "700", fontSize: 13 },
  tabTextActive: { color: lp.white },

  // Tabla de posiciones
  standRow: { flexDirection: "row", alignItems: "center", backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingVertical: 12, paddingHorizontal: 14, marginBottom: 8 },
  rank: { width: 26, color: lp.accent, fontWeight: "800", fontSize: 15 },
  pts: { color: lp.textDark, fontWeight: "800", fontSize: 14 },

  // Filas de info (detalle de torneo próximo)
  infoRow: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, padding: 14, marginBottom: 10 },
  infoLabel: { color: lp.textMuted, fontSize: 12, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  infoValue: { color: lp.textDark, fontSize: 16, fontWeight: "700", marginTop: 4 },

  empty: { color: lp.textMuted, textAlign: "center", paddingVertical: 40 },

  // Botón de "Ingresar" en la cabecera
  loginPill: { backgroundColor: lp.green, paddingHorizontal: 14, paddingVertical: 7, borderRadius: 999, marginRight: 12 },
  loginPillText: { color: lp.greenText, fontWeight: "800", fontSize: 13 },
});
