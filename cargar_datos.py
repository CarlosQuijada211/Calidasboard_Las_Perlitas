# =============================================================
#  cargar_datos.py · Carga las 12 lecturas de práctica
#  ATENCIÓN: borra y recrea SOLO las tablas "lecturas" y "lotes".
#  La tabla "usuarios" no se toca (se conservan las cuentas).
#
#  REQUISITO: las cuentas de prueba deben existir. Corre antes usuarios_prueba.sql.
#  Ejecutar:  python cargar_datos.py
# =============================================================
from datetime import date, time, datetime

from app import Lectura, Lote, Usuario, app, db

# Cada lectura queda a nombre del usuario (técnico) que la "capturó".
# La clave es el nombre que aparece en la columna "Técnico".
AUTORES = {
    "Ana López": "alopez",
    "Carlos Méndez": "cmendez",
    "Sofía Ramírez": "sramirez",
}


def revisor_del_dia(dia):
    """Supervisor que revisó las lecturas de ese día (los días 10 y 11 Marta, 12 y 13 Luis)."""
    return "mflores" if dia <= 11 else "lortiz"


# Datos INVENTADOS para practicar
# Formato: (dia, hora, numero_lote, ph, tds, tecnico, sabor, olor, color, sello, obs, estado, motivo_rechazo)
#   estado: "aprobada" | "pendiente" | "rechazada"
datos_lecturas = [
    (10, 8,  "25253-01", 7.20, 180, "Ana López",     True, True,  True, True,  "", "aprobada", ""),
    (10, 10, "25253-01", 7.05, 175, "Ana López",     True, True,  True, True,  "", "aprobada", ""),
    (10, 14, "25253-02", 8.90, 190, "Carlos Méndez", True, True,  True, True,  "", "aprobada", ""),
    (11, 8,  "25254-01", 6.80, 520, "Carlos Méndez", True, True,  True, True,  "", "aprobada", ""),
    (11, 10, "25254-01", 7.40, 210, "Ana López",     True, True,  True, False, "Tapa sin sello de seguridad", "aprobada", ""),
    (11, 14, "25254-02", 7.10, 195, "Carlos Méndez", True, True,  True, True,  "", "rechazada",
        "La hora no coincide con el muestreo. Corregir la hora y reenviar."),
    (12, 8,  "25254-02", 7.30, 200, "Sofía Ramírez", True, True,  True, True,  "", "aprobada", ""),
    (12, 10, "25255-01", 7.60, 230, "Sofía Ramírez", True, False, True, True,  "Olor a plástico", "aprobada", ""),
    (12, 14, "25255-01", 7.50, 225, "Ana López",     True, True,  True, True,  "", "aprobada", ""),
    (13, 8,  "25255-02", 6.40, 160, "Sofía Ramírez", True, True,  True, True,  "", "aprobada", ""),
    (13, 10, "25255-02", 7.00, 170, "Carlos Méndez", True, True,  True, True,  "", "pendiente", ""),
    (13, 14, "25255-02", 7.15, 185, "Sofía Ramírez", True, True,  True, True,  "", "pendiente", ""),
]

with app.app_context():
    db.create_all()               # por si falta alguna tabla (ej. usuarios en una BD nueva)

    # --- Las cuentas de prueba deben existir (ver usuarios_prueba.sql) ---
    # Se leen SOLO los ids y se cierra la transacción enseguida (session.remove()).
    # Si la sesión se queda abierta con un SELECT sobre "usuarios", MySQL mantiene un
    # bloqueo y el DROP TABLE de "lecturas" (que tiene llave foránea a usuarios) se
    # queda esperando para siempre: ese era el congelamiento.
    ids = {nombre: id_ for nombre, id_ in db.session.query(Usuario.usuario, Usuario.id).all()}
    db.session.remove()

    necesarios = set(AUTORES.values()) | {"mflores", "lortiz"}
    faltan = sorted(necesarios - set(ids))
    if faltan:
        print("Faltan usuarios de prueba:", ", ".join(faltan))
        print("Corre primero usuarios_prueba.sql en MySQL y vuelve a ejecutar este script.")
        raise SystemExit(1)

    # Solo estas dos tablas: lecturas primero, porque depende de lotes
    tablas = [Lectura.__table__, Lote.__table__]  # type: ignore
    db.metadata.drop_all(db.engine, tables=tablas)
    db.metadata.create_all(db.engine, tables=tablas)

    # Diccionario para almacenar los objetos Lote y reutilizarlos según su código
    lotes_creados = {}

    for d in datos_lecturas:
        dia, hora, num_lote, ph, tds, tecnico, sabor, olor, color, sello, obs, estado, motivo = d

        # Si el lote no existe en el diccionario, se crea y añade a la sesión
        if num_lote not in lotes_creados:
            nuevo_lote = Lote(numero=num_lote)
            db.session.add(nuevo_lote)
            lotes_creados[num_lote] = nuevo_lote

        lectura = Lectura(
            fecha=date(2026, 9, dia),
            hora=time(hora, 0),
            lote_rel=lotes_creados[num_lote],
            ph=ph,
            tds=tds,
            sabor=sabor,
            olor=olor,
            color=color,
            sello=sello,
            tecnico=tecnico,
            observaciones=obs,
            estado=estado,
            creado_por_id=ids[AUTORES[tecnico]],
            motivo_rechazo=motivo or None,
        )

        # Las lecturas ya revisadas (aprobadas o rechazadas) guardan quién y cuándo
        if estado != "pendiente":
            lectura.revisado_por_id = ids[revisor_del_dia(dia)]
            lectura.fecha_revision = datetime(2026, 9, dia, 18, 0)

        db.session.add(lectura)

    db.session.commit()
    print("Lotes guardados:", Lote.query.count())
    print("Lecturas guardadas:", Lectura.query.count())
    for e in ("aprobada", "pendiente", "rechazada"):
        print(f"  {e}: {Lectura.query.filter_by(estado=e).count()}")