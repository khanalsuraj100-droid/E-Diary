from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import os

load_dotenv()

app = Flask(__name__)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship("User", backref="posts")

class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    post_id = db.Column(
        db.Integer,
        db.ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id", name="unique_user_post_like"),
    )
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = db.session.get(User, session["user_id"])
    posts = Post.query.order_by(Post.created_at.desc()).all()

    like_counts = {}
    liked_posts = set()

    for post in posts:
        like_counts[post.id] = Like.query.filter_by(
            post_id=post.id
        ).count()

        existing_like = Like.query.filter_by(
            user_id=user.id,
            post_id=post.id
        ).first()

        if existing_like:
            liked_posts.add(post.id)

    return render_template(
        "home.html",
        user=user,
        posts=posts,
        like_counts=like_counts,
        liked_posts=liked_posts
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("सबै field भर्नुहोस्।", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Password मिलेन।", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password कम्तीमा 6 characters हुनुपर्छ।", "error")
            return redirect(url_for("register"))

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash("Username वा Email पहिले नै प्रयोग भएको छ।", "error")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        flash("Account सफलतापूर्वक बन्यो। अब Login गर्नुहोस्।", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        login_value = request.form.get("login", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == login_value) |
            (User.email == login_value.lower())
        ).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            return redirect(url_for("home"))

        flash("Username/Email वा Password गलत छ।", "error")

    return render_template("login.html")


@app.route("/create-post", methods=["POST"])
def create_post():
    if "user_id" not in session:
        return redirect(url_for("login"))

    content = request.form.get("content", "").strip()

    if content:
        post = Post(
            user_id=session["user_id"],
            content=content
        )

        db.session.add(post)
        db.session.commit()

    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/api/posts/<int:post_id>/like", methods=["POST"])
def toggle_like(post_id):
    if "user_id" not in session:
        return {"success": False, "message": "Login required"}, 401

    post = db.session.get(Post, post_id)

    if not post:
        return {"success": False, "message": "Post not found"}, 404

    user_id = session["user_id"]

    existing_like = Like.query.filter_by(
        user_id=user_id,
        post_id=post_id
    ).first()

    if existing_like:
        db.session.delete(existing_like)
        liked = False
    else:
        new_like = Like(
            user_id=user_id,
            post_id=post_id
        )
        db.session.add(new_like)
        liked = True

    db.session.commit()

    like_count = Like.query.filter_by(
        post_id=post_id
    ).count()

    return {
        "success": True,
        "liked": liked,
        "like_count": like_count
    }
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)
