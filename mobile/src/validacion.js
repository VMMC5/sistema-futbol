// Validaciones de formulario del lado del cliente.
// La barrera REAL de seguridad es Pydantic en la API; esto solo mejora la
// experiencia: avisa antes de enviar y evita mostrar errores 422 crudos.
// Las reglas replican las del servidor (ver api/app/schemas.py) para que
// cliente y servidor coincidan.

// Formato de correo: suficiente para uso, no pretende cubrir el RFC completo.
const RE_CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function esCorreo(v) {
  return typeof v === "string" && RE_CORREO.test(v.trim());
}

// Devuelve un mensaje de error (string) o null si todo está bien.

export function validarRegistroJugador({ nombre, correo, password }) {
  if (nombre.trim().length < 2) return "Escribe tu nombre (mínimo 2 caracteres).";
  if (!esCorreo(correo)) return "Escribe un correo válido (ej. nombre@correo.com).";
  if (password.length < 8) return "La contraseña debe tener al menos 8 caracteres.";
  return null;
}

export function validarSolicitudStaff({ nombre, correo }) {
  if (nombre.trim().length < 2) return "Escribe tu nombre (mínimo 2 caracteres).";
  if (!esCorreo(correo)) return "Escribe un correo válido (ej. nombre@correo.com).";
  return null;
}

// Tarjeta: mismas reglas que schemas.DatosTarjeta (numero 13–19 dígitos,
// cvv 3–4 dígitos, mes 1–12, y que no esté vencida).
export function validarTarjeta({ numero, cvv, titular, expMes, expAnio }) {
  const num = String(numero).replace(/\s/g, "");
  if (!/^\d{13,19}$/.test(num)) return "Número de tarjeta inválido (13 a 19 dígitos).";
  if (!/^\d{3,4}$/.test(String(cvv))) return "CVV inválido (3 o 4 dígitos).";
  if (titular.trim().length < 2) return "Escribe el nombre del titular.";

  const mes = parseInt(expMes, 10);
  const anio = parseInt(expAnio, 10);
  if (Number.isNaN(mes) || mes < 1 || mes > 12) return "Mes de expiración inválido (1 a 12).";
  if (Number.isNaN(anio) || String(expAnio).length !== 4) return "Año de expiración inválido (AAAA).";

  const hoy = new Date();
  if (anio < hoy.getFullYear() || (anio === hoy.getFullYear() && mes < hoy.getMonth() + 1)) {
    return "La tarjeta está vencida.";
  }
  return null;
}
