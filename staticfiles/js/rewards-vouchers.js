(() => {
    const successModal = document.getElementById("voucher-success-modal");
    if (successModal) {
        const closeSuccessModal = () => {
            successModal.hidden = true;
            successModal.classList.remove("is-open");
            document.body.classList.remove("voucher-confirm-open");
        };

        successModal.querySelectorAll("[data-voucher-success-close]").forEach((control) => {
            control.addEventListener("click", closeSuccessModal);
        });
        successModal.addEventListener("keydown", (event) => {
            if (event.key === "Escape") closeSuccessModal();
        });
        document.body.classList.add("voucher-confirm-open");
        successModal.querySelector("[data-voucher-success-close]")?.focus();
    }

    const modal = document.getElementById("voucher-confirm-modal");
    const confirmationForm = document.getElementById("voucher-confirm-form");
    if (!modal || !confirmationForm) return;

    const dialog = modal.querySelector(".voucher-confirm-dialog");
    let returnFocus = null;

    const setText = (id, value) => {
        const element = document.getElementById(id);
        if (element) element.textContent = value;
    };

    const openModal = (triggerForm) => {
        const data = triggerForm.dataset;
        const balance = Number.parseInt(data.voucherBalance, 10) || 0;
        const cost = Number.parseInt(data.voucherPoints, 10) || 0;

        returnFocus = triggerForm.querySelector("button[type='submit']");
        confirmationForm.action = triggerForm.action;
        confirmationForm.querySelector("[name='csrfmiddlewaretoken']").value =
            triggerForm.querySelector("[name='csrfmiddlewaretoken']").value;
        const returnToInput = confirmationForm.querySelector("[name='return_to']");
        const triggerReturnTo = triggerForm.querySelector("[name='return_to']");
        if (returnToInput) returnToInput.value = triggerReturnTo?.value || "catalog";

        setText("voucher-confirm-name", data.voucherName);
        setText("voucher-confirm-discount", data.voucherDiscount);
        setText("voucher-confirm-points", String(cost));
        setText("voucher-confirm-balance", String(balance));
        setText("voucher-confirm-remaining", String(balance - cost));
        setText(
            "voucher-confirm-description",
            data.voucherDescription || "Pastikan nilai diskon dan saldo poinmu sudah sesuai."
        );

        modal.hidden = false;
        modal.classList.add("is-open");
        document.body.classList.add("voucher-confirm-open");
        modal.querySelector("[data-voucher-modal-close]").focus();
    };

    const closeModal = () => {
        modal.hidden = true;
        modal.classList.remove("is-open");
        document.body.classList.remove("voucher-confirm-open");
        if (returnFocus && returnFocus.isConnected) returnFocus.focus();
        returnFocus = null;
    };

    document.querySelectorAll(".voucher-redemption-trigger").forEach((form) => {
        form.addEventListener("submit", (event) => {
            event.preventDefault();
            openModal(form);
        });
    });

    modal.querySelectorAll("[data-voucher-modal-close]").forEach((control) => {
        control.addEventListener("click", closeModal);
    });

    modal.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            event.preventDefault();
            closeModal();
            return;
        }

        if (event.key !== "Tab") return;
        const focusable = Array.from(
            modal.querySelectorAll("button:not([disabled]), a[href], input:not([disabled])")
        );
        if (!focusable.length) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    if (!modal.hidden) {
        document.body.classList.add("voucher-confirm-open");
        modal.querySelector("[data-voucher-modal-close]").focus();
    }
})();
