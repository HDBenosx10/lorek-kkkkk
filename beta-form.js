"use strict";

// Public form identifiers, not API credentials. Field options mirror HubSpot.
(() => {
  const form = document.getElementById("contact-native");
  if (!form) return;
  const status = document.getElementById("native-status");
  const success = document.getElementById("contact-success");
  const button = form.querySelector('button[type="submit"]');
  const buttonLabel = button.querySelector("span");
  const endpoint =
    "https://api.hsforms.com/submissions/v3/integration/submit/51906766/c2ff372a-85ba-40e0-8f90-18badde87196";
  let sending = false;
  form.hidden = false;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (sending || !form.reportValidity()) return;
    const data = new FormData(form);
    const fields = ["firstname", "lastname", "email", "origem_formulario_1"]
      .map((name) => ({
        objectTypeId: "0-1",
        name,
        value: String(data.get(name) || "").trim(),
      }))
      .filter((field) => field.value);
    sending = true;
    button.disabled = true;
    form.setAttribute("aria-busy", "true");
    buttonLabel.textContent = "Enviando…";
    status.textContent = "Enviando seu contato com segurança…";
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fields,
          context: {
            pageUri: window.location.origin + window.location.pathname,
            pageName: document.title,
          },
        }),
        signal: controller.signal,
        credentials: "omit",
      });
      if (!response.ok) {
        const result = await response.json().catch(() => ({}));
        const types = (result.errors || []).map((error) => error.errorType);
        status.textContent =
          response.status === 429
            ? "Muitos envios em pouco tempo. Aguarde um minuto antes de tentar novamente."
            : types.some((type) =>
                  ["INVALID_EMAIL", "BLOCKED_EMAIL"].includes(type),
                )
              ? "Confira seu endereço de e-mail ou use outro endereço para continuar."
              : "O HubSpot não aceitou o envio. Confira os campos ou use o formulário original abaixo.";
        return;
      }
      form.hidden = true;
      success.hidden = false;
      success.focus();
      form.reset();
    } catch {
      // A timeout can happen after acceptance; never retry automatically.
      status.textContent =
        "Não conseguimos confirmar o envio. Verifique sua conexão e seu e-mail antes de tentar novamente. Seus dados continuam aqui.";
    } finally {
      window.clearTimeout(timeout);
      sending = false;
      button.disabled = false;
      form.removeAttribute("aria-busy");
      buttonLabel.textContent = "Enviar contato";
    }
  });
})();
