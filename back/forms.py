import re
from datetime import date

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, BooleanField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, URL, Regexp, ValidationError, InputRequired

class FormularioBase(FlaskForm):

    class Meta:
        locales = ["pt_BR", "pt"]


CAMPO_CODIGO_6_DIGITOS = {
    "inputmode": "numeric",
    "autocomplete": "one-time-code",
    "maxlength": 6,
    "pattern": "[0-9]{6}",
    "placeholder": "000000",
    "oninput": "this.value = this.value.replace(/[^0-9]/g, '')",
}

ANO_MINIMO_PUBLICACAO = 1450


def normalizar_isbn(valor):
    if not valor:
        return valor
    return re.sub(r"[\s.\-]", "", valor).upper()


def isbn_valido(isbn):
    if re.fullmatch(r"\d{9}[\dX]", isbn):
        digitos = [10 if c == "X" else int(c) for c in isbn]
        return sum(d * peso for d, peso in zip(digitos, range(10, 0, -1))) % 11 == 0
    if re.fullmatch(r"97[89]\d{10}", isbn):
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(isbn)) % 10 == 0
    return False


def validar_isbn(form, campo):
    if campo.data and not isbn_valido(campo.data):
        raise ValidationError(
            "ISBN inválido: confira os números (10 ou 13 dígitos; o ISBN-13 começa com 978 ou 979)."
        )


def validar_ano_publicacao(form, campo):
    ano_atual = date.today().year
    if campo.data is not None and not ANO_MINIMO_PUBLICACAO <= campo.data <= ano_atual:
        raise ValidationError(f"Informe um ano entre {ANO_MINIMO_PUBLICACAO} e {ano_atual}.")


class LoginForm(FormularioBase):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])


class CodigoDoisFatoresForm(FormularioBase):
    codigo = StringField(
        "Código de verificação",
        validators=[
            DataRequired(message="Informe o código de 6 dígitos."),
            Regexp(r"^\s*\d{3}\s?\d{3}\s*$", message="O código deve ter 6 dígitos."),
        ],
        render_kw=CAMPO_CODIGO_6_DIGITOS,
    )
    aceite_termos = BooleanField("Li e aceito a Política de Privacidade e os Termos de Aceite")


class AcaoAdminForm(FormularioBase):
    pass


class CadastroForm(FormularioBase):
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


class LivroForm(FormularioBase):
    titulo = StringField("Título", validators=[DataRequired(), Length(min=1, max=200)])
    autor = StringField("Autor", validators=[DataRequired(), Length(min=1, max=150)])
    isbn = StringField(
        "ISBN",
        filters=[normalizar_isbn],
        validators=[Optional(), validar_isbn],
        render_kw={"placeholder": "10 ou 13 dígitos", "maxlength": 17},
    )
    editora = StringField("Editora", validators=[Optional(), Length(max=120)])
    ano_publicacao = IntegerField(
        "Ano de publicação",
        validators=[Optional(), validar_ano_publicacao],
    )
    quantidade = IntegerField(
        "Quantidade de exemplares",
        validators=[
            InputRequired(message="Informe a quantidade de exemplares."),
            NumberRange(min=1, max=999, message="A quantidade deve estar entre 1 e 999."),
        ],
    )
    sinopse = TextAreaField("Sinopse", validators=[Optional(), Length(max=2000)])
    categoria = StringField("Categoria", validators=[Optional(), Length(max=150)])
    capa_url = HiddenField(validators=[Optional(), URL(message="URL de capa inválida."), Length(max=500)])
    google_books_id = HiddenField(validators=[Optional(), Length(max=50)])


class AcaoForm(FormularioBase):
    pass


class DisciplinaForm(FormularioBase):
    nome = StringField(
        "Nome da disciplina",
        validators=[DataRequired(message="Informe o nome da disciplina."), Length(min=2, max=120)],
    )
    codigo = StringField("Código (opcional)", validators=[Optional(), Length(max=20)])
    descricao = TextAreaField(
        "Curso / turma / descrição (opcional)", validators=[Optional(), Length(max=1000)]
    )


class RecomendacaoForm(FormularioBase):
    mensagem = TextAreaField(
        "Comentário para os alunos (opcional)",
        validators=[Optional(), Length(max=500, message="O comentário pode ter no máximo 500 caracteres.")],
    )


class EsqueciSenhaForm(FormularioBase):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    codigo = StringField(
        "Código do Google Authenticator",
        validators=[
            DataRequired(message="Informe o código de 6 dígitos."),
            Regexp(r"^\s*\d{3}\s?\d{3}\s*$", message="O código deve ter 6 dígitos."),
        ],
        render_kw=CAMPO_CODIGO_6_DIGITOS,
    )
    nova_senha = PasswordField(
        "Nova senha",
        validators=[DataRequired(), Length(min=6, message="A senha deve ter ao menos 6 caracteres.")],
    )
    confirmar_senha = PasswordField(
        "Confirmar nova senha",
        validators=[DataRequired(), EqualTo("nova_senha", message="As senhas não conferem.")],
    )


class AutorizarCadastroForm(FormularioBase):
    email = StringField(
        "E-mail institucional",
        validators=[DataRequired(), Email(), Length(max=120)],
        render_kw={"placeholder": "nome@aluno.com"},
    )

    def validate_email(self, campo):
        from flask import current_app
        dominios = current_app.config["DOMINIOS_PERFIL"]
        dominio = campo.data.lower().strip().split("@")[-1]
        if dominio not in dominios:
            aceitos = ", ".join("@" + d for d in dominios)
            raise ValidationError(f"Domínio não reconhecido. Use {aceitos}.")


class CodigoRecuperacaoForm(FormularioBase):
    codigo = StringField(
        "Código de recuperação",
        validators=[
            DataRequired(message="Informe um código de recuperação."),
            Regexp(r"^\s*[A-Za-z0-9]{4}[\s-]?[A-Za-z0-9]{4}\s*$", message="O código tem 8 caracteres, no formato XXXX-XXXX."),
        ],
        render_kw={"placeholder": "XXXX-XXXX", "maxlength": 9, "autocomplete": "off",
                   "style": "font-family: monospace; letter-spacing: .08em;"},
    )


class ConfirmarCodigosForm(FormularioBase):
    guardei = BooleanField(
        "Guardei meus códigos de recuperação em local seguro",
        validators=[DataRequired(message="Confirme que guardou os códigos antes de continuar.")],
    )
