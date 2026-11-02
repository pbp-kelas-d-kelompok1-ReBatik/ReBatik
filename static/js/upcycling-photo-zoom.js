(() => {
    /** Connect the photo gallery dialog once; do nothing until its controls exist. */
    function initializePhotoZoom() {
        const dialog = document.getElementById("artisan-photo-zoom");
        const preview = document.getElementById("artisan-photo-zoom-image");
        const counter = document.getElementById("artisan-photo-zoom-counter");
        const closeButton = document.getElementById("artisan-photo-zoom-close");
        const previousButton = document.getElementById("artisan-photo-zoom-previous");
        const nextButton = document.getElementById("artisan-photo-zoom-next");
        if (
            !dialog
            || dialog.dataset.zoomInitialized
            || !preview
            || !counter
            || !closeButton
            || !previousButton
            || !nextButton
        ) return;
        dialog.dataset.zoomInitialized = "true";

        let gallery = [];
        let activeIndex = 0;

        function showPhoto(index) {
            activeIndex = (index + gallery.length) % gallery.length;
            const button = gallery[activeIndex];
            preview.src = button.dataset.photoSrc;
            preview.alt = button.dataset.photoAlt || "Foto kain";
            counter.textContent = `Foto ${activeIndex + 1} dari ${gallery.length}`;
            const hasMultiplePhotos = gallery.length > 1;
            previousButton.disabled = !hasMultiplePhotos;
            nextButton.disabled = !hasMultiplePhotos;
            previousButton.classList.toggle("opacity-40", !hasMultiplePhotos);
            nextButton.classList.toggle("opacity-40", !hasMultiplePhotos);
        }

        document.querySelectorAll("[data-fabric-photo-zoom]").forEach((button) => {
            button.addEventListener("click", () => {
                const galleryId = button.dataset.fabricPhotoZoom;
                gallery = Array.from(
                    document.querySelectorAll("[data-fabric-photo-zoom]")
                ).filter((photoButton) => photoButton.dataset.fabricPhotoZoom === galleryId);
                showPhoto(gallery.indexOf(button));
                dialog.showModal();
                closeButton.focus();
            });
        });

        previousButton.addEventListener("click", () => showPhoto(activeIndex - 1));
        nextButton.addEventListener("click", () => showPhoto(activeIndex + 1));
        closeButton.addEventListener("click", () => dialog.close());
        dialog.addEventListener("click", (event) => {
            if (event.target === dialog) dialog.close();
        });
        dialog.addEventListener("keydown", (event) => {
            if (event.key === "ArrowLeft" && gallery.length > 1) showPhoto(activeIndex - 1);
            if (event.key === "ArrowRight" && gallery.length > 1) showPhoto(activeIndex + 1);
        });
    }

    initializePhotoZoom();
    document.body.addEventListener("htmx:afterSwap", initializePhotoZoom);
})();
