from flask import Flask, flash, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeField, SubmitField, SelectMultipleField, IntegerField, TimeField, SelectField
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms.validators import DataRequired, Email
from datetime import datetime, timedelta, time, date
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()
# Clave secreta
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Clase para configuraciones horarios
class Configuracion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dias_no_laborales = db.Column(db.String(200), default="[]")  # Almacena como JSON
    limite_turnos = db.Column(db.Integer, default=90)  # Límite en días para sacar turnos
    horario_inicio = db.Column(db.Time, nullable=False, default=time(9, 0))  # Cambiado a time
    horario_fin = db.Column(db.Time, nullable=False, default=time(17, 0))  # Cambiado a time
    duracion_turno = db.Column(db.Integer, default=30)  # Minutos

# Clase formulario para configuracion
class ConfiguracionForm(FlaskForm):
    dias_no_laborales = SelectMultipleField("Días no laborales", choices=[
        ("0", "Lunes"), ("1", "Martes"), ("2", "Miércoles"),
        ("3", "Jueves"), ("4", "Viernes"), ("5", "Sábado"), ("6", "Domingo")
    ], widget=ListWidget(prefix_label=False), option_widget=CheckboxInput())
    limite_turnos = IntegerField("Límite de turnos (días)", default=90)
    horario_inicio = TimeField("Horario de inicio", default=time(9, 0))  # Cambiado a time para consistencia
    horario_fin = TimeField("Horario de fin", default=time(17, 0))      # Cambiado a time para consistencia
    submit = SubmitField("Guardar Configuración")

# Funcion para generar turnos disponibles
def generar_disponibilidades(configuracion):
    hoy = date.today()
    limite = hoy + timedelta(days=configuracion.limite_turnos)
    horarios = []

    # Obtener todos los turnos ya reservados
    turnos_reservados = [t.fecha_turno for t in Turno.query.all()]

    dia_actual = hoy
    while dia_actual <= limite:
        if str(dia_actual.weekday()) not in eval(configuracion.dias_no_laborales):
            horario_actual = configuracion.horario_inicio
            while horario_actual < configuracion.horario_fin:
                horarios.append({
                    "fecha": dia_actual,
                    "hora": horario_actual
                })
                horario_actual = (datetime.combine(date.min, horario_actual) + timedelta(minutes=configuracion.duracion_turno)).time()
        dia_actual += timedelta(days=1)  # FIX: Cambiado de `return horarios` a continuar el bucle correctamente
    return horarios

# Clase para los turnos
class Turno(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    email_cliente = db.Column(db.String(120), nullable=False)
    fecha_turno = db.Column(db.DateTime, nullable=False)
    pagado = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f"<turno {self.nombre_cliente} - {self.fecha_turno}>"

# Formulario agregar turno
class TurnoForm(FlaskForm):
    nombre_cliente = StringField("Nombre del Cliente", validators=[DataRequired()])
    email_cliente = StringField("Email del Cliente", validators=[DataRequired(), Email()])
    fecha_turno = SelectField("Selecciona un turno disponible", validators=[DataRequired()])
    submit = SubmitField("Reservar Turno")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cancelar-turno/<int:id>", methods=["POST"])
def cancelar_turno(id):
    turno = Turno.query.get_or_404(id)
    tiempo_restante = turno.fecha_turno - datetime.now()
    
    # Bloquear cancelación si faltan menos de 48 horas
    if tiempo_restante < timedelta(hours=48):
        flash("No puedes cancelar este turno porque faltan menos de 48 horas.", "danger")
        return redirect(url_for("listar_turnos"))
    
    # Si faltan más de 48 horas, se permite cancelar
    db.session.delete(turno)
    db.session.commit()
    flash("Turno cancelado exitosamente.", "success")
    return redirect(url_for("listar_turnos"))

@app.route("/profesional/configuracion", methods=["GET", "POST"])
def configuracion():
    configuracion = Configuracion.query.first()

    # Si no existe una configuracion, crear una nueva con valores predeterminados
    if not configuracion:
        configuracion = Configuracion()
        db.session.add(configuracion)
        db.session.commit

    form = ConfiguracionForm(obj=configuracion)

    if form.validate_on_submit():
        configuracion.dias_no_laborales = str(form.dias_no_laborales.data)
        configuracion.limite_turnos = form.limite_turnos.data
        configuracion.horario_inicio = form.horario_inicio.data
        configuracion.horario_fin = form.horario_fin.data
        db.session.commit()
        flash("Configuracion actualizada", "success")
        return redirect(url_for("index"))
    return render_template("configuracion.html", form=form)

@app.route("/cliente/disponibilidades")
def mostrar_disponibilidades():
    configuracion = Configuracion.query.first()
    if not configuracion:
        flash("No se ha configurado el sistema aún.", "warning")
        return redirect(url_for("index"))
    
    turnos_disponibles = generar_disponibilidades(configuracion)
    turnos_reservados = [t.fecha_turno for t in Turno.query.all()]
    turnos_finales = [t for t in turnos_disponibles if datetime.combine(t["fecha"], t["hora"]) not in turnos_reservados]

    return render_template("disponibilidades.html", turnos=turnos_finales)

@app.route("/cliente/nuevo-turno", methods=["GET", "POST"])
def nuevo_turno():
    configuracion = Configuracion.query.first()
    if not configuracion:
        flash("No se ha configurado el sistema aún.", "warning")
        return redirect(url_for("index"))

    form = TurnoForm()
    turnos_disponibles = generar_disponibilidades(configuracion)
    turnos_reservados = [t.fecha_turno for t in Turno.query.all()]
    turnos_finales = [
        t for t in turnos_disponibles
        if datetime.combine(t["fecha"], t["hora"]) not in turnos_reservados
    ]

    # Rellenar las opciones del SelectField
    form.fecha_turno.choices = [
        (f"{t['fecha']} {t['hora'].strftime('%H:%M')}", f"{t['fecha']} {t['hora'].strftime('%H:%M')}")
        for t in turnos_finales
    ]

    # Verificar si el turno ya existe
    if form.validate_on_submit():
        fecha_turno = datetime.strptime(form.fecha_turno.data, "%Y-%m-%d %H:%M").replace(second=0)
        turno_existente = Turno.query.filter_by(fecha_turno=fecha_turno).first()
        if turno_existente:
            flash("El turno seleccionado ya está reservado. Por favor, elige otro.", "danger")
            return redirect(url_for("nuevo_turno"))

        # Crear nuevo turno
        nuevo_turno = Turno(
            nombre_cliente=form.nombre_cliente.data,
            email_cliente=form.email_cliente.data,
            fecha_turno=datetime.strptime(form.fecha_turno.data, "%Y-%m-%d %H:%M")
        )
        db.session.add(nuevo_turno)
        db.session.commit()
        flash("Turno reservado exitosamente", "success")
        return redirect(url_for("listar_turnos"))
    return render_template("nuevo_turno.html", form=form)

@app.route("/profesional/turnos")
def listar_turnos():
    turnos = Turno.query.all()
    return render_template("turnos.html", turnos=turnos)

if __name__=="__main__":
    app.run(debug=True)