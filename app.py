from flask import Flask, jsonify, request, send_from_directory
import mysql.connector
import pymysql
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
from pytz import timezone
import pytz

app = Flask(__name__)
CORS(app)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "deguzman09!"
app.config["MYSQL_DB"] = "todo_db"
app.config["DEBUG"] = True
app.config['UPLOAD_FOLDER'] = './images'

def init_db():
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        # Create subjects table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                class VARCHAR(20) NOT NULL,
                color VARCHAR(20)
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
                subject_id INT NOT NULL,
                FOREIGN KEY (subject_id) REFERENCES subjects(id)
            )
            """
        )
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
  

# ROUTES  
@app.route('/')
def home():
    return "Hello world!"

@app.route('/subjects', methods=['GET'])
def get_subjects():
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
            SELECT * FROM subjects;
            """
        )
        
        fetched_subjects = cursor.fetchall()
        
        if not fetched_subjects:
            return [], 200
        
        subjects = []
        for subj in fetched_subjects:
            # subj_dict = {}
            
            # subj_dict["id"] = subj[0]
            # subj_dict["name"] = subj[1]
            # subj_dict["img_filename"] = subj[2]
            # subj_dict["classification_id"] = subj[3]
            
            # subjects.append(subj_dict)
            
            subjects.append(
                    {
                        "id": subj[0], 
                        "name": subj[1],   
                        "class": subj[2],
                        "color": subj[3]              
                    }
                )
            
            
        return jsonify(subjects), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()
        
@app.route('/subjects/<int:id>', methods=['GET'])
def get_indiv_subject(id):
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM subjects WHERE id = %s", (id))
        
        fetched_subject = cursor.fetchone()
        if not fetched_subject:
            return jsonify({'error': f'Subject with id {id} not found'}), 404

        subject = {
            "id": fetched_subject[0],
            "name": fetched_subject[1],
            "img_filename": fetched_subject[2],
            "class": fetched_subject[3]
        }
        return jsonify(subject), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:subject_id>/tasks', methods=['GET'])
def get_subject_tasks(subject_id):
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM tasks WHERE subject_id = %s", (subject_id))
        
        fetched_tasks = cursor.fetchall()
        if not fetched_tasks:
            return jsonify({'error': f'Subject with an id of {subject_id} is not found'}), 404
        
        tasks = []
        ph_tz = pytz.timezone('Asia/Manila')
        now_ph = datetime.now(ph_tz)
        for task in fetched_tasks:
            deadline_dt = task[3]  # naive datetime from DB

            # Step 3: Get current time in Manila
            # Step 4: Calculate difference
            deadline_ph = ph_tz.localize(deadline_dt)
            time_diff = deadline_ph - now_ph

            # Now build the due_str as you did before
            if time_diff.total_seconds() < 0:
                due_str = "Past due"
            elif time_diff.days > 0:
                due_str = f"Due in {time_diff.days} day{'s' if time_diff.days > 1 else ''}"
            elif time_diff.seconds >= 3600:
                hours = time_diff.seconds // 3600
                due_str = f"Due in {hours} hour{'s' if hours > 1 else ''}"
            else:
                due_str = "Due soon"

            # Format date and time
            formatted_date = deadline_dt.strftime("%B %d, %Y")
            formatted_time = deadline_dt.strftime("%I:%M %p").lstrip("0")

            # Append result
            tasks.append({
                "id": task[0],
                "name": task[1],
                "description": task[2],
                "deadline_date": formatted_date,
                "deadline_time": formatted_time,
                "due_text": due_str,
                "img_filename": task[4],
                "subject_id": task[5]
            })
        return jsonify(tasks), 200
    
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
def get_subjects_major():
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
def get_subjects_minor():
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
        
@app.route('/subjects', methods=['POST'])
def create_subject():
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
            INSERT INTO subjects (name, `class`, color)
            VALUES (%s, %s, %s)
            """, (name, classname, color)
        )
        
        conn.commit()
        return jsonify({'response': 'Successfully created a subject'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()    

@app.route('/subjects/<int:subject_id>/tasks', methods=['POST'])
def create_task(subject_id):
    name = request.form['name']
    description = request.form['description']
    deadline = request.form['deadline']
    image = request.files.get('img_filename')
    
    if deadline is None or image is None or name is None or description is None:
        return jsonify({'error':'Missing required fields'})
    
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
            INSERT INTO tasks (name, description, deadline, img_filename, subject_id)
            VALUES (%s, %s, %s, %s, %s)
            """, (name, description, deadline_dt, img_name, subject_id)
        )
        
        conn.commit()
        return jsonify({'response': 'Task successfully created!', 'img_filename': img_name}), 200

    
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

@app.route('/subjects/<int:id>', methods=['DELETE'])
def delete_subject(id):
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
            DELETE FROM tasks
            WHERE subject_id = %s
            """, (id,)
        )
        cursor.execute(
            """
            DELETE FROM subjects
            WHERE id = %s
            """, (id,)
        )
        
        conn.commit()
        return jsonify({'response': 'Subject successfully deleted'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close() 

@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
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
            DELETE FROM tasks
            WHERE id = %s
            """, (id,)
        )
        
        conn.commit()
        return jsonify({'response': 'Task successfully edited!'}), 200
    
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
        