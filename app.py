from flask import Flask, request, redirect, url_for, render_template as rt,make_response,session,jsonify
from flask_security import Security, SQLAlchemyUserDatastore, login_required, login_user,logout_user,current_user
from flask_security.utils import hash_password, verify_password
from flask_jwt_extended import JWTManager, create_access_token
from flask_login import current_user
from flask_restful import Api
from model import *
from api import *
import os
from celery_worker import make_celery
from functools import wraps
from flask import flash
from intances import cache

app = Flask(__name__)
current_dir = os.path.abspath(os.path.dirname(__file__))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(current_dir, "mad2data.sqlite3")
app.config['SECRET_KEY'] = 'supersecret'
app.config['SECURITY_PASSWORD_SALT'] = 'salt'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY']='SECRETKEYFORENCRYPTION'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=30)
app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379',
    result_backend='redis://localhost:6379'
)

app.config["CACHE_TYPE"] = "RedisCache"
app.config["CACHE_REDIS_HOST"] = "localhost"
app.config["CACHE_REDIS_PORT"] = 6379
app.config["CACHE_REDIS_DB"] = 3
app.config["CACHE_REDIS_URL"] = "redis://localhost:6379/3"
app.config["CACHE_DEFAULT_TIMEOUT"] = 300

db.init_app(app)
jwt= JWTManager(app)


app.jinja_options = app.jinja_options.copy()
app.jinja_options['variable_start_string'] = '[[ '
app.jinja_options['variable_end_string'] = ' ]]'

celery=make_celery(app)
cache.init_app(app)

# Setup Flask-Security
user_datastore = SQLAlchemyUserDatastore(db, User, Role)
security = Security(app, user_datastore)

api = Api(app)
api.add_resource(SectionResource, '/api/sections', '/api/sections/<section_id>')
api.add_resource(BookResource, '/api/sections/<int:section_id>/books','/api/sections/<int:section_id>/books/<int:book_id>')
api.add_resource(RequestedBooksResource, '/api/requested_books')
api.add_resource(GrantBookResource, '/api/grant_book')
api.add_resource(RejectBookResource, '/api/reject_book')
api.add_resource(BooksBySection,'/api/books_by_section')
api.add_resource(RequestBook, '/api/request_book/<int:book_id>')
api.add_resource(BookDetails, '/api/book_details/<int:book_id>')
api.add_resource(AllBooksResource,'/api/avail_books')
api.add_resource(AllocatedBooksResource,'/api/alloc_books')
api.add_resource(RevokeAccessResource,'/api/revoke_book')
api.add_resource(ReturnBook,'/api/return_book/<int:book_id>')
api.add_resource(FeedBack,'/api/submit_feedback')
api.add_resource(ReturnedBooks,'/api/returned_bks')
api.add_resource(IssuedBooks,'/api/my_books')
api.add_resource(LibStatistics,'/api/graphs/librarian_stats')
api.add_resource(UsrStatistics,'/api/graphs/user_stats')
api.add_resource(CurrentUser,'/api/current_user')

# Admin credentials
ADMIN_EMAIL = 'admin@example.com'
ADMIN_PASSWORD = 'admin123'

initialized_roles = False  

def initialize_roles():
    global initialized_roles
    if not initialized_roles:
        if not Role.query.filter_by(name='user').first():
            user_role = Role(name='user', description='Basic User Role')
            db.session.add(user_role)
        if not Role.query.filter_by(name='admin').first():
            admin_role = Role(name='admin', description='Administrator Role')
            db.session.add(admin_role)
        db.session.commit()
        initialized_roles = True  # Set flag to True after roles are initialized
    
    if not User.query.filter_by(email=ADMIN_EMAIL).first():
        admin_user = user_datastore.create_user(
            username='admin',
            email=ADMIN_EMAIL,
            password=hash_password(ADMIN_PASSWORD),
            user_type='admin',
            active=True
        )
        admin_role = Role.query.filter_by(name='admin').first()
        admin_user.roles.append(admin_role)
        db.session.commit()


with app.app_context():
    db.create_all()
    initialize_roles()


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_role('admin'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.has_role('user'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_data = User.query.filter_by(email=email).first()
        if user_data and verify_password(password, user_data.password):
            login_user(user_data)
            global token
            token = create_access_token(identity = user_data.email)
            user_data.API_token = token
            user_data.log_login()
            db.session.commit()
            if user_data.user_type == 'user':
                return jsonify({'redirect': url_for('user_dashboard'), 'token': token})
            elif user_data.user_type == 'admin':
                return jsonify({'redirect': url_for('librarian_dashboard'), 'token': token})

        # return rt('home.html', message="Wrong email or password")
        return jsonify({'error': 'Wrong email or password'}), 401
    return rt('home.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        if not User.query.filter_by(email=email).first():
            new_user = user_datastore.create_user(
                username=username,
                email=email,
                password=hash_password(password),
                user_type='user'
            )
            role =  Role.query.filter_by(name='user').first()
            if role:
                new_user.roles.append(role)
            db.session.commit()
            return redirect(url_for('home'))
    return rt('signup.html')

@app.route('/user_dashboard', methods=['GET'])
@login_required
@user_required
def user_dashboard():
    return rt('all_books.html')

@app.route('/librarian_dashboard', methods=['GET'])
@login_required
@admin_required
def librarian_dashboard():
    return rt('librarianDashboard.html')

@app.route('/add_book', methods=['GET'])
@login_required
@admin_required
def add_book():
    section_id = request.args.get('sectionId')
    print(f"Section ID: {section_id}") 

    if not section_id:
        return "Section ID is required", 400

    return rt('add_book.html', sectionId=section_id)

@app.route('/requested_books', methods=['GET'])
@login_required
@admin_required
def requestedbooks():
    return rt('requested_books.html')

@app.route('/allocated_books', methods=['GET'])
@login_required
@admin_required
def allocatedbooks():
    return rt('allocated_books.html')

@app.route('/available_books', methods=['GET'])
@login_required
@admin_required
def availablebooks():
    return rt('available_books.html')

@app.route('/book_details', methods=['GET'])
@login_required
@user_required
def bookdet():
    book_id = request.args.get('bookId')
    print(f"Book ID: {book_id}") 
    if not book_id:
        return "Book ID is required",400
    
    return rt('book_details.html',bookId=book_id)

@app.route('/usr_returned_books', methods=['GET'])
@login_required
@user_required
def usrreturnedbooks():
    return rt('returned_books.html')

@app.route('/issued_books', methods=['GET'])
@login_required
@user_required
def mybooks():
    return rt('my_books.html')

@app.route('/lib_stats',methods=['GET'])
@login_required
@admin_required
def libstats():
    return rt('lib_stats.html')

@app.route('/usr_stats',methods=['GET'])
@login_required
@user_required
def usrstats():
    return rt('usr_stats.html')

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return rt('logout.html')


###################################################   CELERY   #########################################3


from datetime import datetime, timedelta
import pytz
from Email import send_email

@celery.task
def daily_user_reminder(): 
    yesterday = datetime.now(pytz.timezone('Asia/Kolkata')) - timedelta(days=1)
    users_to_remind = User.query.filter(User.last_login < yesterday).all()
    for user in users_to_remind:
        msg = rt('daily_rem.html', user_name= user.username)
        send_email(to_address=user.email, subject= "Website reminder", message=msg)


from sqlalchemy import func

@celery.task
def generate_monthly_report(): 
    users = User.query.all()
    for user in users:
        allocated_books_count = BookIssued.query.filter_by(user_id=user.email).count()
        # print(allocated_books_count) 
        distinct_sections_count = Book.query.join(BookIssued).filter(BookIssued.user_id == user.email).distinct(Book.section_id).count()
        returned_books_count = BookIssued.query.filter_by(user_id=user.email, returned=1).count()
        avg_rating = db.session.query(func.avg(BookIssued.rating)).filter(BookIssued.user_id == user.email).scalar()
        msg = rt("monthly_report.html", user=user.username, books_alloc=allocated_books_count,sections_explored=distinct_sections_count,books_returned=returned_books_count,
            average_rating=avg_rating
        )
        send_email(to_address=user.email, subject="Montly User Report", message=msg)


###################################################### CSV ASYNC EXPORT JOB ################################################

from flask import flash, send_file
import csv

@celery.task(name='app.gen_csv')
def gen_csv(user_email):
    rows = []

    book_issued_data = db.session.query(
        BookIssued.user_id,
        BookIssued.book_id,
        Book.title,
        Book.content,
        Book.authors,
        BookIssued.date_of_issue,
        BookIssued.return_date
    ).join(Book, Book.id == BookIssued.book_id).all()

    for book in book_issued_data:
        rows.append([
            
            book.user_id,
            book.book_id,
            book.title,
            book.content,
            book.authors,
            book.date_of_issue,
            book.return_date
        ])

    fields = ['User Id','Book Id', 'Title', 'Content', 'Author(s)', 'Date Issued', 'Return Date']

    output_path = os.path.join("static", "report.csv")

    with open(output_path, 'w', newline='') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)
        csvwriter.writerows(rows)

    send_email( to_address=user_email, subject="CSV Export Completed", message="The CSV export has been completed. Please download the file from the admin dashboard.")
    
    return "CSV file generated"

@app.route("/triger_celery_job", methods=["POST"])
def triger_celery_job():
    user_email = request.json.get('email')  
    task = gen_csv.delay(user_email)
    return jsonify({
        "Task_ID": task.id,
        "Task_State": task.state,
        "Task_Result": task.result
    }), 202

@app.route("/status/<id>")
def check_status(id):
    res = celery.AsyncResult(id)
    return jsonify({
        "Task_ID": res.id,
        "Task_State": res.state,
        "Task_Result": res.result
    })

@app.route("/download-csv")
def download_file():
    return send_file("static/report.csv", as_attachment=True, download_name='books_report.csv')


celery.conf.beat_schedule = {

            'task_daily_reminder': {
            'task': 'app.daily_user_reminder',
            'schedule': timedelta(seconds=30),  
            },

            'task_monthly_report': {
                'task': 'app.generate_monthly_report',
                'schedule': timedelta(seconds=30),  
            },
            'task_gen_csv': {
                'task': 'app.gen_csv',
                'schedule': timedelta(seconds=30),  # Example: Run weekly
                'args': ['admin@example.com']  
            }
            
                            
    }


if __name__ == '__main__':  
    app.run(host='0.0.0.0', debug=True)
