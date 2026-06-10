// Contexto de autenticación: guarda el token y el usuario, y expone login/logout.
import React, { createContext, useContext, useEffect, useState } from "react";
import { apiGet, apiPost, guardarToken, leerToken, borrarToken } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

  // Al abrir la app, si hay token guardado intentamos recuperar el usuario.
  useEffect(() => {
    (async () => {
      try {
        const t = await leerToken();
        if (t) {
          const me = await apiGet("/auth/me");
          setUsuario(me);
        }
      } catch (_) {
        await borrarToken();
      } finally {
        setCargando(false);
      }
    })();
  }, []);

  async function login(correo, password) {
    const r = await apiPost("/auth/login", { correo, password }, false);
    await guardarToken(r.access_token);
    const me = await apiGet("/auth/me");
    setUsuario(me);
    return { debeCambiar: r.debe_cambiar_password, usuario: me };
  }

  async function refrescar() {
    const me = await apiGet("/auth/me");
    setUsuario(me);
    return me;
  }

  async function logout() {
    await borrarToken();
    setUsuario(null);
  }

  return (
    <AuthContext.Provider value={{ usuario, cargando, login, logout, refrescar }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

// Devuelve la ruta del panel según el rol del usuario.
export function rutaPanel(usuario) {
  if (usuario?.rol === "entrenador") return "Coach";
  if (usuario?.rol === "arbitro") return "Referee";
  return "Home";
}
