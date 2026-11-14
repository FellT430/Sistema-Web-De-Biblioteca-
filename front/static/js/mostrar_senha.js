document.querySelectorAll(".btn-mostrar-senha").forEach(function (botao) {
    var campo = document.getElementById(botao.dataset.alvo);
    if (!campo) return;

    botao.addEventListener("click", function () {
        var mostrando = campo.type === "text";
        campo.type = mostrando ? "password" : "text";
        botao.setAttribute("aria-pressed", String(!mostrando));
        botao.setAttribute("aria-label", mostrando ? "Mostrar senha" : "Ocultar senha");
        botao.querySelector(".icone-mostrar").classList.toggle("d-none", !mostrando);
        botao.querySelector(".icone-ocultar").classList.toggle("d-none", mostrando);
        campo.focus();
    });
});
