from app import app, db

def reset_database():
    with app.app_context():
        print("Eliminando tablas existentes...")
        db.drop_all()
        print("Creando tablas nuevas...")
        db.create_all()
        print("Tablas creadas exitosamente.")

if __name__ == "__main__":
    reset_database()