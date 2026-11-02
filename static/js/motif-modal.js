document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("motif-modal");
    if (!modal) return;

    const modalImage = document.getElementById("motif-modal-image");
    const modalName = document.getElementById("motif-modal-name");
    const modalDescription = document.getElementById("motif-modal-description");
    const confirmButton = document.getElementById("confirm-motif");
    let selectedMotifId = null;
    let previousFocus = null;

    function openModal(button) {
        selectedMotifId = button.dataset.id;
        modalName.textContent = button.dataset.name || "Motif Batik";
        modalDescription.textContent = button.dataset.description || "";
        modalImage.src = button.dataset.image || "";
        modalImage.alt = button.dataset.name || "Preview motif batik";
        modalImage.style.display = button.dataset.image ? "block" : "none";

        previousFocus = button;
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        confirmButton.focus();
    }

    function closeModal() {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("modal-open");
        selectedMotifId = null;
        if (previousFocus) previousFocus.focus();
    }

    document.addEventListener("click", function (event) {
        const button = event.target.closest(".motif-select");

        if (button) {
            openModal(button);
            return;
        }

        if (event.target.closest("[data-close-modal]")) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && modal.classList.contains("is-open")) {
            closeModal();
        }
    });

    confirmButton.addEventListener("click", function () {
        if (!selectedMotifId) return;

        const url = new URL(modal.dataset.studioUrl, window.location.origin);
        url.searchParams.set("motif", selectedMotifId);
        window.location.href = url.toString();
    });
});
