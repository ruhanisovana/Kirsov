import os

BASE_URL = os.getenv("KIRSOV_URL", "")

from flask import Flask, render_template, request, redirect, session
from cs50 import SQL
from datetime import datetime
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from werkzeug.utils import secure_filename


import traceback

import faulthandler
faulthandler.enable()

app = Flask(__name__)

os.makedirs("static/uploads", exist_ok=True)
app.config["SESSION_COOKIE_NAME"] = "kirsov_session"
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.secret_key = os.getenv("SECRET_KEY", "change-this-in-render")

from datetime import timedelta

app.permanent_session_lifetime = timedelta(days=30)


DATABASE_URL = os.getenv("DATABASE_URL")

    
if DATABASE_URL:
    db = SQL(DATABASE_URL)
else:
    db = SQL("sqlite:///kirsov.db")

db.execute("""
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    sender_id INTEGER,
    receiver_id INTEGER,
    name TEXT,
    category TEXT,
    phone TEXT,
    address TEXT,
    amount INTEGER,
    amount_paid INTEGER DEFAULT 0,
    payment_mode TEXT,
    payment_info TEXT,
    status TEXT,
    deadline TEXT,
    message TEXT,
    admin_name TEXT,
    created_at TEXT,
    status_flag TEXT DEFAULT 'active',
    previous_status TEXT,
    version INTEGER DEFAULT 1,
    edited_at TEXT,
    edited_by INTEGER

)
""")

db.execute("""CREATE TABLE IF NOT EXISTS payment_history ( id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER, amount INTEGER, payment_date TEXT, created_at TEXT, status_flag TEXT DEFAULT 'active', deleted_at TEXT, user_id INTEGER, owner_id INTEGER)""")

db.execute("""CREATE TABLE IF NOT EXISTS payment_notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    amount INTEGER,
    note TEXT,
    created_at TEXT,
    status TEXT DEFAULT 'waiting',
    rejection_reason TEXT,
    proof TEXT,
    proof_image TEXT,
    sender_reply TEXT,
    status_flag TEXT DEFAULT 'active',
    deleted_at TEXT,
    user_id INTEGER,
    owner_id INTEGER
)""")

db.execute("""
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    category TEXT,
    title TEXT,
    message TEXT,
    supports INTEGER DEFAULT 0,
    created_at TEXT
)""")

db.execute("""CREATE TABLE IF NOT EXISTS feedback_supports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feedback_id INTEGER,
    user_id INTEGER
)
""")
db.execute("""CREATE TABLE IF NOT EXISTS feedback_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    feedback_id INTEGER,
    message TEXT,
    created_at TEXT
)""")

db.execute("""
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    request_id INTEGER,
    message TEXT,
    type TEXT,
    is_read INTEGER DEFAULT 0,
    created_at TEXT
)
""")

db.execute("""CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    purpose TEXT
)""")

db.execute("""
CREATE TABLE IF NOT EXISTS payment_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    payment_id INTEGER,
    from_user_id INTEGER,
    to_user_id INTEGER,
    amount INTEGER,
    reason TEXT,
    status TEXT DEFAULT 'waiting',
    created_at TEXT
)
""")
@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    user_rows = db.execute(
        "SELECT * FROM users WHERE id = ?",
        session["user_id"]
    )

    if len(user_rows) == 0:
        session.clear()
        return redirect("/login")

    return render_template(
        "home.html",
        user=user_rows[0],
        BASE_URL=BASE_URL
    )

@app.route("/index")
def index():
   
    if "user_id" not in session:
        return redirect("/login")

    total_count = db.execute("""
SELECT COUNT(*) AS total
FROM requests
WHERE user_id = ?
""", session["user_id"])[0]["total"]

    pending_count = db.execute("""
SELECT COUNT(*) AS total
FROM requests
WHERE status = 'Pending' AND user_id = ?
""", session["user_id"])[0]["total"]


    progress_count = db.execute("""
SELECT COUNT(*) AS total
FROM requests
WHERE status = 'In Progress' AND user_id = ?
""", session["user_id"])[0]["total"]


    completed_count = db.execute("""
SELECT COUNT(*) AS total
FROM requests
WHERE status = 'Completed' AND user_id =?
""", session["user_id"])[0]["total"]
    
    
    cancelled_count = db.execute("""
SELECT COUNT(*) AS total
FROM requests
WHERE status = 'Cancelled' AND user_id = ?
""", session["user_id"])[0]["total"]
        
    user = db.execute("""
SELECT username, purpose
FROM users
WHERE id = ?
""", session["user_id"])[0]

    people = db.execute("""
SELECT *
FROM requests
WHERE (sender_id = ? OR receiver_id = ?)
AND status_flag = 'active'
ORDER BY id DESC
""",
session["user_id"],
session["user_id"])

    unread_count = db.execute("""
SELECT COUNT(*) AS total
FROM notifications
WHERE receiver_id = ?
AND is_read = 0
""", session["user_id"])[0]["total"]
    
    return render_template("index.html", people=people,
    total_count=total_count,
    pending_count=pending_count,
    progress_count=progress_count,
    completed_count=completed_count,
    cancelled_count=cancelled_count,
    user=user,
    unread_count=unread_count)
@app.route("/add", methods=["POST"])
def add():
  
  
    if "user_id" not in session:  
        return redirect("/login")  
  
    created_at = datetime.now().strftime("%H:%M:%S")  

    name = request.form.get("name")  

    category = request.form.get("category")  

    phone = request.form.get("phone")  

    address = request.form.get("address")  

    amount = request.form.get("amount")  

    payment_mode = request.form.get("payment_mode")  
    payment_info = request.form.get("payment_info")  
  
    status = request.form.get("status")  
  
    deadline = request.form.get("deadline")  

    message = request.form.get("message")    
  
    admin_name = request.form.get("admin_name")  

    sender_id = session["user_id"]  

    receiver = db.execute("""

SELECT id
FROM users
WHERE phone = ?
""", phone)

    if receiver:  
        receiver_id = receiver[0]["id"]  
    else:  
        receiver_id = None  
      
    print("Phone from form:", repr(phone))  
    print("Receiver:", receiver)  
    print("Receiver ID:", receiver_id)  
  
    db.execute("""

INSERT INTO requests
(
user_id,
sender_id,
receiver_id,
name,
category,
phone,
address,
amount,
payment_mode,
payment_info,
deadline,
message,
created_at,
admin_name
)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
""",
session["user_id"],
sender_id,
receiver_id,
name,
category,
phone,
address,
amount,
payment_mode,
payment_info,
deadline,
message,
created_at,
admin_name
)

    request_id = db.execute(  
"SELECT last_insert_rowid() AS id"

)[0]["id"]


    sender = db.execute(  
"SELECT username FROM users WHERE id = ?",  
sender_id

)[0]

    print("About to insert notification")  
  
    print("sender_id =", sender_id)  
    print("receiver_id =", receiver_id)  
    print("phone =", phone)  
    print(receiver)  
   
  
    if receiver_id:  
        db.execute("""

INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
sender_id,
receiver_id,
request_id,
f"{sender['username']} sent you a new Kirsov request.",
"new_request",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)


    return redirect("/index")  

@app.route("/delete/<int:id>")
def delete(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
    
    row = db.execute(
        "SELECT status FROM requests WHERE id = ? AND user_id = ?",
        id, session["user_id"]
    )[0]
    
    if row["status"] != "Cancelled":
        db.execute("""
    UPDATE requests
    SET previous_status = ?,
        status = 'Cancelled'
    WHERE id = ? AND user_id = ?
    """,
    row["status"], id, session["user_id"])
    
    request_row = db.execute("""
SELECT receiver_id
FROM requests
WHERE id = ?
""", id)[0]

    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]

    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
id,
f'{sender["full_name"]} deleted your payment.',
"request_deleted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

    return redirect("/details")
    
@app.route("/edit/<int:id>")
def edit(id):
    
    if "user_id" not in session:
        return redirect("/login")

    person = db.execute(
        "SELECT * FROM requests WHERE id = ? AND user_id = ?",
        id, session["user_id"]
    )

    return render_template(
        "edit.html",
        person=person[0]
    )
        
@app.route("/update/<int:id>",
methods=["POST"])

def update(id):
    
    
    if "user_id" not in session:
        return redirect("/login")

    name = request.form.get("name")

    phone = request.form.get("phone")

    address = request.form.get("address")

    amount = int(request.form.get("amount"))
   
    payment_mode = request.form.get("payment_mode")

    payment_info = request.form.get("payment_info")
    
    deadline = request.form.get("deadline")

    message = request.form.get("message")
    
    admin_name = request.form.get("admin_name")
    
    print("Amount:", amount)
        
    person = db.execute("""
SELECT version, receiver_id
FROM requests
WHERE id = ?
AND user_id = ?
""", id, session["user_id"])[0]

    version = person["version"] + 1

    edited_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    edited_by = session["user_id"]

    db.execute("""
    UPDATE requests

    SET
    name = ?,
    phone = ?,
    address = ?,
    amount = ?,
    payment_mode = ?,
    payment_info = ?,
    deadline = ?,
    message = ?,
    version = ?,
    edited_at = ?,
    edited_by = ?,
    admin_name = ?

    WHERE id = ? AND user_id = ?
    """,

    name,
    phone,
    address,
    amount,
    payment_mode,
    payment_info,
    deadline,
    message,
    version,
    edited_at,
    edited_by,
    admin_name,
    id, session["user_id"]
    )
    
    payments = db.execute("""
SELECT COALESCE(SUM(amount),0) AS total
FROM payment_history
WHERE request_id = ?
AND status_flag = 'active'
""", id)

    amount_paid = payments[0]["total"]
    
    print("Active payment total:", payments[0]["total"])

    if amount_paid >= amount:
        status = "Completed"
    elif amount_paid > 0:
        status = "In Progress"
    else:
        status = "Pending"
    
    db.execute("""
UPDATE requests
SET amount_paid=?, status=?
WHERE id=?
""",
amount_paid,
status,
id)

    row = db.execute("""
SELECT amount_paid
FROM requests
WHERE id=?
""", id)[0]
    
    print(db.execute("""
SELECT version, edited_at, edited_by
FROM requests
WHERE id = ?
""", id))
    print(db.execute("""
SELECT amount, amount_paid, status
FROM requests
WHERE id = ?
""", id))

    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]

    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
person["receiver_id"],
id,
f'{sender["full_name"]} update your payment.',
"request_updated",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
    
    return redirect("/index")
  
@app.route("/record_payment/<int:id>", methods=["POST"])
def record_payment(id):
    
    
    if "user_id" not in session:
        return redirect("/login")

    payment = int(request.form.get("payment"))

    row = db.execute(
        "SELECT amount, amount_paid FROM requests WHERE id = ? AND user_id = ?",
        id, session["user_id"]
    )[0]

    payment_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        """
        INSERT INTO payment_history
        (request_id, amount, payment_date, user_id, owner_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        id,
        payment,
        payment_date,
        session["user_id"],
        session["user_id"]
    )
    
    payments=db.execute("""
SELECT COALESCE(SUM(amount),0) AS total
FROM payment_history
WHERE request_id=?
AND status_flag='active'
""",id)

    new_paid = payments[0]["total"]
    

    if new_paid >= row["amount"]:
        status = "Completed"
    elif new_paid > 0:
        status = "In Progress"
    else:
        status = "Pending"

    db.execute(
        """
        UPDATE requests
        SET amount_paid = ?, status = ?
        WHERE id = ? AND user_id = ?
        """,
        new_paid,
        status,
        id, session["user_id"]
    )
    
    request_row = db.execute(
    "SELECT * FROM requests WHERE id = ?",
    id
)[0]

    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    

    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
id,
f'{sender["full_name"]} recorded a new payment.',
"payment_recorded",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

    return redirect("/details")
    
@app.route("/payment_history/<int:id>")
def payment_history(id):

     
    
    if "user_id" not in session:
        return redirect("/login")

    payments = db.execute(
    
        """
        SELECT *
        FROM payment_history
        WHERE request_id = ? AND user_id = ?
        AND status_flag = 'active'
        ORDER BY id DESC
        """,
        id, session["user_id"]
    )
    
    corrections = db.execute("""
SELECT *
FROM payment_corrections
WHERE request_id=?
ORDER BY id DESC
""",
id
)
    
    person = db.execute("""
SELECT *
FROM requests
WHERE id = ?
AND (sender_id = ? OR receiver_id = ?)
""", id, session["user_id"], session["user_id"])


    if not person:
        return "Request not found"

    person = person[0]

    return render_template(
       "payment_history.html",
        payments=payments,
        person=person,
        corrections=corrections
    )
    
@app.route("/send_notice/<int:id>",
methods=["POST"])
def send_notice(id):
    

    amount = request.form.get("amount")
    
    proof = request.form.get("proof")

    note = request.form.get("note")
    
    proof_image = request.files.get("proof_image")
    
    if not proof and (
          not proof_image or
          proof_image.filename == ""
    ):
          return "Please provide a transaction ID or screenshot."
    
    filename = ""

    if proof_image and proof_image.filename:
        filename = secure_filename(proof_image.filename)
        proof_image.save(
               os.path.join("static/uploads", filename)
        )

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    
    owner = db.execute(
    "SELECT user_id FROM requests WHERE id = ?",
    id
)[0]["user_id"]



    db.execute("""
    INSERT INTO payment_notices
    (
    request_id,
    amount,
    proof,
    proof_image,
    note,
    created_at,
    owner_id
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    id,
    amount,
    proof,
    filename,
    note,
    created_at,
    owner)
    
    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    
    
    
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
owner,
id,
f'{sender["full_name"]} sent a new notice',
"payment_notice",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
    
    notice_id = db.execute(
    "SELECT last_insert_rowid() AS id"
)[0]["id"]

    return render_template(
    "send_notice.html",
    request_id=id
)

    
@app.route("/notices")
def notices():
    
    if "user_id" not in session:
        return redirect("/login")
    notices = db.execute("""
    SELECT payment_notices.*, requests.name
    FROM payment_notices
    JOIN requests
    ON payment_notices.request_id = requests.id
    WHERE payment_notices.status_flag = 'active'
    AND payment_notices.owner_id = ?
    ORDER BY payment_notices.id DESC
    """, session["user_id"])

    return render_template("notices.html", notices=notices)

@app.route("/accept_notice/<int:id>")
def accept_notice(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
        
    notice = db.execute(
"SELECT * FROM payment_notices WHERE id=? AND owner_id = ?",
id, session["user_id"]
)

    if not notice:
        return "Notice not found"

    notice = notice[0]

    if notice["status"] == "accepted":
       return "Already accepted"

    db.execute("""
UPDATE payment_notices
SET status='accepted'
WHERE id=? AND owner_id = ?
""",
id, session["user_id"])

    request_row = db.execute(
"""
SELECT *
FROM requests
WHERE id = ?
""",
notice["request_id"]
)

   
    if not request_row:
        return "Request not found"

    request_row = request_row[0]
    
    
    db.execute("""
INSERT INTO payment_history
(
request_id,
user_id,
owner_id,
amount,
payment_date,
status_flag
)
VALUES (?, ?, ?, ?, ?, ?)
""",
notice["request_id"],
request_row["user_id"],
request_row["user_id"],
notice["amount"],
datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
"active"
)

    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    

    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
notice["request_id"],
f'{sender["full_name"]} has been accepted your notice.',
"notice_accepted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
    
    

    new_paid = int(request_row["amount_paid"] or 0) + int(notice["amount"])
    
    print("Current Paid:", request_row["amount_paid"])
    print("Notice Amount:", notice["amount"])
    print("New Paid:", new_paid)
    print("Request ID:", notice["request_id"])
    
    if new_paid >= int(request_row["amount"]):
        status = "Completed"
    elif new_paid > 0:
        status = "In Progress"
    else:
        status = "Pending"
        
    print("Notice request_id:", notice["request_id"])

    print("Before UPDATE")
    print("Request ID:", notice["request_id"])
    print("New Paid:", new_paid)
    print("Status:", status)

    rows = db.execute("""
UPDATE requests
SET amount_paid = ?,
    status = ?
WHERE id = ?
""",
new_paid,
status,
notice["request_id"]
)

    print("UPDATE executed")
    print(db.execute("""
SELECT id, amount_paid, status
FROM requests
WHERE id = ?
""", notice["request_id"]))


    return redirect("/notices")
  
@app.route("/reject_notice/<int:id>", methods=["POST"])
def reject_notice(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
    
    
    reason = request.form.get("reason")

    db.execute("""
    UPDATE payment_notices

    SET
    status = 'rejected',
    rejection_reason = ?

    WHERE id = ?
    """,
    reason,
    id)
    
    
    notice = db.execute(
    "SELECT * FROM payment_notices WHERE id = ?",
    id
)[0]

    request_row = db.execute(
    "SELECT * FROM requests WHERE id = ?",
    notice["request_id"]
)[0]

    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    


    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
notice["request_id"],
f'{sender["full_name"]} rejected your notice',
"payment_notice",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

    return redirect("/notices")
    
@app.route(
"/submit_proof/<int:id>",
methods=["POST"]
)
def submit_proof(id):
    

    proof = request.form.get("proof")

    db.execute("""
    UPDATE payment_notices

    SET
    proof = ?,
    status = 'waiting'

    WHERE id = ?
    """,
    proof,
    id)

    return redirect("/details")

@app.route("/notify_sender/<int:id>")
def notify_sender(id):
    
    person = db.execute("SELECT * FROM requests WHERE id = ?", id)
    
    if not person:
        return "Request not found"
        
    person = person[0]
    
    notices = db.execute("""
    SELECT *
    FROM payment_notices
    WHERE request_id = ? AND status_flag = 'active'
    ORDER BY id DESC
    """, id)
    
    corrections = db.execute("""
SELECT *
FROM payment_corrections
WHERE from_user_id = ?
OR to_user_id = ?
ORDER BY id DESC
""",
session["user_id"],
session["user_id"])
      
    return render_template("notify_sender.html", person=person, notices=notices, corrections=corrections)
    
@app.route("/notice_status/<int:id>")
def notice_status(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
    

    notice = db.execute(
        "SELECT * FROM payment_notices WHERE id=? AND user_id = ?",
        id, session["user_id"]
    )[0]

    return render_template(
        "notice_status.html",
        notice=notice
    )
    
@app.route("/timeline/<int:id>")
def timeline(id):
    
    if "user_id" not in session:
        
        
        return redirect("/login")
        

    person = db.execute(
        "SELECT * FROM requests WHERE id=? AND user_id = ?",
        id, session["user_id"]
    )[0]

    notices = db.execute("""
SELECT *
FROM payment_notices
WHERE request_id = ?
AND status_flag = 'active'
ORDER BY id
""", id)

    payments = db.execute("""
    SELECT *
    FROM payment_history
    WHERE request_id=?
    AND status_flag = 'active'
    """, id)
    
    corrections = db.execute("""
SELECT *
FROM payment_corrections
WHERE request_id = ?
ORDER BY created_at
""", id)
    
    events = []

    events.append({
    "time": person["created_at"],
    "icon": "🟢",
    "title": "Request Created",
    "text": f"{person['name']} request was created."
})

    for notice in notices:
        events.append({
        "time": notice["created_at"],
        "icon": "📨",
        "title": "Payment Notice",
        "text": f"Receiver sent a payment notice of    ₹{notice['amount']} ({notice['status']})." 
    })
    
    for payment in payments:
        events.append({
        "time": payment["payment_date"],
        "icon": "💵",
        "title": "Payment Recorded",
        "text": f"₹{payment['amount']} was added to payment history."
    })
    
    for correction in corrections:
        if correction["status"]=="waiting":
            icon="📝"

            title="Correction Requested"

            text=f"Requested correction of ₹{correction['amount']}."

        elif correction["status"]=="approved":

            icon="✅"

            title="Correction Approved"

            text=f"₹{correction['amount']} removed."

        else:

            icon="❌"

            title="Correction Rejected"

            text=f"Correction rejected."
            
        events.append({
    "time": correction["created_at"],
    "icon": icon,
    "title": title,
    "text": text
})
    
    events = sorted(events, key=lambda x: x["time"])
    
    return render_template(
        "timeline.html",
        person=person,
        events=events
    )
    
@app.route("/restore/<int:id>")
def restore(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
    
    
    
    row = db.execute(
        "SELECT previous_status FROM requests WHERE id = ? AND user_id = ?",
        id, session["user_id"]
    )[0]
    
    db.execute("""
    UPDATE requests
    SET status = ?
    WHERE id = ? AND user_id = ?
    """,
    row["previous_status"], id, session["user_id"])
    
       
    request_row = db.execute("""
SELECT receiver_id
FROM requests
WHERE id = ?
""", id)[0]

    
    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
        
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
id,
f'{sender["full_name"]} restored your payment request',
"notice_accepted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
    
    return redirect("/details")
    
@app.route("/trash")
def trash():
    
    
    if "user_id" not in session:
        return redirect("/login")
    

    people = db.execute("""
    SELECT * FROM requests
    WHERE status = 'Cancelled' AND user_id = ?
    ORDER BY id DESC
    """, session["user_id"])
    
    
    return render_template("trash.html", people=people)
    
@app.route("/permanent_delete/<int:id>")
def permanent_delete(id):
    
    
    
    if "user_id" not in session:
        return redirect("/login")
    
    
    request_row = db.execute("""
SELECT receiver_id
FROM requests
WHERE id = ?
""", id)[0]

    
    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    


    
    db.execute(
        "DELETE FROM requests WHERE id = ? AND user_id = ?",
        id, session["user_id"]
    )
  

    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
id,
f'{sender["full_name"]} permanently deleted your payment request.',
"request_deleted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

        
    return redirect("/trash")
    
@app.route("/notices_trash")
def notices_trash():
    
    if "user_id" not in session:
        return redirect("/login")
    

    notices = db.execute("""
    SELECT payment_notices.*, requests.name
    FROM payment_notices
    JOIN requests
    ON payment_notices.request_id = requests.id
    WHERE payment_notices.status_flag = 'deleted' AND payment_notices.owner_id = ?
    ORDER BY payment_notices.id DESC
    """, session["user_id"])
    


    return render_template(
        "notices_trash.html",
        notices=notices
    )
    
@app.route("/notices_restore/<int:id>")
def notices_restore(id):
        
    if "user_id" not in session:
        return redirect("/login")
        
    
    row = db.execute("""
    SELECT request_id
    FROM payment_notices
    WHERE id = ? AND owner_id = ?
    """, id, session["user_id"])[0]
    
    db.execute("""
    UPDATE payment_notices
    SET status_flag = 'active'
    WHERE id = ? AND owner_id = ?
    """, id, session["user_id"])
    
    notice = db.execute(
    "SELECT * FROM payment_notices WHERE id=?",
    id
)[0]

    request_row = db.execute(
    "SELECT * FROM requests WHERE id=?",
    notice["request_id"]
)[0]

    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    
    
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
notice["request_id"],
f'{sender["full_name"]} has restore your notice',
"notice_accepted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
    
    return redirect("/notices_trash")
    
@app.route("/permanent_notices_delete/<int:id>")
def permanent_notices_delete(id):
    
      
    if "user_id" not in session:
        return redirect("/login")
        
        
    notice = db.execute(
    "SELECT * FROM payment_notices WHERE id=?",
    id
)[0]
    
    
    db.execute("""
    DELETE FROM payment_notices
    WHERE id = ? AND owner_id = ?
    """, id, session["user_id"])

    request_row = db.execute(
    "SELECT * FROM requests WHERE id=?",
    notice["request_id"]
)[0]

    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
    
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
notice["request_id"],
f'{sender["full_name"]} deleted your notice permanently.',
"notice_accepted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

    return redirect("/notices_trash")
    
@app.route("/delete_notice_client/<int:id>")
def delete_notice_client(id):


    db.execute("""
    UPDATE payment_notices
    SET status_flag = 'deleted'
    WHERE id = ?
    AND status = 'waiting'
    """, id)
    
    notice = db.execute("""
SELECT request_id
FROM payment_notices
WHERE id = ?
""", id)[0]

    db.execute("""
DELETE FROM notifications
WHERE request_id = ?
AND type = 'payment_notice'
""", notice["request_id"])


    notice = db.execute(
    "SELECT * FROM payment_notices WHERE id=?",
    id
)[0]

    request_row = db.execute(
    "SELECT * FROM requests WHERE id=?",
    notice["request_id"]
)[0]

    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]


    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
request_row["receiver_id"],
notice["request_id"],
f'{sender["full_name"]} has deleted your notice.',
"notice_accepted",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

    return redirect(request.referrer)
        
@app.route("/guide")
def guide():
    return render_template("guide.html")
    
@app.route("/feedback")
def feedback():

        
              
    if "user_id" not in session:
        return redirect("/login")
    

    category = request.args.get("category")
    

    

    if category:


        feedbacks = db.execute("""
        SELECT
        feedback.*,
        users.username,
        COUNT(feedback_supports.id) AS supports


        FROM feedback


        JOIN users
        ON feedback.user_id = users.id


        LEFT JOIN feedback_supports
        ON feedback.id = feedback_supports.feedback_id


        WHERE feedback.category = ?


        GROUP BY feedback.id


        ORDER BY supports DESC, feedback.id DESC
        """, category)




    else:


        feedbacks = db.execute("""
        SELECT
        feedback.*,
        users.username,
        COUNT(feedback_supports.id) AS supports


        FROM feedback


        JOIN users
        ON feedback.user_id = users.id


        LEFT JOIN feedback_supports
        ON feedback.id = feedback_supports.feedback_id


        GROUP BY feedback.id


        ORDER BY supports DESC, feedback.id DESC
        """)

    bug_count = db.execute("""
SELECT COUNT(*) AS total
FROM feedback
WHERE category = 'Bug'
""")[0]["total"]
    feature_count = db.execute("""
SELECT COUNT(*) AS total
FROM feedback
WHERE category = 'Feature Request'
""")[0]["total"]
    question_count = db.execute("""
SELECT COUNT(*) AS total
FROM feedback
WHERE category = 'Question'
""")[0]["total"]
    improvement_count = db.execute("""
SELECT COUNT(*) AS total
FROM feedback
WHERE category = 'Improvement'
""")[0]["total"]
    confusing_count = db.execute("""
SELECT COUNT(*) AS total
FROM feedback
WHERE category = 'Confusing'
""")[0]["total"]
    all_count = db.execute("""
SELECT COUNT(*) AS total
FROM feedback
""")[0]["total"]

    for item in feedbacks:
        item["replies"] = db.execute("""SELECT feedback_replies.*, users.username FROM feedback_replies JOIN users ON feedback_replies.user_id = users.id WHERE feedback_replies.feedback_id = ? ORDER BY feedback_replies.id DESC""", item["id"])
        
    return render_template(
    "feedback.html",
    feedbacks=feedbacks,
    bug_count=bug_count,
    feature_count=feature_count,
    question_count=question_count,
    improvement_count=improvement_count,
    confusing_count=confusing_count,
    all_count=all_count
)
    
@app.route("/add_feedback", methods=["POST"])
def add_feedback():
    
    
    if "user_id" not in session:
        return redirect("/login")
    

    category = request.form.get("category")
    title = request.form.get("title")
    message = request.form.get("message")

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    db.execute("""
    INSERT INTO feedback
    (
    user_id,
    category,
    title,
    message,
    created_at
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    session["user_id"],
    category,
    title,
    message,
    created_at)

    return redirect("/feedback")
    
    
@app.route("/support_feedback/<int:id>")
def support_feedback(id):
    
       
    if "user_id" not in session:
       return redirect("/login")
       
    
    user_id = session["user_id"]

    existing = db.execute("""
    SELECT *
    FROM feedback_supports
    WHERE feedback_id = ?
    AND user_id = ?
    """, id,
    session["user_id"])

    if existing:

        db.execute("""
        DELETE FROM feedback_supports
        WHERE feedback_id = ?
        AND user_id = ?
        """, id, session["user_id"])
        
    else:

        db.execute("""
        INSERT INTO feedback_supports
        (feedback_id, user_id)
        VALUES (?, ?)
        """, id, user_id)

    return redirect("/feedback")
    
    
@app.route("/delete_feedback/<int:id>")
def delete_feedback(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
    
    db.execute("""
DELETE FROM feedback
WHERE id = ? AND user_id = ?
""", id, session["user_id"])

    db.execute("""
DELETE FROM feedback_supports
WHERE feedback_id = ?
""", id)

    return redirect("/feedback")
    
    
@app.route("/reply_feedback/<int:id>", methods=["POST"])
def reply_feedback(id):
    
    
    if "user_id" not in session:
        return redirect("/login")
    

    message = request.form.get("message")

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    
 
    db.execute("""
    INSERT INTO feedback_replies
    (
    user_id,
    feedback_id,
    message,
    created_at
    )
    VALUES (?, ?, ?, ?)
    """,
    session["user_id"],
    id,
    message,
    created_at)

    return redirect("/feedback")
    
@app.route("/register")
def register():
    return render_template("register.html")
   
@app.route("/register", methods=["POST"])
def register_post():

    full_name = request.form.get("full_name")
    print(type(request))
    print(request)
    username = request.form.get("username")
    phone = request.form.get("phone")
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    purpose = request.form.get("purpose")
    
    
    if not all([full_name, username, phone, password, confirm_password]):
        return "All fields required"
        
    if password != confirm_password:
        return "Passwords do not match"

    existing_username = db.execute("""
    SELECT *
    FROM users
    WHERE username = ?
    """, username)

    if existing_username:
        return "Username already exists"

    existing_phone = db.execute("""
    SELECT *
    FROM users
    WHERE phone = ?
    """, phone)

    if existing_phone:
        return "Phone number already registered"

    if len(username) < 3:
        return "Username must be at least 3 characters"

    password_hash = generate_password_hash(
        password
    )

    created_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    
   

    db.execute("""
    INSERT INTO users
    (
    full_name,
    username,
    phone,
    email,
    password_hash,
    created_at,
    purpose
    )
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    full_name,
    username,
    phone,
    email,
    password_hash,
    created_at,
    purpose)
    
    new_user = db.execute(
    "SELECT id FROM users WHERE phone = ?",
    phone
)

    print(db.execute("""
SELECT id, full_name, phone
FROM users
WHERE phone = ?
""", phone))

    new_user_id = new_user[0]["id"]
    
    db.execute("""
UPDATE requests
SET receiver_id = ?
WHERE phone = ?
AND (receiver_id IS NULL OR receiver_id = 0)
""",
new_user_id,
phone
)

    print(db.execute("""
SELECT id, phone, sender_id, receiver_id
FROM requests
WHERE phone = ?
""", phone))

    requests = db.execute("""
SELECT id, sender_id, admin_name
FROM requests
WHERE receiver_id = ?
""", new_user_id)
        
    user_id = session.get("user_id")

    if user_id:
        sender = db.execute("""
    SELECT full_name
    FROM users
    WHERE id = ?
    """, user_id)
    else:
        sender = []

    if sender:
        sender_name = sender[0]["full_name"]
    else:
        sender_name = "Someone"


    requests = db.execute("""
SELECT id, sender_id, admin_name
FROM requests
WHERE receiver_id = ?
""", new_user_id)


    for req in requests:

        if req["sender_id"] is None:
            continue

        db.execute("""
    INSERT INTO notifications
    (
        sender_id,
        receiver_id,
        request_id,
        message,
        type,
        created_at
    )
    VALUES (?, ?, ?, ?, ?, ?)
    """,
    req["sender_id"],
    new_user_id,
    req["id"],
    f"{sender_name} sent you a payment request.",
    "new_request",
    created_at
    )

    print(db.execute("""
SELECT *
FROM notifications
WHERE receiver_id = ?
""", new_user_id))

    return redirect("/login")
    
@app.route("/login")
def login():
    return render_template(
        "login.html"
    )
    
@app.route(
"/login",
methods=["POST"]
)
def login_post():
  
    username = request.form.get(
    "username"
)

    password = request.form.get(
    "password"
)
    print("Username entered:", username)

    print(db.execute("""
SELECT id, username, phone
FROM users
"""))

    user = db.execute("""
SELECT *
FROM users
WHERE username = ?
""", username)

    if not user:
        return "User not found"
    
    if not check_password_hash(
    user[0]["password_hash"],
    password):
        return "Wrong password"
        
    session.permanent = True
    
    session["user_id"] = user[0]["id"]
    
      
    

    return redirect("/")
    
    
@app.route("/logout")
def logout():
    
    session.clear()
    return redirect("/login")
    
    
@app.route("/delete_reply/<int:id>")
def delete_reply(id):

    if "user_id" not in session:
        return redirect("/login")


    reply = db.execute("""
    SELECT user_id
    FROM feedback_replies
    WHERE id = ?
    """, id)


    if not reply:
        return "Reply not found"


    if reply[0]["user_id"] != session["user_id"]:
        return "You cannot delete this reply"


    db.execute("""
    DELETE FROM feedback_replies
    WHERE id = ?
    """, id)


    return redirect("/feedback")
    
@app.route("/details")
def details():

    if "user_id" not in session:
        return redirect("/login")


    search = request.args.get("search")

    status = request.args.get("status")


    if search:

        people = db.execute("""
        SELECT *
        FROM requests
        WHERE name LIKE ?
        AND user_id = ?
        ORDER BY id DESC
        """,
        "%" + search + "%",
        session["user_id"]
        )


    elif status:

        people = db.execute("""
        SELECT *
        FROM requests
        WHERE status = ?
        AND status_flag = 'active'
        AND user_id = ?
        ORDER BY id DESC
        """,
        status,
        session["user_id"]
        )


    else:

        people = db.execute("""
        SELECT *
        FROM requests
        WHERE user_id = ?
        ORDER BY id DESC
        """,
        session["user_id"]
        )


    return render_template(
        "details.html",
        people=people
    )
    
@app.route("/details/<int:id>")
def request_details(id):

    if "user_id" not in session:
        return redirect("/login")

    person = db.execute(
        """
        SELECT *
        FROM requests
        WHERE id=? AND user_id=?
        """,
        id,
        session["user_id"]
    )[0]
    
    remaining = person["amount"] - person["amount_paid"]

    if remaining < 0:
        remaining = 0

    overpaid = 0

    if person["amount_paid"] > person["amount"]:
        overpaid = person["amount_paid"] - person["amount"]

    payments = db.execute(
        """
        SELECT *
        FROM payment_history
        WHERE request_id=?
        AND user_id=?
        AND status_flag='active'
        ORDER BY id DESC
        """,
        id,
        session["user_id"]
    )


    notices = db.execute(
        """
        SELECT *
        FROM payment_notices
        WHERE request_id=?
        AND owner_id=?
        """,
        id,
        session["user_id"]
    )
    

    return render_template(
    "request_details.html",
    person=person,
    payments=payments,
    notices=notices,
    remaining=remaining,
    overpaid=overpaid
)
    
@app.route("/request_correction/<int:id>", methods=["POST"])
def request_correction(id):

    if "user_id" not in session:
        return redirect("/login")

    payment_rows = db.execute("""
        SELECT *
        FROM payment_history
        WHERE id=?
    """, id)

    if len(payment_rows) == 0:
        return "Payment not found"

    payment = payment_rows[0]

    request_rows = db.execute("""
        SELECT *
        FROM requests
        WHERE id=?
    """, payment["request_id"]
    )

    if len(request_rows) == 0:
        return "Request not found"

    req = request_rows[0]

    from_user_id = session["user_id"]

    if from_user_id == req["sender_id"]:
        to_user_id = req["receiver_id"]
    else:
        to_user_id = req["sender_id"]
        
 

    db.execute("""
        INSERT INTO payment_corrections
        (request_id, payment_id, from_user_id, to_user_id, amount, reason, status, created_at)
        VALUES (?,?,?,?,?,?,?,?)
    """,
    payment["request_id"],
    payment["id"],
    from_user_id,
    to_user_id,
    payment["amount"],
    request.form.get("reason"),
    "waiting",
    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    
    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
        
    
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
from_user_id,
to_user_id,
payment["request_id"],
f'{sender["full_name"]} sent you a correction waiting for you.',
"correction_request",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)

    return redirect(request.referrer)
    
@app.route("/corrections")
def corrections():
    
    
    if "user_id" not in session:
        return redirect("/login")
        


    corrections = db.execute("""
    SELECT *
    FROM payment_corrections
    WHERE from_user_id = ? OR
to_user_id = ?    
    ORDER BY id DESC
    """, session["user_id"], session["user_id"])
    


    return render_template(
    "corrections.html",
    corrections=corrections
    )
    
@app.route("/approve_correction/<int:id>", methods=["POST"])
def approve_correction(id):

    if "user_id" not in session:
        return redirect("/login")

    correction = db.execute("""
    SELECT *
    FROM payment_corrections
    WHERE id=?
    AND to_user_id=?
    """,
    id,
    session["user_id"]
    )


    if not correction:
        return "You are not allowed"


    correction = correction[0]

    db.execute("""
    UPDATE payment_corrections
    SET status='approved'
    WHERE id=?
    """,
    id)
    
    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
        
        
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
correction["from_user_id"],
correction["request_id"],
f'{sender["full_name"]} approved your correction.',
"correction_approved",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)


    db.execute("""
    UPDATE payment_history
    SET status_flag='corrected'
    WHERE id=?""",
    correction["payment_id"])
    
    payments = db.execute("""
SELECT COALESCE(SUM(amount),0) AS total
FROM payment_history
WHERE request_id = ?
AND status_flag = 'active'
""", correction["request_id"])

    amount_paid = payments[0]["total"]
    
    
    db.execute("""
UPDATE requests
SET amount_paid = ?
WHERE id = ?
""",
amount_paid,
correction["request_id"])
     
    request_row = db.execute("""
SELECT amount, amount_paid
FROM requests
WHERE id = ?
""", correction["request_id"])[0]

    if amount_paid >= request_row["amount"]:
        status = "Completed"
    elif amount_paid > 0:
        status = "In Progress"
    else:
        status = "Pending"
    db.execute("""
UPDATE requests
SET status = ?
WHERE id = ?
""",
status,
correction["request_id"])


    return redirect("/corrections")
    
@app.route("/reject_correction/<int:id>", methods=["POST"])
def reject_correction(id):

    if "user_id" not in session:
        return redirect("/login")


    correction = db.execute("""
    SELECT *
    FROM payment_corrections
    WHERE id=?
    AND to_user_id=?
    """,
    id,
    session["user_id"]
    )

    if not correction:
        return "You are not allowed"
        
    correction = correction[0]

    db.execute("""
    UPDATE payment_corrections
    SET status='rejected'
    WHERE id=?
    """,
    id)
    
    sender = db.execute("""
SELECT full_name
FROM users
WHERE id = ?
""", session["user_id"])[0]
        
    db.execute("""
INSERT INTO notifications
(sender_id, receiver_id, request_id, message, type, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""",
session["user_id"],
correction["from_user_id"],
correction["request_id"],
f'{sender["full_name"]} rejected your correction.',
"correction_rejected",
datetime.now().strftime("%Y-%m-%d %H:%M:%S")
)
  

    request_row = db.execute("""
SELECT amount, amount_paid
FROM requests
WHERE id = ?
""",
correction["request_id"])[0]


    if request_row["amount_paid"] >= request_row["amount"]:
        status = "Completed"
    elif request_row["amount_paid"] > 0:
        status = "In Progress"
    else:
        status = "Pending"

    db.execute("""
UPDATE requests
SET status = ?
WHERE id = ?
""",
status,
correction["request_id"])


    return redirect("/corrections")
    
@app.route("/notifications")
def notifications():
    
    if "user_id" not in session:
        return redirect("/login")
        
    notifications = db.execute("""
SELECT
notifications.*,
users.full_name
FROM notifications
LEFT JOIN users
ON notifications.sender_id = users.id
WHERE notifications.receiver_id = ?
ORDER BY notifications.id DESC
""", session["user_id"])

    db.execute("""
    UPDATE notifications
    SET is_read = 1
    WHERE receiver_id = ?
    """, session["user_id"])
    
    rows = db.execute("SELECT * FROM notifications")
    print(rows)  

    return render_template(
        "notifications.html",
        notifications=notifications
    )
    
    
@app.route("/shared_request/<int:id>")
def shared_request(id):

    if "user_id" not in session:
        return redirect("/login")
        

    person = db.execute("""
    SELECT *
    FROM requests
    WHERE id = ?
    AND (sender_id = ? OR receiver_id = ?)
    """,
    id,
    session["user_id"],
    session["user_id"])

    if not person:
        return "Request not found"

    person = person[0]

    payments = db.execute("""
    SELECT *
    FROM payment_history
    WHERE request_id = ?
    AND status_flag='active'
    ORDER BY id DESC
    """, id)

    notices = db.execute("""
    SELECT *
    FROM payment_notices
    WHERE request_id = ?
    AND status_flag = 'active'
    ORDER BY id DESC
    """, id)

    corrections = db.execute("""
    SELECT *
    FROM payment_corrections
    WHERE request_id = ?
    ORDER BY id DESC
    """, id)
    
    if person["amount"] > 0:
        progress = round((person["amount_paid"] / person["amount"]) * 100)
    else:
        progress = 0

    if progress > 100:
        progress = 100
        
    remaining = person["amount"] - person["amount_paid"]

    if remaining < 0:
        remaining = 0

    overpaid = 0

    if person["amount_paid"] > person["amount"]:
        overpaid = person["amount_paid"] - person["amount"]

    if person["amount"] > 0:
        progress = (person["amount_paid"] / person["amount"]) * 100
    else:
        progress = 0

    if progress > 100:
        progress = 100

    return render_template(
        "shared_request.html",
        person=person,
        payments=payments,
        notices=notices,
        corrections=corrections,
        progress=progress,
        remaining=remaining,
        overpaid=overpaid
    )
  
if __name__ == "__main__":
    import traceback

    try:
        app.run(
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False
        )
    except BaseException:
        traceback.print_exc()
        while True:
            pass
