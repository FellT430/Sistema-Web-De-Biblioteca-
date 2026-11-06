import re
from datetime import date

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, BooleanField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange, URL, Regexp, ValidationError, InputRequired

class FormularioBase(FlaskForm):
    """Base de todos os formulários: mensagens de validação padrão em português.

    Usa as traduções que já vêm com o WTForms (ex.: "Este campo é obrigatório."
    em vez de "This field is required."). Requer WTF_I18N_ENABLED = False no config.
    """

    class Meta:
        locales = ["pt_BR", "pt"]


ANO_MINIMO_PUBLICACAO = 1450  # prensa de Gutenberg: antes disso não há livro impresso


def normalizar_isbn(valor):
    """Remove traços, pontos e espaços: '978-85-7936-085-5' -> '9788579360855'."""
    if not valor:
        return valor
    return re.sub(r"[\s.\-]", "", valor).upper()


def validar_isbn(form, campo):
    """ISBN-10 (9 dígitos + dígito ou X) ou ISBN-13 (13 dígitos)."""
    if campo.data and not re.fullmatch(r"\d{9}[\dX]|\d{13}", campo.data):
        raise ValidationError("ISBN inválido: informe 10 ou 13 dígitos (traços e espaços são ignorados).")


def validar_ano_publicacao(form, campo):
    """O ano máximo é calculado na hora, para continuar certo nos próximos anos."""
    ano_atual = date.today().year
    if campo.data is not None and not ANO_MINIMO_PUBLICACAO <= campo.data <= ano_atual:
        raise ValidationError(f"Informe um ano entre {ANO_MINIMO_PUBLICACAO} e {ano_atual}.")


class LoginForm(FormularioBase):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])


class CodigoDoisFatoresForm(FormularioBase):
    """Código de 6 dígitos gerado pelo app autenticador (Google Authenticator)."""
    codigo = StringField(
        "Código de verificação",
        validators=[
            DataRequired(message="Informe o código de 6 dígitos."),
            Regexp(r"^\s*\d{3}\s?\d{3}\s*$", message="O código deve ter 6 dígitos."),
        ],
        render_kw={"inputmode": "numeric", "autocomplete": "one-time-code", "maxlength": 7, "placeholder": "000000"},
    )


class AcaoAdminForm(FormularioBase):
    """Formulário vazio: só carrega o token CSRF de botões de ação do admin."""


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
        render_kw={"placeholder": "10 ou 13 dígitos"},
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
    # Preenchidos via JS ao escolher um resultado da busca na Google Books API.
    capa_url = HiddenField(validators=[Optional(), URL(message="URL de capa inválida."), Length(max=500)])
    google_books_id = HiddenField(validators=[Optional(), Length(max=50)])


class AcaoForm(FormularioBase):
    """Formulário vazio: só carrega o token CSRF de botões de ação (POST),
    como "Adicionar livro", "Remover" e "Excluir" nas telas de disciplinas."""


class DisciplinaForm(FormularioBase):
    """Cadastro e edição de disciplina pelo professor (RF10)."""
    nome = StringField(
        "Nome da disciplina",
        validators=[DataRequired(message="Informe o nome da disciplina."), Length(min=2, max=120)],
    )
    codigo = StringField("Código (opcional)", validators=[Optional(), Length(max=20)])
    descricao = TextAreaField(
        "Curso / turma / descrição (opcional)", validators=[Optional(), Length(max=1000)]
    )


class RecomendacaoForm(FormularioBase):
    """Recomendação de um livro da disciplina aos alunos (RF11).

    RN36: o comentário é opcional e tem no máximo 500 caracteres.
    """
    mensagem = TextAreaField(
        "Comentário para os alunos (opcional)",
        validators=[Optional(), Length(max=500, message="O comentário pode ter no máximo 500 caracteres.")],
    )


class EsqueciSenhaForm(FormularioBase):
    """Redefinição de senha usando o código do Google Authenticator.

    Como o 2FA é obrigatório para todos, o código do app prova que é o dono
    da conta, sem precisar de servidor de e-mail.
    """
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    codigo = StringField(
        "Código do Google Authenticator",
        validators=[
            DataRequired(message="Informe o código de 6 dígitos."),
            Regexp(r"^\s*\d{3}\s?\d{3}\s*$", message="O código deve ter 6 dígitos."),
        ],
        render_kw={"inputmode": "numeric", "autocomplete": "one-time-code", "maxlength": 7, "placeholder": "000000"},
    )
    nova_senha = PasswordField(
        "Nova senha",
        validators=[DataRequired(), Length(min=6, message="A senha deve ter ao menos 6 caracteres.")],
    )
    confirmar_senha = PasswordField(
        "Confirmar nova senha",
        validators=[DataRequired(), EqualTo("nova_senha", message="As senhas não conferem.")],
    )
