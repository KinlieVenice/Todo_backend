from flask import Flask, jsonify, request, send_from_directory
import mysql.connector
import pymysql
from flask_cors import CORS
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime, timedelta
from pytz import timezone
import pytz
import re
import jwt
from functools import wraps

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = os.getenv("SQL_PASSWORD")
app.config["MYSQL_DB"] = "todo_db"
app.config["DEBUG"] = True
app.config['UPLOAD_FOLDER'] = './images'
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY")

def get_db_connection():
    return pymysql.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"],
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create subjects table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users(   
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(20) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                class VARCHAR(20) NOT NULL,
                color VARCHAR(20),
                user_id INT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )

        # Create tasks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                deadline DATETIME NOT NULL,
                img_filename VARCHAR(255) NOT NULL,
                is_done BOOLEAN NOT NULL DEFAULT 0,
                subject_id INT NOT NULL,
                user_id INT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        # added an is_done column with default 0, deleted to not duplicate columns
        

        conn.commit()
        print("Successfully created tables!")
        
    except Exception as e:
        print(f"Error creating tables | Error: {e}")
        
    finally:
        cursor.close()
        conn.close()

# run one time only
with app.app_context():
    init_db()  

# LOGIN REGISTER ROUTES

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    username_or_email = data.get("username_or_email", "").strip()
    password = data.get("password", "").strip()

    if not username_or_email or not password:
        return jsonify({"error": "Both fields are required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Find user by username or email
        cursor.execute(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (username_or_email, username_or_email)
        )
        user = cursor.fetchone()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Check password
        if not check_password_hash(user["password"], password):
            return jsonify({"error": "Incorrect password"}), 401

        # Create JWT token
        token = jwt.encode({
            "user_id": user["id"],
            "username": user["username"],
            "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp())
        }, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({"message": "Login successful", "token": token}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    confirm_password = data.get("confirm_password", "").strip()
    
    # === Validation ===
    if not all([username, email, password, confirm_password]):
        return jsonify({"error": "All fields are required"}), 400

    if not re.match(r"^[a-zA-Z0-9_]{4,20}$", username):
        return jsonify({"error": "Username must be 4–20 characters, alphanumeric with underscores only."}), 400

    if not is_valid_email(email):
        return jsonify({"error": "Invalid email format."}), 400

    if not is_strong_password(password):
        return jsonify({"error": "Password must be at least 8 characters, include a number and a symbol."}), 400

    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400
    
    # === Hash password ===
    hashed_pw = generate_password_hash(password)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
        existing = cursor.fetchone()
        if existing:
            if existing["username"] == username:
                return jsonify({"error": "Username already taken"}), 409
            if existing["email"] == email:
                return jsonify({"error": "Email already registered"}), 409
        
        # === Save user ===
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_pw)
        )
        
        conn.commit()
        
        # === Get the newly made user id ===
        user_id = cursor.lastrowid
        
        # === Generate JWT Token ===
        token = jwt.encode({
            "user_id": user_id,
            "username": username,
            "exp": int((datetime.utcnow() + timedelta(days=30)).timestamp())
        }, app.config["SECRET_KEY"], algorithm="HS256")
        
        return jsonify({"message": "Registration successful", "token": token}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            request.user_id = decoded["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


# === validate email format ===
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

# === enforce strong password ===
def is_strong_password(pw):
    return (
        len(pw) >= 8 and
        re.search(r"\d", pw) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", pw)
    )

    
# ACTUAL NOTES ROUTES  
@app.route('/')
def home():
    return "Hello world!"

@app.route('/subjects', methods=['GET'])
@token_required
def get_subjects():
    user_id = request.user_id  # ✅ user_id extracted from token

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id, name, class, color FROM subjects WHERE user_id = %s",
            (user_id,)
        )

        fetched_subjects = cursor.fetchall()

        if not fetched_subjects:
            return jsonify([]), 200

        subjects = []
        for subj in fetched_subjects:
            subjects.append({
                "id": subj["id"], 
                "name": subj["name"],   
                "class": subj["class"],
                "color": subj["color"]
            })

        return jsonify(subjects), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:subject_id>/tasks', methods=['GET'])
@token_required
def get_subject_tasks(subject_id):
    user_id = request.user_id

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"],
        cursorclass=pymysql.cursors.DictCursor  # Return dicts instead of tuples
    )
    cursor = conn.cursor()

    try:
        # Step 1: Get tasks for the user and subject
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE is_done = 0 AND subject_id = %s AND user_id = %s
        """, (subject_id, user_id))
        fetched_tasks = cursor.fetchall()

        if not fetched_tasks:
            return jsonify([]), 200

        # Step 2: Get subject color
        cursor.execute("SELECT color FROM subjects WHERE id = %s", (subject_id,))
        subject = cursor.fetchone()
        subject_color = subject["color"] if subject else "#000000"

        # Step 3: Format response
        tasks = []
        ph_tz = pytz.timezone('Asia/Manila')
        now_ph = datetime.now(ph_tz)

        for task in fetched_tasks:
            deadline_dt = task["deadline"]
            deadline_ph = ph_tz.localize(deadline_dt)
            time_diff = deadline_ph - now_ph

            if time_diff.total_seconds() < 0:
                due_str = "Past due"
            elif time_diff.days > 0:
                due_str = f"Due in {time_diff.days} day{'s' if time_diff.days > 1 else ''}"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                due_str = f"Due in {hours} hour{'s' if hours > 1 else ''}"
            else:
                due_str = "Due soon"

            formatted_date = deadline_dt.strftime("%B %d, %Y")
            formatted_time = deadline_dt.strftime("%I:%M %p").lstrip("0")

            tasks.append({
                "id": task["id"],
                "name": task["name"],
                "description": task["description"],
                "deadline_date": formatted_date,
                "deadline_time": formatted_time,
                "due_text": due_str,
                "img_filename": task["img_filename"],
                "subject_id": task["subject_id"],
                "subject_color": subject_color
            })

        return jsonify(tasks), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:subject_id>/tasks', methods=['POST'])
@token_required
def create_task(subject_id):
    user_id = request.user_id
    name = request.form['name']
    description = request.form['description']
    deadline = request.form['deadline']
    image = request.files.get('img_filename')
    
    if deadline is None or image is None or name is None or description is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    img_filename = secure_filename(image.filename)
    img_name = str(uuid.uuid1()) + '_' + img_filename
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
    image.save(save_path)
    
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        deadline_dt = datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S')

        cursor.execute(
            """
            INSERT INTO tasks (name, description, deadline, img_filename, subject_id, user_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, description, deadline_dt, img_name, subject_id, user_id)
        )
        
        conn.commit()
        return jsonify({'response': 'Task successfully created!', 'img_filename': img_name}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects', methods=['POST'])
@token_required
def create_subject():
    user_id = request.user_id  
    name = request.form['name']
    classname = request.form['classname']
    color = request.form['color']

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO subjects (name, `class`, color, user_id)
            VALUES (%s, %s, %s, %s)
            """, (name, classname, color, user_id)
        )

        conn.commit()
        return jsonify({'response': 'Successfully created a subject'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:id>', methods=['DELETE'])
@token_required
def delete_subject(id):
    user_id = request.user_id  # Retrieved from the JWT token

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"],
        cursorclass=pymysql.cursors.DictCursor
    )
    cursor = conn.cursor()

    try:
        # Check if the subject exists and belongs to the user
        cursor.execute("SELECT * FROM subjects WHERE id = %s AND user_id = %s", (id, user_id))
        subject = cursor.fetchone()

        if not subject:
            return jsonify({'error': 'Subject not found or unauthorized'}), 404

        # Delete tasks associated with this subject
        cursor.execute("DELETE FROM tasks WHERE subject_id = %s AND user_id = %s", (id, user_id))

        # Delete the subject
        cursor.execute("DELETE FROM subjects WHERE id = %s AND user_id = %s", (id, user_id))

        conn.commit()
        return jsonify({'response': 'Subject successfully deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/tasks/<int:id>', methods=['DELETE'])
@token_required
def delete_task(id):
    user_id = request.user_id  # Extracted from JWT token

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()

    try:
        # Step 1: Check if the task belongs to the logged-in user
        cursor.execute("SELECT user_id FROM tasks WHERE id = %s", (id,))
        task = cursor.fetchone()

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task[0] != user_id:
            return jsonify({'error': 'Unauthorized to delete this task'}), 403

        # Step 2: Proceed to delete
        cursor.execute("DELETE FROM tasks WHERE id = %s", (id,))
        conn.commit()

        return jsonify({'response': 'Task successfully deleted!'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:id>', methods=['GET'])
@token_required
def get_indiv_subject(id):
    user_id = request.user_id  # Extracted from JWT token
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM subjects WHERE id = %s AND user_id = %s", (id, user_id))
        
        subj = cursor.fetchone()
        if not subj:
            return jsonify({'error': f'Subject with id {id} not found'}), 404

        subject = {
            "id": subj["id"], 
            "name": subj["name"],   
            "class": subj["class"],
            "color": subj["color"]
        }
        return jsonify(subject), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/tasks/<int:id>', methods=['GET'])
def get_indiv_task(id):
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (id,))
        fetched_task = cursor.fetchone()

        if not fetched_task:
            return jsonify({'error': f'Task with an id of {id} is not found'}), 404

        ph_tz = pytz.timezone('Asia/Manila')
        now_ph = datetime.now(ph_tz)

        deadline_dt = fetched_task[3]  # naive datetime from DB
        deadline_ph = ph_tz.localize(deadline_dt)
        time_diff = deadline_ph - now_ph

        if time_diff.total_seconds() < 0:
            due_str = "Past due"
        elif time_diff.days > 0:
            due_str = f"Due in {time_diff.days} day{'s' if time_diff.days > 1 else ''}"
        elif time_diff.seconds >= 3600:
            hours = time_diff.seconds // 3600
            due_str = f"Due in {hours} hour{'s' if hours > 1 else ''}"
        else:
            due_str = "Due soon"

        formatted_date = deadline_dt.strftime("%B %d, %Y")
        formatted_time = deadline_dt.strftime("%I:%M %p").lstrip("0")

        task = {
            "id": fetched_task[0],
            "name": fetched_task[1],
            "description": fetched_task[2],
            "deadline_date": formatted_date,
            "deadline_time": formatted_time,
            "due_text": due_str,
            "img_filename": fetched_task[4],
            "subject_id": fetched_task[5]
        }

        return jsonify(task), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/majors', methods=['GET'])
def get_major():
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        class_name = "major"
        cursor.execute("SELECT * FROM subjects WHERE `class` = %s", (class_name))
        
        fetched_major = cursor.fetchall()
        
        if not fetched_major:
            return [], 200
        
        majors = []
        for major in fetched_major:
            # subj_dict = {}
            
            # subj_dict["id"] = subj[0]
            # subj_dict["name"] = subj[1]
            # subj_dict["img_filename"] = subj[2]
            # subj_dict["classification_id"] = subj[3]
            
            # subjects.append(subj_dict)
            
            majors.append(
                    {
                        "id": major[0], 
                        "name": major[1],   
                        "class": major[2],
                        "color": major[3]              
                    }
                )
            
            
        return jsonify(majors), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/minors', methods=['GET'])
def get_minor():
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        class_name = "minor"
        cursor.execute("SELECT * FROM subjects WHERE `class` = %s", (class_name))
        
        fetched_minor = cursor.fetchall()
        
        if not fetched_minor:
            return [], 200
        
        minors = []
        for minor in fetched_minor:
            # subj_dict = {}
            
            # subj_dict["id"] = subj[0]
            # subj_dict["name"] = subj[1]
            # subj_dict["img_filename"] = subj[2]
            # subj_dict["classification_id"] = subj[3]
            
            # subjects.append(subj_dict)
            
            minors.append(
                    {
                        "id": minor[0], 
                        "name": minor[1],   
                        "class": minor[2],
                        "color": minor[3]              
                    }
                )
            
            
        return jsonify(minors), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()
        
@app.route('/subjects/tasks/done', methods=['GET'])
@token_required
def get_done_tasks():
    user_id = request.user_id

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()

    try:
        # Get all done tasks for the user
        cursor.execute("""
            SELECT id, name, description, deadline, img_filename, subject_id, is_done
            FROM tasks
            WHERE is_done = 1 AND user_id = %s
        """, (user_id,))
        fetched_tasks = cursor.fetchall()

        if not fetched_tasks:
            return jsonify([]), 200  # Empty list is okay

        tasks = []
        ph_tz = pytz.timezone('Asia/Manila')
        now_ph = datetime.now(ph_tz)

        for task in fetched_tasks:
            task_id, name, description, deadline_dt, img_filename, subject_id, is_done = task

            # Get subject details per task
            cursor.execute("""
                SELECT name, class, color
                FROM subjects
                WHERE id = %s AND user_id = %s
            """, (subject_id, user_id))
            subject = cursor.fetchone()

            if not subject:
                continue  # skip if subject not found (in case of orphan task)

            subject_name, subject_class, subject_color = subject

            # Manila deadline calculations
            deadline_ph = ph_tz.localize(deadline_dt)
            time_diff = deadline_ph - now_ph

            if time_diff.total_seconds() < 0:
                due_str = "Past due"
            elif time_diff.days > 0:
                due_str = f"Due in {time_diff.days} day{'s' if time_diff.days > 1 else ''}"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                due_str = f"Due in {hours} hour{'s' if hours > 1 else ''}"
            else:
                due_str = "Due soon"

            formatted_date = deadline_dt.strftime("%B %d, %Y")
            formatted_time = deadline_dt.strftime("%I:%M %p").lstrip("0")

            tasks.append({
                "id": task_id,
                "name": name,
                "description": description,
                "deadline_date": formatted_date,
                "deadline_time": formatted_time,
                "due_text": due_str,
                "img_filename": img_filename,
                "subject_id": subject_id,
                "is_done": is_done,
                "subject_name": subject_name,
                "subject_class": subject_class,
                "subject_color": subject_color
            })

        return jsonify(tasks), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:id>', methods=['PATCH'])
def edit_subject(id):
    name = request.form.get('name')
    classname = request.form.get('classname')
    color = request.form.get('color')  # fixed line
    
    print(f"Received PATCH request with: name={name}, classname={classname}, color={color}")

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            """ 
            UPDATE subjects
            SET name = %s, `class` = %s, color = %s
            WHERE id = %s
            """, (name, classname, color, id)
        )
        
        conn.commit()
        return jsonify({'response': 'Subject successfully edited'}), 200
    
    except Exception as e:
        print("ERROR:", str(e))  # Add log
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/tasks/<int:id>', methods=['PATCH'])
def edit_task(id):
    name = request.form.get('name')
    description = request.form.get('description')
    deadline = request.form.get('deadline')
    image = request.files.get('image')
    
    if deadline is None or image is None or description is None or name is None:
        return jsonify({'error': 'Missing required fields'}), 404
    
    # grab image file name
    img_filename = secure_filename(image.filename)
    
    # make img file name unique
    img_name = str(uuid.uuid1()) + '_' + img_filename
    
    # build full img path
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], img_name)
    
    # save the img
    image.save(save_path)
    
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        deadline_dt = datetime.strptime(deadline, '%Y-%m-%d %H:%M:%S')
        cursor.execute(
            """
            UPDATE tasks
            SET name = %s, description = %s, deadline = %s, img_filename = %s
            WHERE id = %s
            """, (name, description, deadline_dt, img_name, id)
        )
        
        conn.commit()
        return jsonify({'response': 'Task successfully edited!'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()    

@app.route('/tasks/done/<int:id>', methods=['PATCH'])
def mark_task_done(id):
    data = request.get_json()
    is_done = data.get('is_done', 1)

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE tasks SET is_done = %s WHERE id = %s", (is_done, id))
        conn.commit()
        return jsonify({'message': 'Task marked as done'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()

@app.route('/tasks/undone/<int:id>', methods=['PATCH'])
def unmark_task_done(id):
    data = request.get_json()
    is_done = data.get('is_done', 0)

    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE tasks SET is_done = %s WHERE id = %s", (is_done, id))
        conn.commit()
        return jsonify({'message': 'Task marked as done'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route('/images/<filename>')
def uploaded_file(filename):
    return send_from_directory('images', filename), 200


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
        
    app.run(host='0.0.0.0', port=5000)
    
    
# @app.route('/classification/<string:classname>/subjects', methods=['GET'])
# def get_class_subjects(classname):
#     conn = pymysql.connect(
#         host=app.config["MYSQL_HOST"], 
#         user=app.config["MYSQL_USER"], 
#         password=app.config["MYSQL_PASSWORD"], 
#         database=app.config["MYSQL_DB"]
#     )
#     cursor = conn.cursor()
    
#     try:
#         if classname.lower() not in ["major", "minor"]:
#             return jsonify({'error': "Invalid classification name"}), 404
        
#         cursor.execute("SELECT id FROM classification WHERE class = %s", {classname})
#         class_id = cursor.fetchone()[0]
        
#         cursor.execute("SELECT * FROM subjects WHERE classification_id = %s", {class_id})
#         fetched_subjects  = cursor.fetchall()
#         subjects = []
#         for subj in fetched_subjects:
#             subjects.append(
#                 {
#                     "id": subj[0], 
#                     "name": subj[1],   
#                     "img_filename": subj[2],
#                     "classification_id": subj[3]              
#                 }
#             )
            
#         return jsonify(subjects), 200
    
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    
#     finally: 
#         cursor.close()
#         conn.close()        
        