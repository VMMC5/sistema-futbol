// Paleta y estilos compartidos — tema "cancha" (igual que el panel web).
import { StyleSheet } from "react-native";

export const colors = {
  pitch900: "#07140d",
  pitch800: "#0b2014",
  pitch700: "#0f2c1b",
  pitch600: "#163d26",
  line: "rgba(198,255,0,0.16)",
  lime: "#c6ff2e",
  chalk: "#eaf3ec",
  muted: "#8aa595",
  danger: "#ff5a5a",
};

export const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.pitch900 },
  content: { padding: 20, paddingBottom: 40 },

  h1: { color: colors.chalk, fontSize: 28, fontWeight: "800", letterSpacing: 0.5 },
  h2: { color: colors.chalk, fontSize: 20, fontWeight: "800", marginBottom: 12, marginTop: 8 },
  muted: { color: colors.muted, fontSize: 14 },

  card: {
    backgroundColor: colors.pitch700,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    marginBottom: 12,
  },
  cardTitle: { color: colors.chalk, fontSize: 16, fontWeight: "700" },
  cardSub: { color: colors.muted, fontSize: 13, marginTop: 4 },

  score: { color: colors.lime, fontSize: 22, fontWeight: "800" },

  input: {
    backgroundColor: colors.pitch900,
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 10,
    color: colors.chalk,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    marginBottom: 14,
  },
  label: { color: colors.muted, fontSize: 13, marginBottom: 6, fontWeight: "600" },

  btn: {
    backgroundColor: colors.lime,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 6,
  },
  btnText: { color: colors.pitch900, fontWeight: "800", fontSize: 15 },

  btnGhost: {
    borderColor: colors.line,
    borderWidth: 1,
    borderRadius: 10,
    paddingVertical: 13,
    alignItems: "center",
    marginTop: 10,
  },
  btnGhostText: { color: colors.chalk, fontWeight: "700", fontSize: 14 },

  link: { color: colors.lime, textAlign: "center", marginTop: 16, fontWeight: "600" },

  pill: {
    alignSelf: "flex-start",
    backgroundColor: "rgba(198,255,0,0.14)",
    color: colors.lime,
    paddingHorizontal: 12,
    paddingVertical: 5,
    borderRadius: 999,
    overflow: "hidden",
    fontSize: 12,
    fontWeight: "700",
  },
  error: { color: colors.danger, marginBottom: 12, fontWeight: "600" },
  ok: { color: colors.lime, marginBottom: 12, fontWeight: "600" },
});
