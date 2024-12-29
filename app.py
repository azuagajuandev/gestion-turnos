from flask import Flask, flash, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, DateTimeField, SubmitField
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
    horario_inicio = db.Column(db.Time, nullable=False, default="09:00:00")
    horario_fin = db.Column(db.Time, nullable=False, default="17:00:00")
    duracion_turno = db.Column(db.Integer, default=30)  # Minutos

# Funcion para generar turnos disponibles
def generar_disponibilidades(configuracion):
    hoy = date.today()
    limite = hoy + timedelta(days=configuracion.limite_turnos)
    horarios = []

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
            dia_actual += timedelta(days=1)
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
    fecha_turno = DateTimeField("Fecha y Hora del Turno (YYYY-MM-DD HH:MM)", format="%Y-%m-%d %H:%M", validators=[DataRequired()])
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

@app.route("/nuevo-turno", methods=["GET", "POST"])
def nuevo_turno():
    form = TurnoForm()
    if form.validate_on_submit():
        # Crear nuevo turno
        nuevo_turno = Turno(
            nombre_cliente=form.nombre_cliente.data,
            email_cliente=form.email_cliente.data,
            fecha_turno=form.fecha_turno.data
        )
        db.session.add(nuevo_turno)
        db.session.commit()
        flash("Turno reservado exitosamente", "success")
        return redirect(url_for("listar_turnos"))
    return render_template("nuevo_turno.html", form=form)

@app.route("/turnos")
def listar_turnos():
    turnos = Turno.query.all()
    return render_template("turnos.html", turnos=turnos)

if __name__=="__main__":
    app.run(debug=True)