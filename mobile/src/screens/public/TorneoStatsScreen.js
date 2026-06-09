// Estadísticas de un torneo EN CURSO: Tabla, Partidos y Goleo.
import React, { useEffect, useState } from "react";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { fechaHora } from "../../format";
import { lp, ls } from "../../publicTheme";

export default function TorneoStatsScreen({ route }) {
  const { torneoId } = route.params;
  const [pestana, setPestana] = useState("tabla");
  const [torneo, setTorneo] = useState(null);
  const [tabla, setTabla] = useState([]);
  const [partidos, setPartidos] = useState([]);
  const [goleo, setGoleo] = useState([]);
  const [cargando, setCargando] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [t, tb, pa, go] = await Promise.all([
          apiGet(`/publico/torneos/${torneoId}`, false),
          apiGet(`/publico/torneos/${torneoId}/tabla`, false),
          apiGet(`/publico/torneos/${torneoId}/partidos`, false),
          apiGet(`/publico/torneos/${torneoId}/goleadores`, false),
        ]);
        setTorneo(t); setTabla(tb); setPartidos(pa); setGoleo(go);
      } catch (_) {
        // deja listas vacías
      } finally {
        setCargando(false);
      }
    })();
  }, [torneoId]);

  if (cargando) {
    return <View style={ls.screen}><ActivityIndicator color={lp.accent} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Cabecera del torneo */}
      <View style={ls.feature}>
        <Text style={ls.featureLabel}>{torneo?.tipo || "Torneo"}</Text>
        <Text style={[ls.teamName, { fontSize: 22, marginTop: 4 }]}>{torneo?.nombre}</Text>
        <Text style={ls.featureMeta}>
          {(torneo?.sede_nombre || "Sede")} · {torneo?.equipos} equipos
        </Text>
      </View>

      {/* Pestañas */}
      <View style={ls.tabs}>
        {[["tabla", "Tabla"], ["partidos", "Partidos"], ["goleo", "Goleo"]].map(([key, label]) => (
          <TouchableOpacity key={key} style={[ls.tab, pestana === key && ls.tabActive]} onPress={() => setPestana(key)}>
            <Text style={[ls.tabText, pestana === key && ls.tabTextActive]}>{label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {pestana === "tabla" && (
        tabla.length === 0 ? <Text style={ls.empty}>Aún no hay partidos jugados.</Text> :
        tabla.map((f, i) => (
          <View key={f.equipo_id} style={ls.standRow}>
            <Text style={ls.rank}>{i + 1}</Text>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{f.equipo}</Text>
              <Text style={ls.rowSub}>PJ {f.pj} · DG {f.dg >= 0 ? "+" : ""}{f.dg}</Text>
            </View>
            <Text style={ls.pts}>{f.puntos} pts</Text>
          </View>
        ))
      )}

      {pestana === "partidos" && (
        partidos.length === 0 ? <Text style={ls.empty}>No hay partidos.</Text> :
        partidos.map((p) => (
          <View key={p.id} style={ls.row}>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>
                {(p.equipo_local_nombre || "?")} {p.goles_local}–{p.goles_visitante} {(p.equipo_visitante_nombre || "?")}
              </Text>
              <Text style={ls.rowSub}>{fechaHora(p.fecha_hora)} · {String(p.estado).replace("_", " ")}</Text>
            </View>
          </View>
        ))
      )}

      {pestana === "goleo" && (
        goleo.length === 0 ? <Text style={ls.empty}>Aún no hay goles registrados.</Text> :
        goleo.map((g, i) => (
          <View key={g.jugador_id} style={ls.standRow}>
            <Text style={ls.rank}>{i + 1}</Text>
            <Text style={[ls.rowTitle, { flex: 1 }]}>{g.nombre}</Text>
            <Text style={ls.pts}>{g.goles} {g.goles === 1 ? "gol" : "goles"}</Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}
