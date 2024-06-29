import os
import re
import copy
import time
import hashlib
import sqlite3

import textract

from flask import Flask, request, redirect, flash, send_from_directory
app = Flask(__name__)
app.secret_key = b'a secret key'
# ----------------------------------------------------
# search engine Configuration
# folders
FILES_UPLOAD_FOLDER = os.path.join("IR", "raw_files")
RAW_UTF_8_FOLDER = os.path.join("IR", "raw_UTF_8")
PROCESSED_UTF_8_FOLDER = os.path.join("IR", "processed_UTF_8")
DATABASES_FOLDER = os.path.join("IR", "databases")
# files
FILES_UPLOAD_DATABASE = os.path.join("IR", "files_db.txt")
# file_hash;file_path
BLOCKED_HOSTS_DATABASE = os.path.join("hosts", "blocked_hosts_db.txt")
# host_ip;date;notes
HOSTS_HASHES_DATABASE = os.path.join("hosts", "hosts_db.txt")
# host_hash;host_ip
ADMIN_LOG_FILE = os.path.join("admin.log")
# log important messages for admin
# database [Corpus table] : (hash512_id, processed content)
PROCESSED_FILES_DATABASE = os.path.join("IR", "processed_files.db")

# settings
SUPPORTED_LANGUAGES=[
    {"value":"english", "text": "english"},
    {"value":"arabic", "text": "عربي"}
];

SUPPORTED_MODELS=[
    {"value":"boolean model", "text": "Boolean Model"},
    {"value":"extended boolean model", "text": "Extended Boolean Model"},
    {"value":"vector model", "text": "Vector Model"},
];

# clean the server
def search_engine_clean():
    pass

# each time the server reload or reboot
def search_engine_startup_tasks():
    # if files does not exist
    if not os.path.exists(FILES_UPLOAD_DATABASE):
        print("", file=open(FILES_UPLOAD_DATABASE, "w", encoding="utf-8"))
    if not os.path.exists(BLOCKED_HOSTS_DATABASE):
        print("", file=open(BLOCKED_HOSTS_DATABASE, "w", encoding="utf-8"))
    if not os.path.exists(HOSTS_HASHES_DATABASE):
        print("", file=open(HOSTS_HASHES_DATABASE, "w", encoding="utf-8"))
    if not os.path.exists(ADMIN_LOG_FILE):
        print("", file=open(ADMIN_LOG_FILE, "w", encoding="utf-8"))
    # create processed_files.db
    if not os.path.exists(PROCESSED_FILES_DATABASE):
        _ = open(PROCESSED_FILES_DATABASE,"wb")
        _.close()
        # create DB
        db_connection = sqlite3.connect(PROCESSED_FILES_DATABASE)
        db_cursor = db_connection.cursor()
        # id is sha512 hex hash of raw file
        # content is processd text file content
        db_connection.execute("""CREATE TABLE corpus(
                    id varchar(128) primary key,
                    content text
                    );"""
        );
        db_cursor.close();
        db_connection.commit();
        db_connection.close();

    # check that each file in the rawfiles exist in files_db.txt

    # check that each raw file mentioned in files_db.txt exist in rawfiles

    # check that each database in databases exist in databases_db.txt

    # check that each database mentioned in databases_db.txt is in databases

# startup tasks
search_engine_startup_tasks()
# ----------------------------------------------------
# search engine
hosts = {} # contains all connected hosts, keys are IPs

class logger():
    pass

class host:
    def __init__(self, 
                 id:str, 
                 ip_address:str, 
                 language:str, 
                 model:str, 
                 session_start_time:time,
                 database_path:str,
                 port_number:str="", 
                ):
        self.id=id;
        self.ip_address=ip_address;
        self.port_number=port_number
        self.language=language;
        self.database_path=database_path;
        self.model=model;
        # when the first time connected to server
        self.session_start_date=session_start_time;
        # the time of the last request sent by host to client
        self.last_request_time=session_start_time;
        self.requests_number=1;
        
        pass
    
    def update(self, language:str, database_path:str, model:str):
        self.language=language;
        self.database_path=database_path;
        self.model=model;
            
    def __str__(self):
        return "<[" + str(self.ip_address) + ":" + str(self.port_number) + "] " + \
                "{" + \
                    "model:\"" + str(self.model) + "\", " + \
                    "language:\"" + str(self.language) + "\"," + \
                    "database:\"" + str(self.database_path) + "\", " + \
                "}>";

# TODO: create DBs if not existed
# TODO: log

# ----------------------------------------------------
# flask Configuration
ALLOWED_EXTENSIONS={'docx', 'pptx', 'xls', 'xlsx', 'txt', 'pdf', 'epub', 'csv', 'rtf', 'ptx'}
allowed_extensions=",".join(["."+str(ext) for ext in ALLOWED_EXTENSIONS])
# MAX_CONTENT_LENGTH=8 * 1000 * 1000 # maximum file size is 1 MB
# app.config(MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH)
# ----------------------------------------------------
# routes
from flask import render_template

@app.route("/", methods=['GET', 'POST'])
@app.route("/index", methods=['GET', 'POST'])
def index(error_message=""):
    # check if user blocked
    host_ip=str(request.environ.get('REMOTE_ADDR')).encode("utf-8")
    if re.match(
        pattern=host_ip, 
        string=open(BLOCKED_HOSTS_DATABASE, "r", encoding="utf-8").read().encode("utf-8")
        ):
        return "User Blocked!!"
    # user allowed
    return render_template(
        "index.html", 
        SUPPORTED_LANGUAGES=SUPPORTED_LANGUAGES, 
        SUPPORTED_MODELS=SUPPORTED_MODELS, 
        ALLOWED_EXTENSIONS=allowed_extensions, 
        error_message=error_message
        );

@app.route("/config", methods=['GET', 'POST'])
def config():
    # check if user blocked
    host_ip=str(request.environ.get('REMOTE_ADDR')).encode("utf-8")
    if re.match(
        pattern=host_ip, 
        string=open(BLOCKED_HOSTS_DATABASE, "r", encoding="utf-8").read().encode("utf-8")
        ):
        return "User Blocked!!"
    host_id=str(hashlib.sha512(host_ip).hexdigest())
    use_dafault_db=str(request.form.get("use_default_db"))
    host_database_path=None
    host_session_start_time=time.asctime()
    try:
        if(use_dafault_db=="on"):
            # using an existed DB
            host_database_path = request.args.get('database-path') if request.method == "GET" else request.form.get("database-path")
        else:
            # create a new DB for the client
            host_dir_path=os.path.join("hosts", host_id)
            if(not os.path.exists(host_dir_path)):
                # create new host_files_db.txt
                os.makedirs(host_dir_path)

            host_files_db_path=os.path.join(host_dir_path, "host_files_db.txt")
            host_files_db_list=[]
            # file_name;file_SHA512;file_path
            # clean host_files_db
            print("",file=open(host_files_db_path, "w", encoding="utf-8"))
            # files uploaded
            files = request.files.getlist("files")
            # no files found, redirect to index with error message
            if(len(files) == 0 or  files[0].filename == ""):
                # TODO: redirect with error message
                flash("Choose Corpus Files.", "error") 
                return redirect("/index")
            _ = len(files)
            # unsupported files found, redirect to index with error message
            files = [file for file in files if file.filename.split(".")[-1] in ALLOWED_EXTENSIONS]
            if(len(files)!=_):
                # TODO: redirect with error message
                flash("Choose Supported Corpus Files Only.", "error") 
                return redirect("/index")

            # reduce memory usage, do not repeate files, databases
            for file in files:
                # calculate hash of each file
                file_sha512=hashlib.sha3_512();
                BUF_SIZE=65536;  # 64kb chunks!
                while(True):
                    data=file.stream.read(BUF_SIZE)
                    if not data:
                        break
                    file_sha512.update(data)
                # SHA512 of the file
                file_sha512_hash=str(file_sha512.hexdigest());
                print(file_sha512_hash)
                # if file does not exist, save by its sha512 name
                file_name = file_sha512_hash+"."+file.filename.split(".")[-1]
                file_path = os.path.join(FILES_UPLOAD_FOLDER,file_name)
                if(
                    open(FILES_UPLOAD_DATABASE, "r", encoding="utf-8").read().find(file_sha512_hash) == -1
                ):
                    # return to start
                    file.stream.seek(0)
                    # save file
                    file.save(file_path)
                    # add to FILES_UPLOAD_DATABASE
                    with open(FILES_UPLOAD_DATABASE, "a") as f:
                        f.write(file_sha512_hash+";"+file_path+"\n")
                    flash("file ["+file.filename+"] uploaded", "success")

                    # get text
                    raw_file_path=os.path.join(RAW_UTF_8_FOLDER, file_sha512_hash+".txt")
                    text = textract.process(file_path).decode("utf-8")
                    # raw_UTF_8
                    print(text, file=open(
                        raw_file_path, 
                        "w",
                        encoding="utf-8")
                    );
                    flash("text extracted from file ["+file.filename+"].", "success")

                    # processed_raw_UTF_8
                    # remove white spaces
                    raw_utf_8_text=open(raw_file_path, "r", encoding="utf-8").read()
                    processed_text=(re.compile(r'[ ]{2,}', re.VERBOSE)).sub(r' ',raw_utf_8_text)
                    processed_text=(re.compile(r'[\t]{2,}', re.VERBOSE)).sub(r' ',processed_text)
                    processed_text=(re.compile(r'[\r]{2,}', re.VERBOSE)).sub(r'\n',processed_text)
                    processed_text=(re.compile(r'[\n]{2,}', re.VERBOSE)).sub(r'\n',processed_text)
                    # save
                    processed_file_path=os.path.join(PROCESSED_UTF_8_FOLDER, file_sha512_hash+".txt")
                    print(processed_text, file=open(
                        processed_file_path, 
                        "w",
                        encoding="utf-8")
                    );
                    flash("text from file ["+file.filename+"] processed.", "success")

                    # add to processed_file.db
                    # id is md5 hex hash of raw file
                    # content is processd text file content
                    # title is the first line of the document
                    db_connection = sqlite3.connect(PROCESSED_FILES_DATABASE)
                    db_cursor = db_connection.cursor()
                    print("here 1")
                    db_cursor.execute("""SELECT COUNT(*) FROM corpus WHERE id=?""", [file_sha512_hash]);
                    query_results = db_cursor.fetchone()[0]
                    
                    if(int(query_results) == 0):
                        # add to DB
                        db_cursor.execute("""INSERT INTO corpus VALUES(?, ?)""", [file_sha512_hash, processed_text])
                        db_connection.commit();
                    db_cursor.close();
                    db_connection.close();
                else:
                    # file already exist
                    flash("file ["+file.filename+"] already exist.", "success")

                # add to host_files_db.txt if not exist 
                if(not file_sha512_hash in host_files_db_list):
                    host_files_db_list.append(file_sha512_hash + ";" + file.filename + ";" + file_path + "\n")
                
            # sort and remove duplicates
            host_files_db_list=sorted(list(set(host_files_db_list)))

            # save
            with open(host_files_db_path, "a") as f:
                for file_data in host_files_db_list:
                    f.write(file_data)
            flash("host raw data min has been created", "success")

            # create DB
            database_sha512=hashlib.sha3_512()
            database_sha512_hash=""
            for file_data in host_files_db_list:
                file_sha512=str(file_data.split(";")[0]).encode("utf-8")
                assert(len(file_sha512)==128)
                database_sha512.update(file_sha512)
            database_sha512_hash=str(database_sha512.hexdigest())
            
            # 

            flash("host database has been created", "success")
    except Exception as e:
        print(e.__context__)
        flash(str(e), "error")

    return redirect("search")

"""
sqlite3 statement to select number of documents based on their ids and then select from them based on their content have specific word
"""
@app.route("/search", methods=['GET', 'POST'])
def search():
    # check if user blocked
    host_ip=str(request.environ.get('REMOTE_ADDR')).encode("utf-8")
    if re.match(
        pattern=host_ip, 
        string=open(BLOCKED_HOSTS_DATABASE, "r", encoding="utf-8").read().encode("utf-8")
        ):
        return "User Blocked!!"
    
    return render_template("search.html")

@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])
# ----------------------------------------------------
if(__name__ == "__main__"):
    app.run(debug=True, port=5000)
