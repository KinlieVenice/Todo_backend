from flask import Flask, jsonify
import mysql.connector
import pymysql
from flask_cors import CORS

app = Flask(__name__)
# CORS(app)

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "deguzman09!"
app.config["MYSQL_DB"] = "todo_db"
app.config["DEBUG"] = True



def init_db():
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
            CREATE TABLE IF NOT EXISTS classification (
                id INT AUTO_INCREMENT PRIMARY KEY,
                class VARCHAR(10) NOT NULL
            )
            """
        )

        # Create subjects table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                img_filename VARCHAR(255),
                classification_id INT NOT NULL,
                FOREIGN KEY (classification_id) REFERENCES classification(id)
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
                        "classification_id": subj[3]              
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
            tasks.append(
                {
                    "id": task[0],
                    "name": task[1],
                    "description": task[2],
                    "deadline": task[3],
                    "subject_id": task[4]
                }
            )
        
        return jsonify(tasks), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()

@app.route('/classification/<string:classname>/subjects', methods=['GET'])
def get_class_subjects(classname):
    conn = pymysql.connect(
        host=app.config["MYSQL_HOST"], 
        user=app.config["MYSQL_USER"], 
        password=app.config["MYSQL_PASSWORD"], 
        database=app.config["MYSQL_DB"]
    )
    cursor = conn.cursor()
    
    try:
        if classname.lower() not in ["major", "minor"]:
            return jsonify({'error': "Invalid classification name"}), 404
        
        cursor.execute("SELECT id FROM classification WHERE class = %s", {classname})
        class_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT * FROM subjects WHERE classification_id = %s", {class_id})
        fetched_subjects  = cursor.fetchall()
        subjects = []
        for subj in fetched_subjects:
            subjects.append(
                {
                    "id": subj[0], 
                    "name": subj[1],   
                    "img_filename": subj[2],
                    "classification_id": subj[3]              
                }
            )
            
        return jsonify(subjects), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally: 
        cursor.close()
        conn.close()        
        

if __name__ == '__main__':
    app.run()
    