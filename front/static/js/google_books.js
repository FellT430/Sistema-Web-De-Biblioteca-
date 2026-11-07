(function () {
    "use strict";

    const input = document.getElementById("busca-google-books");
    const botaoBuscar = document.getElementById("btn-buscar-google-books");
    const containerResultados = document.getElementById("resultados-google-books");
    const capaPreview = document.getElementById("capa-preview");

    if (!input || !botaoBuscar || !containerResultados) {
        return;
    }

    const REGEX_ISBN = /^(?:\d{9}[\dXx]|\d{13})$/;

    function limparResultados() {
        containerResultados.innerHTML = "";
    }

    function mostrarMensagem(texto, tipo) {
        limparResultados();
        const div = document.createElement("div");
        div.className = "alert alert-" + tipo + " mb-0 py-2";
        div.textContent = texto;
        containerResultados.appendChild(div);
    }

    function definirValor(id, valor) {
        const campo = document.getElementById(id);
        if (campo && valor !== null && valor !== undefined && valor !== "") {
            campo.value = valor;
        }
    }

    function preencherFormulario(livro) {
        definirValor("titulo", livro.titulo);
        definirValor("autor", livro.autor);
        definirValor("editora", livro.editora);
        definirValor("isbn", livro.isbn);
        definirValor("ano_publicacao", livro.ano_publicacao);
        definirValor("sinopse", livro.sinopse);
        definirValor("categoria", livro.categoria);
        definirValor("capa_url", livro.capa_url);
        definirValor("google_books_id", livro.google_books_id);

        if (capaPreview) {
            if (livro.capa_url) {
                capaPreview.src = livro.capa_url;
                capaPreview.classList.remove("d-none");
            } else {
                capaPreview.classList.add("d-none");
            }
        }

        mostrarMensagem("Dados preenchidos a partir da Google Books API. Revise antes de salvar.", "success");
    }

    function criarItemResultado(livro) {
        const item = document.createElement("button");
        item.type = "button";
        item.className = "list-group-item list-group-item-action d-flex align-items-center gap-3";

        if (livro.capa_url) {
            const img = document.createElement("img");
            img.src = livro.capa_url;
            img.alt = "";
            img.width = 40;
            img.height = 56;
            img.style.objectFit = "cover";
            item.appendChild(img);
        }

        const texto = document.createElement("span");
        const autor = livro.autor ? " — " + livro.autor : "";
        texto.textContent = livro.titulo + autor;
        item.appendChild(texto);

        item.addEventListener("click", function () {
            preencherFormulario(livro);
        });

        return item;
    }

    function renderizarResultados(resultados) {
        limparResultados();

        if (!resultados || resultados.length === 0) {
            mostrarMensagem("Nenhum livro encontrado para essa busca.", "warning");
            return;
        }

        resultados.forEach(function (livro) {
            containerResultados.appendChild(criarItemResultado(livro));
        });
    }

    async function buscar() {
        const termo = input.value.trim();
        if (!termo) {
            mostrarMensagem("Digite um ISBN ou um título para buscar.", "warning");
            return;
        }

        const porIsbn = REGEX_ISBN.test(termo.replace(/[\s-]/g, ""));

        botaoBuscar.disabled = true;
        const textoOriginal = botaoBuscar.textContent;
        botaoBuscar.textContent = "Buscando...";
        mostrarMensagem("Buscando na Google Books API...", "secondary");

        try {
            const params = new URLSearchParams({ q: termo, por_isbn: porIsbn ? "1" : "0" });
            const resposta = await fetch("/livros/buscar-google-books?" + params.toString(), {
                headers: { "X-Requested-With": "XMLHttpRequest" },
            });
            const dados = await resposta.json();

            if (!resposta.ok) {
                mostrarMensagem(dados.erro || "Erro ao buscar na Google Books API.", "danger");
                return;
            }

            renderizarResultados(dados.resultados);
        } catch (erro) {
            mostrarMensagem("Não foi possível conectar à Google Books API. Verifique sua internet.", "danger");
        } finally {
            botaoBuscar.disabled = false;
            botaoBuscar.textContent = textoOriginal;
        }
    }

    botaoBuscar.addEventListener("click", buscar);
    input.addEventListener("keydown", function (evento) {
        if (evento.key === "Enter") {
            evento.preventDefault();
            buscar();
        }
    });
})();
