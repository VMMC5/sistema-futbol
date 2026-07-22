"""índices de rendimiento en claves foráneas y filtros de listado

Postgres solo indexa automáticamente PK y UNIQUE: las claves foráneas quedan
sin índice. Los listados filtran justamente por ellas, así que cada consulta
terminaba en un scan secuencial.

No se incluyen los casos ya cubiertos por el índice de un UNIQUE compuesto
(un índice sobre (a, b) sirve también para filtrar solo por `a`):
  - alineaciones.partido_id     -> uq_alineacion_partido_jugador
  - inscripciones.torneo_id     -> uq_inscripcion_torneo_equipo
  - jugadores_equipo.equipo_id  -> uq_jugador_en_equipo
  - jugadores_equipo.jugador_id -> uq_jugador_un_solo_equipo
  - alineacion_planes.partido_id-> uq_plan_partido_equipo

Revision ID: c2e3f4a5b6d7
Revises: b1d2e3f4a5c6
Create Date: 2026-07-21 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op

revision: str = "c2e3f4a5b6d7"
down_revision: Union[str, None] = "b1d2e3f4a5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (nombre, tabla, columnas)
_INDICES = [
    # El chequeo de solapamiento de reservas filtra siempre por cancha + fecha.
    ("ix_reservas_cancha_fecha", "reservas", ["cancha_id", "fecha"]),
    ("ix_reservas_usuario", "reservas", ["usuario_id"]),
    ("ix_partidos_torneo_estado", "partidos", ["torneo_id", "estado"]),
    ("ix_partidos_arbitro", "partidos", ["arbitro_id"]),
    ("ix_partidos_equipo_local", "partidos", ["equipo_local_id"]),
    ("ix_partidos_equipo_visitante", "partidos", ["equipo_visitante_id"]),
    ("ix_eventos_partido", "eventos_partido", ["partido_id"]),
    ("ix_eventos_jugador", "eventos_partido", ["jugador_id"]),
    ("ix_inscripciones_equipo", "inscripciones", ["equipo_id"]),
    ("ix_invitaciones_jugador_estado", "invitaciones_equipo", ["jugador_id", "estado"]),
    ("ix_invitaciones_equipo_estado", "invitaciones_equipo", ["equipo_id", "estado"]),
    ("ix_notificaciones_usuario", "notificaciones", ["usuario_id"]),
]


def upgrade() -> None:
    for nombre, tabla, columnas in _INDICES:
        op.create_index(nombre, tabla, columnas)


def downgrade() -> None:
    for nombre, tabla, _ in reversed(_INDICES):
        op.drop_index(nombre, table_name=tabla)
