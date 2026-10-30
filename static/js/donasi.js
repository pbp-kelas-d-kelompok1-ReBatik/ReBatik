
document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("donasiForm");
    const photoInput = document.querySelector(
        '.donasi-file-input, input[type="file"]'
    );
    const previewImage = document.getElementById("photoPreviewImage");
    const placeholder = document.getElementById("photoPlaceholder");
    const submitButton = document.getElementById("donasiSubmit");

    const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
    let previewUrl = null;

    // Tampilkan pratinjau foto sebelum formulir dikirim.
    if (photoInput) {
        photoInput.addEventListener("change", function () {
            const file = photoInput.files[0];

            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
                previewUrl = null;
            }

            if (!file) {
                if (previewImage) {
                    previewImage.removeAttribute("src");
                    previewImage.hidden = true;
                }

                if (placeholder) {
                    placeholder.hidden = false;
                    placeholder.textContent =
                        "Pilih foto barang yang akan didonasikan";
                }

                return;
            }

            // Pastikan file yang dipilih merupakan gambar.
            if (!file.type.startsWith("image/")) {
                alert("Pilih file gambar yang valid.");

                photoInput.value = "";
                resetPreview();
                return;
            }

            // Periksa ukuran file.
            if (file.size > MAX_FILE_SIZE) {
                alert("Ukuran foto maksimal 5 MB.");

                photoInput.value = "";
                resetPreview();
                return;
            }

            // Buat URL lokal untuk pratinjau.
            if (previewImage) {
                previewUrl = URL.createObjectURL(file);

                previewImage.src = previewUrl;
                previewImage.hidden = false;
            }

            if (placeholder) {
                placeholder.hidden = true;
            }
        });
    }

    function resetPreview() {
        if (previewImage) {
            previewImage.removeAttribute("src");
            previewImage.hidden = true;
        }

        if (placeholder) {
            placeholder.hidden = false;
            placeholder.textContent =
                "Pilih foto barang yang akan didonasikan";
        }

        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
    }

    // Beri umpan balik saat formulir dikirim.
    // Validasi HTML dan Django tetap berjalan seperti biasa.
    if (form) {
        form.addEventListener("submit", function (event) {
            if (!form.checkValidity()) {
                return;
            }

            if (photoInput && photoInput.files.length > 0) {
                const file = photoInput.files[0];

                if (
                    !file.type.startsWith("image/") ||
                    file.size > MAX_FILE_SIZE
                ) {
                    event.preventDefault();

                    alert(
                        "Periksa kembali foto. File harus berupa gambar " +
                        "dengan ukuran maksimal 5 MB."
                    );

                    return;
                }
            }

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "Mengirim...";
            }
        });
    }

    // Bersihkan URL pratinjau saat halaman ditinggalkan.
    window.addEventListener("pagehide", function () {
        if (previewUrl) {
            URL.revokeObjectURL(previewUrl);
            previewUrl = null;
        }
    });
});
