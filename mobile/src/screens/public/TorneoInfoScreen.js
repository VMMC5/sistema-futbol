// Información de un torneo PRÓXIMO a empezar (datos de inscripción).
import React, { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Text, View } from "react-native";
import { apiGet } from "../../api";
import { fecha } from "../../format";
import { lp, ls } from "../../publicTheme";

function Info({ label, value }) {
  return (
    <View style={ls.infoRow}>
      <Text style={ls.infoLabel}>{label}</Text>
      <Text style={ls.infoValue}>{value}</Text>
    </View>
  );
}

export default function TorneoInfoScreen({ route }) {
  const { torneoId } = route.params;
  const [t, setT] = useState(null);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        setT(await apiGet(`/publico/torneos/${torneoId}`, false));
      } catch (_) {
        setT(null);
      } finally {
        setCargando(false);
      }
    })();
  }, [torneoId]);

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.accent} style={{ marginTop: 40 }} /></View>;
  }
  if (!t) {
    return <View style={ls.screen}><Text style={ls.empty}>No se encontró el torneo.</Text></View>;
  }

  const cuota = t.cuota_inscripcion != null ? `$${Number(t.cuota_inscripcion).toFixed(2)}` : "Gratis / por definir";

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      <View style={ls.feature}>
        <Text style={ls.featureLabel}>Próximo torneo</Text>
        <Text style={[ls.teamName, { fontSize: 22, marginTop: 4 }]}>{t.nombre}</Text>
        {t.descripcion ? <Text style={ls.featureMeta}>{t.descripcion}</Text> : null}
      </View>

      <Info label="Tipo de torneo" value={t.tipo || "Por definir"} />
      <Info label="Sede" value={t.sede_nombre || "Por definir"} />
      <Info label="Cuota de inscripción" value={cuota} />
      <Info label="Premio al ganador" value={t.premio || "Por definir"} />
      <Info label="Cierre de inscripciones" value={t.fecha_cierre_inscripciones ? fecha(t.fecha_cierre_inscripciones) : "Por definir"} />
      <Info label="Inicio del torneo" value={t.fecha_inicio ? fecha(t.fecha_inicio) : "Por definir"} />
      {t.cupo_maximo ? <Info label="Cupo máximo" value={`${t.cupo_maximo} equipos`} /> : null}
    </ScrollView>
  );
}
