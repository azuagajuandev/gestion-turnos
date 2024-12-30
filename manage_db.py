from app import app, db
from app import Usuario  # Importa el modelo Usuario

def reset_database():
    with app.app_context():
        print("Eliminando tablas existentes...")
        db.drop_all()
        print("Creando tablas nuevas...")
        db.create_all()
        print("Tablas creadas exitosamente.")

        # Crear usuarios de ejemplo
        print("Creando usuarios de ejemplo...")
        profesional = Usuario(nombre="Profesional", email="profesional@example.com", rol="profesional")
        cliente1 = Usuario(nombre="Cliente 1", email="cliente1@example.com", rol="cliente")
        cliente2 = Usuario(nombre="Cliente 2", email="cliente2@example.com", rol="cliente")
        db.session.add_all([profesional, cliente1, cliente2])
        db.session.commit()
        print("Usuarios creados exitosamente.")

if __name__ == "__main__":
    reset_database()