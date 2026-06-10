"""
Modelos de la base de datos — Sistema Integral de Canchas y Torneos.

Traducción del diagrama relacional (14 entidades) a modelos SQLAlchemy.

NOTA sobre el alcance:
- Las tablas puente/hijas (jugadores_equipo, alineaciones, eventos_partido,
  inscripciones) tienen las columnas EXACTAS del diagrama.
- En las tablas principales (usuarios, sedes, canchas, torneos, reservas,
  equipos, partidos, pagos, notificaciones) se completaron columnas razonables
  a partir de los requerimientos del proyecto. Revísalas contra tu diagrama y
  ajusta nombres/tipos si hace falta antes de generar la primera migración.

Convención: los "estados" y "tipos" se modelan como texto (String) en lugar de
ENUM de PostgreSQL, porque son más fáciles de migrar y ampliar. La validación
de valores permitidos se hace en los esquemas Pydantic de la API.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy import Column

from app.database import Base


# ----------------------------------------------------------------------
# 1. roles  (1:N -> usuarios)
# ----------------------------------------------------------------------
class Rol(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(30), unique=True, nullable=False)  # jugador, entrenador, arbitro, superadmin

    usuarios = relationship("Usuario", back_populates="rol")


# ----------------------------------------------------------------------
# 2. usuarios  (FK rol_id) — actor central del sistema
# ----------------------------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)

    nombre = Column(String(80), nullable=False)
    correo = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)  # NUNCA la contraseña en texto plano
    telefono = Column(String(20))
    activo = Column(Boolean, default=True, nullable=False)
    debe_cambiar_password = Column(Boolean, default=False, nullable=False)
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    rol = relationship("Rol", back_populates="usuarios")
    reservas = relationship("Reserva", back_populates="usuario")
    pagos = relationship("Pago", back_populates="usuario")
    equipos = relationship("Equipo", back_populates="entrenador")
    partidos_arbitrados = relationship("Partido", back_populates="arbitro")
    notificaciones = relationship("Notificacion", back_populates="usuario")
    membresias = relationship("JugadorEquipo", back_populates="jugador")


# ----------------------------------------------------------------------
# 3. sedes  (1:N -> canchas, torneos)
# ----------------------------------------------------------------------
class Sede(Base):
    __tablename__ = "sedes"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    direccion = Column(String(200))
    ciudad = Column(String(80))
    telefono = Column(String(20))

    canchas = relationship("Cancha", back_populates="sede")
    torneos = relationship("Torneo", back_populates="sede")


# ----------------------------------------------------------------------
# 4. canchas  (FK sede_id) (1:N -> reservas, partidos)
# ----------------------------------------------------------------------
class Cancha(Base):
    __tablename__ = "canchas"

    id = Column(Integer, primary_key=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)

    nombre = Column(String(60), nullable=False)
    tipo = Column(String(30))            # futbol 5, futbol 7, futbol 11, etc.
    precio_hora = Column(Numeric(10, 2))
    disponible = Column(Boolean, default=True, nullable=False)

    sede = relationship("Sede", back_populates="canchas")
    reservas = relationship("Reserva", back_populates="cancha")
    partidos = relationship("Partido", back_populates="cancha")

    @property
    def sede_nombre(self):
        return self.sede.nombre if self.sede else None


# ----------------------------------------------------------------------
# 5. torneos  (FK sede_id) (1:N -> partidos, inscripciones)
# ----------------------------------------------------------------------
class Torneo(Base):
    __tablename__ = "torneos"

    id = Column(Integer, primary_key=True)
    sede_id = Column(Integer, ForeignKey("sedes.id"), nullable=False)

    nombre = Column(String(100), nullable=False)
    descripcion = Column(Text)
    tipo = Column(String(40))                              # liga, eliminacion directa, etc.
    fecha_inicio = Column(DateTime(timezone=True))
    fecha_fin = Column(DateTime(timezone=True))
    fecha_cierre_inscripciones = Column(Date)              # cierre de inscripciones
    cuota_inscripcion = Column(Numeric(10, 2))             # cuota para entrar
    premio = Column(String(200))                           # premio al equipo ganador
    estado = Column(String(20), default="programado")  # programado, en_curso, finalizado
    cupo_maximo = Column(Integer)

    sede = relationship("Sede", back_populates="torneos")
    partidos = relationship("Partido", back_populates="torneo")
    inscripciones = relationship("Inscripcion", back_populates="torneo")

    @property
    def sede_nombre(self):
        return self.sede.nombre if self.sede else None


# ----------------------------------------------------------------------
# 6. reservas  (FK usuario_id, cancha_id; pago 1:1)
# ----------------------------------------------------------------------
class Reserva(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    cancha_id = Column(Integer, ForeignKey("canchas.id"), nullable=False)
    # 1:1 con pago -> la FK es única para que una reserva tenga a lo sumo un pago
    pago_id = Column(Integer, ForeignKey("pagos.id"), unique=True)

    fecha = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    estado = Column(String(20), default="pendiente")  # pendiente, confirmada, cancelada

    usuario = relationship("Usuario", back_populates="reservas")
    cancha = relationship("Cancha", back_populates="reservas")
    pago = relationship("Pago", back_populates="reserva")

    @property
    def usuario_nombre(self):
        return self.usuario.nombre if self.usuario else None

    @property
    def cancha_nombre(self):
        return self.cancha.nombre if self.cancha else None


# ----------------------------------------------------------------------
# 7. equipos  (FK entrenador_id -> usuarios)
# ----------------------------------------------------------------------
class Equipo(Base):
    __tablename__ = "equipos"

    id = Column(Integer, primary_key=True)
    entrenador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    nombre = Column(String(80), nullable=False)
    color = Column(String(40))                             # color / uniforme
    categoria = Column(String(40))                         # Liga A, Sub-17, Liga F, etc.
    escudo_url = Column(String(255))
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    entrenador = relationship("Usuario", back_populates="equipos")
    jugadores = relationship("JugadorEquipo", back_populates="equipo")
    inscripciones = relationship("Inscripcion", back_populates="equipo")


# ----------------------------------------------------------------------
# 8. partidos  (FK torneo_id, cancha_id, arbitro_id; equipos local/visitante)
# ----------------------------------------------------------------------
class Partido(Base):
    __tablename__ = "partidos"

    id = Column(Integer, primary_key=True)
    torneo_id = Column(Integer, ForeignKey("torneos.id"), nullable=False)
    cancha_id = Column(Integer, ForeignKey("canchas.id"))
    arbitro_id = Column(Integer, ForeignKey("usuarios.id"))
    # Un partido enfrenta a dos equipos (no estaba dibujado como línea pero es necesario)
    equipo_local_id = Column(Integer, ForeignKey("equipos.id"))
    equipo_visitante_id = Column(Integer, ForeignKey("equipos.id"))

    fecha_hora = Column(DateTime(timezone=True))
    goles_local = Column(Integer, default=0)
    goles_visitante = Column(Integer, default=0)
    estado = Column(String(20), default="programado")  # programado, en_juego, finalizado

    torneo = relationship("Torneo", back_populates="partidos")
    cancha = relationship("Cancha", back_populates="partidos")
    arbitro = relationship("Usuario", back_populates="partidos_arbitrados")
    equipo_local = relationship("Equipo", foreign_keys=[equipo_local_id])
    equipo_visitante = relationship("Equipo", foreign_keys=[equipo_visitante_id])
    alineaciones = relationship("Alineacion", back_populates="partido")
    eventos = relationship("EventoPartido", back_populates="partido")

    @property
    def torneo_nombre(self):
        return self.torneo.nombre if self.torneo else None

    @property
    def cancha_nombre(self):
        return self.cancha.nombre if self.cancha else None

    @property
    def arbitro_nombre(self):
        return self.arbitro.nombre if self.arbitro else None

    @property
    def equipo_local_nombre(self):
        return self.equipo_local.nombre if self.equipo_local else None

    @property
    def equipo_visitante_nombre(self):
        return self.equipo_visitante.nombre if self.equipo_visitante else None


# ----------------------------------------------------------------------
# 9. alineaciones  (PK id; FK partido_id, equipo_id, jugador_id; titular, posicion)
# ----------------------------------------------------------------------
class Alineacion(Base):
    __tablename__ = "alineaciones"

    id = Column(Integer, primary_key=True)
    partido_id = Column(Integer, ForeignKey("partidos.id"), nullable=False)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    jugador_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    titular = Column(Boolean, default=True)
    posicion = Column(String(30))

    __table_args__ = (
        UniqueConstraint("partido_id", "jugador_id", name="uq_alineacion_partido_jugador"),
    )

    partido = relationship("Partido", back_populates="alineaciones")
    equipo = relationship("Equipo", foreign_keys=[equipo_id])
    jugador = relationship("Usuario", foreign_keys=[jugador_id])

    @property
    def equipo_nombre(self):
        return self.equipo.nombre if self.equipo else None

    @property
    def jugador_nombre(self):
        return self.jugador.nombre if self.jugador else None


# ----------------------------------------------------------------------
# 10. eventos_partido  (PK id; FK partido_id, jugador_id, equipo_id; tipo, minuto, detalle)
# ----------------------------------------------------------------------
class EventoPartido(Base):
    __tablename__ = "eventos_partido"

    id = Column(Integer, primary_key=True)
    partido_id = Column(Integer, ForeignKey("partidos.id"), nullable=False)
    jugador_id = Column(Integer, ForeignKey("usuarios.id"))
    equipo_id = Column(Integer, ForeignKey("equipos.id"))

    tipo = Column(String(20), nullable=False)  # gol, tarjeta_amarilla, tarjeta_roja, cambio
    minuto = Column(Integer)
    detalle = Column(String(120))

    partido = relationship("Partido", back_populates="eventos")
    equipo = relationship("Equipo", foreign_keys=[equipo_id])
    jugador = relationship("Usuario", foreign_keys=[jugador_id])

    @property
    def equipo_nombre(self):
        return self.equipo.nombre if self.equipo else None

    @property
    def jugador_nombre(self):
        return self.jugador.nombre if self.jugador else None


# ----------------------------------------------------------------------
# 11. inscripciones  (PK id; FK torneo_id, equipo_id, pago_id 1:1; fecha, estado)
# ----------------------------------------------------------------------
class Inscripcion(Base):
    __tablename__ = "inscripciones"

    id = Column(Integer, primary_key=True)
    torneo_id = Column(Integer, ForeignKey("torneos.id"), nullable=False)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    pago_id = Column(Integer, ForeignKey("pagos.id"), unique=True)  # 1:1

    fecha = Column(DateTime(timezone=True), server_default=func.now())
    estado = Column(String(20), default="pendiente")  # pendiente, aceptada, rechazada

    __table_args__ = (
        UniqueConstraint("torneo_id", "equipo_id", name="uq_inscripcion_torneo_equipo"),
    )

    torneo = relationship("Torneo", back_populates="inscripciones")
    equipo = relationship("Equipo", back_populates="inscripciones")
    pago = relationship("Pago", back_populates="inscripcion")


# ----------------------------------------------------------------------
# 12. pagos  (FK usuario_id) — 1:1 con reserva y con inscripción
# ----------------------------------------------------------------------
class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    monto = Column(Numeric(10, 2), nullable=False)
    metodo = Column(String(20), nullable=False)   # tarjeta, transferencia
    estado = Column(String(20), default="pendiente")  # pendiente, completado, fallido
    referencia = Column(String(100))              # id de la pasarela de pago
    creado_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="pagos")
    reserva = relationship("Reserva", back_populates="pago", uselist=False)
    inscripcion = relationship("Inscripcion", back_populates="pago", uselist=False)


# ----------------------------------------------------------------------
# 13. jugadores_equipo  (PK id; FK equipo_id, jugador_id; dorsal, posicion)
# ----------------------------------------------------------------------
class JugadorEquipo(Base):
    __tablename__ = "jugadores_equipo"

    id = Column(Integer, primary_key=True)
    equipo_id = Column(Integer, ForeignKey("equipos.id"), nullable=False)
    jugador_id = Column(Integer, ForeignKey("usuarios.id"))  # opcional: jugador registrado

    nombre = Column(String(80))   # nombre del jugador en la plantilla (texto libre)
    dorsal = Column(Integer)
    posicion = Column(String(30))

    __table_args__ = (
        UniqueConstraint("equipo_id", "jugador_id", name="uq_jugador_en_equipo"),
    )

    equipo = relationship("Equipo", back_populates="jugadores")
    jugador = relationship("Usuario", back_populates="membresias")

    @property
    def nombre_jugador(self):
        # Nombre tecleado por el entrenador o, si está vinculado, el del usuario
        return self.nombre or (self.jugador.nombre if self.jugador else None)


# ----------------------------------------------------------------------
# 14. notificaciones  (FK usuario_id)
# ----------------------------------------------------------------------
class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    titulo = Column(String(120))
    mensaje = Column(Text, nullable=False)
    leida = Column(Boolean, default=False, nullable=False)
    creada_en = Column(DateTime(timezone=True), server_default=func.now())

    usuario = relationship("Usuario", back_populates="notificaciones")


# ----------------------------------------------------------------------
# 15. solicitudes_registro  (altas de entrenador/arbitro pendientes de aprobacion)
# ----------------------------------------------------------------------
class SolicitudRegistro(Base):
    __tablename__ = "solicitudes_registro"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(80), nullable=False)
    correo = Column(String(120), nullable=False, index=True)
    telefono = Column(String(20))
    rol_solicitado = Column(String(20), nullable=False)   # entrenador | arbitro
    documento_nombre = Column(String(255))                # archivo guardado (pdf o imagen)
    estado = Column(String(20), default="pendiente", nullable=False)  # pendiente | aceptada | rechazada
    motivo = Column(String(255))                          # motivo de rechazo, opcional
    creada_en = Column(DateTime(timezone=True), server_default=func.now())
