document.addEventListener("DOMContentLoaded", function () {
    const cancelButton = document.getElementById("cancel-batik-btn");
    const modal = document.getElementById("cancel-modal");
    const continueButton = document.getElementById("continue-editing-btn");
    const confirmButton = document.getElementById("confirm-cancel-btn");

    console.log("Add Batik JS berhasil dimuat");
    console.log({ cancelButton, modal, continueButton, confirmButton });

    if (!cancelButton || !modal) {
        console.error("Tombol Batal atau modal tidak ditemukan!");
        return;
    }

    cancelButton.addEventListener("click", function () {
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("modal-open");
        console.log("Modal dibuka");
    });

    if (continueButton) {
        continueButton.addEventListener("click", function () {
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
            document.body.classList.remove("modal-open");
        });
    }

    const backdrop = modal.querySelector("[data-close-modal]");

    if (backdrop) {
        backdrop.addEventListener("click", function () {
            modal.classList.remove("is-open");
            modal.setAttribute("aria-hidden", "true");
            document.body.classList.remove("modal-open");
        });
    }

    if (confirmButton) {
        confirmButton.addEventListener("click", function () {
            window.location.href = cancelButton.dataset.cancelUrl;
        });
    }
});