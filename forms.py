from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])


class CadastroForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired(), Length(min=6, message="A senha deve ter ao menos 6 caracteres.")])
    confirmar_senha = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("senha", message="As senhas não conferem.")],
    )


class LivroForm(FlaskForm):
    titulo = StringField("Título", validators=[DataRequired(), Length(min=1, max=200)])
    autor = StringField("Autor", validators=[DataRequired(), Length(min=1, max=150)])
    isbn = StringField("ISBN", validators=[Optional(), Length(max=20)])
    editora = StringField("Editora", validators=[Optional(), Length(max=120)])
    ano_publicacao = IntegerField(
        "Ano de publicação",
        validators=[Optional(), NumberRange(min=0, max=2100, message="Informe um ano válido.")],
    )
    quantidade = IntegerField(
        "Quantidade de exemplares",
        validators=[DataRequired(), NumberRange(min=1, message="A quantidade deve ser ao menos 1.")],
    )
