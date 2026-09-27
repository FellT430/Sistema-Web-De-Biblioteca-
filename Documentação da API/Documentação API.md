# Integração com a Google Books API

No cadastro de livros, o administrador busca pelo **ISBN** ou pelo **título** e o sistema preenche
automaticamente título, autor, editora, ano, ISBN, categoria, sinopse e capa, usando a
[Google Books API](https://developers.google.com/books). Antes de salvar, o administrador revisa os dados.

## Fluxo

```
Navegador (google_books.js) → Servidor Flask (/livros/buscar-google-books) → Google Books API
```

1. O administrador digita o ISBN ou o título e clica em **Buscar**.
2. O JavaScript chama a rota do servidor, que consulta o Google e devolve até 5 resultados.
3. Ao clicar em um resultado, o formulário é preenchido. O livro só é gravado ao clicar em **Salvar**.


A consulta passa pelo servidor para que a chave da API não fique exposta no navegador, só o admin possa
buscar e toda busca fique registrada nos logs de auditoria.

## Arquivos

| Arquivo | Função |
|---|---|
| `back/services/google_books.py` | Chama a API e converte a resposta |
| `back/controllers/livros_controller.py` | Rota `/livros/buscar-google-books` |
| `front/static/js/google_books.js` | Busca na tela e preenchimento do formulário |
| `front/templates/livros/form.html` | Formulário com a caixa de busca |
| `back/config.py` | URL e chave da API |

## Configuração

A API funciona sem chave, com limite menor de buscas por dia. Para usar uma chave, crie-a no
[Google Cloud Console](https://console.cloud.google.com/) (ativando a **Books API**) e coloque em `back/.env`:

```
GOOGLE_BOOKS_API_KEY=sua-chave-aqui
```

## Requisição à API

```
GET https://www.googleapis.com/books/v1/volumes?q=isbn:9788535910663&maxResults=5&key=<chave>
```

O prefixo `isbn:` é usado quando o termo é um ISBN. O tempo limite é de 5 segundos.

| Campo do Google | Campo no sistema |
|---|---|
| `title` | `titulo` |
| `authors` | `autor` (unidos por vírgula) |
| `publisher` | `editora` |
| `publishedDate` | `ano_publicacao` (só o ano) |
| `industryIdentifiers` | `isbn` (ISBN-13 ou, se não houver, ISBN-10) |
| `categories` | `categoria` |
| `description` | `sinopse` |
| `imageLinks.thumbnail` | `capa_url` (convertida para https) |

## Respostas da rota `/livros/buscar-google-books`

| Situação | Status |
|---|---|
| Sucesso (com ou sem resultados) | `200` com `{"resultados": [...]}` |
| Busca vazia | `400` |
| Google fora do ar, sem internet ou tempo esgotado | `502` com mensagem de erro |

Se a API falhar, o livro ainda pode ser cadastrado manualmente.

## Limitações

- Sem chave, o Google limita o número de buscas por dia.
- Alguns livros vêm sem ISBN, capa ou sinopse.
- As categorias vêm em inglês.
