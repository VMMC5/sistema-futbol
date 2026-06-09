// Pestaña TORNEOS (pública): activos y próximos.
import React, { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ActivityIndicator, ScrollView, Text, TouchableOpacity, View } from "react-native";
import { apiGet } from "../../api";
import { fecha } from "../../format";
import { lp, ls } from "../../publicTheme";

export default function TorneosScreen({ navigation }) {
  const [pestana, setPestana] = useState("activos");
  const [data, setData] = useState({ activos: [], proximos: [] });
  const [cargando, setCargando] = useState(true);

  const cargar = useCallback(async () => {
    try {
      setData(await apiGet("/publico/torneos", false));
    } catch (_) {
      setData({ activos: [], proximos: [] });
    } finally {
      setCargando(false);
    }
  }, []);

  useFocusEffect(useCallback(() => { cargar(); }, [cargar]));

  const lista = pestana === "activos" ? data.activos : data.proximos;

  function abrir(t) {
    if (t.estado === "en_curso") navigation.navigate("TorneoStats", { torneoId: t.id, nombre: t.nombre });
    else navigation.navigate("TorneoInfo", { torneoId: t.id, nombre: t.nombre });
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Pestañas Activos / Próximos */}
      <View style={ls.tabs}>
        {[["activos", "Activos"], ["proximos", "Próximos"]].map(([key, label]) => (
          <TouchableOpacity key={key} style={[ls.tab, pestana === key && ls.tabActive]} onPress={() => setPestana(key)}>
            <Text style={[ls.tabText, pestana === key && ls.tabTextActive]}>{label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {cargando ? (
        <ActivityIndicator color={lp.accent} style={{ marginTop: 30 }} />
      ) : lista.length === 0 ? (
        <Text style={ls.empty}>
          {pestana === "activos" ? "No hay torneos en curso." : "No hay torneos próximos."}
        </Text>
      ) : (
        lista.map((t) => (
          <TouchableOpacity key={t.id} style={ls.row} onPress={() => abrir(t)}>
            <View style={ls.iconCircle}><Text style={ls.iconText}>🏆</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={ls.rowTitle}>{t.nombre}</Text>
              <Text style={ls.rowSub}>
                {pestana === "activos"
                  ? `${t.equipos} equipos · ${t.partidos_jugados}/${t.partidos_total} partidos`
                  : `${t.tipo || "Torneo"}${t.fecha_inicio ? ` · inicia ${fecha(t.fecha_inicio)}` : ""}`}
              </Text>
            </View>
            <Text style={[ls.badge, pestana === "activos" ? ls.badgeOn : ls.badgeNext]}>
              {pestana === "activos" ? "EN CURSO" : "PRÓXIMO"}
            </Text>
          </TouchableOpacity>
        ))
      )}
    </ScrollView>
  );
}
