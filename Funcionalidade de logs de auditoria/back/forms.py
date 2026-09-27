from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Regexp

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

