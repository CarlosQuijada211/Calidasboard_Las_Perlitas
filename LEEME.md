# Calidashboard · Sistema de práctica (Semana 8)

Aplicación Flask + MySQL para registrar lecturas de calidad del agua producto.
Las instrucciones completas están en la **Guía 8**.

## Dónde va cada archivo

```
calidashboard/                  <- carpeta del proyecto (por ejemplo, en Documentos)
├── app.py                      <- la aplicación: conexión, modelo Lectura y rutas
├── cargar_datos.py             <- reinicia la tabla y carga 12 lecturas de práctica
├── requirements.txt            <- librerías que hay que instalar
├── LEEME.md                    <- este archivo
├── database/
│   └── calidashboard_db.sql    <- se IMPORTA en phpMyAdmin (no se ejecuta con Python)
├── templates/                  <- páginas HTML (Flask las busca aquí; no cambies el nombre)
│   ├── base.html
│   ├── lecturas.html
│   └── nueva.html
└── static/                     <- archivos de estilo (Flask los busca aquí)
    └── estilos.css
```

No pongas la carpeta dentro de `C:\xampp\htdocs`: esa carpeta es para PHP. Tu proyecto Flask
puede estar en cualquier otra carpeta.

## Puesta en marcha (resumen)

1. XAMPP → Start en **Apache** y **MySQL**.
2. phpMyAdmin (`http://localhost/phpmyadmin`) → **Importar** → `database/calidashboard_db.sql` → Continuar.
3. En la terminal de VS Code, dentro de la carpeta `calidashboard`:
   ```
   python -m venv venv
   venv\Scripts\activate            (Windows)   |   source venv/bin/activate   (macOS/Linux)
   pip install -r requirements.txt
   python app.py
   ```
4. Abre `http://127.0.0.1:5000`.

Si tu MySQL tiene contraseña, edítala en `app.py` (línea `SQLALCHEMY_DATABASE_URI`).

Los datos de práctica son inventados y los límites de calidad (pH 6.5–8.5, TDS ≤ 500) son ilustrativos.
