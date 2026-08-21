from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-to-a-long-random-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///student_management.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    enrollments = db.relationship("Enrollment", backref="student", cascade="all, delete-orphan")


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(150), nullable=False)
    course_code = db.Column(db.String(30), unique=True, nullable=False)
    enrollments = db.relationship("Enrollment", backref="course", cascade="all, delete-orphan")


class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("course.id"), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        student_total=Student.query.count(),
        course_total=Course.query.count(),
        enrollment_total=Enrollment.query.count()
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))

        flash("Incorrect username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/students")
@login_required
def students():
    search = request.args.get("search", "")
    query = Student.query

    if search:
        query = query.filter(
            Student.full_name.ilike(f"%{search}%") |
            Student.email.ilike(f"%{search}%") |
            Student.department.ilike(f"%{search}%")
        )

    return render_template("students.html", students=query.order_by(Student.full_name).all(), search=search)


@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        student = Student(
            full_name=request.form["full_name"],
            email=request.form["email"],
            department=request.form["department"]
        )
        db.session.add(student)
        db.session.commit()
        flash("Student added successfully.", "success")
        return redirect(url_for("students"))

    return render_template("student_form.html", student=None)


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    student = db.get_or_404(Student, student_id)

    if request.method == "POST":
        student.full_name = request.form["full_name"]
        student.email = request.form["email"]
        student.department = request.form["department"]
        db.session.commit()
        flash("Student updated successfully.", "success")
        return redirect(url_for("students"))

    return render_template("student_form.html", student=student)


@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    student = db.get_or_404(Student, student_id)
    db.session.delete(student)
    db.session.commit()
    flash("Student deleted successfully.", "success")
    return redirect(url_for("students"))


@app.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    if request.method == "POST":
        course = Course(
            course_name=request.form["course_name"],
            course_code=request.form["course_code"]
        )
        db.session.add(course)
        db.session.commit()
        flash("Course added successfully.", "success")
        return redirect(url_for("courses"))

    return render_template("courses.html", courses=Course.query.order_by(Course.course_name).all())


@app.route("/enrollments", methods=["GET", "POST"])
@login_required
def enrollments():
    if request.method == "POST":
        enrollment = Enrollment(
            student_id=request.form["student_id"],
            course_id=request.form["course_id"]
        )
        db.session.add(enrollment)
        db.session.commit()
        flash("Student enrolled successfully.", "success")
        return redirect(url_for("enrollments"))

    return render_template(
        "enrollments.html",
        students=Student.query.order_by(Student.full_name).all(),
        courses=Course.query.order_by(Course.course_name).all(),
        enrollments=Enrollment.query.all()
    )


def create_demo_data():
    if not User.query.filter_by(username="admin").first():
        admin = User(
            username="admin",
            password_hash=generate_password_hash("DemoAdmin123!")
        )
        db.session.add(admin)

    if Course.query.count() == 0:
        db.session.add_all([
            Course(course_name="Web Development", course_code="SWE301"),
            Course(course_name="Database Systems", course_code="SWE302"),
            Course(course_name="Machine Learning", course_code="CSE401")
        ])

    if Student.query.count() == 0:
        db.session.add_all([
            Student(full_name="Demo Student One", email="student1@example.com", department="Software Engineering"),
            Student(full_name="Demo Student Two", email="student2@example.com", department="Computer Science")
        ])

    db.session.commit()


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_demo_data()

    app.run(debug=True)