import os
import re
import time
import hashlib

from flask import Flask, request
app = Flask(__name__)

# ----------------------------------------------------
# search engine Configuration
# folders
FILES_UPLOAD_FOLDER = os.path.join("IR", "raw_files")
RAW_UTF_8_FOLDER = os.path.join("IR", "raw_UTF_8")
PROCESSED_UTF_8_FOLDER = os.path.join("IR", "processed_UTF_8")
DATABASES_FOLDER = os.path.join("IR", "databases")
# databases
FILES_UPLOAD_DATABASE = os.path.join("IR", "raw_files", "files_db.txt")
# file_hash;file_path
BLOCKED_HOSTS_DATABASE = os.path.join("hosts", "blocked_hosts_db.txt")
# host_ip;date;notes
HOSTS_HASHES_DATABASE = os.path.join("hosts", "hosts_db.txt")
# host_hash;host_ip

def initiate_search_engine():
    # if files does not exist
    if not os.path.exists(FILES_UPLOAD_DATABASE):
        print("", file=open(FILES_UPLOAD_DATABASE, "w", encoding="utf-8"))
    if not os.path.exists(BLOCKED_HOSTS_DATABASE):
        print("", file=open(BLOCKED_HOSTS_DATABASE, "w", encoding="utf-8"))
    if not os.path.exists(HOSTS_HASHES_DATABASE):
        print("", file=open(HOSTS_HASHES_DATABASE, "w", encoding="utf-8"))

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
ALLOWED_EXTENSIONS = {'docx', 'pptx', 'xls', 'xlsx', 'txt', 'pdf', 'epub', 'csv', 'rtf', 'ptx'}
MAX_CONTENT_LENGTH = 8 * 1000 * 1000 # maximum file size is 1 MB

# ----------------------------------------------------
# routes
from flask import render_template

@app.route("/", methods=['GET', 'POST'])
@app.route("/index", methods=['GET', 'POST'])
def index():
    # check if user blocked
    host_ip=str(request.environ.get('REMOTE_ADDR')).encode("utf-8")
    if re.match(
        pattern=host_ip, 
        string=open(BLOCKED_HOSTS_DATABASE, "r", encoding="utf-8").read().encode("utf-8")
        ):
        return "User Blocked!!"
    host_id=hashlib.sha512(host_ip).hexdigest()
    use_dafault_db=str(request.form.get("use_default_db"))
    host_database_path=None
    host_raw_files_path=None
    host_session_start_time=time.asctime()
    return render_template("index.html", error_message="")

@app.route("/search", methods=['GET', 'POST'])
def search():
    # check if user blocked
    host_ip=str(request.environ.get('REMOTE_ADDR')).encode("utf-8")
    if re.match(
        pattern=host_ip, 
        string=open(BLOCKED_HOSTS_DATABASE, "r")
        ):
        return "User Blocked!!"
    return render_template("search.html")

# ----------------------------------------------------
if(__name__ == "__main__"):
    app.run(debug=True, port=5000)
