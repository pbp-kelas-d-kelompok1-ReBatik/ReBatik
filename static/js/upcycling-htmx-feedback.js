(() => {
    const updateStatusTabs = (selectedStatus) => {
        document.querySelectorAll("[data-status-filter]").forEach((link) => {
            const tabStatus = link.dataset.statusFilter;
            const active = tabStatus
                ? tabStatus === selectedStatus
                : selectedStatus !== "ONGOING" && selectedStatus !== "COMPLETED";

            link.setAttribute("aria-current", active ? "page" : "false");
            link.classList.toggle("bg-[var(--brown)]", active);
            link.classList.toggle("font-bold", active);
            link.classList.toggle("text-[var(--cream-light)]", active);
            link.classList.toggle("ring-1", active);
            link.classList.toggle("ring-[var(--gold)]", active);
            link.classList.toggle("text-[var(--brown)]", !active);
            link.classList.toggle("hover:bg-[var(--upcycling-soft)]", !active);
        });
    };

    const getFeedbackRegion = (event) => {
        const trigger = event.detail?.elt;
        const page = trigger?.closest("#upcycling-page-content");
        return page?.querySelector("[data-htmx-feedback]")
            || document.querySelector("[data-htmx-feedback]");
    };

    const clearFeedback = (event) => {
        const region = getFeedbackRegion(event);
        if (!region) return;
        region.textContent = "";
        region.classList.add("hidden");
    };

    const showFeedback = (event) => {
        const region = getFeedbackRegion(event);
        if (!region) return;
        region.textContent = "Permintaan gagal diproses. Periksa koneksi lalu coba lagi.";
        region.classList.remove("hidden");
    };

    document.body.addEventListener("htmx:beforeRequest", clearFeedback);
    document.body.addEventListener("htmx:responseError", showFeedback);
    document.body.addEventListener("htmx:sendError", showFeedback);

    document.body.addEventListener("click", (event) => {
        const deleteDialog = document.getElementById("delete-request-dialog");
        const openDeleteDialog = event.target.closest("[data-open-delete-dialog]");
        if (openDeleteDialog && deleteDialog?.showModal) {
            event.preventDefault();
            deleteDialog.showModal();
            deleteDialog.querySelector("[data-close-delete-dialog]")?.focus();
        }

        if (event.target.closest("[data-close-delete-dialog]")) {
            deleteDialog?.close();
        }

        if (deleteDialog && event.target === deleteDialog) {
            deleteDialog.close();
        }

        const filterPanel = document.getElementById("upcycling-extra-filters");
        if (filterPanel?.open && !filterPanel.contains(event.target)) {
            filterPanel.open = false;
        }

        const statusLink = event.target.closest("[data-status-filter]");
        const statusField = document.getElementById("filter-status");
        if (statusLink && statusField) {
            statusField.value = statusLink.dataset.statusFilter;
            updateStatusTabs(statusField.value);
        }

        const resetLink = event.target.closest("[data-reset-filters]");
        if (resetLink) {
            const form = document.getElementById("upcycling-extra-filter-form");
            if (form) {
                form.elements.status.value = "";
                form.elements.category.value = "";
                form.elements.q.value = "";
                form.elements.from.value = "";
                form.elements.to.value = "";
                form.elements.order.value = "newest";
                updateStatusTabs("");
            }
        }
    });

    document.body.addEventListener("change", (event) => {
        if (event.target.matches("#filter-status")) {
            updateStatusTabs(event.target.value);
        }
    });

    document.body.addEventListener("keydown", (event) => {
        const filterPanel = document.getElementById("upcycling-extra-filters");
        if (event.key === "Escape" && filterPanel?.open) {
            filterPanel.open = false;
            filterPanel.querySelector("summary")?.focus();
        }
    });
})();
