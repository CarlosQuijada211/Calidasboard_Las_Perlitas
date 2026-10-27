import os
from datetime import date, time, datetime, timedelta
import re 
from sqlalchemy.orm import validates  
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, g
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash

# Importaciones para el módulo de dashboard
from dashboard_data import obtener_registros, obtener_lotes, construir_dashboard

app = Flask(__name__)

# Configuración de la Base de Datos
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    "mysql+pymysql://root:renovacionSQL59@localhost:3306/calidashboard_db",
)

# La clave firma la cookie de sesión. Sin ella, Flask no permite usar "session".
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-larga-y-aleatoria")
app.permanent_session_lifetime = timedelta(days=14)   # duración de "Mantener sesión iniciada"

# Iniciar la base de datos
db = SQLAlchemy(app)

# LÍMITES DE CALIDAD (valores ilustrativos para practicar)
PH_MIN = 6.5
PH_MAX = 8.5
TDS_MAX = 500

# Permite usar los límites dentro de las plantillas: {{ PH_MIN }}, {{ TDS_MAX }}...
app.jinja_env.globals.update(PH_MIN=PH_MIN, PH_MAX=PH_MAX, TDS_MAX=TDS_MAX)


# Roles y estados globales
ROLES = ("admin", "supervisor", "tecnico")           # en la BD "tecnico" va sin acento
ESTADOS = ("pendiente", "aprobada", "rechazada")
ETIQUETAS_ROL = {"admin": "Administrador", "supervisor": "Supervisor", "tecnico": "Técnico"}
app.jinja_env.globals.update(ETIQUETAS_ROL=ETIQUETAS_ROL)

# Clases para tablas de la base de datos

class Lote(db.Model):
    __tablename__ = "lotes"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(8), unique=True, nullable=False)

    lecturas = db.relationship("Lectura", backref="lote_rel", lazy=True)
    @validates("numero")
    def validar_numero(self, key, valor):
        valor = valor.strip()
        if not re.fullmatch(r"\d{5}-\d{2}", valor):
            raise ValueError("El lote debe tener el formato XXXXX-XX (ej. 12345-01).")
        return valor
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

    # --- Aprobación ---
    estado = db.Column(db.String(15), nullable=False, default="pendiente")
    creado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    revisado_por_id = db.Column(db.Integer, db.ForeignKey("usuarios.id", ondelete="SET NULL"))
    fecha_revision = db.Column(db.DateTime)
    motivo_rechazo = db.Column(db.Text)

    creado_por = db.relationship("Usuario", foreign_keys=[creado_por_id])
    revisado_por = db.relationship("Usuario", foreign_keys=[revisado_por_id])
    @validates("fecha")
    def validar_fecha(self, key, valor):
        if valor > date.today():
            raise ValueError("La fecha no puede ser futura.")
        return valor

    @validates("ph")
    def validar_ph(self, key, valor):
        if not 0 <= valor <= 14:
            raise ValueError("El pH debe estar entre 0 y 14.")
        return round(valor, 2)

    @validates("tds")
    def validar_tds(self, key, valor):
        if not 0 <= valor <= 999:
            raise ValueError("El TDS debe estar entre 0 y 999.")
        return valor

    @validates("tecnico")
    def validar_tecnico(self, key, valor):
        valor = valor.strip()
        if valor == "":
            raise ValueError("El nombre del técnico es obligatorio.")
        if len(valor) > 100:
            raise ValueError("El nombre del técnico no puede pasar de 100 caracteres.")
        return valor
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


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    correo = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)   # NUNCA la contraseña en texto plano
    rol = db.Column(db.String(20), nullable=False, default="tecnico")
    creado = db.Column(db.DateTime, default=datetime.now)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def poner_password(self, password):
        self.password_hash = generate_password_hash(password)

    def revisar_password(self, password):
        return check_password_hash(self.password_hash, password)


# Permisos por rol

TODOS = {"admin", "supervisor", "tecnico"}
ADMIN_Y_SUPERVISOR = {"admin", "supervisor"}    # se usará en el Paso 4 (aprobar / rechazar)
SOLO_ADMIN = {"admin"}

PERMISOS = {
    "inicio":               TODOS,
    "logout":               TODOS,
    "listar_lecturas":      TODOS,
    "buscar_lecturas":      TODOS,
    "nueva_lectura":        TODOS,
    "observar":             TODOS,          
    "ver_alertas":          TODOS,          
    "resumen":              TODOS,          
    "dashboard":            TODOS,          # <-- Añadido
    "editar":               ADMIN_Y_SUPERVISOR,          # <-- Añadido (controlado por puede_editar internamente)
    "listar_pendientes":    ADMIN_Y_SUPERVISOR,  
    "listar_rechazadas":    ADMIN_Y_SUPERVISOR,
    "aprobar_lectura":      ADMIN_Y_SUPERVISOR,  
    "rechazar_lectura":     ADMIN_Y_SUPERVISOR,  
    "borrar":               SOLO_ADMIN,
    "listar_usuarios":      SOLO_ADMIN,
    "crear_usuario":        SOLO_ADMIN,
    "eliminar_usuario":     SOLO_ADMIN,
}

RUTAS_PUBLICAS = {"login", "static"}


@app.before_request
def controlar_acceso():
    # Se consulta el usuario en la BD en cada petición
    uid = session.get("usuario_id")
    g.usuario = db.session.get(Usuario, uid) if uid else None

    endpoint = request.endpoint
    if endpoint is None or endpoint in RUTAS_PUBLICAS:
        return

    if g.usuario is None:
        session.clear()
        return redirect(url_for("login", next=request.full_path.rstrip("?")))

    if g.usuario.rol not in PERMISOS.get(endpoint, SOLO_ADMIN):
        abort(403)


@app.errorhandler(403)
def prohibido(e):
    flash("No tienes permiso para entrar a esa página.", "error")
    return redirect(request.referrer or url_for("listar_lecturas"))

@app.errorhandler(ValueError)
def error_de_validacion(e):
    db.session.rollback()
    flash(str(e), "error")
    return redirect(request.referrer or url_for("listar_lecturas"))
# Disponible en todas las plantillas: {{ usuario_actual.nombre }}, {{ usuario_actual.rol }}
@app.context_processor
def inyectar_usuario():
    return {"usuario_actual": g.get("usuario"), "ETIQUETAS_ROL": ETIQUETAS_ROL}


def destino_seguro(destino):
    """Solo acepta rutas internas (evita redirigir a sitios externos)."""
    if destino and destino.startswith("/") and not destino.startswith("//"):
        return destino
    return url_for("listar_lecturas")


# -------------------------------------------------------------
# VISIBILIDAD DE LECTURAS
# -------------------------------------------------------------
def lecturas_visibles():
    """Consulta base con las lecturas que el usuario actual puede ver."""
    consulta = Lectura.query
    if g.usuario.rol == "tecnico":
        consulta = consulta.filter(
            or_(Lectura.estado == "aprobada", Lectura.creado_por_id == g.usuario.id)
        )
    return consulta


def puede_ver(lectura):
    if g.usuario.rol in ADMIN_Y_SUPERVISOR:
        return True
    return lectura.estado == "aprobada" or lectura.creado_por_id == g.usuario.id


def puede_editar(lectura):
    """admin y supervisor editan cualquiera; el técnico solo las que él creó."""
    if g.usuario.rol in ADMIN_Y_SUPERVISOR:
        return True
    return lectura.creado_por_id == g.usuario.id


# Permite usar funciones dentro de las plantillas Jinja
app.jinja_env.globals.update(puede_ver=puede_ver, puede_editar=puede_editar)


# -------------------------------------------------------------
# RUTAS · SESIÓN
# -------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario:
        return redirect(url_for("listar_lecturas"))

    if request.method == "POST":
        f = request.form
        usuario = f.get("usuario", "").strip().lower()
        contrasena = f.get("contrasena", "")

        user = Usuario.query.filter_by(usuario=usuario).first()

        if user is None or not user.revisar_password(contrasena):
            return render_template("login.html", error="Usuario o contraseña incorrectos.",
                                   datos=f, next=f.get("next"))

        session.clear()
        session["usuario_id"] = user.id
        session.permanent = "recordar" in f
        flash(f"Bienvenido, {user.nombre}.")
        return redirect(destino_seguro(f.get("next")))

    return render_template("login.html", error=None, datos={}, next=request.args.get("next"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Sesión cerrada.")
    return redirect(url_for("login"))


# -------------------------------------------------------------
# RUTAS · LECTURAS
# -------------------------------------------------------------
@app.route("/")
def inicio():
    return redirect(url_for("listar_lecturas"))


@app.route("/lecturas")
def listar_lecturas():
    lecturas = (lecturas_visibles()
                 .filter(Lectura.estado != "rechazada")  # Oculta las rechazadas aquí
                 .order_by(Lectura.fecha.desc(), Lectura.hora.desc())
                 .all())
    return render_template("lecturas.html", lecturas=lecturas, titulo="Todas las lecturas")


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
            fecha=date.fromisoformat(f["fecha"]),
            hora=time.fromisoformat(f["hora"]),
            lote_rel=lote_obj,
            ph=float(f["ph"]),
            tds=int(f["tds"]),
            sabor="sabor" in f,
            olor="olor" in f,
            color="color" in f,
            sello="sello" in f,
            tecnico=f["tecnico"].strip(),
            observaciones=f["observaciones"].strip(),
            creado_por_id=g.usuario.id,  # Vinculamos la lectura al usuario logueado
            estado="pendiente",            # Nace como pendiente de aprobación
        )
        db.session.add(nueva)
        db.session.commit()
        return redirect(url_for("listar_lecturas"))
    return render_template("nueva.html", hoy=date.today().isoformat())


@app.route("/lecturas/buscar", methods=["GET"])
def buscar_lecturas():
    lote = request.args.get("lote", "").strip()
    tecnico = request.args.get("tecnico", "").strip()

    query = lecturas_visibles().filter(Lectura.estado != "rechazada")

    if lote:
        query = query.join(Lote).filter(Lote.numero == lote)

    if tecnico:
        query = query.filter(Lectura.tecnico == tecnico)

    lecturas = query.order_by(Lectura.fecha.desc(), Lectura.hora.desc()).all()
    return render_template("lecturas.html", lecturas=lecturas, titulo="Lecturas Filtradas")


@app.route("/lecturas/rechazadas")
def listar_rechazadas():
    if g.usuario.rol not in ADMIN_Y_SUPERVISOR:
        abort(403)
    lecturas = (Lectura.query.filter_by(estado="rechazada")
                .order_by(Lectura.fecha.desc(), Lectura.hora.desc())
                .all())
    return render_template("lecturas.html", lecturas=lecturas, titulo="Lecturas Rechazadas")


@app.route("/alertas")
def ver_alertas():
    # Solo lecturas aprobadas
    todas = (Lectura.query.filter_by(estado="aprobada")
             .order_by(Lectura.fecha, Lectura.hora).all())
    alertas = [l for l in todas if not l.cumple()]
    return render_template("lecturas.html", lecturas=alertas, titulo="Lecturas que NO cumplen")


@app.route("/lecturas/<int:id>/observar", methods=["POST"])
def observar(id):
    lectura = db.session.get(Lectura, id)
    if lectura is None or not puede_ver(lectura):
        return "Lectura no encontrada", 404
    if not puede_editar(lectura):
        abort(403)

    texto = request.form["observaciones"].strip()
    if texto != "":
        lectura.observaciones = texto
        db.session.commit()
    return redirect(request.referrer or url_for("listar_lecturas"))


@app.route("/lecturas/<int:id>/aprobar", methods=["POST"])
def aprobar_lectura(id):
    lectura = db.session.get(Lectura, id)
    if lectura is None or not puede_ver(lectura):
        return "Lectura no encontrada", 404
    
    if g.usuario.rol not in ADMIN_Y_SUPERVISOR:
        abort(403)

    lectura.estado = "aprobada"
    lectura.revisado_por_id = g.usuario.id
    lectura.fecha_revision = datetime.now()
    lectura.motivo_rechazo = None
    db.session.commit()

    flash(f"Lectura del lote {lectura.lote_rel.numero} aprobada exitosamente.", "success")
    return redirect(request.referrer or url_for("listar_lecturas"))


@app.route("/lecturas/<int:id>/rechazar", methods=["POST"])
def rechazar_lectura(id):
    lectura = db.session.get(Lectura, id)
    if lectura is None or not puede_ver(lectura):
        return "Lectura no encontrada", 404
    
    if g.usuario.rol not in ADMIN_Y_SUPERVISOR:
        abort(403)

    motivo = request.form.get("motivo_rechazo", "").strip()
    if not motivo:
        flash("Debes especificar un motivo de rechazo.", "error")
        return redirect(request.referrer or url_for("listar_lecturas"))

    lectura.estado = "rechazada"
    lectura.revisado_por_id = g.usuario.id
    lectura.fecha_revision = datetime.now()
    lectura.motivo_rechazo = motivo
    db.session.commit()

    flash(f"Lectura del lote {lectura.lote_rel.numero} rechazada.", "warning")
    return redirect(request.referrer or url_for("listar_lecturas"))


@app.route("/lecturas/pendientes")
def listar_pendientes():
    if g.usuario.rol not in ADMIN_Y_SUPERVISOR:
        abort(403)
    lecturas = (Lectura.query.filter_by(estado="pendiente")
                .order_by(Lectura.fecha.desc(), Lectura.hora.desc())
                .all())
    return render_template("lecturas.html", lecturas=lecturas, titulo="Lecturas Pendientes de Aprobación")

@app.route("/lecturas/<int:id>/borrar", methods=["POST"])
def borrar(id):
    lectura = Lectura.query.get_or_404(id)
    db.session.delete(lectura)
    db.session.commit()
    return redirect(request.referrer or url_for("listar_lecturas"))


# -------------------------------------------------------------
# NUEVAS RUTAS AÑADIDAS: DASHBOARD Y EDICIÓN
# -------------------------------------------------------------
@app.route("/dashboard")
def dashboard():
    registros = obtener_registros(Lectura, Lote)
    lotes = obtener_lotes(Lote)
    datos = construir_dashboard(registros, lotes, PH_MIN, PH_MAX, TDS_MAX)
    return render_template("dashboard.html", d=datos, titulo="Dashboard")


@app.route("/lecturas/<int:id>/editar", methods=["GET", "POST"])
def editar(id):
    lectura = db.session.get(Lectura, id)
    if lectura is None or not puede_ver(lectura):
        return "Lectura no encontrada", 404
    if not puede_editar(lectura):
        abort(403)

    if request.method == "POST":
        f = request.form

        numero_lote = f["lote"].strip()
        lote_obj = Lote.query.filter_by(numero=numero_lote).first()
        if not lote_obj:
            lote_obj = Lote(numero=numero_lote)
            db.session.add(lote_obj)
            db.session.flush()

        lectura.fecha = date.fromisoformat(f["fecha"])
        lectura.hora = time.fromisoformat(f["hora"])
        lectura.lote_rel = lote_obj
        lectura.ph = float(f["ph"])
        lectura.tds = int(f["tds"])
        lectura.sabor = "sabor" in f
        lectura.olor = "olor" in f
        lectura.color = "color" in f
        lectura.sello = "sello" in f
        lectura.tecnico = f["tecnico"].strip()
        lectura.observaciones = f["observaciones"].strip()
 
        db.session.commit()
        flash(f"Los cambios de la lectura #{lectura.id} se guardaron correctamente.", "success")
        return redirect(url_for("listar_lecturas"))
    return render_template("editar.html", l=lectura, titulo=f"Editar lectura #{lectura.id}")


# -------------------------------------------------------------
# 8. RUTAS · ADMINISTRACIÓN DE USUARIOS (solo admin)
# -------------------------------------------------------------
@app.route("/usuarios")
def listar_usuarios():
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template("usuarios.html", usuarios=usuarios, roles=ROLES, error=None, datos={})


@app.route("/usuarios/nuevo", methods=["POST"])
def crear_usuario():
    f = request.form
    nombre = f.get("nombre", "").strip()
    usuario = f.get("usuario", "").strip().lower()
    correo = f.get("correo", "").strip().lower()
    contrasena = f.get("contrasena", "")
    rol = f.get("rol", "")

    error = None
    if not nombre or not usuario or not correo or not contrasena:
        error = "Completa todos los campos."
    elif rol not in ROLES:
        error = "Elige un rol válido."
    elif len(usuario) < 3:
        error = "El usuario debe tener al menos 3 caracteres."
    elif len(contrasena) < 8:
        error = "La contraseña debe tener al menos 8 caracteres."
    elif Usuario.query.filter_by(usuario=usuario).first():
        error = "Ese usuario ya existe. Elige otro nombre de usuario."
    elif Usuario.query.filter_by(correo=correo).first():
        error = "Ese correo ya está registrado."

    if error:
        usuarios = Usuario.query.order_by(Usuario.nombre).all()
        return render_template("usuarios.html", usuarios=usuarios, roles=ROLES, error=error, datos=f)

    nuevo = Usuario(nombre=nombre, usuario=usuario, correo=correo, rol=rol)
    nuevo.poner_password(contrasena)
    db.session.add(nuevo)
    db.session.commit()

    flash(f"Usuario «{usuario}» creado como {rol}.")
    return redirect(url_for("listar_usuarios"))


@app.route("/usuarios/<int:id>/eliminar", methods=["POST"])
def eliminar_usuario(id):
    objetivo = db.session.get(Usuario, id)
    if objetivo is None:
        abort(404)

    if objetivo.id == g.usuario.id:
        flash("No puedes eliminar tu propia cuenta.", "error")
    elif objetivo.rol == "admin" and Usuario.query.filter_by(rol="admin").count() <= 1:
        flash("No puedes eliminar al único administrador.", "error")
    else:
        db.session.delete(objetivo)
        db.session.commit()
        flash(f"Usuario «{objetivo.usuario}» eliminado.")
    return redirect(url_for("listar_usuarios"))


# -------------------------------------------------------------
# 9. ADMIN INICIAL
# -------------------------------------------------------------
def crear_admin_inicial():
    if Usuario.query.filter_by(rol="admin").first():
        return
    user = os.environ.get("ADMIN_USER", "admin")
    password = os.environ.get("ADMIN_PASSWORD", "Admin12345")
    admin = Usuario(nombre="Administrador", usuario=user,
                    correo=f"{user}@calidashboard.local", rol="admin")
    admin.poner_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f"[Calidashboard] Admin inicial creado: usuario '{user}'. Cambia esa contraseña cuanto antes.")


# -------------------------------------------------------------
# 10. ARRANQUE
# -------------------------------------------------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()           # crea las tablas que aún no existan
        crear_admin_inicial()
    app.run(debug=True)