import os
from datetime import datetime, timezone

from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_login import (
    LoginManager, UserMixin, current_user, login_required, login_user, logout_user
)
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect, FlaskForm
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError

app = Flask(__name__, instance_relative_config=True)
os.makedirs(app.instance_path, exist_ok=True)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-change-this-secret-key"),
    SQLALCHEMY_DATABASE_URI="sqlite:///noteflow_accounts.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please sign in to access your notes."
csrf = CSRFProtect(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    notes = db.relationship("Note", backref="owner", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(120), nullable=False)
    content = db.Column(db.Text, nullable=False)
    pinned = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "pinned": self.pinned,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class RegisterForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=80)])
    email = StringField("Email address", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign in")


@app.get("/")
def home():
    if not current_user.is_authenticated:
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("home"))
    return render_template("auth.html", form=form, mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            return redirect(url_for("home"))
        form.password.errors.append("Email or password is incorrect.")
    return render_template("auth.html", form=form, mode="login")


@app.post("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


def owned_note_or_404(note_id):
    return Note.query.filter_by(id=note_id, user_id=current_user.id).first_or_404()


@app.get("/api/notes")
@login_required
def get_notes():
    search = request.args.get("q", "").strip()
    query = Note.query.filter_by(user_id=current_user.id)
    if search:
        pattern = f"%{search}%"
        query = query.filter(or_(Note.title.ilike(pattern), Note.content.ilike(pattern)))
    notes = query.order_by(Note.pinned.desc(), Note.updated_at.desc()).all()
    return jsonify([note.to_dict() for note in notes])


@app.post("/api/notes")
@login_required
def create_note():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title:
        return jsonify({"error": "Please enter a title."}), 400
    if not content:
        return jsonify({"error": "Please write something in your note."}), 400
    if len(title) > 120:
        return jsonify({"error": "Title must be 120 characters or fewer."}), 400

    note = Note(title=title, content=content, user_id=current_user.id)
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@app.put("/api/notes/<int:note_id>")
@login_required
def update_note(note_id):
    note = owned_note_or_404(note_id)
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    if not title or not content:
        return jsonify({"error": "Both title and content are required."}), 400
    if len(title) > 120:
        return jsonify({"error": "Title must be 120 characters or fewer."}), 400
    note.title = title
    note.content = content
    db.session.commit()
    return jsonify(note.to_dict())


@app.patch("/api/notes/<int:note_id>/pin")
@login_required
def toggle_pin(note_id):
    note = owned_note_or_404(note_id)
    note.pinned = not note.pinned
    db.session.commit()
    return jsonify(note.to_dict())


@app.delete("/api/notes/<int:note_id>")
@login_required
def delete_note(note_id):
    note = owned_note_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted successfully."})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "NoteFlow API"})


@app.errorhandler(400)
def handle_bad_request(error):
    # Flask-WTF raises CSRF failures as HTTP 400. Keep API responses JSON.
    if request.path.startswith("/api/"):
        return jsonify({"error": "Request could not be verified. Refresh the page and try again."}), 400
    return error


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
