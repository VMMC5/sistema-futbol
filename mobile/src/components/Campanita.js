// Campana de cabecera con punto rojo de "hay avisos sin leer".
// El color depende de la cabecera de cada panel (verde/dorada/guinda).
import React from "react";
import { TouchableOpacity, View } from "react-native";
import Icono from "./Icono";
import { lp } from "../publicTheme";

export default function Campanita({ onPress, hayNuevas, color = lp.white }) {
  return (
    <TouchableOpacity onPress={onPress} style={{ paddingHorizontal: 14 }}>
      <Icono nombre="bell" size={20} color={color} />
      {/* El glifo de la campana no llena el viewBox de 24 (deja aire a los
          lados y arriba), así que el punto va más adentro y más arriba para
          apoyarse en la esquina superior derecha real. */}
      {hayNuevas && <View style={{ position: "absolute", right: 11, top: -4, width: 10, height: 10, borderRadius: 5, backgroundColor: lp.red }} />}
    </TouchableOpacity>
  );
}
