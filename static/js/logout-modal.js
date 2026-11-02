
document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("logoutConfirmModal");
    const cancelButton = document.getElementById("cancelLogout");
    const confirmButton = document.getElementById("confirmLogout");

    if (!modal || !cancelButton || !confirmButton) return;

    // Sesuaikan selector dengan class form logout di navbar.
    const logoutForms = document.querySelectorAll(
        ".nav-logout-form, .nav-menu-logout-form"
    );

    let pendingLogoutForm = null;
    let previousFocus = null;

    function openLogoutModal(form) {
        pendingLogoutForm = form;
        previousFocus = document.activeElement;

        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("logout-modal-active");

        cancelButton.focus();
    }

    function closeLogoutModal() {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("logout-modal-active");

        pendingLogoutForm = null;

        if (previousFocus && typeof previousFocus.focus === "function") {
            previousFocus.focus();
        }
    }

    // Cegah form langsung logout sebelum konfirmasi.
    logoutForms.forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            openLogoutModal(form);
        });
    });

    cancelButton.addEventListener("click", closeLogoutModal);

    // Klik area gelap juga membatalkan logout.
    modal.querySelectorAll("[data-logout-cancel]").forEach((element) => {
        element.addEventListener("click", closeLogoutModal);
    });

    confirmButton.addEventListener("click", () => {
        if (!pendingLogoutForm) return;

        const formToSubmit = pendingLogoutForm;

        // Jangan sampai tombol diklik berulang kali.
        confirmButton.disabled = true;
        confirmButton.textContent = "Memproses...";

        // form.submit() mengirim POST tanpa memicu event submit lagi.
        formToSubmit.submit();
    });

    // Tombol Escape untuk menutup modal.
    document.addEventListener("keydown", (event) => {
        if (
            event.key === "Escape" &&
            modal.classList.contains("is-open")
        ) {
            closeLogoutModal();
        }
    });
});
