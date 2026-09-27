from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, BooleanField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, URL, Regexp


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])


class CodigoDoisFatoresForm(FlaskForm):
    codigo = StringField(
        "Código de verificação",
        validators=[
            DataRequired(message="Informe o código de 6 dígitos."),
            Regexp(r"^\s*\d{3}\s?\d{3}\s*$", message="O código deve ter 6 dígitos."),
        ],
        render_kw={"inputmode": "numeric", "autocomplete": "one-time-code", "maxlength": 7, "placeholder": "000000"},
    )


class AcaoAdminForm(FlaskForm):
    pass


class CadastroForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(min=3, max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired(), Length(min=6, message="A senha deve ter ao menos 6 caracteres.")])
    confirmar_senha = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("senha", message="As senhas não conferem.")],
    )
    aceite_termos = BooleanField(
        "Li e aceito a Política de Privacidade e os Termos de Aceite",
        validators=[DataRequired(message="Você precisa aceitar a Política de Privacidade e os Termos de Aceite para se cadastrar.")],
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
    sinopse = TextAreaField("Sinopse", validators=[Optional(), Length(max=2000)])
    categoria = StringField("Categoria", validators=[Optional(), Length(max=150)])
    capa_url = HiddenField(validators=[Optional(), URL(message="URL de capa inválida."), Length(max=500)])
    google_books_id = HiddenField(validators=[Optional(), Length(max=50)])
