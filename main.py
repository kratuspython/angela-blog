from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
import os

#----------------------- APP --------------------------------#
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)
#------------------------------------------------------------#

#----------------------- Gravatar --------------------------------#
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)
#-----------------------------------------------------------------#

#----------------------- Decorator --------------------------------#
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        #If id is not 1 then return abort with 403 error
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        #Otherwise continue with the route function
        return f(*args, **kwargs)
    return decorated_function
#-----------------------------------------------------------------#

#----------------------- Login --------------------------------#
login_manager = LoginManager()
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
#--------------------------------------------------------------#

#----------------------- CONNECT TO DB --------------------------------#
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",  "sqlite:///blog.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
#----------------------------------------------------------------------#

#----------------------- CONFIGURE TABLES --------------------------------#
with app.app_context():
    class User(UserMixin, db.Model):
        __tablename__ = 'users'
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(100), unique=True)
        password = db.Column(db.String(100))
        name = db.Column(db.String(100))

        #*******Add parent relationship*******#
        #This will act like a List of Blogpost objects attached to each user.
        #The 'author' refers to the author property in the Blogpost class.
        posts = relationship("BlogPost", back_populates="author")
        #*************************************#

        # *******Add parent relationship*******#
        #This will act like a List of Comment object attached to each user.
        #The 'author' refers to the author property in the Comment class
        comments = relationship("Comment", back_populates="comment_author")
        #*************************************#
    class BlogPost(db.Model):
        __tablename__ = "blog_posts"
        id = db.Column(db.Integer, primary_key=True)

        # *******Add child relationship*******#
        # Create a Foreign key, 'users.id' the users refers to the tablename of User.
        author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
        # Create reference to the User object, the "posts" refers to the posts property in the User class.
        author = relationship("User", back_populates="posts")
        #*************************************#

        title = db.Column(db.String(250), unique=True, nullable=False)
        subtitle = db.Column(db.String(250), nullable=False)
        date = db.Column(db.String(250), nullable=False)
        body = db.Column(db.Text, nullable=False)
        img_url = db.Column(db.String(250), nullable=False)

        # ***************Parent Relationship*************#
        comments = relationship("Comment", back_populates="parent_post")
        #*************************************#
    class Comment(db.Model):
        __tablename__ = 'comments'
        id = db.Column(db.Integer, primary_key=True)

        # *******Add child relationship*******#
        #Create a Foreign key, 'users.id' the users refers to the tablename of User.
        author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
        #Create a reference to the User object, the "comments" refers to the comments property in the User class
        comment_author = relationship("User", back_populates="comments")
        #*************************************#

        # *******Add child relationship*******#
        post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
        parent_post = relationship("BlogPost", back_populates="comments")
        text = db.Column(db.Text, nullable=False)
        #*************************************#
    db.create_all()
#-------------------------------------------------------------------------#

#----------------------------- Home ---------------------------#
@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, logged_in=current_user.is_authenticated)
#--------------------------------------------------------------#

#----------------------------- Register ---------------------------#
@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        email = form.email.data
        password = generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=8)
        name = form.name.data


        if User.query.filter_by(email=email).first():
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))
        else:

            new_user = User(email=email, password=password, name=name)
            db.session.add(new_user)
            db.session.commit()

            # This line will authenticate the user with Flask_login
            login_user(new_user)
        return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, logged_in=current_user.is_authenticated)
#-------------------------------------------------------------------#

#----------------------------- Login ---------------------------#
@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        #Store inputs in variables
        email = form.email.data
        password = form.password.data

        #Look for input in database
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        elif user == None:
            flash("Please the email does not exist, please try again!")
            return redirect(url_for('login'))
        elif check_password_hash(user.password, password) == False:
            flash("The password is incorrect, please try again!")
            return redirect(url_for('login'))

    return render_template("login.html", form=form, logged_in=current_user.is_authenticated)
#-----------------------------------------------------------------#

#----------------------------- Logout ---------------------------#
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))
#----------------------------------------------------------------#

#----------------------------- Show Post ---------------------------#
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    all_comments = db.session.query(Comment).all()
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if current_user.is_authenticated:
            new_comment = Comment(text=form.comment.data, comment_author=current_user, parent_post=requested_post)
            db.session.add(new_comment)
            db.session.commit()
            return redirect(url_for('show_post', post_id=post_id))
        else:
            flash("You need to login or register to comment.")
            return redirect(url_for('login'))
    requested_post = BlogPost.query.get(post_id)
    return render_template("post.html", post=requested_post, logged_in=current_user.is_authenticated, form=form, gravatar=gravatar )
#--------------------------------------------------------------------#

#----------------------------- About ---------------------------#
@app.route("/about")
def about():
    return render_template("about.html", logged_in=current_user.is_authenticated)
#---------------------------------------------------------------#

#----------------------------- Contact ---------------------------#
@app.route("/contact")
def contact():
    return render_template("contact.html", logged_in=current_user.is_authenticated)
#-----------------------------------------------------------------#

#----------------------------- Add Post ---------------------------#
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=str(form.title.data).title(),
            subtitle=str(form.subtitle.data).capitalize(),
            body=str(form.body.data).capitalize(),
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, logged_in=current_user.is_authenticated)
#-----------------------------------------------------------------#

#----------------------------- Edit Post ---------------------------#
@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, logged_in=current_user.is_authenticated)
#--------------------------------------------------------------------#

#----------------------------- Delete Post ---------------------------#
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))
#---------------------------------------------------------------------#

#----------------------------- Run ---------------------------#
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
#-------------------------------------------------------------#


