import io
import time

import pyotp
import qrcode
import qrcode.image.svg

NOME_EMISSOR = "Livro +"
INTERVALO_SEGUNDOS = 30
JANELA_TOLERANCIA = 1


def gerar_segredo() -> str:
    return pyotp.random_base32(length=32)


def uri_provisionamento(segredo: str, email: str) -> str:
    return pyotp.TOTP(segredo, interval=INTERVALO_SEGUNDOS).provisioning_uri(
        name=email, issuer_name=NOME_EMISSOR
    )


def qr_code_svg(conteudo: str) -> str:
    imagem = qrcode.make(conteudo, image_factory=qrcode.image.svg.SvgPathImage, box_size=8)
    buffer = io.BytesIO()
    imagem.save(buffer)
    return buffer.getvalue().decode("utf-8")


def formatar_segredo(segredo: str) -> str:
    return " ".join(segredo[i:i + 4] for i in range(0, len(segredo), 4))


def _normalizar(codigo: str) -> str:
    return "".join((codigo or "").split())


def verificar_codigo(segredo: str, codigo: str, ultimo_passo=None):
    codigo = _normalizar(codigo)
    if not segredo or len(codigo) != 6 or not codigo.isdigit():
        return None

    totp = pyotp.TOTP(segredo, interval=INTERVALO_SEGUNDOS)
    passo_atual = int(time.time()) // INTERVALO_SEGUNDOS

    for desvio in range(-JANELA_TOLERANCIA, JANELA_TOLERANCIA + 1):
        passo = passo_atual + desvio
        if ultimo_passo is not None and passo <= ultimo_passo:
            continue
        if totp.verify(codigo, for_time=passo * INTERVALO_SEGUNDOS):
            return passo
    return None
