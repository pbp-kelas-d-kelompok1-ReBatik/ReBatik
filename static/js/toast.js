let toastTimer = null;
let toastHideTimer = null;

function showToast(title, message, type = "normal", duration = 3500) {
    const toast = document.getElementById("toast-component");
    const toastTitle = document.getElementById("toast-title");
    const toastMessage = document.getElementById("toast-message");
    const toastMascot = document.getElementById("toast-mascot");

    if (!toast || !toastTitle || !toastMessage) {
        console.warn("Toast component tidak ditemukan. Pastikan base.html memuat components/toast.html.");
        return;
    }

    clearTimeout(toastTimer);
    clearTimeout(toastHideTimer);

    toast.classList.remove("toast-success", "toast-error", "toast-normal");
    toast.classList.add(
        type === "success" ? "toast-success" :
        type === "error" ? "toast-error" : "toast-normal"
    );

    if (toastMascot) {
        toastMascot.src = type === "error"
            ? "/static/img/mascot/crying.webp"
            : type === "success"
                ? "/static/img/mascot/happy.webp"
                : "/static/img/mascot/pointing.webp";
        toastMascot.alt = type === "error" ? "Maskot ReBatik memberi tanda perhatian" : "Maskot ReBatik";
    }

    toastTitle.textContent = title;
    toastMessage.textContent = message;

    if (typeof toast.showPopover === "function") {
        if (!toast.matches(":popover-open")) toast.showPopover();
    } else {
        toast.hidden = false;
    }

    requestAnimationFrame(() => {
        toast.classList.remove("toast-hidden");
        toast.classList.add("toast-show");
    });

    toastTimer = setTimeout(() => {
        toast.classList.remove("toast-show");
        toast.classList.add("toast-hidden");
        toastHideTimer = setTimeout(() => {
            if (typeof toast.hidePopover === "function") {
                if (toast.matches(":popover-open")) toast.hidePopover();
            } else {
                toast.hidden = true;
            }
        }, 250);
    }, duration);
}

window.showToast = showToast;
