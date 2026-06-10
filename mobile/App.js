// Punto de entrada: navegación + contexto de autenticación.
import React from "react";
import { View, Text, TouchableOpacity } from "react-native";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer, DefaultTheme, useNavigation } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";

import { AuthProvider, useAuth, rutaPanel } from "./src/auth";
import { colors } from "./src/theme";
import { lp, ls } from "./src/publicTheme";

// Pantallas públicas (tema claro)
import InicioScreen from "./src/screens/public/InicioScreen";
import TorneosScreen from "./src/screens/public/TorneosScreen";
import TorneoStatsScreen from "./src/screens/public/TorneoStatsScreen";
import TorneoInfoScreen from "./src/screens/public/TorneoInfoScreen";

// Panel del entrenador (tema claro, cabecera dorada)
import CoachHomeScreen from "./src/screens/coach/CoachHomeScreen";
import TeamListScreen from "./src/screens/coach/TeamListScreen";
import TeamEditScreen from "./src/screens/coach/TeamEditScreen";
import TeamStatsScreen from "./src/screens/coach/TeamStatsScreen";
import PerfilScreen from "./src/screens/coach/PerfilScreen";
import LineupMatchesScreen from "./src/screens/coach/LineupMatchesScreen";
import LineupScreen from "./src/screens/coach/LineupScreen";
import InvitePlayersScreen from "./src/screens/coach/InvitePlayersScreen";
import InvitationsScreen from "./src/screens/InvitationsScreen";

// Pantallas de cuenta / roles (tema oscuro)
import LoginScreen from "./src/screens/LoginScreen";
import RegisterPlayerScreen from "./src/screens/RegisterPlayerScreen";
import RegisterStaffScreen from "./src/screens/RegisterStaffScreen";
import ChangePasswordScreen from "./src/screens/ChangePasswordScreen";
import HomeScreen from "./src/screens/HomeScreen";
import RefereeMatchesScreen from "./src/screens/RefereeMatchesScreen";
import RefereeLiveScreen from "./src/screens/RefereeLiveScreen";

const Stack = createNativeStackNavigator();
const Tab = createBottomTabNavigator();

const navTheme = {
  ...DefaultTheme,
  colors: { ...DefaultTheme.colors, background: lp.bg, card: lp.bg, text: lp.textDark, border: lp.surfaceBorder, primary: lp.accent },
};

// Botón de "Ingresar" / "Mi panel" en la cabecera de las pestañas públicas.
function LoginButton() {
  const { usuario } = useAuth();
  const navigation = useNavigation();
  return (
    <TouchableOpacity style={ls.loginPill} onPress={() => navigation.navigate(usuario ? rutaPanel(usuario) : "Login")}>
      <Text style={ls.loginPillText}>{usuario ? "Mi panel" : "Ingresar"}</Text>
    </TouchableOpacity>
  );
}

// Indicador (puntito) de cada pestaña, como en el mockup.
function Punto({ focused }) {
  return <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: focused ? lp.accent : "#C7C2B5" }} />;
}

const lightHeader = {
  headerStyle: { backgroundColor: lp.bg },
  headerTintColor: lp.textDark,
  headerTitleStyle: { color: lp.textDark, fontWeight: "800", letterSpacing: 1 },
  headerShadowVisible: false,
};

function PublicTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        ...lightHeader,
        headerRight: () => <LoginButton />,
        tabBarActiveTintColor: lp.accent,
        tabBarInactiveTintColor: lp.textMuted,
        tabBarStyle: { backgroundColor: lp.bg, borderTopColor: lp.surfaceBorder },
        tabBarIcon: ({ focused }) => <Punto focused={focused} />,
      }}
    >
      <Tab.Screen name="Inicio" component={InicioScreen} options={{ title: "INICIO" }} />
      <Tab.Screen name="Torneos" component={TorneosScreen} options={{ title: "TORNEOS" }} />
    </Tab.Navigator>
  );
}

// Cabecera oscura para las pantallas de cuenta/roles
const darkHeader = {
  headerStyle: { backgroundColor: colors.pitch800 },
  headerTintColor: colors.chalk,
  headerTitleStyle: { color: colors.chalk },
};

// Cabecera dorada del panel del entrenador
const goldHeader = {
  headerStyle: { backgroundColor: lp.gold },
  headerTintColor: lp.goldText,
  headerTitleStyle: { color: lp.goldText, fontWeight: "800", letterSpacing: 1 },
  headerShadowVisible: false,
};

function CoachTabs() {
  return (
    <Tab.Navigator
      screenOptions={{
        ...goldHeader,
        tabBarActiveTintColor: lp.accent,
        tabBarInactiveTintColor: lp.textMuted,
        tabBarStyle: { backgroundColor: lp.bg, borderTopColor: lp.surfaceBorder },
        tabBarIcon: ({ focused }) => <Punto focused={focused} />,
      }}
    >
      <Tab.Screen name="Inicio" component={CoachHomeScreen} options={{ title: "INICIO" }} />
      <Tab.Screen name="Equipos" component={TeamListScreen} options={{ title: "MIS EQUIPOS" }} />
      <Tab.Screen name="Torneos" component={TorneosScreen} options={{ title: "TORNEOS" }} />
      <Tab.Screen name="Perfil" component={PerfilScreen} options={{ title: "PERFIL" }} />
    </Tab.Navigator>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="dark" />
      <NavigationContainer theme={navTheme}>
        <Stack.Navigator initialRouteName="Public">
          {/* Área pública con pestañas inferiores */}
          <Stack.Screen name="Public" component={PublicTabs} options={{ headerShown: false }} />

          {/* Detalle de torneo (tema claro) */}
          <Stack.Screen name="TorneoStats" component={TorneoStatsScreen} options={{ ...lightHeader, title: "TORNEO" }} />
          <Stack.Screen name="TorneoInfo" component={TorneoInfoScreen} options={{ ...lightHeader, title: "TORNEO" }} />

          {/* Panel del entrenador (tema claro, cabecera dorada) */}
          <Stack.Screen name="Coach" component={CoachTabs} options={{ headerShown: false }} />
          <Stack.Screen name="TeamEdit" component={TeamEditScreen} options={{ ...goldHeader, title: "EQUIPO" }} />
          <Stack.Screen name="TeamStats" component={TeamStatsScreen} options={{ ...goldHeader, title: "ESTADÍSTICAS" }} />
          <Stack.Screen name="LineupMatches" component={LineupMatchesScreen} options={{ ...goldHeader, title: "ALINEACIÓN" }} />
          <Stack.Screen name="Lineup" component={LineupScreen} options={{ ...goldHeader, title: "ALINEACIÓN" }} />
          <Stack.Screen name="InvitePlayers" component={InvitePlayersScreen} options={{ ...goldHeader, title: "INVITAR" }} />

          {/* Cuenta / roles (tema oscuro) */}
          <Stack.Screen name="Login" component={LoginScreen} options={{ ...darkHeader, title: "Ingresar" }} />
          <Stack.Screen name="RegisterPlayer" component={RegisterPlayerScreen} options={{ ...darkHeader, title: "Crear cuenta" }} />
          <Stack.Screen name="RegisterStaff" component={RegisterStaffScreen} options={{ ...darkHeader, title: "Entrenador / Árbitro" }} />
          <Stack.Screen name="ChangePassword" component={ChangePasswordScreen} options={{ ...darkHeader, title: "Cambiar contraseña" }} />
          <Stack.Screen name="Home" component={HomeScreen} options={{ ...darkHeader, title: "Mi panel" }} />
          <Stack.Screen name="Invitations" component={InvitationsScreen} options={{ ...darkHeader, title: "Invitaciones" }} />
          <Stack.Screen name="RefereeMatches" component={RefereeMatchesScreen} options={{ ...darkHeader, title: "Mis partidos" }} />
          <Stack.Screen name="RefereeLive" component={RefereeLiveScreen} options={{ ...darkHeader, title: "Partido en vivo" }} />
        </Stack.Navigator>
      </NavigationContainer>
    </AuthProvider>
  );
}
