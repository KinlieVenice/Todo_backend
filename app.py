from flask import Flask, jsonify, request
import mysql.connector
import pymysql
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime

app = Flask(__name__)
# CORS(app)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
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
                img_filename VARCHAR(255),
                class VARCHAR(20) NOT NULL
            )
            """
        )

        # Create tasks table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                description VARCHAR(255) NOT NULL,
                deadline DATETIME NOT NULL,
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
                        "img_filename": subj[2],
                        "class": subj[3]              
                    }
                )
            
            
        return jsonify(subjects), 200
    
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
        for task in fetched_tasks:
            # process format of deadline
            deadline_dt = task[3].strftime("%Y-%m-%d %H:%M:%S")
            
            tasks.append(
                {
                    "id": task[0],
                    "name": task[1],
                    "description": task[2],
                    "deadline": deadline_dt,
                    "subject_id": task[4]
                }
            )
        
        return jsonify(tasks), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/subjects', methods=['POST'])
def create_subject():
    name = request.form['name']
    classname = request.form['classname']
    image = request.files['image']
    
    if image is None or classname is None or name is None:
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
        cursor.execute(
            """
            INSERT INTO subjects (name, img_filename, class)
            VALUES (%s, %s, %s)
            """, (name, img_name, classname)
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
    
    if deadline is None or name is None or description is None:
        return jsonify({'error':'Missing required fields'})
    
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
            INSERT INTO tasks (name, description, deadline, subject_id)
            VALUES (%s, %s, %s, %s)
            """, (name, description, deadline_dt, subject_id)
        )
        
        conn.commit()
        return jsonify({'response': 'Task successfully created!'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/subjects/<int:id>', methods=['PATCH'])
def edit_subject(id):
    name = request.form.get('name')
    classname = request.form.get('classname')
    image = request.files.get('image')
        
    if image is None or classname is None or name is None:
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
        cursor.execute(
            """ 
            UPDATE subjects
            SET name = %s, `class` = %s, img_filename = %s
            WHERE id = %s
            """, (name, classname, img_name, id)
        )
        
        conn.commit()
        return jsonify({'response': 'Subject successfully edited'}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close() 

@app.route('/tasks/<int:id>', methods=['PATCH'])
def edit_task(id):
    name = request.form['name']
    description = request.form['description']
    deadline = request.form['deadline']
    
    if deadline is None or description is None or name is None:
        return jsonify({'error': 'Missing required fields'}), 404
    
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
            SET name = %s, description = %s, deadline = %s
            WHERE id = %s
            """, (name, description, deadline_dt, id)
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
        