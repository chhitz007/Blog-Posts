

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from bson.objectid import ObjectId

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change to a secure random key
app.config['MONGO_URI'] = 'mongodb://localhost:27017/blog'  # Change if needed

mongo = PyMongo(app)
login_manager = LoginManager(app)

# User model
class User(UserMixin):
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.id = username  # Use username as the unique ID

    def get_id(self):
        return self.username  # Return username as ID

@login_manager.user_loader
def load_user(username):
    # Load user by username instead of ObjectId
    user_data = mongo.db.users.find_one({"username": username})
    if user_data:
        return User(user_data['username'], user_data['password'])
    return None

# WTForms
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    tags = StringField('Tags (comma-separated)')
    submit = SubmitField('Post')

# Routes
@app.route('/')
def index():
    posts = mongo.db.posts.find()
    return render_template('index.html', posts=posts)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = generate_password_hash(form.password.data)
        mongo.db.users.insert_one({'username': username, 'password': password})
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)



@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user_data = mongo.db.users.find_one({'username': username})

        # Check if user exists and password is correct
        if user_data and check_password_hash(user_data['password'], password):
            user = User(username, user_data['password'])  # Create User instance
            login_user(user)  # Log the user in
            return redirect(url_for('index'))  # Redirect to the homepage
        else:
            flash('Invalid username or password', 'danger')  # Flash error message

    return render_template('login.html', form=form)  # Render login form

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))



@app.route('/create_post', methods=['GET', 'POST'])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        tags = form.tags.data.split(',') if form.tags.data else []
        mongo.db.posts.insert_one({
            'title': title,
            'content': content,
            'author': current_user.username,
            'tags': [tag.strip() for tag in tags],
            'comments': []
        })
        flash('Post created!', 'success')
        return redirect(url_for('index'))
    return render_template('create_post.html', form=form)



@app.route('/view_post/<post_id>', methods=['GET', 'POST'])
def view_post(post_id):
    post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    if request.method == 'POST':
        comment = request.form['comment']
        mongo.db.posts.update_one({'_id': ObjectId(post_id)}, {'$push': {'comments': comment}})
        flash('Comment added!', 'success')
        return redirect(url_for('view_post', post_id=post_id))
    return render_template('view_post.html', post=post)


@app.route('/edit_post/<post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = mongo.db.posts.find_one({'_id': ObjectId(post_id)})
    form = PostForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        tags = form.tags.data.split(',') if form.tags.data else []
        mongo.db.posts.update_one({'_id': ObjectId(post_id)}, {'$set': {
            'title': title,
            'content': content,
            'tags': [tag.strip() for tag in tags]
        }})
        flash('Post updated!', 'success')
        return redirect(url_for('index'))
    form.title.data = post['title']
    form.content.data = post['content']
    form.tags.data = ', '.join(post['tags'])
    return render_template('edit_post.html', form=form)



if __name__ == '__main__':
    app.run(debug=True)
