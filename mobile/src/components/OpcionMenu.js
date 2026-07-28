// Fila de menú de las pantallas de perfil: icono, texto y chevron.
import React from "react";
import { Text, TouchableOpacity } from "react-native";
import Icono from "./Icono";
import { lp, ls } from "../publicTheme";

export default function OpcionMenu({ icono, texto, onPress, color }) {
  const tinte = color || lp.textDark;
  return (
    <TouchableOpacity style={[ls.row, { alignItems: "center" }]} onPress={onPress}>
      <Icono nombre={icono} size={18} color={tinte} />
      <Text style={{ flex: 1, fontWeight: "700", color: tinte, marginLeft: 12 }}>{texto}</Text>
      <Text style={{ color: lp.textMuted, fontSize: 20 }}>›</Text>
    </TouchableOpacity>
  );
}
