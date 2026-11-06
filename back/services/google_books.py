"""Integração com a Google Books API (https://developers.google.com/books).

A chamada HTTP e o parsing da resposta ficam isolados aqui, fora do
controller: a rota em `controllers/livros_controller.py` apenas repassa
a busca e devolve JSON, sem conhecer detalhes do formato da API externa.
"""
import requests
from flask import current_app


class GoogleBooksError(Exception):
    """Falha ao consultar a Google Books API (rede, timeout ou resposta inválida)."""


def _montar_url_capa(image_links):
    if not image_links:
        return None
    url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
    # A API às vezes retorna a capa em http://: forçamos https para evitar
    # conteúdo misto (mixed content) ao exibir a imagem em uma página https.
    return url.replace("http://", "https://") if url else None


def _extrair_isbn(identificadores):
    if not identificadores:
        return None
    por_tipo = {item.get("type"): item.get("identifier") for item in identificadores}
    return por_tipo.get("ISBN_13") or por_tipo.get("ISBN_10")


def _normalizar_volume(volume):
    info = volume.get("volumeInfo", {})
    data_publicacao = info.get("publishedDate", "") or ""
    ano_publicacao = int(data_publicacao[:4]) if data_publicacao[:4].isdigit() else None

    return {
        "google_books_id": volume.get("id"),
        "titulo": info.get("title", ""),
        "autor": ", ".join(info.get("authors", [])),
        "editora": info.get("publisher", ""),
        "ano_publicacao": ano_publicacao,
        "isbn": _extrair_isbn(info.get("industryIdentifiers")),
        "sinopse": info.get("description", ""),
        "categoria": ", ".join(info.get("categories", [])),
        "capa_url": _montar_url_capa(info.get("imageLinks")),
    }


def buscar_livros(termo: str, por_isbn: bool = False, max_resultados: int = 5) -> list:
    """Busca livros na Google Books API por ISBN ou por texto livre (título/autor).

    Retorna uma lista de dicts já normalizados para os campos usados no
    formulário de cadastro. Lança GoogleBooksError em falha de rede, timeout
    ou status de erro HTTP — o chamador decide como comunicar isso ao usuário.
    """
    termo = (termo or "").strip()
    if not termo:
        return []

    prefixo = "isbn:" if por_isbn else ""
    params = {"q": f"{prefixo}{termo}", "maxResults": max_resultados}

    api_key = current_app.config.get("GOOGLE_BOOKS_API_KEY")
    if api_key:
        params["key"] = api_key

    try:
        resposta = requests.get(
            current_app.config["GOOGLE_BOOKS_API_URL"],
            params=params,
            timeout=5,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.exceptions.RequestException as erro:
        raise GoogleBooksError(
            "Não foi possível consultar a Google Books API no momento. Tente novamente em instantes."
        ) from erro
    except ValueError as erro:
        raise GoogleBooksError("A Google Books API retornou uma resposta inválida.") from erro

    return [_normalizar_volume(volume) for volume in dados.get("items", [])]
