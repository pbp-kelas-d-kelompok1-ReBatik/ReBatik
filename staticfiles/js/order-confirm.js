
document.addEventListener("DOMContentLoaded", function () {
    const form = document.querySelector(".order-form");
    const modal = document.getElementById("orderConfirmModal");

    // Hentikan jika halaman ini tidak memiliki form atau modal.
    if (!form || !modal) {
        console.warn("ReBatik: form atau modal konfirmasi tidak ditemukan.");
        return;
    }

    const confirmBtn = document.getElementById("confirmOrderBtn");
    const cancelBtn = document.getElementById("cancelOrderBtn");
    const closeBtn = document.getElementById("closeOrderModal");
    const backdrop = modal.querySelector(".order-confirm-backdrop");
    const submitBtn = form.querySelector('button[type="submit"]');

    if (!confirmBtn || !cancelBtn || !closeBtn || !backdrop) {
        console.error("ReBatik: elemen tombol popup tidak lengkap.");
        return;
    }

    let confirmed = false;
    let submitting = false;

    // Membuka popup konfirmasi.
    function openModal() {
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        confirmBtn.focus();
    }

    // Menutup popup konfirmasi.
    function closeModal() {
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
    }

    // Menampilkan pesan jika ada input yang belum valid.
    function showFormError(field) {
        const wrapper = field.closest(".order-field-wrap");

        if (wrapper) {
            wrapper.classList.add("has-error");
        }

        if (typeof window.showToast === "function") {
            window.showToast(
                "Data Belum Lengkap",
                field.validationMessage ||
                    "Mohon lengkapi kolom yang wajib diisi.",
                "error",
                4500
            );
        } else {
            field.reportValidity();
        }

        field.focus();
        field.scrollIntoView({
            behavior: "smooth",
            block: "center"
        });
    }

    // Tahan pengiriman form sampai pengguna menyetujui popup.
    form.addEventListener("submit", function (event) {
        if (confirmed) {
            return;
        }

        event.preventDefault();

        if (!form.checkValidity()) {
            const invalidField = form.querySelector(":invalid");

            if (invalidField) {
                showFormError(invalidField);
            }

            return;
        }

        openModal();
    });

    // Pengguna menyetujui pesanan.
    confirmBtn.addEventListener("click", function () {
        if (submitting) {
            return;
        }

        submitting = true;
        confirmed = true;

        confirmBtn.disabled = true;
        confirmBtn.textContent = "Memproses Pesanan...";

        closeModal();

        // Kirim form setelah persetujuan diberikan.
        if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
        } else {
            form.submit();
        }
    });

    // Pengguna membatalkan konfirmasi.
    function cancelConfirmation() {
        if (submitting) {
            return;
        }

        closeModal();

        if (submitBtn) {
            submitBtn.focus();
        }
    }

    cancelBtn.addEventListener("click", cancelConfirmation);
    closeBtn.addEventListener("click", cancelConfirmation);
    backdrop.addEventListener("click", cancelConfirmation);

    // Tutup popup dengan tombol Escape.
    document.addEventListener("keydown", function (event) {
        if (
            event.key === "Escape" &&
            modal.classList.contains("is-open")
        ) {
            cancelConfirmation();
        }
    });

    // Hapus tanda error ketika input diperbaiki.
    form.querySelectorAll("input, select, textarea").forEach(function (field) {
        function clearError() {
            if (field.checkValidity()) {
                const wrapper = field.closest(".order-field-wrap");

                if (wrapper) {
                    wrapper.classList.remove("has-error");
                }
            }
        }

        field.addEventListener("input", clearError);
        field.addEventListener("change", clearError);
    });

    console.log("ReBatik: JavaScript konfirmasi pesanan aktif.");
});
