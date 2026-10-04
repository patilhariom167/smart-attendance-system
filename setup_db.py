from app import app, db, Employee

with app.app_context():
    db.drop_all()
    db.create_all()

    admin = Employee(name='Admin', email='admin@gmail.com', password='admin123', role='Admin')
    db.session.add(admin)
    db.session.commit()
    print("DATABASE RESET AND ADMIN CREATED SUCCESSFULLY!")