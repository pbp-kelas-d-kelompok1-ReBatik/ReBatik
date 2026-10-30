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
        fabric: ["Jenis bahan", "Pilih jenis bahan yang paling mendekati."],
        current_item_form: ["Bentuk barang", "Pilih bentuk barang atau kain yang Anda miliki."],
        current_item_form_other: ["Bentuk lainnya", "Sebutkan bentuk barang atau kain."],
        fabric_other_description: ["Bahan lainnya", "Sebutkan bahan lainnya."],
        has_batik_pattern: ["Motif batik", "Pilih apakah barang atau kain sudah memiliki motif batik."],
        fabric_photos: ["Foto barang atau kain", "Unggah 1 sampai 3 foto barang atau kain."],
        reference_photos: ["Foto contoh hasil", "Pilih maksimal 3 gambar referensi."],
        fabric_condition: ["Kondisi barang atau kain", "Pilih kondisi barang atau kain jika diketahui."],
        fabric_dimensions: ["Jumlah barang atau bahan", "Isi perkiraan jumlah barang atau bahan yang ingin diolah."],
        category: ["Kategori produk", "Pilih kategori produk."],
        product: ["Produk yang ingin dibuat", "Pilih produk yang ingin dibuat."],
        custom_product: ["Produk yang diinginkan", "Tuliskan produk yang Anda inginkan."],
        quantity: ["Jumlah produk", "Masukkan jumlah antara 1 dan 20."],
        whatsapp: ["Nomor WhatsApp", "Masukkan nomor HP Indonesia yang valid, misalnya +6281234567890."],
    };
    const validationTargets = {
        fabric: "#pilih-kain",
        current_item_form: "#current-item-form-options",
        current_item_form_other: "#id_current_item_form_other",
        fabric_other_description: "#id_fabric_other_description",
        has_batik_pattern: "#has-batik-pattern",
        fabric_photos: "#id_fabric_photos",
        reference_photos: "#id_reference_photos",
        fabric_condition: "#id_fabric_condition",
        fabric_dimensions: "#id_fabric_dimensions",
        category: "#pilih-produk",
        product: "#product-options",
        custom_product: "#id_custom_product",
        quantity: "#id_quantity",
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

    const fabricPhotoField = document.getElementById("id_fabric_photos");
    const fabricPhotoPreview = document.getElementById("fabric-photo-preview");
    const fabricPhotoPlaceholder = document.getElementById("fabric-photo-placeholder");
    const fabricPhotoMascot = document.getElementById("fabric-photo-mascot");
    const fabricPhotoChangeLabel = document.getElementById("fabric-photo-change-label");
    const fabricPhotoCount = document.getElementById("fabric-photo-count");
    let fabricPhotoPreviewUrl = null;
    fabricPhotoField?.addEventListener("change", () => {
        const photos = Array.from(fabricPhotoField.files);
        if (!photos.length) return;
        const photo = photos[0];
        if (!photo.type.startsWith("image/")) return;

        if (fabricPhotoPreviewUrl) URL.revokeObjectURL(fabricPhotoPreviewUrl);
        fabricPhotoPreviewUrl = URL.createObjectURL(photo);
        fabricPhotoPreview.src = fabricPhotoPreviewUrl;
        fabricPhotoPreview.classList.remove("hidden");
        fabricPhotoPlaceholder.classList.add("hidden");
        fabricPhotoMascot.classList.add("hidden");
        fabricPhotoChangeLabel.classList.remove("hidden");
        fabricPhotoCount.textContent = `${photos.length} foto dipilih. Maksimal 3 foto.`;
        fabricPhotoCount.classList.remove("hidden");
    });

    const referencePhotoField = document.getElementById("id_reference_photos");
    const referencePhotoPlaceholder = document.getElementById("reference-photo-placeholder");
    const referencePhotoMascot = document.getElementById("reference-photo-mascot");
    const referencePhotoPreviews = document.getElementById("reference-photo-previews");
    const referencePhotoCount = document.getElementById("reference-photo-count");
    let referencePhotoPreviewUrls = [];
    referencePhotoField?.addEventListener("change", () => {
        const photos = Array.from(referencePhotoField.files).filter((photo) => photo.type.startsWith("image/"));
        referencePhotoPreviewUrls.forEach((url) => URL.revokeObjectURL(url));
        referencePhotoPreviewUrls = [];
        referencePhotoPreviews.replaceChildren();
        if (!photos.length) {
            referencePhotoPreviews.classList.add("hidden");
            referencePhotoPreviews.classList.remove("grid");
            referencePhotoPlaceholder.classList.remove("hidden");
            referencePhotoMascot.classList.remove("hidden");
            referencePhotoCount.classList.add("hidden");
            return;
        }
        photos.forEach((photo) => {
            const image = document.createElement("img");
            const url = URL.createObjectURL(photo);
            referencePhotoPreviewUrls.push(url);
            image.src = url;
            image.alt = "Pratinjau foto referensi";
            image.className = "h-full min-h-0 w-full rounded-lg object-cover";
            referencePhotoPreviews.append(image);
        });
        referencePhotoPreviews.classList.remove("hidden");
        referencePhotoPreviews.classList.add("grid");
        referencePhotoPlaceholder.classList.add("hidden");
        referencePhotoMascot.classList.add("hidden");
        referencePhotoCount.textContent = `${photos.length} foto referensi dipilih. Maksimal 3 foto.`;
        referencePhotoCount.classList.remove("hidden");
    });

    const categoryFields = form.querySelectorAll('[name="category"]');
    const fabricFields = form.querySelectorAll('[name="fabric"]');
    const currentItemFormFields = form.querySelectorAll('[name="current_item_form"]');
    const currentItemFormOther = document.getElementById("id_current_item_form_other");
    const otherItemFormContainer = document.getElementById("other-item-form-field");
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
    const itemFormSummary = document.getElementById("summary-item-form");
    const patternSummary = document.getElementById("summary-pattern");
    const categorySummary = document.getElementById("summary-category");
    const productSummary = document.getElementById("summary-product");
    const batikSummary = document.getElementById("summary-batik");
    const batikAccentToggle = document.getElementById("id_wants_batik_accent");
    const batikAccentFields = document.getElementById("batik-accent-fields");
    const batikPreferenceFields = [
        document.getElementById("id_batik_motif"),
        document.getElementById("id_motif_placement"),
    ];
    function getRadioLabel(name, fallback) {
        const selectedRadio = form.querySelector(`input[name="${name}"]:checked`);
        const label = selectedRadio?.closest("label");
        return label?.dataset.summaryLabel || label?.querySelector("span")?.textContent.trim() || fallback;
    }

    function updateSummary() {
        const selectedItemForm = form.querySelector('input[name="current_item_form"]:checked')?.value;
        itemFormSummary.textContent = selectedItemForm === "OTHER" && currentItemFormOther.value.trim()
            ? currentItemFormOther.value.trim()
            : getRadioLabel("current_item_form", "Pilih bentuk barang");
        const selectedFabric = form.querySelector('input[name="fabric"]:checked')?.value;
        const selectedFabricLabel = getRadioLabel("fabric", "Pilih kain");
        fabricSummary.textContent = selectedFabric === "OTHER" && otherFabricField.value.trim()
            ? `${selectedFabricLabel}: ${otherFabricField.value.trim()}`
            : selectedFabricLabel;
        patternSummary.textContent = getRadioLabel(
            "has_batik_pattern",
            "Motif batik belum dipilih"
        );
        categorySummary.textContent = getRadioLabel("category", "Pilih kategori produk");
        const selectedProduct = productField.selectedOptions[0];
        if (productField.value === "LAINNYA") {
            productSummary.textContent = customProductField.value.trim() || "Isi nama produk";
        } else {
            productSummary.textContent = productField.value && selectedProduct
                ? selectedProduct.textContent
                : "Pilih model produk";
        }
        if (batikAccentToggle.checked) {
            const motif = batikPreferenceFields[0].value.trim();
            batikSummary.textContent = motif
                ? `Tambahan batik: ${motif}`
                : "Tambahan batik diminta";
        } else {
            batikSummary.textContent = "Tanpa tambahan batik";
        }
    }

    function updateOtherItemFormField() {
        const isOtherItemForm = form.querySelector('input[name="current_item_form"]:checked')?.value === "OTHER";
        otherItemFormContainer.classList.toggle("hidden", !isOtherItemForm);
        currentItemFormOther.required = isOtherItemForm;
        currentItemFormOther.setAttribute("aria-required", String(isOtherItemForm));
        if (!isOtherItemForm) currentItemFormOther.value = "";
        updateSummary();
    }

    function updateBatikAccentFields() {
        const isRequested = batikAccentToggle.checked;
        batikAccentFields.classList.toggle("hidden", !isRequested);
        if (!isRequested) {
            batikPreferenceFields.forEach((field) => {
                field.value = "";
            });
        }
        updateSummary();
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
    currentItemFormFields.forEach((field) => field.addEventListener("change", updateOtherItemFormField));
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
    currentItemFormOther.addEventListener("input", updateSummary);
    batikAccentToggle.addEventListener("change", updateBatikAccentFields);
    batikPreferenceFields.forEach((field) => {
        field.addEventListener("input", updateSummary);
    });
    updateBatikAccentFields();
    updateOtherItemFormField();
    updateOtherFabricField();
    loadProducts(true);

};

document.addEventListener("DOMContentLoaded", () => initializeUpcyclingForm());
document.body.addEventListener("htmx:afterSwap", initializeUpcyclingForm);
