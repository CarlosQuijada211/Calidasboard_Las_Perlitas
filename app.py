# =============================================================
#  CALIDASHBOARD · Sistema de práctica · Semana 8
#  Flask + MySQL (Flask-SQLAlchemy + PyMySQL)
#  Fundamentos de Programación · Key Institute
# =============================================================
from datetime import date, time

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# -------------------------------------------------------------
# 1. CONEXIÓN A LA BASE DE DATOS
#    Formato: mysql+pymysql://USUARIO:CONTRASEÑA@SERVIDOR:PUERTO/BASE
#    XAMPP trae el usuario "root" con contraseña vacía (root:@).
#    Si tu MySQL tiene contraseña, escríbela después de "root:".
# -------------------------------------------------------------
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:renovacionSQL59@localhost:3306/calidashboard_db"

db = SQLAlchemy(app)

# -------------------------------------------------------------
# 2. LÍMITES DE CALIDAD (valores ilustrativos para practicar)
#    Cámbialos por los límites de especificación de la planta.
# -------------------------------------------------------------
PH_MIN = 6.5
PH_MAX = 8.5
TDS_MAX = 500

# Permite usar los límites dentro de las plantillas: {{ PH_MIN }}, {{ TDS_MAX }}...
app.jinja_env.globals.update(PH_MIN=PH_MIN, PH_MAX=PH_MAX, TDS_MAX=TDS_MAX)


# -------------------------------------------------------------
# 3. MODELO: una fila de la tabla "lecturas" = una muestra analizada
# -------------------------------------------------------------

class Lote(db.Model):
    __tablename__="lotes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(8), unique=True, nullable=False)

    lecturas = db.relationship("Lectura", backref="lote_rel", lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

class Lectura(db.Model):
    __tablename__ = "lecturas"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    hora = db.Column(db.Time, nullable=False)

    lote_id = db.Column(db.Integer, db.ForeignKey("lotes.id"), nullable=False)

    ph = db.Column(db.Float, nullable=False)              # X.XX
    tds = db.Column(db.Integer, nullable=False)           # XXX
    sabor = db.Column(db.Boolean, default=True)           # True = cumple
    olor = db.Column(db.Boolean, default=True)
    color = db.Column(db.Boolean, default=True)
    sello = db.Column(db.Boolean, default=True)
    observaciones = db.Column(db.Text)
    tecnico = db.Column(db.String(100), nullable=False)

    # --- Funciones del modelo: cada una responde una pregunta ---
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def ph_ok(self):
        return PH_MIN <= self.ph <= PH_MAX

    def tds_ok(self):
        return self.tds <= TDS_MAX

    def sensorial_ok(self):
        return self.sabor and self.olor and self.color and self.sello

    def cumple(self):
        return self.ph_ok() and self.tds_ok() and self.sensorial_ok()


# -------------------------------------------------------------
# 4. RUTAS
# -------------------------------------------------------------
@app.route("/")
def inicio():
    return redirect(url_for("listar_lecturas"))

@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/lecturas")
def listar_lecturas():
    lecturas = Lectura.query.order_by(Lectura.fecha.desc(), Lectura.hora.desc()).all()
    return render_template("lecturas.html", lecturas=lecturas,
                           titulo="Todas las lecturas")


@app.route("/lecturas/nueva", methods=["GET", "POST"])
def nueva_lectura():
    if request.method == "POST":
        f = request.form

        numero_lote = f["lote"].strip()

        lote_obj = Lote.query.filter_by(numero=numero_lote).first()
        if not lote_obj:
            lote_obj = Lote(numero=numero_lote)
            db.session.add(lote_obj)
            db.session.flush()

        nueva = Lectura(
            fecha=date.fromisoformat(f["fecha"]),      # "2026-09-11" -> fecha
            hora=time.fromisoformat(f["hora"]),        # "08:30" -> hora
            lote_rel=lote_obj,
            ph=float(f["ph"]),                         # texto -> decimal
            tds=int(f["tds"]),                         # texto -> entero
            sabor="sabor" in f,                        # casilla marcada = True
            olor="olor" in f,
            color="color" in f,
            sello="sello" in f,
            tecnico=f["tecnico"].strip(),
            observaciones=f["observaciones"].strip(),
        )
        db.session.add(nueva)
        db.session.commit()
        return redirect(url_for("listar_lecturas"))
    return render_template("nueva.html", hoy=date.today().isoformat())


@app.route("/alertas")
def ver_alertas():
    todas = Lectura.query.order_by(Lectura.fecha, Lectura.hora).all()
    alertas = []
    for l in todas:
        if not l.cumple():
            alertas.append(l)
    return render_template("lecturas.html", lecturas=alertas,
                           titulo="Lecturas que NO cumplen")


@app.route("/lecturas/<int:id>/observar", methods=["POST"])
def observar(id):
    lectura = db.session.get(Lectura, id)
    if lectura is None:
        return "Lectura no encontrada", 404
    texto = request.form["observaciones"].strip()
    if texto != "":
        lectura.observaciones = texto
        db.session.commit()
    # request.referrer = la página desde donde se envió el formulario
    return redirect(request.referrer or url_for("listar_lecturas"))


# =============================================================
#  ZONA DE PRÁCTICA: escribe aquí tus rutas (ver Guía 8)
# =============================================================

# Ejercicio 1: ruta /lote/<codigo>
#   Muestra solo las lecturas de un lote. Reutiliza lecturas.html.

@app.route("/lecturas/buscar", methods=["GET"])
def buscar_lecturas():
    # Obtener los parámetros enviados por el formulario
    lote = request.args.get("lote", "").strip()
    tecnico = request.args.get("tecnico", "").strip()

    # Iniciar la consulta base
    query = Lectura.query

    # Filtrar por lote si el campo no está vacío
    if lote:
        query = query.join(Lote).filter(Lote.numero == lote)

    # Filtrar por técnico si el campo no está vacío
    if tecnico:
        query = query.filter_by(tecnico=tecnico)

    # Ordenar de la lectura más reciente a la más antigua
    lecturas = query.order_by(Lectura.fecha.desc(), Lectura.hora.desc()).all()

    return render_template("lecturas.html", lecturas=lecturas, titulo="Lecturas Filtradas")


# Ejercicio 3: ruta /resumen + plantilla resumen.html
#   Total de lecturas, pH promedio, TDS promedio y % que cumple.
@app.route("/resumen")
def resumen():
    todas = Lectura.query.order_by(Lectura.fecha, Lectura.hora).all()

    total = len(todas)
    
    # Manejo de caso sin registros
    if total == 0:
        Datos = {
            "TotalLecturas": 0,
            "pHPromedio": "0.00",
            "TDSPromedio": "0.00",
            "LecturasCumplen": 0,
            "Porcentaje": "0.00%"
        }
        return render_template("resumen.html", lecturas=Datos, titulo="Resumen de Lecturas")

    ph_suma = sum(l.ph for l in todas)
    tds_suma = sum(l.tds for l in todas)
    cumplen = sum(1 for l in todas if l.cumple())

    ph_promedio = ph_suma / total
    tds_promedio = tds_suma / total
    porcentaje = (cumplen / total) * 100

    Datos = {
        "TotalLecturas": total,
        "pHPromedio": f"{ph_promedio:.2f}",
        "TDSPromedio": f"{tds_promedio:.2f}",
        "LecturasCumplen": cumplen,
        "Porcentaje": f"{porcentaje:.2f}%"
    }

    return render_template("resumen.html", lecturas=Datos, titulo="Resumen de Lecturas")



# Ejercicio 4: ruta /lecturas/<int:id>/eliminar  (methods=["POST"])
@app.route("/lecturas/<int:id>/borrar", methods=["POST"])
def borrar(id):

    lectura = Lectura.query.get_or_404(id)
    db.session.delete(lectura)
    db.session.commit()

    # request.referrer = la página desde donde se envió el formulario
    return redirect(request.referrer or url_for("listar_lecturas"))


# Ejercicio 5 (reto): modelo Lote + ruta /lotes
#   Estado de cada lote: "Liberado" o "Retenido".


# -------------------------------------------------------------
# 5. ARRANQUE
# -------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()          # crea las tablas que aún no existan
    app.run(debug=True)
