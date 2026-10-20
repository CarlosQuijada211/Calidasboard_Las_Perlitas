# =============================================================
#  cargar_datos.py · Carga las 12 lecturas de práctica
#  ATENCIÓN: borra todas las tablas ("lotes" y "lecturas") y las vuelve a crear.
#  Úsalo cuando quieras empezar de cero.
#  Ejecutar:  python cargar_datos.py
# =============================================================
from datetime import date, time

from app import Lectura, Lote, app, db


def L(dia, hora, lote_obj, ph, tds, tecnico,
      sabor=True, olor=True, color=True, sello=True, obs=""):
    """Crea una lectura asociándola directamente al objeto de Lote."""
    return Lectura(fecha=date(2026, 9, dia), hora=time(hora, 0), lote_rel=lote_obj,
                   ph=ph, tds=tds, sabor=sabor, olor=olor, color=color,
                   sello=sello, tecnico=tecnico, observaciones=obs)


# Datos INVENTADOS para practicar
# Formato: (dia, hora, numero_lote, ph, tds, tecnico, sabor, olor, color, sello, obs)
datos_lecturas = [
    (10, 8,  "25253-01", 7.20, 180, "Ana López", True, True, True, True, ""),
    (10, 10, "25253-01", 7.05, 175, "Ana López", True, True, True, True, ""),
    (10, 14, "25253-02", 8.90, 190, "Carlos Méndez", True, True, True, True, ""),
    (11, 8,  "25254-01", 6.80, 520, "Carlos Méndez", True, True, True, True, ""),
    (11, 10, "25254-01", 7.40, 210, "Ana López", True, True, True, False, "Tapa sin sello de seguridad"),
    (11, 14, "25254-02", 7.10, 195, "Carlos Méndez", True, True, True, True, ""),
    (12, 8,  "25254-02", 7.30, 200, "Sofía Ramírez", True, True, True, True, ""),
    (12, 10, "25255-01", 7.60, 230, "Sofía Ramírez", True, False, True, True, "Olor a plástico"),
    (12, 14, "25255-01", 7.50, 225, "Ana López", True, True, True, True, ""),
    (13, 8,  "25255-02", 6.40, 160, "Sofía Ramírez", True, True, True, True, ""),
    (13, 10, "25255-02", 7.00, 170, "Carlos Méndez", True, True, True, True, ""),
    (13, 14, "25255-02", 7.15, 185, "Sofía Ramírez", True, True, True, True, ""),
]

with app.app_context():
    db.drop_all()                 # borra las tablas del modelo (lotes y lecturas)
    db.create_all()               # las vuelve a crear vacías

    # Diccionario para almacenar los objetos Lote y reutilizarlos según su código
    lotes_creados = {}

    for d in datos_lecturas:
        dia, hora, num_lote, ph, tds, tecnico, sabor, olor, color, sello, obs = d

        # Si el lote no existe en el diccionario, se crea y añade a la sesión
        if num_lote not in lotes_creados:
            nuevo_lote = Lote(numero=num_lote)
            db.session.add(nuevo_lote)
            lotes_creados[num_lote] = nuevo_lote

        # Crear la lectura asociando el objeto Lote correspondiente
        lectura = L(
            dia=dia,
            hora=hora,
            lote_obj=lotes_creados[num_lote],
            ph=ph,
            tds=tds,
            tecnico=tecnico,
            sabor=sabor,
            olor=olor,
            color=color,
            sello=sello,
            obs=obs
        )
        db.session.add(lectura)

    db.session.commit()
    print("Lotes guardados:", Lote.query.count())
    print("Lecturas guardadas:", Lectura.query.count())