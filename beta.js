"use strict";

// Progressive enhancement: all projects and native details work without JS.
const filterGroup = document.querySelector(".filters");
const projectCards = [...document.querySelectorAll("[data-category]")];
const filterStatus = document.getElementById("filter-status");
if (filterGroup && projectCards.length) {
  filterGroup.hidden = false;
  filterGroup.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-filter]");
    if (!button) return;
    const category = button.dataset.filter;
    for (const control of filterGroup.querySelectorAll("button")) {
      control.setAttribute("aria-pressed", String(control === button));
    }
    let visible = 0;
    for (const card of projectCards) {
      card.hidden = category !== "all" && card.dataset.category !== category;
      if (!card.hidden) visible += 1;
    }
    const pair = document.querySelector(".project-pair");
    if (pair) {
      const visiblePairCards = pair.querySelectorAll(".project:not([hidden])");
      pair.hidden = visiblePairCards.length === 0;
      pair.classList.toggle("single-project", visiblePairCards.length === 1);
    }
    if (filterStatus)
      filterStatus.textContent = `${visible} ${visible === 1 ? "projeto" : "projetos"}`;
  });
}

// Deep links open the corresponding native disclosure without a modal trap.
function openLinkedCase() {
  const id = window.location.hash.slice(1);
  if (!id) return;
  const target = document.getElementById(id);
  if (target instanceof HTMLDetailsElement) target.open = true;
}
window.addEventListener("hashchange", openLinkedCase);
document.querySelectorAll('a[href^="#case-"]').forEach((link) => {
  link.addEventListener("click", () => {
    const target = document.getElementById(link.getAttribute("href").slice(1));
    if (target instanceof HTMLDetailsElement) target.open = true;
  });
});
openLinkedCase();
document.querySelectorAll("[data-year]").forEach((element) => {
  element.textContent = String(new Date().getFullYear());
});
