"""Serviço de autenticação de dois fatores (2FA) via TOTP.

TOTP (Time-based One-Time Password, RFC 6238) é o padrão usado pelo
Google Authenticator, Microsoft Authenticator, Authy etc. Funciona assim:

1. O servidor gera um segredo aleatório (base32) para o usuário.
2. O segredo é passado ao app do celular por um QR Code no formato
   otpauth://totp/Livro%2B:email?secret=...&issuer=Livro%2B
3. A cada 30 segundos, o app e o servidor calculam o mesmo código de
   6 dígitos a partir do segredo + horário atual. Se baterem, o usuário
   provou que está com o celular em mãos (o "segundo fator").

Nenhum dado é enviado ao Google: o cálculo é feito localmente no app e
no servidor. Por isso o relógio do servidor precisa estar correto.
"""
import io
import time

import pyotp
import qrcode
import qrcode.image.svg

NOME_EMISSOR = "Livro +"   # nome que aparece no app autenticador
INTERVALO_SEGUNDOS = 30
# Tolerância de ±1 janela (±30s) para pequenas diferenças de relógio
JANELA_TOLERANCIA = 1


def gerar_segredo() -> str:
    """Gera um novo segredo base32 aleatório (160 bits)."""
    return pyotp.random_base32(length=32)


def uri_provisionamento(segredo: str, email: str) -> str:
    """Monta a URI otpauth:// que o Google Authenticator lê pelo QR Code."""
    return pyotp.TOTP(segredo, interval=INTERVALO_SEGUNDOS).provisioning_uri(
        name=email, issuer_name=NOME_EMISSOR
    )


def qr_code_svg(conteudo: str) -> str:
    """Gera o QR Code como SVG (texto), pronto para colocar no HTML.

    Usa SVG em vez de PNG para não depender da biblioteca Pillow.
    """
    imagem = qrcode.make(conteudo, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buffer = io.BytesIO()
    imagem.save(buffer)
    return buffer.getvalue().decode("utf-8")


def formatar_segredo(segredo: str) -> str:
    """Agrupa o segredo de 4 em 4 caracteres para digitação manual."""
    return " ".join(segredo[i:i + 4] for i in range(0, len(segredo), 4))


def _normalizar(codigo: str) -> str:
    return "".join((codigo or "").split())


def verificar_codigo(segredo: str, codigo: str, ultimo_passo=None):
    """Confere um código de 6 dígitos.

    Retorna o "passo" (número da janela de 30s) do código aceito, ou None
    se o código for inválido. O passo deve ser salvo no usuário e passado
    como `ultimo_passo` na próxima verificação: códigos de uma janela igual
    ou anterior são recusados, impedindo reutilização (replay).
    """
    codigo = _normalizar(codigo)
    if not segredo or len(codigo) != 6 or not codigo.isdigit():
        return None

    totp = pyotp.TOTP(segredo, interval=INTERVALO_SEGUNDOS)
    passo_atual = int(time.time()) // INTERVALO_SEGUNDOS

    for desvio in range(-JANELA_TOLERANCIA, JANELA_TOLERANCIA + 1):
        passo = passo_atual + desvio
        if ultimo_passo is not None and passo <= ultimo_passo:
            continue
        # verify() com for_time compara em tempo constante
        if totp.verify(codigo, for_time=passo * INTERVALO_SEGUNDOS):
            return passo
    return None
