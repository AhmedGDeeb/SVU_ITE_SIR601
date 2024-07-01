import os
import re
import copy
import time
import hashlib
import sqlite3
import traceback
import math

import textract

from flask import Flask, request, redirect, flash, jsonify, send_from_directory
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
    {"value":"english", "text": "english", "dir":"ltr"},
    {"value":"arabic", "text": "عربي", "dir":"rtl"}
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
                 database_path:str,
                 last_request_time_ns:time,
                 search_def=None,
                ):
        self.id=id;
        self.ip_address=ip_address;
        self.language=language;
        self.database_path=database_path;
        self.model=model;
        # the time of the last request sent by host to client
        self.last_request_time_ns=last_request_time_ns;
        self.search_def=search_def
        self.requests_number=1;
    
    def update(self, language:str, database_path:str, model:str, search_def):
        self.language=language;
        self.database_path=database_path;
        self.model=model;
        self.search_def = search_def;
        return self
            
    def __str__(self):
        return "<[" + str(self.ip_address) + ":" + str(self.id)[5:] + "] " + \
                "{" + \
                    "model:\"" + str(self.model) + "\", " + \
                    "language:\"" + str(self.language) + "\"," + \
                    "database:\"" + str(self.database_path)[:5] + "\", " + \
                "}>";



def boolean_model_query(search_query, documents_ids=None):
    print("getting query: ", search_query)
    #TODO, process request
    tokens=(re.compile(r'\s+', re.VERBOSE)).sub(r' ',search_query).split(" ")
    # clean query
    query=""
    query_params = None
    if(documents_ids==None):
        # use default DB
        query = "SELECT * FROM corpus WHERE " + " OR ".join(["content LIKE ?"] * len(tokens))
        query_params = ['% ' + token + ' %' for token in tokens]
    # open DB
    con = sqlite3.connect(PROCESSED_FILES_DATABASE)
    # get the documenets
    cur = con.cursor()
    # query
    cur.execute(query, query_params);
    query_results=cur.fetchall();
    con.close();
    search_results = []
    for result in query_results:
        content=result[1]
        if(tokens[0] in content):
            title = content[:content.find(" ", 25)]
            l = content.find(tokens[0])
            summary = "..." + content[l-50:l+len(tokens[0])+50] +"..."
            for token in tokens:
                summary=summary.replace(token, "<span class=selected>" + token + "</span>")
            search_results.append(
                {
                    "document_id" : result[0],
                    "title" :  title,
                    "summary" : summary,# content[max(0, result[1].find(tokens[1])-100):result[1].find(tokens[0])+len(tokens[0])+100]+"..."
                    "rank" : -1
                }
            )       
    # return results
    return search_results

def extended_boolean_model_query(search_query, documents_ids=None):
    #TODO, process request
    tokens=(re.compile(r'\s+', re.VERBOSE)).sub(r' ',search_query).split(" ")
    search_results=[]
    # clean query
    query=""
    query_params = None
    if(documents_ids==None):
        # use default DB
        query = "SELECT * FROM corpus WHERE " + " OR ".join(["content LIKE ?"] * len(tokens))
        query_params = ['% ' + token + ' %' for token in tokens]
    
    print("getting query: ", query)
    # clean query
    # open DB
    con = sqlite3.connect(os.path.join(PROCESSED_FILES_DATABASE))
    # get the documenets
    cur = con.cursor()
    # query

    cur.execute(query, query_params);
    query_results=cur.fetchall();
    con.close();
    # check content
    # ranking
    # calculate term frequency in document
    # f0 = [[t1_f_d1, t2_f_d1, t3_f_d1]]
    f = [[result[1].count(token) for token in tokens] for result in query_results]
    tf = [[ f[j][i] / len((re.compile(r'\s+', re.VERBOSE)).sub(r' ',query_results[j][1]).split(" ")) for i in range(len(f[j]))] for j in range(len(query_results))]
    d = [0] * len(tokens)
    for i in range(len(d)):
        for doc in query_results:
            if doc[1].find(tokens[i]) != -1:
                d[i] = d[i] + 1

    import math
    idf = [len(query_results)/(d[i] + 1) for i in range(len(d))]

    w = [[ f[j][i] * idf[i] / (1 + max(idf)) for i in range(len(tokens))] for j in range(len(query_results))]

    # simplification, all ands
    rank = [sum([w_i_doc**len(query_results) for w_i_doc in w_doc])**(1/len(query_results)) for w_doc in w]
    print(rank)
    for i in range(len(query_results)):
        result=query_results[i]
        content=result[1]
        print(tokens[0] in result[1])
        if(tokens[0] in result[1]):
            title = content[:content.find(" ", 25)]
            l = content.find(tokens[0])
            summary = "..." + content[l-50:l+len(tokens[0])+50] +"..."
            for token in tokens:
                summary=summary.replace(token, "<span class=selected>" + token + "</span>")
            search_results.append(
                {
                    "document_id" : result[0],
                    "title" :  title,
                    "summary" : summary,
                    "rank" : round(rank[i],5)
                }
            )
    # sorting by rank
    search_results = sorted(search_results, key=lambda d: d['rank'])
    search_results.reverse()
    # return results
    return search_results

def vector_model_query(search_query, documents_ids=None):
    # Tokenize and clean the search query
    tokens = re.sub(r'\s+', ' ', search_query).strip().split(" ")
    search_results = []

    # Construct the SQL query based on the search tokens
    query = ""
    query_params = None
    if documents_ids is None:
        query = "SELECT * FROM corpus WHERE " + " OR ".join(["content LIKE ?"] * len(tokens))
        query_params = ['%' + token + '%' for token in tokens]
    else:
        # Handle the case where documents_ids are provided (not implemented in this snippet)
        pass
    
    print("Executing query: ", query)
    
    # Execute the SQL query to fetch relevant documents
    con = sqlite3.connect(PROCESSED_FILES_DATABASE)
    cur = con.cursor()
    cur.execute(query, query_params)
    query_results = cur.fetchall()
    con.close()

    # Calculate term frequency (TF) for each document
    f = [[result[1].count(token) for token in tokens] for result in query_results]
    tf = [[f[j][i] / len(re.sub(r'\s+', ' ', query_results[j][1]).split(" ")) for i in range(len(f[j]))] for j in range(len(query_results))]

    # Calculate document frequency (DF) for each token
    d = [0] * len(tokens)
    for i in range(len(d)):
        for doc in query_results:
            if doc[1].find(tokens[i]) != -1:
                d[i] += 1

    # Calculate inverse document frequency (IDF)
    idf = [math.log(len(query_results) / (d[i] + 1)) for i in range(len(d))]

    # Calculate TF-IDF vectors for each document
    tf_idf_docs = [[tf[j][i] * idf[i] for i in range(len(tokens))] for j in range(len(query_results))]

    # Calculate TF-IDF vector for the query
    query_tf = [tokens.count(token) / len(tokens) for token in tokens]
    query_tf_idf = [query_tf[i] * idf[i] for i in range(len(tokens))]

    # Calculate cosine similarity between query and document vectors
    def cosine_similarity(vec1, vec2):
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))
        if not norm1 or not norm2:
            return 0.0
        return dot_product / (norm1 * norm2)

    similarities = [cosine_similarity(query_tf_idf, doc_tf_idf) for doc_tf_idf in tf_idf_docs]

    # Format the search results
    for i in range(len(query_results)):
        result = query_results[i]
        content = result[1]
        if tokens[0] in content:
            title = content[:content.find(" ", 25)]
            l = content.find(tokens[0])
            summary = "..." + content[max(l-50, 0):l+len(tokens[0])+50] + "..."
            for token in tokens:
                summary = summary.replace(token, "<span class=selected>" + token + "</span>")
            search_results.append({
                "document_id": result[0],
                "title": title,
                "summary": summary,
                "rank": round(similarities[i], 2)
            })

    # Sort search results by similarity (rank) in descending order
    search_results.sort(key=lambda d: d['rank'], reverse=True)

    return search_results

SUPPORTED_MODELS=[
    {"id":"0M01", "value":"boolean model", "text": "Boolean Model", "def" : boolean_model_query},
    {"id":"0M02", "value":"extended boolean model", "text": "Extended Boolean Model", "def" : extended_boolean_model_query},
    {"id":"0M03", "value":"vector model", "text": "Vector Model", "def" : vector_model_query},
];
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
    use_dafault_db=str(request.args.get('use_default_db')) if request.method == "GET" else str(request.form.get("use_default_db"))
    host_language=str(request.args.get('language')) if request.method == "GET" else str(request.form.get("language"))
    host_model=str(request.args.get('model')) if request.method == "GET" else str(request.form.get("model"))
    if(host_language == None or host_model==None):
        flash("Bad Request!!", "error")
    if(
        not any([host_language==language["value"] for language in SUPPORTED_LANGUAGES])
    ):
        flash("Unsupported language!!", "error")
        return redirect("/")
    
    _ = [host_model == smodel["value"] for smodel in SUPPORTED_MODELS]
    if(
        not any(_)
    ):
        flash("Ussuported model!!", "error")
        return redirect("search")
    
    # set search_def
    hosts_search_def = SUPPORTED_MODELS[_.index(True)]["def"]
    host_database_path = None
    
    last_request_time_ns=time.time_ns()
    try:
        if(use_dafault_db=="on"):
            # using an existed DB
            host_database_path = None

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
                return redirect("/")
            _ = len(files)
            # unsupported files found, redirect to index with error message
            files = [file for file in files if file.filename.split(".")[-1] in ALLOWED_EXTENSIONS]
            if(len(files)!=_):
                # TODO: redirect with error message
                flash("Choose Supported Corpus Files Only.", "error") 
                return redirect("/")

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
                cols = file_data.split(";")
                if(len(cols) == 3):
                    file_sha512=str([0]).encode("utf-8")
                    database_sha512.update(file_sha512)
            database_sha512_hash=str(database_sha512.hexdigest())
            if not os.path.exists(FILES_UPLOAD_DATABASE):
                print("", file=open(FILES_UPLOAD_DATABASE, "w", encoding="utf-8"))
            flash("host database has been created", "success")

        # save host settings
        if(host_id in hosts.keys()):
            # update
            hosts[host_id] = hosts[host_id].update(
                model=host_model,
                language=host_language,
                database_path=host_database_path,
                search_def=hosts_search_def
            )
            hosts[host_id].last_request_time_ns=time.time()
            hosts[host_id].requests_number=hosts[host_id].requests_number+1
        else:
            # create new
            hosts[host_id]=host(
                id=host_id, 
                ip_address=host_ip, 
                language=host_language, 
                model=host_model, 
                last_request_time_ns=last_request_time_ns, 
                database_path=host_database_path,
                search_def=hosts_search_def
            );

        
    except Exception as e:
        traceback.print_exc()
        flash("Sever had an internal error, that is all we known!!", "error")

    # make the request and send the results back in ajax
    return redirect("/search")

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

    # if host not in hosts, redirect to index
    host_id=str(hashlib.sha512(host_ip).hexdigest())
    if(not host_id in hosts.keys()):
        return redirect("/")
    
    host = hosts[host_id]
    # you can add condition here to block user that send requests fast
    # or how accessed the number of requests allowed
    host.last_request_time_ns=time.time()
    host.requests_number=host.requests_number+1
    
    # seach parameters
    language=host.language
    model=host.model
    database=host.database_path
    search_util=host.search_def

    # get the request
    search_request=request.args.get('search-request') if request.method == "GET" else str(request.form.get("search-request"))
    if(search_request==None):
        return render_template("search.html", 
                            search_request="Ask me anything...", 
                            total_results_count=0, 
                            search_results=[], 
                            search_time_sec=0,
                            search_model=model

        );

    search_request=str(search_request)

    

    if(
        not any([language==slanguage["value"] for slanguage in SUPPORTED_LANGUAGES])
    ):
        flash("Unsupported language!!", "error")
        return redirect("search")
    
    _ = [model == smodel["value"] for smodel in SUPPORTED_MODELS]
    if(
        not any(_)
    ):
        flash("Ussuported model!!", "error")
        return redirect("search")

    print("get the request: ", search_request, language, model, database, search_util)
        

    # TODO, search
    _ = time.time()
    search_results = search_util(*[search_request, None])
    _ = time.time() - _
    # make the request and send the results back in ajax
    return render_template("search.html", 
                           search_request=search_request, 
                           total_results_count=len(search_results), 
                           search_results=search_results, 
                           search_time_sec=round(_,2),
                           search_model=model
    );

@app.route("/doc", methods=['POST'])
def doc():
    # check if user blocked
    host_ip=str(request.environ.get('REMOTE_ADDR')).encode("utf-8")
    if re.match(
        pattern=host_ip, 
        string=open(BLOCKED_HOSTS_DATABASE, "r", encoding="utf-8").read().encode("utf-8")
        ):
        return "User Blocked!!"
    # returns the document in ajax
    # get the document id
    if request.method == "POST":
        json_data = request.get_json()
        print(json_data)

    print(json_data)
    db_connection = sqlite3.connect(PROCESSED_FILES_DATABASE)
    db_cursor = db_connection.cursor()
    db_cursor.execute("""SELECT * FROM corpus WHERE id=?""", [json_data["doc_id"]]);
    query_result = db_cursor.fetchone()[1]
    db_cursor.close();
    db_connection.close();
    content=query_result    
    results = {'content': content}
    return jsonify(results)
    
@app.route('/robots.txt')
@app.route('/sitemap.xml')
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])
# ----------------------------------------------------
if(__name__ == "__main__"):
    app.run(debug=True, port=5000)
