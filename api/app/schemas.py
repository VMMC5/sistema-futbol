"""
Esquemas Pydantic: definen y validan la forma de los datos que entran y
salen de la API. La validación en el servidor es la barrera real de seguridad
(la del cliente solo mejora la experiencia).
"""
from pydantic import BaseModel, EmailStr, Field


# ---------- Registro ----------
class RegistroUsuario(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    telefono: str | None = Field(default=None, max_length=20)


# ---------- Login ----------
class LoginRequest(BaseModel):
    correo: EmailStr
    password: str


# ---------- Respuestas ----------
class UsuarioOut(BaseModel):
    id: int
    nombre: str
    correo: EmailStr
    rol: str
    activo: bool
    telefono: str | None = None

    # Permite construir el esquema desde un objeto SQLAlchemy
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    debe_cambiar_password: bool = False


# ======================================================================
#  TORNEOS  (plantilla de CRUD para replicar en otros modulos)
# ======================================================================
from datetime import datetime, date
from pydantic import model_validator

_ESTADOS_TORNEO = "^(programado|en_curso|finalizado)$"


class TorneoBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    sede_id: int
    descripcion: str | None = None
    tipo: str | None = Field(default=None, max_length=40)
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    fecha_cierre_inscripciones: date | None = None
    cuota_inscripcion: float | None = Field(default=None, ge=0)
    premio: str | None = Field(default=None, max_length=200)
    cupo_maximo: int | None = Field(default=None, gt=0)


class TorneoCreate(TorneoBase):
    estado: str = Field(default="programado", pattern=_ESTADOS_TORNEO)

    @model_validator(mode="after")
    def _fechas_coherentes(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class TorneoUpdate(BaseModel):
    # Todos opcionales: actualizacion parcial
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    sede_id: int | None = None
    descripcion: str | None = None
    tipo: str | None = Field(default=None, max_length=40)
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    fecha_cierre_inscripciones: date | None = None
    cuota_inscripcion: float | None = Field(default=None, ge=0)
    premio: str | None = Field(default=None, max_length=200)
    cupo_maximo: int | None = Field(default=None, gt=0)
    estado: str | None = Field(default=None, pattern=_ESTADOS_TORNEO)


class TorneoOut(TorneoBase):
    id: int
    estado: str
    sede_nombre: str | None = None

    model_config = {"from_attributes": True}


# ======================================================================
#  RESERVAS  (incluye la regla de no solapar horarios en una cancha)
# ======================================================================
from datetime import date, time

_ESTADOS_RESERVA = "^(pendiente|confirmada|cancelada)$"


class ReservaCreate(BaseModel):
    # OJO: el usuario NO se envia aqui; se toma del token (no se puede
    # reservar a nombre de otra persona).
    cancha_id: int
    fecha: date
    hora_inicio: time
    hora_fin: time

    @model_validator(mode="after")
    def _horas_coherentes(self):
        if self.hora_fin <= self.hora_inicio:
            raise ValueError("hora_fin debe ser posterior a hora_inicio")
        return self


class ReservaOut(BaseModel):
    id: int
    usuario_id: int
    usuario_nombre: str | None = None
    cancha_id: int
    cancha_nombre: str | None = None
    fecha: date
    hora_inicio: time
    hora_fin: time
    estado: str
    pago_id: int | None = None

    model_config = {"from_attributes": True}


class CambioEstadoReserva(BaseModel):
    estado: str = Field(pattern=_ESTADOS_RESERVA)


# ======================================================================
#  PARTIDOS Y EVENTOS EN VIVO  (modulo del arbitro)
# ======================================================================
_ESTADOS_PARTIDO = "^(programado|en_juego|finalizado)$"
_TIPOS_EVENTO = "^(gol|tarjeta_amarilla|tarjeta_roja|cambio)$"


class PartidoCreate(BaseModel):
    torneo_id: int
    equipo_local_id: int
    equipo_visitante_id: int
    cancha_id: int | None = None
    arbitro_id: int | None = None
    fecha_hora: datetime | None = None

    @model_validator(mode="after")
    def _equipos_distintos(self):
        if self.equipo_local_id == self.equipo_visitante_id:
            raise ValueError("un equipo no puede jugar contra si mismo")
        return self


class PartidoUpdate(BaseModel):
    # El estado NO se cambia aqui: se usa /iniciar y /finalizar.
    cancha_id: int | None = None
    arbitro_id: int | None = None
    fecha_hora: datetime | None = None


class PartidoOut(BaseModel):
    id: int
    torneo_id: int
    torneo_nombre: str | None = None
    cancha_id: int | None = None
    cancha_nombre: str | None = None
    arbitro_id: int | None = None
    arbitro_nombre: str | None = None
    equipo_local_id: int | None = None
    equipo_local_nombre: str | None = None
    equipo_visitante_id: int | None = None
    equipo_visitante_nombre: str | None = None
    fecha_hora: datetime | None = None
    goles_local: int
    goles_visitante: int
    estado: str
    acta_firmada: bool = False

    model_config = {"from_attributes": True}


class EventoCreate(BaseModel):
    tipo: str = Field(pattern=_TIPOS_EVENTO)
    equipo_id: int
    jugador_id: int | None = None
    jugador_secundario_id: int | None = None     # asistente (gol) o quien entra (cambio)
    subtipo: str | None = Field(default=None, pattern="^(normal|penal|autogol)$")
    minuto: int | None = Field(default=None, ge=0, le=130)
    detalle: str | None = Field(default=None, max_length=120)


class EventoOut(BaseModel):
    id: int
    partido_id: int
    equipo_id: int | None = None
    equipo_nombre: str | None = None
    jugador_id: int | None = None
    jugador_nombre: str | None = None
    jugador_secundario_id: int | None = None
    jugador_secundario_nombre: str | None = None
    tipo: str
    subtipo: str | None = None
    minuto: int | None = None
    detalle: str | None = None

    model_config = {"from_attributes": True}


# ======================================================================
#  ALINEACIONES  (quien juega en un partido; lo define el entrenador)
# ======================================================================
class AlineacionCreate(BaseModel):
    equipo_id: int
    jugador_id: int
    titular: bool = True
    posicion: str | None = Field(default=None, max_length=30)


class AlineacionOut(BaseModel):
    id: int
    partido_id: int
    equipo_id: int
    equipo_nombre: str | None = None
    jugador_id: int
    jugador_nombre: str | None = None
    titular: bool
    posicion: str | None = None

    model_config = {"from_attributes": True}


# ======================================================================
#  ESTADISTICAS  (se calculan a partir de eventos y resultados)
# ======================================================================
class GoleadorOut(BaseModel):
    jugador_id: int
    nombre: str
    goles: int


class TarjetasJugadorOut(BaseModel):
    jugador_id: int
    nombre: str
    amarillas: int
    rojas: int


class FilaTabla(BaseModel):
    equipo_id: int
    equipo: str
    pj: int   # partidos jugados
    pg: int   # ganados
    pe: int   # empatados
    pp: int   # perdidos
    gf: int   # goles a favor
    gc: int   # goles en contra
    dg: int   # diferencia de goles
    puntos: int


# ======================================================================
#  SEDES
# ======================================================================
class SedeCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    ciudad: str | None = Field(default=None, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)


class SedeUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=100)
    direccion: str | None = Field(default=None, max_length=200)
    ciudad: str | None = Field(default=None, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)


class SedeOut(BaseModel):
    id: int
    nombre: str
    direccion: str | None = None
    ciudad: str | None = None
    telefono: str | None = None

    model_config = {"from_attributes": True}


# ======================================================================
#  CANCHAS
# ======================================================================
_TIPOS_CANCHA = "^(futbol 5|futbol 7|futbol 11)$"


class CanchaCreate(BaseModel):
    sede_id: int
    nombre: str = Field(min_length=1, max_length=60)
    tipo: str | None = Field(default=None, pattern=_TIPOS_CANCHA)
    precio_hora: float | None = Field(default=None, ge=0)
    disponible: bool = True


class CanchaUpdate(BaseModel):
    sede_id: int | None = None
    nombre: str | None = Field(default=None, min_length=1, max_length=60)
    tipo: str | None = Field(default=None, pattern=_TIPOS_CANCHA)
    precio_hora: float | None = Field(default=None, ge=0)
    disponible: bool | None = None


class CanchaOut(BaseModel):
    id: int
    sede_id: int
    sede_nombre: str | None = None
    nombre: str
    tipo: str | None = None
    precio_hora: float | None = None
    disponible: bool

    model_config = {"from_attributes": True}


# ======================================================================
#  USUARIOS  (gestion por el administrador)
# ======================================================================
class UsuarioAdminCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    correo: EmailStr
    password: str = Field(min_length=8, max_length=128)
    rol: str   # nombre del rol: jugador | entrenador | arbitro | superadmin
    telefono: str | None = Field(default=None, max_length=20)


class UsuarioAdminUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)
    rol: str | None = None
    activo: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)  # reset opcional


class UsuarioAdminOut(BaseModel):
    id: int
    nombre: str
    correo: EmailStr
    rol: str
    telefono: str | None = None
    activo: bool


# ======================================================================
#  SOLICITUDES DE REGISTRO (entrenador / arbitro) y cambio de contrasena
# ======================================================================
class SolicitudOut(BaseModel):
    id: int
    nombre: str
    correo: EmailStr
    telefono: str | None = None
    rol_solicitado: str
    documento_nombre: str | None = None
    estado: str
    motivo: str | None = None

    model_config = {"from_attributes": True}


class RechazoSolicitud(BaseModel):
    motivo: str | None = Field(default=None, max_length=255)


class CambioPassword(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8, max_length=128)


# ======================================================================
#  EQUIPOS y PLANTILLA (panel del entrenador)
# ======================================================================
class JugadorEquipoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    posicion: str | None = Field(default=None, max_length=30)
    dorsal: int | None = Field(default=None, ge=0, le=999)


class JugadorEquipoOut(BaseModel):
    id: int
    nombre: str | None = None
    posicion: str | None = None
    dorsal: int | None = None
    jugador_id: int | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def _nombre_efectivo(cls, obj):
        # Permite construir desde el modelo usando nombre_jugador
        if hasattr(obj, "nombre_jugador"):
            return {
                "id": obj.id,
                "nombre": obj.nombre_jugador,
                "posicion": obj.posicion,
                "dorsal": obj.dorsal,
                "jugador_id": obj.jugador_id,
            }
        return obj


class EquipoCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)
    color: str | None = Field(default=None, max_length=40)
    categoria: str | None = Field(default=None, max_length=40)
    escudo_url: str | None = Field(default=None, max_length=255)


class EquipoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    color: str | None = Field(default=None, max_length=40)
    categoria: str | None = Field(default=None, max_length=40)
    escudo_url: str | None = Field(default=None, max_length=255)


class EquipoOut(BaseModel):
    id: int
    nombre: str
    color: str | None = None
    categoria: str | None = None
    escudo_url: str | None = None
    entrenador_id: int
    jugadores: list[JugadorEquipoOut] = []
    jugadores_count: int = 0

    model_config = {"from_attributes": True}


# ======================================================================
#  PLAN DE ALINEACIÓN (formación del entrenador)
# ======================================================================
class PlanItemIn(BaseModel):
    jugador_equipo_id: int
    posicion: str | None = Field(default=None, max_length=30)  # etiqueta del hueco
    orden: int = 0                                             # índice del hueco en la formación


class PlanIn(BaseModel):
    equipo_id: int
    formacion: str = Field(default="4-4-2", max_length=10)
    jugadores: list[PlanItemIn] = []


class PlanItemOut(BaseModel):
    jugador_equipo_id: int
    jugador_id: int | None = None   # usuario registrado (para el árbitro)
    nombre: str | None = None
    dorsal: int | None = None
    posicion: str | None = None
    orden: int = 0


class PlanOut(BaseModel):
    partido_id: int
    equipo_id: int
    formacion: str
    jugadores: list[PlanItemOut] = []
    suplentes: list[PlanItemOut] = []


# ======================================================================
#  INVITACIONES A EQUIPO (jugadores registrados)
# ======================================================================
class JugadorDisponibleOut(BaseModel):
    id: int            # id del usuario
    nombre: str
    correo: EmailStr

    model_config = {"from_attributes": True}


class InvitacionCrear(BaseModel):
    jugador_id: int


class InvitacionOut(BaseModel):
    id: int
    equipo_id: int
    equipo_nombre: str | None = None
    entrenador_nombre: str | None = None
    jugador_id: int
    jugador_nombre: str | None = None
    estado: str

    model_config = {"from_attributes": True}


class JugadorEquipoUpdate(BaseModel):
    dorsal: int | None = Field(default=None, ge=0, le=999)
    posicion: str | None = Field(default=None, max_length=30)


# ======================================================================
#  NOTIFICACIONES y PERFIL del jugador
# ======================================================================
class NotificacionOut(BaseModel):
    id: int
    titulo: str | None = None
    mensaje: str
    leida: bool
    creada_en: datetime | None = None

    model_config = {"from_attributes": True}


class DispositivoRegistro(BaseModel):
    token: str = Field(min_length=1, max_length=255)
    plataforma: str | None = Field(default=None, max_length=20)


class PerfilUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=80)
    telefono: str | None = Field(default=None, max_length=20)


# ======================================================================
#  PAGOS
# ======================================================================
from typing import Literal
from pydantic import field_validator


class DatosTarjeta(BaseModel):
    numero: str
    exp_mes: int = Field(ge=1, le=12)
    exp_anio: int
    cvv: str
    titular: str = Field(min_length=2, max_length=80)

    @field_validator("numero")
    @classmethod
    def _numero_valido(cls, v: str) -> str:
        limpio = v.replace(" ", "")
        if not limpio.isdigit() or not (13 <= len(limpio) <= 19):
            raise ValueError("número de tarjeta inválido")
        return limpio

    @field_validator("cvv")
    @classmethod
    def _cvv_valido(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 3:
            raise ValueError("CVV inválido")
        return v


class PagoCreate(BaseModel):
    metodo: Literal["tarjeta", "transferencia"]
    tarjeta: DatosTarjeta | None = None

    @model_validator(mode="after")
    def _coherencia(self):
        if self.metodo == "tarjeta":
            if self.tarjeta is None:
                raise ValueError("faltan los datos de la tarjeta")
            hoy = datetime.now()
            if (self.tarjeta.exp_anio, self.tarjeta.exp_mes) < (hoy.year, hoy.month):
                raise ValueError("la tarjeta está vencida")
        return self


class PagoOut(BaseModel):
    id: int
    concepto: str | None = None
    monto: float
    metodo: str
    estado: str
    referencia: str | None = None
    creado_en: datetime | None = None
    completado_en: datetime | None = None
    usuario_nombre: str | None = None

    model_config = {"from_attributes": True}


# ======================================================================
#  INSCRIPCIONES (equipo a torneo)
# ======================================================================
class InscripcionCreate(BaseModel):
    torneo_id: int
    equipo_id: int


class InscripcionOut(BaseModel):
    id: int
    torneo_id: int
    torneo_nombre: str | None = None
    equipo_id: int
    equipo_nombre: str | None = None
    estado: str
    pago_id: int | None = None

    model_config = {"from_attributes": True}
