import cx_Oracle

from flask import Flask, render_template, request, url_for, redirect, jsonify, flash, g, session
from sqlalchemy import create_engine, text, select
from .forms import RegisterForm, UserLoginForm
import cx_Oracle
cx_Oracle.init_oracle_client(
    lib_dir="/Users/soongjamm/downloads/instantclient_19_8")
engine = create_engine(
    "oracle://system:oracle@127.0.0.1:1521/xe", echo=True)
app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"


@app.route("/")
def index():
    with engine.connect() as connection:
        result = connection.execute(text("select * from employee"))
        res_dict = list(result)
        # for row in result:
        #     print("emp_name:", row['emp_name'], type(result))
    return render_template('index.html', emp_list=res_dict)


def register_ok(id, emp_name, emp_no):
    dept_no = -1
    with engine.connect() as connection:
        # emp_name과 emp_no가 일치하는지 확인
        stmt = text(
            "select * from employee where emp_no = :emp_no and emp_name = :emp_name")
        stmt = stmt.bindparams(emp_name=emp_name, emp_no=emp_no)
        result = connection.execute(stmt)
        result = list(result)
        if len(result) <= 0:
            return False, "사원정보가 일치하지 않습니다.", dept_no

        # 중복 id 존재 여부 확인
        stmt = text("select id from web_user where id = :id")
        stmt = stmt.bindparams(id=id)
        result = list(result)
        if len(result) <= 0:
            return False, "이미 존재하는 아이디 입니다.", dept_no
    dept_no = result[0][4]
    return True, "정상적인 입력입니다.", dept_no


@app.route("/register", methods=("GET", "POST"))
def register():
    form = RegisterForm()
    if request.method == "GET":
        return render_template('register.html', form=form)
    elif request.method == "POST":
        if form.validate_on_submit():
            # form data 생성
            id = form.id.data
            pw = form.pw.data
            emp_no = form.emp_no.data
            emp_name = form.emp_name.data

            # 계정 생성 가능 여부 확인
            # ok==True이면 생성
            ok, msg, dept_no = register_ok(id, emp_name, emp_no)
            if ok:
                auth = 0
                if dept_no == 15:
                    auth = 1
                # 임직원(dept_no==15)이면 권한(1) 줘야 함.
                with engine.connect() as connection:
                    stmt = text(
                        "insert into web_user (id, pw, auth, emp_no) values(:id, :pw, :auth, :emp_no)")
                    stmt = stmt.bindparams(
                        id=id, pw=pw, auth=auth, emp_no=emp_no)
                    result = connection.execute(stmt)

                msg = "정상적으로 생성되었습니다."
                flash(msg)
                return redirect(url_for('index'))
            else:
                flash(msg)
                return redirect(url_for('register', form=form))
        else:
            return render_template('register.html', form=form)


def check_login(id, pw):
    with engine.connect() as connection:
        stmt = text("select * from web_user where id=:id and pw=:pw")
        stmt = stmt.bindparams(id=id, pw=pw)
        result = connection.execute(stmt)
        result = list(result)
    if len(result) == 1:
        return True, "로그인 성공"
    return False, "로그인 실패"


@app.route("/login", methods=("GET", "POST"))
def login():
    form = UserLoginForm()
    if request.method == 'GET':
        return render_template('login.html', form=form)

    elif request.method == 'POST':
        if form.validate_on_submit():
            # form data 생성
            id = form.id.data
            pw = form.pw.data
            ok, msg = check_login(id, pw)
            flash(msg)
            # ok면 로그인 성공
            if ok:

                with engine.connect() as connection:
                    stmt = text(
                        "select * from employee, web_user where employee.emp_no=web_user.emp_no and id=:id")
                    stmt = stmt.bindparams(
                        id=id)
                    result = connection.execute(stmt)
                result = list(result)
                res = dict()
                res["emp_no"] = result[0][0]
                res["emp_name"] = result[0][1]
                res["rrn"] = result[0][2]
                res["edu_no"] = result[0][3]
                res["dept_no"] = result[0][4]
                res["id"] = result[0][5]
                res["auth"] = result[0][7]

                session.clear()
                session["user"] = res
                print(session["user"])
                # session[]
                # session["emp_name"] =
                return redirect(url_for("index"))
            else:
                return render_template('login.html', form=form)


@app.route("/edit-profile")
def edit_profile():
    return "아직이용"


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))
