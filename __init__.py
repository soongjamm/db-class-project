import cx_Oracle
from .forms import RegisterForm, UserLoginForm, EditForm
from sqlalchemy import create_engine, text, select
from flask import Flask, render_template, request, url_for, redirect, jsonify, flash, g, session
import os
from .filter import format_datetime

ORACLE_LIB_DIR = os.path.dirname(__name__) + "instantclient_19_8"
cx_Oracle.init_oracle_client(lib_dir=ORACLE_LIB_DIR)
DB_URI = "oracle://system:oracle@127.0.0.1:1521/xe"
engine = create_engine(DB_URI, echo=True)
app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"


app.jinja_env.filters[
    "datetime"
] = format_datetime


@app.route("/")
def index():
    return render_template('index.html')


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
        stmt = text("select * from web_user where id = :id")
        stmt = stmt.bindparams(id=id)
        result = connection.execute(stmt)
        result = [dict(row) for row in result]
        result = result if len(result) == 0 else result[0]
        if len(result) > 0:
            return False, "이미 존재하는 아이디 입니다.", dept_no

        # 이미 가입한 사원인지 확인
        stmt = text("select * from web_user where emp_no = :emp_no")
        stmt = stmt.bindparams(emp_no=emp_no)
        result = connection.execute(stmt)
        result = [dict(row) for row in result]
        result = result if len(result) == 0 else result[0]
        if len(result) > 0:
            return False, "이미 가입한 사원입니다.", dept_no

        stmt = text(
            "select dept_no from employee where emp_no = :emp_no and emp_name = :emp_name")
        stmt = stmt.bindparams(emp_name=emp_name, emp_no=emp_no)
        result = connection.execute(stmt)
        result = [dict(row) for row in result]
        result = result if len(result) == 0 else result[0]
        dept_no = result["dept_no"]

        return True, "정상적인 입력입니다.", dept_no


@app.route("/register", methods=("GET", "POST"))
def register():
    form = RegisterForm()
    if request.method == "GET":
        return render_template('register.html', form=form)
    elif request.method == "POST":
        if form.validate_on_submit():
            # form data 분해
            id = form.id.data
            pw = form.pw.data
            emp_no = form.emp_no.data
            emp_name = form.emp_name.data

            # 계정 생성 가능 여부 확인
            ok, msg, dept_no = register_ok(id, emp_name, emp_no)
            # 생성
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
                return redirect(url_for("index"))
            else:
                return render_template('login.html', form=form)


def parsing_raw(list):
    for i in range(len(list)):
        list[i] = str(list[i]).replace('\'', '').replace(
            '(', '').replace(')', '').replace(',', '')
    return list


@app.route("/edit-profile", methods=("GET", "POST"))
def edit_profile():
    # 최종학력, 직군 리스트
    with engine.connect() as connection:
        stmt = text("select dept_name from dept")
        result = connection.execute(stmt)
        dept_list = list(result)
        for i in range(len(dept_list)):
            dept_list[i] = str(dept_list[i]).replace('\'', '').replace(
                '(', '').replace(')', '').replace(',', '')

        stmt = text("select edu_name from education")
        result = connection.execute(stmt)
        edu_list = list(result)
        for i in range(len(edu_list)):
            edu_list[i] = str(edu_list[i]).replace('\'', '').replace(
                '(', '').replace(')', '').replace(',', '')

    if request.method == 'GET':
        if session["user"]:
            id = session.get("user")["id"]
            emp_info = get_emp_info(id)
            form = EditForm(
                id=emp_info["id"],
                emp_no=emp_info["emp_no"],
                name=emp_info["name"],
                rrn=emp_info["rrn"],
                education=emp_info["education"],
                dept=emp_info["dept"]
            )

        return render_template('edit.html', form=form, dept_list=dept_list, edu_list=edu_list)

    elif request.method == 'POST':
        form = EditForm()
        if form.validate_on_submit:
            with engine.connect() as connection:
                # 직군번호, 학력번호 가져오기
                dept_name = form.dept.data
                edu_name = form.education.data

                stmt = text("select dept_no from dept where dept_name=:dept_name").bindparams(
                    dept_name=dept_name)
                result = connection.execute(stmt)
                dept_no = parsing_raw(list(result))
                dept_no = int(dept_no[0])

                stmt = text("select edu_no from education where edu_name=:edu_name").bindparams(
                    edu_name=edu_name)
                result = connection.execute(stmt)
                edu_no = parsing_raw(list(result))
                edu_no = int(edu_no[0])

                # 업데이트
                stmt = text("update employee set emp_name=:emp_name, edu_no=:edu_no, dept_no=:dept_no where emp_no=:emp_no").bindparams(
                    emp_name=form.name.data, edu_no=edu_no, dept_no=dept_no, emp_no=form.emp_no.data)
                result = connection.execute(stmt)

            flash("성공적으로 변경하였습니다.")
            return redirect(url_for('index'))
        else:
            return render_template('edit.html', form=form, dept_list=dept_list, edu_list=edu_list)


def get_emp_info(id):
    with engine.connect() as connection:
        stmt = text(
            "select * from (select emp_name as name, emp_no, rrn, education.edu_name as education, dept.dept_name as dept from employee, education, dept where employee.edu_no=education.edu_no and employee.dept_no=dept.dept_no) emp, web_user where web_user.emp_no=emp.emp_no")
        result = connection.execute(stmt)
        result = [dict(row) for row in result]
        result = result if len(result) == 0 else result[0]
        return result


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/inquire", methods=("GET", "POST"))
def inquire():
    if not session.get("user") or session.get("user")["auth"] is not 1:
        print(session.get("user")["auth"])
        flash("조회 권한이 없습니다.")
        return redirect(url_for('index'))

    if request.method == 'POST':
        search = request.form.get('search')
        if search == 'current_proj':
            with engine.connect() as connection:
                stmt = text(
                    "SELECT proj_emp.emp_no, employee.emp_name,proj_emp.proj_no, project.proj_name, duty.duty_name, proj_emp.put_day, proj_emp.finish_day FROM proj_emp JOIN employee ON proj_emp.emp_no = employee.emp_no JOIN project ON proj_emp.proj_no = project.proj_no join duty on proj_emp.duty_no = duty.duty_no")
                result = connection.execute(stmt)
                result = list(result)
                stmt = text(
                    "SELECT proj_name, count(*) FROM proj_emp JOIN employee ON proj_emp.emp_no = employee.emp_no JOIN project ON proj_emp.proj_no = project.proj_no group by proj_name")
                count = connection.execute(stmt)
            return render_template("result_current.html", result=result, count=count)
        elif search == 'bydate':
            date = request.form.get('date').replace('T', '-')
            date = list(map(int, date.split('-')[:3]))
            from datetime import datetime
            date = datetime(date[0], date[1], date[2])
            # date = '/'.join(date)
            with engine.connect() as connection:
                stmt = text("select manage.proj_no , project.proj_name, manage.emp_no ,manage.emp_name, manage.duty_no, manage.put_day, manage.finish_day , duty.duty_name from manage JOIN project ON manage.proj_no =  project.proj_no  JOIN duty ON manage.duty_no =  duty.duty_no where :date between manage.put_day and manage.finish_day").bindparams(date=date)
                result = connection.execute(stmt)
            return render_template("result_datetime.html", result=result, date=date)
        elif search == 'bynum':
            num = int(request.form.get('num'))
            with engine.connect() as connection:
                stmt = text("SELECT project.proj_no, project.proj_name, employee.emp_no, employee.emp_name, eval_kinds.eval_kinds, eval_content.perfo_grade, eval_content.perfo_content, eval_content.comm_grade, eval_content.comm_content FROM eval JOIN project ON eval.eval_cust_no = project.proj_no JOIN employee ON eval.subject_no = employee.emp_no JOIN eval_content ON eval_content.eval_no = eval.eval_no JOIN eval_kinds on eval_kinds.eval_no = eval.eval_no where employee.emp_no = :num").bindparams(num=num)
                result = connection.execute(stmt)
                result = list(result)
            return render_template("result_empno.html", result=result, empno=num)

    else:
        return render_template("inquire.html")
