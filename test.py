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
                FOREIGN KEY (subject_id) REFERENCES subjects(id),
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

# ROUTES  
@app.route('/')
def home():
    return "Hello world!"

@app.route('/users/<id:user_id>/subjects', methods=['GET'])
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
            cursor.execute("SELECT id, name, class, color FROM subjects WHERE user_id = %s", (user_id,));
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
                        "color": subj[3],
                        "user_id": subj[4]
                                      
                    }
                )
            
            
        return jsonify(subjects), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    finally:
        cursor.close()
        conn.close()


# @app.route('/tasks/done', methods=['GET'])
# def get_done():
#     conn = pymysql.connect(
#         host=app.config["MYSQL_HOST"], 
#         user=app.config["MYSQL_USER"], 
#         password=app.config["MYSQL_PASSWORD"], 
#         database=app.config["MYSQL_DB"]
#     )
#     cursor = conn.cursor()
    
#     try:
#         cursor.execute(
#             """
#             SELECT * FROM tasks WHERE is_done = 1;
#             """
#         )
        
#         fetched_done = cursor.fetchall()
        
#         if not fetched_done:
#             return [], 200
        
#         done = []
#         for indiv in fetched_done:
#             # subj_dict = {}
            
#             # subj_dict["id"] = subj[0]
#             # subj_dict["name"] = subj[1]
#             # subj_dict["img_filename"] = subj[2]
#             # subj_dict["classification_id"] = subj[3]
            
#             # subjects.append(subj_dict)
            
#             done.append(
#                     {
#                         "id": indiv[0], 
#                         "name": indiv[1],   
#                         "description": indiv[2],
#                         "deadline": indiv[3],
#                         "img_filename": indiv[4],
#                         "subject_id": indiv[5],
#                         "is_done": indiv[6]              
#                     }
#                 )
            
            
#         return jsonify(done), 200
    
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500
    
#     finally:
#         cursor.close()
#         conn.close()

