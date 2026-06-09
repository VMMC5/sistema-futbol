// Pantalla principal PÚBLICA (sin login): muestra lo más relevante del sistema.
import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { apiGet } from "../api";
import { useAuth } from "../auth";
import { colors, styles } from "../theme";

export default function LandingScreen({ navigation }) {
  const { usuario } = useAuth();
  const [datos, setDatos] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [refrescando, setRefrescando] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const r = await apiGet("/publico/inicio", false); // endpoint público
      setDatos(r);
    } catch (_) {
      setDatos({ proximos_partidos: [], torneos_activos: [], goleadores_top: [] });
    } finally {
      setCargando(false);
      setRefrescando(false);
    }
  }, []);

  useEffect(() => {
    cargar();
  }, [cargar]);

  return (
    <View style={styles.screen}>
      {/* Barra superior con botón de ingreso a la derecha */}
      <View style={barra.top}>
        <View>
          <Text style={barra.brand}>⚽ TORNEOS</Text>
          <Text style={styles.muted}>Fútbol · canchas y torneos</Text>
        </View>
        <TouchableOpacity
          style={barra.loginBtn}
          onPress={() => navigation.navigate(usuario ? "Home" : "Login")}
        >
          <Text style={barra.loginBtnText}>{usuario ? "Mi panel" : "Ingresar"}</Text>
        </TouchableOpacity>
      </View>

      {cargando ? (
        <ActivityIndicator color={colors.lime} style={{ marginTop: 40 }} />
      ) : (
        <ScrollView
          contentContainerStyle={styles.content}
          refreshControl={
            <RefreshControl
              refreshing={refrescando}
              onRefresh={() => {
                setRefrescando(true);
                cargar();
              }}
              tintColor={colors.lime}
            />
          }
        >
          {/* Próximos partidos */}
          <Text style={styles.h2}>Próximos partidos</Text>
          {datos.proximos_partidos.length === 0 ? (
            <Text style={styles.muted}>No hay partidos programados.</Text>
          ) : (
            datos.proximos_partidos.map((p) => (
              <View key={p.id} style={styles.card}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={styles.cardTitle}>
                    {(p.equipo_local_nombre || "?") + "  vs  " + (p.equipo_visitante_nombre || "?")}
                  </Text>
                  <Text style={styles.score}>{p.goles_local}–{p.goles_visitante}</Text>
                </View>
                <Text style={styles.cardSub}>
                  {(p.torneo_nombre || "Torneo")}
                  {p.cancha_nombre ? ` · ${p.cancha_nombre}` : ""}
                  {p.fecha_hora ? ` · ${p.fecha_hora.replace("T", " ").slice(0, 16)}` : ""}
                </Text>
                <Text style={[styles.pill, { marginTop: 8 }]}>{String(p.estado).replace("_", " ")}</Text>
              </View>
            ))
          )}

          {/* Torneos activos */}
          <Text style={styles.h2}>Torneos activos</Text>
          {datos.torneos_activos.length === 0 ? (
            <Text style={styles.muted}>No hay torneos en curso.</Text>
          ) : (
            datos.torneos_activos.map((t) => (
              <View key={t.id} style={styles.card}>
                <Text style={styles.cardTitle}>{t.nombre}</Text>
                <Text style={styles.cardSub}>
                  {(t.sede_nombre || "Sede")} · {t.partidos_jugados} partidos jugados · {t.goles_totales} goles
                </Text>
              </View>
            ))
          )}

          {/* Goleadores */}
          <Text style={styles.h2}>Goleadores</Text>
          {datos.goleadores_top.length === 0 ? (
            <Text style={styles.muted}>Aún no hay goles registrados.</Text>
          ) : (
            <View style={styles.card}>
              {datos.goleadores_top.map((g, i) => (
                <View
                  key={g.jugador_id}
                  style={{
                    flexDirection: "row",
                    justifyContent: "space-between",
                    paddingVertical: 8,
                    borderBottomWidth: i < datos.goleadores_top.length - 1 ? 1 : 0,
                    borderBottomColor: "rgba(255,255,255,0.05)",
                  }}
                >
                  <Text style={{ color: colors.chalk }}>{i + 1}. {g.nombre}</Text>
                  <Text style={styles.score}>{g.goles}</Text>
                </View>
              ))}
            </View>
          )}
        </ScrollView>
      )}
    </View>
  );
}

const barra = {
  top: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 16,
    backgroundColor: colors.pitch800,
    borderBottomColor: colors.line,
    borderBottomWidth: 1,
  },
  brand: { color: colors.chalk, fontSize: 24, fontWeight: "800", letterSpacing: 1 },
  loginBtn: {
    backgroundColor: colors.lime,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 999,
  },
  loginBtnText: { color: colors.pitch900, fontWeight: "800" },
};
