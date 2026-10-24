document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upcycling-form");
    const errorSummary = document.getElementById("form-error-summary");
    if (errorSummary) {
        errorSummary.focus({ preventScroll: true });
        errorSummary.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    const errorList = document.getElementById("form-error-list");
    const validationMessages = {
        fabric: ["Kain", "Pilih kain yang ingin digunakan."],
        category: ["Kategori produk", "Pilih kategori produk."],
        product: ["Model produk", "Pilih model produk."],
        custom_product: ["Produk yang diinginkan", "Tuliskan produk yang Anda inginkan."],
        quantity: ["Jumlah produk", "Masukkan jumlah antara 1 dan 20."],
        delivery_method: ["Metode pengiriman", "Pilih metode pengiriman kain."],
        address: ["Alamat / Lokasi", "Isi alamat atau lokasi penyerahan kain."],
        whatsapp: ["No. WhatsApp", "Masukkan nomor HP Indonesia yang valid, misalnya +6281234567890."],
    };
    const validationTargets = {
        fabric: "#pilih-kain",
        category: "#pilih-produk",
        product: "#product-options",
        custom_product: "#id_custom_product",
        quantity: "#id_quantity",
        delivery_method: "#metode-pengiriman",
        address: "#id_address",
        whatsapp: "#id_whatsapp",
    };

    document.querySelectorAll("[data-error-field]").forEach((link) => {
        const target = validationTargets[link.dataset.errorField];
        if (target) link.href = target;
    });

    function showClientValidationErrors() {
        const invalidNames = [...new Set(
            Array.from(form.elements)
                .filter((element) => element.willValidate && !element.validity.valid)
                .map((element) => element.name)
                .filter(Boolean)
        )];

        if (invalidNames.includes("category")) {
            const productIndex = invalidNames.indexOf("product");
            if (productIndex >= 0) {
                invalidNames.splice(productIndex, 1);
            }
        }

        errorList.replaceChildren();
        invalidNames.forEach((name) => {
            const [label, message] = validationMessages[name] || [name, "Periksa kembali isian ini."];
            const item = document.createElement("li");
            const link = document.createElement("a");
            link.className = "underline underline-offset-2 hover:font-bold";
            link.href = validationTargets[name] || "#upcycling-form";
            link.textContent = `${label}: ${message}`;
            item.append(link);
            errorList.append(item);
        });

        errorSummary.classList.remove("hidden");
        errorSummary.focus({ preventScroll: true });
        errorSummary.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    form.addEventListener("invalid", (event) => {
        event.preventDefault();
        window.requestAnimationFrame(showClientValidationErrors);
    }, true);

    const categoryFields = form.querySelectorAll('[name="category"]');
    const fabricFields = form.querySelectorAll('[name="fabric"]');
    const productField = document.getElementById("id_product");
    const productOptions = document.getElementById("product-options");
    const standardProductOptions = document.getElementById("standard-product-options");
    const productOptionsLabel = document.getElementById("product-options-label");
    const customProductField = document.getElementById("id_custom_product");
    const customProductContainer = document.getElementById("custom-product-field");
    const productsByCategory = JSON.parse(
        document.getElementById("product-options-data").textContent
    );
    const fabricSummary = document.getElementById("summary-fabric");
    const categorySummary = document.getElementById("summary-category");
    const productSummary = document.getElementById("summary-product");
    function getRadioLabel(name, fallback) {
        const selectedRadio = form.querySelector(`input[name="${name}"]:checked`);
        const label = selectedRadio?.closest("label");
        return label?.dataset.summaryLabel || label?.querySelector("span")?.textContent.trim() || fallback;
    }

    function updateSummary() {
        fabricSummary.textContent = getRadioLabel("fabric", "Pilih kain");
        categorySummary.textContent = getRadioLabel("category", "Pilih kategori");
        const selectedProduct = productField.selectedOptions[0];
        if (productField.value === "LAINNYA") {
            productSummary.textContent = customProductField.value.trim() || "Isi nama produk";
        } else {
            productSummary.textContent = productField.value && selectedProduct
                ? selectedProduct.textContent
                : "Pilih model";
        }
    }

    function getSelectedCategory() {
        return form.querySelector('input[name="category"]:checked')?.value || "";
    }

    function updateCustomProductField() {
        const isOtherCategory = getSelectedCategory() === "LAINNYA";
        const isCustomProduct = isOtherCategory || productField.value === "LAINNYA";
        standardProductOptions.classList.toggle("hidden", isOtherCategory);
        productOptionsLabel.classList.toggle("hidden", isOtherCategory);
        customProductContainer.classList.toggle("hidden", !isCustomProduct);
        customProductField.required = isCustomProduct;
        customProductField.setAttribute("aria-required", String(isCustomProduct));
        updateSummary();
    }

    function renderProductOptions(products) {
        productOptions.replaceChildren();
        products.forEach((item) => {
            const option = new Option(
                item.label,
                item.value
            );
            productField.add(option);

            const button = document.createElement("button");
            button.type = "button";
            button.className = "upcycling-product-option";
            button.textContent = item.value === "LAINNYA"
                ? "Tulis sendiri"
                : option.textContent;
            button.dataset.productValue = item.value;
            button.setAttribute("aria-pressed", String(item.value === productField.value));
            button.addEventListener("click", () => {
                productField.value = item.value;
                productOptions.querySelectorAll("button").forEach((itemButton) => {
                    itemButton.setAttribute(
                        "aria-pressed",
                        String(itemButton.dataset.productValue === item.value)
                    );
                });
                updateCustomProductField();
            });
            productOptions.append(button);
        });
    }

    function loadProducts(keepSelection = false) {
        const previousProduct = productField.value;
        const category = getSelectedCategory();
        productField.replaceChildren(new Option("Pilih model produk", ""));
        productOptions.replaceChildren();
        updateCustomProductField();

        if (!category) {
            productOptions.textContent = "Pilih kategori untuk melihat model.";
            updateCustomProductField();
            return;
        }

        const products = productsByCategory[category] || [];
        renderProductOptions(products);

        if (category === "LAINNYA") {
            productField.value = "LAINNYA";
            productOptions.querySelectorAll("button").forEach((button) => {
                button.setAttribute("aria-pressed", String(button.dataset.productValue === "LAINNYA"));
            });
            updateCustomProductField();
            return;
        }

        if (keepSelection && products.some((item) => item.value === previousProduct)) {
            productField.value = previousProduct;
            productOptions.querySelectorAll("button").forEach((button) => {
                button.setAttribute("aria-pressed", String(button.dataset.productValue === previousProduct));
            });
        }
        updateCustomProductField();
    }

    fabricFields.forEach((field) => field.addEventListener("change", updateSummary));
    categoryFields.forEach((field) => field.addEventListener("change", () => {
        customProductField.value = "";
        loadProducts();
    }));
    productField.addEventListener("change", () => {
        productOptions.querySelectorAll("button").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.productValue === productField.value));
        });
        updateCustomProductField();
    });
    customProductField.addEventListener("input", updateSummary);
    loadProducts(true);

});
