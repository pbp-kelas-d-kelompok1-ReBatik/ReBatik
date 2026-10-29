const initializeUpcyclingForm = () => {
    const form = document.getElementById("upcycling-form");
    if (!form) return;
    const errorSummary = document.getElementById("form-error-summary");
    if (errorSummary) {
        errorSummary.focus({ preventScroll: true });
        errorSummary.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    const errorList = document.getElementById("form-error-list");
    const validationMessages = {
        fabric: ["Kain", "Pilih kain yang ingin digunakan."],
        fabric_other_description: ["Jenis kain lainnya", "Tuliskan jenis kain yang akan digunakan."],
        fabric_photo: ["Foto kain", "Unggah foto kain yang akan diolah."],
        fabric_condition: ["Kondisi kain", "Pilih kondisi kain jika diketahui."],
        fabric_dimensions: ["Ukuran kain", "Isi perkiraan ukuran atau jumlah kain."],
        category: ["Kategori produk", "Pilih kategori produk."],
        product: ["Model produk", "Pilih model produk."],
        custom_product: ["Produk yang diinginkan", "Tuliskan produk yang Anda inginkan."],
        quantity: ["Jumlah produk", "Masukkan jumlah antara 1 dan 20."],
        delivery_method: [
            "Metode penerimaan produk",
            "Pilih cara menerima produk jadi.",
        ],
        address: [
            "Alamat / Lokasi Penerimaan Produk",
            "Isi alamat pengiriman atau lokasi pengambilan produk.",
        ],
        whatsapp: ["Nomor WhatsApp", "Masukkan nomor HP Indonesia yang valid, misalnya +6281234567890."],
    };
    const validationTargets = {
        fabric: "#pilih-kain",
        fabric_other_description: "#id_fabric_other_description",
        fabric_photo: "#id_fabric_photo",
        fabric_condition: "#id_fabric_condition",
        fabric_dimensions: "#id_fabric_dimensions",
        category: "#pilih-produk",
        product: "#product-options",
        custom_product: "#id_custom_product",
        quantity: "#id_quantity",
        delivery_method: "#metode-pengiriman",
        address: "#id_address",
        whatsapp: "#id_whatsapp",
    };
    const deliveryMethodFields = form.querySelectorAll('[name="delivery_method"]');
    const addressField = document.getElementById("id_address");
    const addressLabel = document.getElementById("address-label");
    const addressHelp = document.getElementById("address-help");

    function updateAddressDetails() {
        const selectedMethod = form.querySelector(
            'input[name="delivery_method"]:checked'
        )?.value;
        const dataPrefix = selectedMethod === "KURIR"
            ? "kurir"
            : selectedMethod === "DROP_OFF"
                ? "dropOff"
                : "default";
        const label = addressField.dataset[`${dataPrefix}Label`];
        const placeholder = addressField.dataset[`${dataPrefix}Placeholder`];
        const helpText = addressField.dataset[`${dataPrefix}HelpText`];
        const requiredMessage = addressField.dataset[`${dataPrefix}RequiredMessage`];

        addressLabel.textContent = label;
        addressField.placeholder = placeholder;
        addressHelp.textContent = helpText;
        validationMessages.address = [label, requiredMessage];
    }

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
    const otherFabricField = document.getElementById("id_fabric_other_description");
    const otherFabricContainer = document.getElementById("other-fabric-field");
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
        const selectedFabric = form.querySelector('input[name="fabric"]:checked')?.value;
        const selectedFabricLabel = getRadioLabel("fabric", "Pilih kain");
        fabricSummary.textContent = selectedFabric === "OTHER" && otherFabricField.value.trim()
            ? `${selectedFabricLabel}: ${otherFabricField.value.trim()}`
            : selectedFabricLabel;
        categorySummary.textContent = getRadioLabel("category", "Pilih kategori produk");
        const selectedProduct = productField.selectedOptions[0];
        if (productField.value === "LAINNYA") {
            productSummary.textContent = customProductField.value.trim() || "Isi nama produk";
        } else {
            productSummary.textContent = productField.value && selectedProduct
                ? selectedProduct.textContent
                : "Pilih model produk";
        }
    }

    function updateOtherFabricField() {
        const isOtherFabric = form.querySelector('input[name="fabric"]:checked')?.value === "OTHER";
        otherFabricContainer.classList.toggle("hidden", !isOtherFabric);
        otherFabricField.required = isOtherFabric;
        otherFabricField.setAttribute("aria-required", String(isOtherFabric));
        if (!isOtherFabric) otherFabricField.value = "";
        updateSummary();
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
            productOptions.textContent = "Pilih kategori produk untuk melihat model produk.";
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

    fabricFields.forEach((field) => field.addEventListener("change", updateOtherFabricField));
    deliveryMethodFields.forEach((field) => {
        field.addEventListener("change", updateAddressDetails);
    });
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
    otherFabricField.addEventListener("input", updateSummary);
    updateAddressDetails();
    updateOtherFabricField();
    loadProducts(true);

};

document.addEventListener("DOMContentLoaded", () => initializeUpcyclingForm());
document.body.addEventListener("htmx:afterSwap", initializeUpcyclingForm);
