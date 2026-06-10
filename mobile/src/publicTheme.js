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
  gold: "#8A6D1E",       // cabecera y tarjeta del panel del entrenador
  maroon: "#7C2B2B",     // cabecera del panel del árbitro
  red: "#C0392B",        // botones principales del árbitro
  goldText: "#F7F1DF",
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

// Estilos extra para el panel del entrenador (tarjeta dorada, grid de acciones,
// avatares, cajas de estadísticas).
export const cs = StyleSheet.create({
  featureGold: { backgroundColor: lp.gold, borderRadius: 14, padding: 18, marginBottom: 16 },
  featureGoldName: { color: lp.goldText, fontSize: 20, fontWeight: "800", letterSpacing: 0.5 },
  featureGoldMeta: { color: lp.goldText, opacity: 0.85, fontSize: 13, marginTop: 6 },

  grid: { flexDirection: "row", flexWrap: "wrap", justifyContent: "space-between", marginBottom: 8 },
  gridItem: { width: "48%", backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 14, paddingVertical: 20, alignItems: "center", marginBottom: 12 },
  gridIcon: { fontSize: 22, marginBottom: 8 },
  gridLabel: { color: lp.textDark, fontWeight: "700", fontSize: 13 },

  avatar: { width: 42, height: 42, borderRadius: 21, alignItems: "center", justifyContent: "center", marginRight: 12 },
  avatarText: { color: lp.white, fontWeight: "800", fontSize: 16 },
  chevron: { color: lp.textMuted, fontSize: 22, marginLeft: 8 },

  statsRow: { flexDirection: "row", justifyContent: "space-between", marginBottom: 14 },
  statBox: { flex: 1, borderRadius: 12, paddingVertical: 14, alignItems: "center", marginHorizontal: 4 },
  statNum: { fontSize: 24, fontWeight: "800" },
  statLabel: { fontSize: 11, fontWeight: "700", marginTop: 2, opacity: 0.85 },

  // mini-formulario de jugador en la edición de plantilla
  playerForm: { flexDirection: "row", gap: 8, alignItems: "center", marginBottom: 10 },
  smallInput: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, color: lp.textDark, paddingHorizontal: 10, paddingVertical: 10 },

  primaryBtn: { backgroundColor: lp.gold, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 8 },
  primaryBtnText: { color: lp.goldText, fontWeight: "800", fontSize: 15 },
  ghostBtn: { borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 12, paddingVertical: 13, alignItems: "center", marginTop: 10 },
  ghostBtnText: { color: lp.textDark, fontWeight: "700" },

  field: { marginBottom: 14 },
  input: { backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, color: lp.textDark, paddingHorizontal: 14, paddingVertical: 12, fontSize: 15 },
});
