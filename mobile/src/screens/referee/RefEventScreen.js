// Registro de evento del árbitro: muestra las alineaciones y, según el tipo,
// pide anotador+asistencia+subtipo (gol), jugador (tarjeta) o sale+entra (cambio).
import React, { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, Alert, ScrollView, Text, TextInput, TouchableOpacity, View } from "react-native";
import { apiGet, apiPost } from "../../api";
import { lp, ls } from "../../publicTheme";

const TITULOS = {
  gol: "REGISTRAR GOL",
  tarjeta_amarilla: "TARJETA AMARILLA",
  tarjeta_roja: "TARJETA ROJA",
  cambio: "CAMBIO",
};

// Lista vertical de jugadores seleccionables
function ListaJugadores({ jugadores, seleccion, onSelect, vacio }) {
  if (!jugadores || jugadores.length === 0) {
    return <Text style={[ls.muted, { marginBottom: 10 }]}>{vacio || "Sin jugadores."}</Text>;
  }
  return jugadores.map((j) => {
    const activo = seleccion === j.jugador_id;
    return (
      <TouchableOpacity
        key={j.jugador_id}
        style={[ls.row, activo && { borderColor: lp.green, borderWidth: 2 }]}
        onPress={() => onSelect(activo ? null : j.jugador_id)}
      >
        <View style={[circulo, activo && { backgroundColor: lp.green }]}>
          <Text style={{ color: activo ? lp.white : lp.textDark, fontWeight: "800" }}>
            {j.dorsal != null ? j.dorsal : (j.nombre || "?").charAt(0)}
          </Text>
        </View>
        <Text style={[ls.rowTitle, { flex: 1 }]}>{j.nombre || `Jugador ${j.jugador_id}`}</Text>
        {activo && <Text style={{ color: lp.green, fontWeight: "800", fontSize: 18 }}>✓</Text>}
      </TouchableOpacity>
    );
  });
}

export default function RefEventScreen({ route, navigation }) {
  const { partidoId, tipo } = route.params;
  const esGol = tipo === "gol";
  const esCambio = tipo === "cambio";

  const [partido, setPartido] = useState(null);
  const [planes, setPlanes] = useState({}); // {equipoId: {titulares, suplentes, nombre}}
  const [equipoSel, setEquipoSel] = useState(null);
  const [cargando, setCargando] = useState(true);
  const [guardando, setGuardando] = useState(false);

  // Selecciones
  const [principal, setPrincipal] = useState(null);   // anotador / sancionado / sale
  const [secundario, setSecundario] = useState(null); // asistente / entra
  const [minuto, setMinuto] = useState("");
  const [subtipo, setSubtipo] = useState("normal");

  useEffect(() => {
    navigation.setOptions({ title: TITULOS[tipo] || "EVENTO" });
    (async () => {
      try {
        const p = await apiGet(`/partidos/${partidoId}`);
        setPartido(p);
        setEquipoSel(p.equipo_local_id);
        const mapa = {};
        for (const [id, nombre] of [[p.equipo_local_id, p.equipo_local_nombre], [p.equipo_visitante_id, p.equipo_visitante_nombre]]) {
          if (!id) continue;
          try {
            const plan = await apiGet(`/partidos/${partidoId}/plan?equipo_id=${id}`);
            mapa[id] = {
              nombre,
              titulares: (plan.jugadores || []).filter((j) => j.jugador_id != null),
              suplentes: (plan.suplentes || []).filter((j) => j.jugador_id != null),
            };
          } catch (_) { mapa[id] = { nombre, titulares: [], suplentes: [] }; }
        }
        setPlanes(mapa);
      } catch (e) {
        Alert.alert("Error", e.message || "No se pudo cargar");
      } finally {
        setCargando(false);
      }
    })();
  }, [partidoId, tipo]);

  // Al cambiar de equipo se limpian las selecciones
  function elegirEquipo(id) { setEquipoSel(id); setPrincipal(null); setSecundario(null); }

  const datosEquipo = planes[equipoSel] || { titulares: [], suplentes: [] };
  const plantilla = useMemo(
    () => [...datosEquipo.titulares, ...datosEquipo.suplentes],
    [datosEquipo]
  );
  // Sin alineación del entrenador el servidor marca en_campo a toda la plantilla:
  // ahí la banca sigue siendo la lista de quién puede entrar.
  const sinPlan = datosEquipo.titulares.length === 0;

  // El servidor decide quién está en el campo (titulares − expulsados − salidos
  // + entrados). Aquí solo se lee la bandera: si la regla cambia, cambia allá.
  const enCancha = useMemo(() => plantilla.filter((j) => j.en_campo), [plantilla]);

  const asistentes = useMemo(
    () => enCancha.filter((j) => j.jugador_id !== principal),
    [enCancha, principal]
  );

  // Quién puede entrar en un cambio: los que no están en el campo y no están
  // expulsados. Sin plan, la banca entera menos los expulsados.
  const entrantes = useMemo(() => {
    const base = sinPlan ? datosEquipo.suplentes : plantilla.filter((j) => !j.en_campo);
    return base.filter((j) => !j.expulsado && j.jugador_id !== principal);
  }, [plantilla, datosEquipo, sinPlan, principal]);

  async function confirmar() {
    if (!esGol && !esCambio && principal == null) {
      Alert.alert("Falta seleccionar", "Elige al jugador sancionado."); return;
    }
    if (esCambio && (principal == null || secundario == null)) {
      Alert.alert("Falta seleccionar", "Elige quién sale y quién entra."); return;
    }
    // Antes se omitía el minuto en silencio si el campo estaba vacío: así se
    // colaban eventos sin saber cuándo ocurrieron. Ahora el API lo exige (422).
    const m = parseInt(minuto, 10);
    if (Number.isNaN(m) || m < 0 || m > 130) {
      Alert.alert("Falta el minuto", "Escribe el minuto del partido (entre 0 y 130)."); return;
    }
    setGuardando(true);
    const cuerpo = { tipo, equipo_id: equipoSel, minuto: m };
    if (principal != null) cuerpo.jugador_id = principal;
    if (secundario != null) cuerpo.jugador_secundario_id = secundario;
    if (esGol) cuerpo.subtipo = subtipo;
    try {
      await apiPost(`/partidos/${partidoId}/eventos`, cuerpo);
      navigation.goBack();
    } catch (e) {
      Alert.alert("Error", e.message || "No se pudo registrar");
    } finally {
      setGuardando(false);
    }
  }

  if (cargando || !partido) {
    return <View style={ls.screen}><ActivityIndicator color={lp.maroon} style={{ marginTop: 40 }} /></View>;
  }

  return (
    <ScrollView style={ls.screen} contentContainerStyle={ls.content}>
      {/* Selector de equipo */}
      <View style={ls.tabs}>
        {[partido.equipo_local_id, partido.equipo_visitante_id].filter(Boolean).map((id) => (
          <TouchableOpacity key={id} style={[ls.tab, equipoSel === id && { backgroundColor: lp.green }]} onPress={() => elegirEquipo(id)}>
            <Text style={[ls.tabText, equipoSel === id && ls.tabTextActive]}>{planes[id]?.nombre || "Equipo"}</Text>
          </TouchableOpacity>
        ))}
      </View>

      {esCambio ? (
        <>
          <Text style={ls.sectionTitle}>Jugador que sale (en cancha)</Text>
          <ListaJugadores jugadores={enCancha} seleccion={principal} onSelect={setPrincipal}
            vacio="No hay jugadores en el campo." />
          <Text style={ls.sectionTitle}>Jugador que entra (banca)</Text>
          <ListaJugadores jugadores={entrantes} seleccion={secundario} onSelect={setSecundario}
            vacio="No hay suplentes disponibles." />
        </>
      ) : (
        <>
          <Text style={ls.sectionTitle}>{esGol ? "Jugador anotador" : "Jugador"}</Text>
          <ListaJugadores jugadores={enCancha} seleccion={principal} onSelect={setPrincipal}
            vacio="El entrenador no cargó la alineación. Puedes registrar sin jugador." />

          {esGol && (
            <>
              <Text style={ls.sectionTitle}>Asistencia (opcional)</Text>
              <ListaJugadores jugadores={asistentes} seleccion={secundario} onSelect={setSecundario} />
            </>
          )}
        </>
      )}

      {/* Minuto */}
      <Text style={[ls.muted, { fontWeight: "700", marginTop: 10, marginBottom: 6 }]}>Minuto</Text>
      <TextInput
        style={{ backgroundColor: lp.surface, borderColor: lp.surfaceBorder, borderWidth: 1, borderRadius: 10, color: lp.textDark, paddingHorizontal: 14, paddingVertical: 12 }}
        keyboardType="number-pad" placeholder="Ej. 67" placeholderTextColor={lp.textMuted}
        value={minuto} onChangeText={setMinuto}
      />

      {/* Tipo de gol */}
      {esGol && (
        <>
          <Text style={[ls.muted, { fontWeight: "700", marginTop: 14, marginBottom: 6 }]}>Tipo de gol</Text>
          <View style={ls.tabs}>
            {[["normal", "Normal"], ["penal", "Penal"], ["autogol", "Autogol"]].map(([k, label]) => (
              <TouchableOpacity key={k} style={[ls.tab, subtipo === k && { backgroundColor: lp.green }]} onPress={() => setSubtipo(k)}>
                <Text style={[ls.tabText, subtipo === k && ls.tabTextActive]}>{label}</Text>
              </TouchableOpacity>
            ))}
          </View>
          {subtipo === "autogol" && (
            <Text style={[ls.muted, { marginTop: 8 }]}>El gol contará para el equipo rival.</Text>
          )}
        </>
      )}

      <TouchableOpacity style={confirmar_btn} onPress={confirmar} disabled={guardando}>
        <Text style={{ color: lp.white, fontWeight: "800", fontSize: 15 }}>
          {guardando ? "Guardando..." : "Confirmar evento"}
        </Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const circulo = { width: 36, height: 36, borderRadius: 18, backgroundColor: lp.surfaceBorder, alignItems: "center", justifyContent: "center", marginRight: 12 };
const confirmar_btn = { backgroundColor: lp.red, borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 20 };
