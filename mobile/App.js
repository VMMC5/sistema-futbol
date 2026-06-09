// Punto de entrada: navegación + contexto de autenticación.
import React from "react";
import { StatusBar } from "expo-status-bar";
import { NavigationContainer, DefaultTheme } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";

import { AuthProvider } from "./src/auth";
import { colors } from "./src/theme";

import LandingScreen from "./src/screens/LandingScreen";
import LoginScreen from "./src/screens/LoginScreen";
import RegisterPlayerScreen from "./src/screens/RegisterPlayerScreen";
import RegisterStaffScreen from "./src/screens/RegisterStaffScreen";
import ChangePasswordScreen from "./src/screens/ChangePasswordScreen";
import HomeScreen from "./src/screens/HomeScreen";
import RefereeMatchesScreen from "./src/screens/RefereeMatchesScreen";
import RefereeLiveScreen from "./src/screens/RefereeLiveScreen";

const Stack = createNativeStackNavigator();

// Tema de navegación con los colores de la app.
const navTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background: colors.pitch900,
    card: colors.pitch800,
    text: colors.chalk,
    border: colors.line,
    primary: colors.lime,
  },
};

const headerStyle = {
  headerStyle: { backgroundColor: colors.pitch800 },
  headerTintColor: colors.chalk,
  headerTitleStyle: { color: colors.chalk },
};

export default function App() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <NavigationContainer theme={navTheme}>
        <Stack.Navigator initialRouteName="Landing">
          <Stack.Screen name="Landing" component={LandingScreen} options={{ headerShown: false }} />
          <Stack.Screen name="Login" component={LoginScreen} options={{ ...headerStyle, title: "Ingresar" }} />
          <Stack.Screen name="RegisterPlayer" component={RegisterPlayerScreen} options={{ ...headerStyle, title: "Crear cuenta" }} />
          <Stack.Screen name="RegisterStaff" component={RegisterStaffScreen} options={{ ...headerStyle, title: "Entrenador / Árbitro" }} />
          <Stack.Screen name="ChangePassword" component={ChangePasswordScreen} options={{ ...headerStyle, title: "Cambiar contraseña", headerBackVisible: false, gestureEnabled: false }} />
          <Stack.Screen name="Home" component={HomeScreen} options={{ ...headerStyle, title: "Mi panel", headerBackVisible: false }} />
          <Stack.Screen name="RefereeMatches" component={RefereeMatchesScreen} options={{ ...headerStyle, title: "Mis partidos" }} />
          <Stack.Screen name="RefereeLive" component={RefereeLiveScreen} options={{ ...headerStyle, title: "Partido en vivo" }} />
        </Stack.Navigator>
      </NavigationContainer>
    </AuthProvider>
  );
}
