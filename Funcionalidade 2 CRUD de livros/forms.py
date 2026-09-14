from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


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
