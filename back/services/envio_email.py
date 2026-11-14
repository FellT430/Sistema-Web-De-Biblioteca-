import logging
import smtplib
from datetime import date
from email.message import EmailMessage
from html import escape

from flask import current_app, has_request_context, url_for
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

_log = logging.getLogger("envio_email")

SALT_CONFIRMACAO = "confirmacao-de-email"


def _serializador():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=SALT_CONFIRMACAO)


def gerar_token_confirmacao(usuario) -> str:
    return _serializador().dumps({"id": usuario.id, "email": usuario.email})


def ler_token_confirmacao(token):
    validade = current_app.config["HORAS_VALIDADE_CONFIRMACAO"] * 3600
    try:
        return _serializador().loads(token, max_age=validade), None
    except SignatureExpired:
        return None, "expirado"
    except BadSignature:
        return None, "invalido"


def _mostrar_no_terminal(destinatario, assunto, texto, motivo):
    print(
        f"\n===== E-MAIL NÃO ENVIADO ({motivo}) =====\n"
        f"Para: {destinatario}\nAssunto: {assunto}\n\n{texto}\n"
        "=========================================\n",
        flush=True,
    )


def enviar(destinatario, assunto, paragrafos, botao=None) -> bool:
    config = current_app.config

    texto = "\n\n".join(paragrafos)
    if botao:
        texto += f"\n\n{botao[0]}: {botao[1]}"
    texto += "\n\n— Equipe LIVRO+"

    html = "".join(f"<p>{escape(p)}</p>" for p in paragrafos)
    if botao:
        html += (
            f'<p><a href="{escape(botao[1])}" style="background:#0d6efd;color:#fff;'
            f'padding:10px 18px;border-radius:6px;text-decoration:none;display:inline-block">'
            f"{escape(botao[0])}</a></p>"
            f'<p style="font-size:12px;color:#666">Se o botão não funcionar, copie este endereço: '
            f"{escape(botao[1])}</p>"
        )
    html += "<p>— Equipe LIVRO+</p>"

    if not config.get("MAIL_SERVER"):
        _mostrar_no_terminal(destinatario, assunto, texto, "MAIL_SERVER não configurado no .env")
        return False

    mensagem = EmailMessage()
    mensagem["From"] = config["MAIL_DEFAULT_SENDER"]
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content(texto)
    mensagem.add_alternative(f"<html><body style='font-family:Arial,sans-serif'>{html}</body></html>", subtype="html")

    try:
        with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"], timeout=10) as smtp:
            if config["MAIL_USE_TLS"]:
                smtp.starttls()
            if config.get("MAIL_USERNAME"):
                smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"] or "")
            smtp.send_message(mensagem)
        return True
    except (smtplib.SMTPException, OSError) as erro:
        _log.error("Falha ao enviar e-mail para %s: %s", destinatario, erro)
        _mostrar_no_terminal(destinatario, assunto, texto, f"falha no envio: {erro}")
        return False


def enviar_confirmacao(usuario) -> bool:
    link = url_for("auth.confirmar_email", token=gerar_token_confirmacao(usuario), _external=True)
    horas = current_app.config["HORAS_VALIDADE_CONFIRMACAO"]
    return enviar(
        usuario.email,
        "Confirme seu e-mail - LIVRO+",
        [
            f"Olá, {usuario.nome}!",
            "Recebemos seu cadastro no LIVRO+. Para continuar, confirme que este e-mail é seu "
            "clicando no botão abaixo.",
            f"O link vale por {horas} horas. Depois da confirmação, seu cadastro será analisado "
            "pela administração e você receberá um aviso quando puder entrar.",
            "Se você não fez este cadastro, ignore esta mensagem.",
        ],
        botao=("Confirmar meu e-mail", link),
    )


def enviar_aprovacao(usuario) -> bool:
    return enviar(
        usuario.email,
        "Seu cadastro foi aprovado - LIVRO+",
        [
            f"Olá, {usuario.nome}!",
            f"Seu cadastro como {usuario.perfil_nome.lower()} foi aprovado. Você já pode entrar no sistema.",
            "No primeiro acesso, será pedido para configurar a verificação em duas etapas "
            "com o Google Authenticator.",
        ],
        botao=("Entrar no LIVRO+", url_for("auth.login", _external=True)),
    )


def enviar_reprovacao(usuario) -> bool:
    return enviar(
        usuario.email,
        "Seu cadastro não foi aprovado - LIVRO+",
        [
            f"Olá, {usuario.nome}.",
            "Seu cadastro no LIVRO+ não foi aprovado pela administração.",
            "Se você acredita que houve um engano, procure a administração da biblioteca.",
        ],
    )


def _link(endpoint, **valores) -> str:
    if has_request_context():
        return url_for(endpoint, _external=True, **valores)
    with current_app.test_request_context(base_url=current_app.config["APP_URL"]):
        return url_for(endpoint, _external=True, **valores)


def _link_entrar() -> str:
    return _link("auth.login")


def _data(valor) -> str:
    return valor.strftime("%d/%m/%Y") if valor else "não definida"


def enviar_lembrete_prazo(emprestimo, hoje=None) -> bool:
    hoje = hoje or date.today()
    aluno, livro = emprestimo.aluno, emprestimo.livro
    quando = "hoje" if emprestimo.data_prevista_devolucao == hoje else "amanhã"
    return enviar(
        aluno.email,
        "Lembrete de devolução - LIVRO+",
        [
            f"Olá, {aluno.nome}!",
            f"O prazo para devolver \"{livro.titulo}\" termina {quando}.",
            f"Data prevista de devolução: {_data(emprestimo.data_prevista_devolucao)}.",
            "Devolva o livro na biblioteca dentro do prazo para evitar atraso.",
        ],
        botao=("Entrar no LIVRO+", _link_entrar()),
    )


def enviar_aviso_atraso(emprestimo, dias) -> bool:
    aluno, livro = emprestimo.aluno, emprestimo.livro
    return enviar(
        aluno.email,
        "Empréstimo em atraso - LIVRO+",
        [
            f"Olá, {aluno.nome}!",
            f"O empréstimo de \"{livro.titulo}\" está atrasado há {dias} dia(s).",
            f"Data prevista de devolução: {_data(emprestimo.data_prevista_devolucao)}.",
            "Devolva o livro para poder fazer novos empréstimos.",
        ],
        botao=("Entrar no LIVRO+", _link_entrar()),
    )


def enviar_devolucao(emprestimo) -> bool:
    aluno, livro = emprestimo.aluno, emprestimo.livro
    paragrafos = [
        f"Olá, {aluno.nome}!",
        f"A devolução de \"{livro.titulo}\" foi registrada.",
        f"Data prevista de devolução: {_data(emprestimo.data_prevista_devolucao)}.",
    ]
    if emprestimo.devolvido_com_atraso:
        paragrafos.append(f"O livro foi devolvido com {emprestimo.dias_atraso()} dia(s) de atraso.")
    paragrafos.append("Obrigado por devolver o livro!")
    return enviar(
        aluno.email,
        "Devolução registrada - LIVRO+",
        paragrafos,
        botao=("Entrar no LIVRO+", _link_entrar()),
    )


def enviar_reserva_disponivel(reserva, data_limite) -> bool:
    aluno, livro = reserva.aluno, reserva.livro
    return enviar(
        aluno.email,
        "O livro que você reservou está disponível - LIVRO+",
        [
            f"Olá, {aluno.nome}!",
            f"O livro que você reservou está disponível para retirada: \"{livro.titulo}\", de {livro.autor}.",
            f"Retire o livro na biblioteca até {_data(data_limite)}.",
            "Se você não retirar até essa data, a reserva expira e o livro passa para o próximo da fila.",
        ],
        botao=("Ver minhas solicitações", _link("emprestimos.meus")),
    )


def enviar_reserva_expirada(reserva) -> bool:
    aluno, livro = reserva.aluno, reserva.livro
    return enviar(
        aluno.email,
        "Sua reserva expirou - LIVRO+",
        [
            f"Olá, {aluno.nome}!",
            f"O prazo para retirar \"{livro.titulo}\" terminou e a sua reserva expirou. "
            "O livro foi para o próximo da fila.",
            "Se você ainda tiver interesse, é possível reservar o livro de novo.",
        ],
        botao=("Ver o livro", _link("acervo.detalhe", livro_id=livro.id)),
    )


def enviar_exclusao_solicitada(usuario) -> bool:
    return enviar(
        usuario.email,
        "Recebemos seu pedido de exclusão de dados - LIVRO+",
        [
            f"Olá, {usuario.nome}.",
            "Recebemos seu pedido de exclusão dos dados pessoais do LIVRO+. Ele será analisado "
            "pela administração e você receberá outro e-mail com a decisão.",
        
            "Se você não fez este pedido, procure a administração da biblioteca.",
        ],
    )


def enviar_exclusao_confirmada(email, nome) -> bool:
    return enviar(
        email,
        "Seus dados foram excluídos - LIVRO+",
        [
            f"Olá, {nome}.",
            "Seu pedido foi aprovado: seus dados pessoais foram excluídos do LIVRO+ "
            "e sua conta foi encerrada.",
            
            "Caso queira utilizar o LIVRO + no futuro, faça o cadastro novamente "
        ],
    )


def enviar_exclusao_recusada(usuario, motivo) -> bool:
    return enviar(
        usuario.email,
        "Seu pedido de exclusão de dados não foi aceito - LIVRO+",
        [
            f"Olá, {usuario.nome}.",
            "Seu pedido de exclusão dos dados pessoais não pôde ser atendido agora.",
            f"Motivo: {motivo}",
            "Sua conta continua ativa. Se tiver dúvidas, procure a administração da biblioteca.",
        ],
    )
