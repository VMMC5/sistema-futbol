// Icono vectorial. Espejo del macro icono() de la web: mismos paths de Reicon
// (reicon.dev, MIT), mismo viewBox 0 0 24 24. El color llega por prop, como
// currentColor en la web.
//
// Formato de cada entrada de iconos-datos.json (el JSON no admite comentarios):
//   d         paths del icono, en orden de pintado
//   trazo     true -> se pintan con stroke y fill none; ausente -> con fill
//   parImpar  true -> fillRule/clipRule "evenodd" (el icono lo declara en su SVG)
import React from "react";
import Svg, { Path } from "react-native-svg";
import ICONOS from "./iconos-datos.json";
import { lp } from "../publicTheme";

export default function Icono({ nombre, size = 18, color = lp.textDark }) {
  const def = ICONOS[nombre];
  // Un nombre desconocido pinta un hueco del tamaño pedido, nunca revienta
  // (mismo criterio que _REICON.get(nombre, "") en la plantilla web).
  const paths = def?.d || [];
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      {paths.map((d, i) =>
        def.trazo ? (
          <Path
            key={i}
            d={d}
            stroke={color}
            strokeWidth={1.5}
            strokeMiterlimit={10}
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
          />
        ) : (
          <Path
            key={i}
            d={d}
            fill={color}
            fillRule={def.parImpar ? "evenodd" : "nonzero"}
            clipRule={def.parImpar ? "evenodd" : "nonzero"}
          />
        ),
      )}
    </Svg>
  );
}
