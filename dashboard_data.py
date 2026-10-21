from collections import defaultdict

def obtener_registros(Lectura, Lote):
    q = (Lectura.query.join(Lote, Lectura.lote_id == Lote.id).order_by(Lectura.fecha, Lectura.hora))

    return [
        {
            "id": l.id,
            "fecha": l.fecha,
            "hora": l.hora,
            "lote": l.lote_rel.numero,
            "ph": l.ph,
            "tds": l.tds,
            "sabor": bool(l.sabor),
            "olor": bool(l.olor),
            "color": bool(l.color),
            "sello": bool(l.sello),
            "tecnico": l.tecnico,
        }
        for l in q.all()
    ]

def obtener_lotes(Lote):
    # Todos los lotes, tengan o no lecturas (los que no tengan salen como 'Sin analizar').

    return [
        {"lote": l.numero, "producto": getattr(l, "producto", None) or "—"}
        for l in Lote.query.order_by(Lote.numero).all()
    ]

# Logica calidad
def motivos(r, ph_min, ph_max, tds_max):
    """Lista de motivos por los que una lectura NO cumple (vacia = cumple)."""
    m = []
    if r["ph"] > ph_max:
        m.append("pH alto")
    elif r["ph"] < ph_min:
        m.append("pH bajo")
    if r["tds"] > tds_max:
        m.append("TDS alto")
    for campo, nombre in (("sabor", "Sabor"), ("olor", "Olor"), ("color", "Color"), ("sello", "Sello")):
        if not r[campo]:
            m.append(nombre)
    return m

def construir_dashboard(registros, lotes, ph_min, ph_max, tds_max):
    """Convierte registros + lotes en todo lo que necesita la plantilla."""
    for r in registros:
        r["motivos"] = motivos(r, ph_min, ph_max, tds_max)
        r["cumple"] = not r["motivos"]
        r["ph_fuera"] = not (ph_min <= r["ph"] <= ph_max)
 
    total = len(registros)
    cumplen = sum(1 for r in registros if r["cumple"])
 
    # --- KPIs (tarjetas de arriba) ---
    kpis = {
        "total": total,
        "cumplen": cumplen,
        "no_cumplen": total - cumplen,
        "pct_cumple": round(cumplen / total * 100, 1) if total else 0,
        "ph_prom": round(sum(r["ph"] for r in registros) / total, 2) if total else 0,
        "tds_prom": round(sum(r["tds"] for r in registros) / total) if total else 0,
    }
 
    # --- Estadistica por lote ---
    stats = defaultdict(lambda: {"total": 0, "cumplen": 0})
    for r in registros:
        stats[r["lote"]]["total"] += 1
        if r["cumple"]:
            stats[r["lote"]]["cumplen"] += 1
 
    # Estado de los lotes: incluye lotes sin lecturas ("Sin analizar")
    productos = {l["lote"]: l["producto"] for l in lotes}
    for numero in stats:                      # por si hay lecturas de un lote no listado
        productos.setdefault(numero, "—")
 
    lotes_estado = []
    for numero in sorted(productos):
        s = stats.get(numero, {"total": 0, "cumplen": 0})
        if s["total"] == 0:
            estado = "Sin analizar"
        elif s["cumplen"] == s["total"]:
            estado = "Liberado"
        else:
            estado = "Retenido"
        lotes_estado.append({
            "lote": numero, 
            "producto": productos[numero],
            "lecturas": s["total"], 
            "estado": estado
        })
 
    # --- Datos SOLO para las graficas (todo JSON-seguro) ---
    con_lecturas = sorted(stats)
    graficas = {
        "ph": {
            "etiquetas": [f'{r["fecha"].strftime("%d/%m")} {r["hora"].strftime("%H:%M")}' for r in registros],
            "valores": [r["ph"] for r in registros],
            "fuera": [r["ph_fuera"] for r in registros],
        },
        "lotes": {
            "etiquetas": con_lecturas,
            "cumplen": [stats[n]["cumplen"] for n in con_lecturas],
            "no_cumplen": [stats[n]["total"] - stats[n]["cumplen"] for n in con_lecturas],
        },
    }
 
    # --- Tabla "Lecturas que no cumplen" (ya formateada para mostrar) ---
    alertas = [
        {
            "fecha": f'{r["fecha"].strftime("%d/%m")} {r["hora"].strftime("%H:%M")}',
            "lote": r["lote"],
            "tecnico": r["tecnico"],
            "motivos": r["motivos"],
        }
        for r in registros if not r["cumple"]
    ][-10:]                                   # las 10 mas recientes, en orden cronologico
 
    return {
        "kpis": kpis,
        "graficas": graficas,
        "lotes_estado": lotes_estado,
        "alertas": alertas,
        "limites": {"ph_min": ph_min, "ph_max": ph_max, "tds_max": tds_max},
    }