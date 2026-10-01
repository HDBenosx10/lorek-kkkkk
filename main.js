"use strict";

// Register before the deferred HubSpot embed runs.
const formStatus = document.getElementById("form-status");
const formFrame = document.querySelector(".hs-form-frame");
let formReady = false;
window.addEventListener("hs-form-event:on-ready", (event) => {
  if (event.detail?.formId !== formFrame?.dataset.formId) return;
  formReady = true;
  if (formStatus) formStatus.hidden = true;
});
const showFormError = () => {
  if (!formStatus || formReady) return;
  formStatus.hidden = false;
  formStatus.textContent =
    "Não foi possível carregar o formulário. Recarregue a página para tentar novamente.";
};
document
  .getElementById("hubspot-embed")
  ?.addEventListener("error", showFormError);
window.setTimeout(showFormError, 20000);

const clock = document.getElementById("clock");
if (clock) {
  let formatter;
  try {
    formatter = new Intl.DateTimeFormat("pt-BR", {
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "America/Sao_Paulo",
    });
  } catch {
    /* Keep the city label when Intl is unavailable. */
  }
  const updateClock = () => {
    clock.textContent = formatter
      ? "Rio de Janeiro · " + formatter.format(new Date())
      : "Rio de Janeiro";
  };
  updateClock();
  window.setInterval(() => {
    if (!document.hidden) updateClock();
  }, 30000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) updateClock();
  });
}
