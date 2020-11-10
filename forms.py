from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField
from wtforms.validators import DataRequired, Length, EqualTo


class RegisterForm(FlaskForm):
    id = StringField("로그인 아이디", validators=[
                     DataRequired("로그인 id를 입력하세요."), Length(min=3, max=30)])
    pw = PasswordField(
        "전화 번호", validators=[DataRequired("비밀번호를 입력하세요."), Length(min=4, max=12)]
    )
    emp_name = StringField("이름", validators=[
                           DataRequired("이름을 입력하세요.")])
    emp_no = IntegerField("사원 번호", validators=[DataRequired("사원 번호를 입력하세요.")])


class UserLoginForm(FlaskForm):
    id = StringField("로그인 아이디", validators=[
        DataRequired(), Length(min=3, max=30)])
    pw = PasswordField("비밀번호", validators=[DataRequired()])
