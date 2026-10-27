
document.addEventListener("DOMContentLoaded", function () {

    // ANIMASI TEKS HERO
    const typingElement = document.getElementById("typing-text");

    if (typingElement) {
        const message = typingElement.textContent.trim();
        const reduceMotion = window.matchMedia(
            "(prefers-reduced-motion: reduce)"
        ).matches;

        if (message && !reduceMotion) {
            typingElement.textContent = "";

            let index = 0;
            let deleting = false;

            function typeWriter() {
                if (!deleting) {
                    index++;
                    typingElement.textContent = message.substring(0, index);

                    if (index >= message.length) {
                        deleting = true;
                        setTimeout(typeWriter, 2400);
                    } else {
                        setTimeout(typeWriter, 65);
                    }
                } else {
                    index--;
                    typingElement.textContent = message.substring(0, index);

                    if (index <= 0) {
                        deleting = false;
                        setTimeout(typeWriter, 650);
                    } else {
                        setTimeout(typeWriter, 30);
                    }
                }
            }

            typeWriter();
        }
    }


    // FITUR FAVORIT
    document.querySelectorAll(".love input").forEach(function (input) {
        input.addEventListener("change", function () {
            const favorite = input.closest(".love");

            if (favorite) {
                favorite.classList.toggle("is-loved", input.checked);
            }
        });
    });


    // SMOOTH SCROLL
    document.querySelectorAll('a[href="#story-section"]').forEach(
        function (link) {
            link.addEventListener("click", function (event) {
                const target = document.getElementById("story-section");

                if (target) {
                    event.preventDefault();

                    const reduceMotion = window.matchMedia(
                        "(prefers-reduced-motion: reduce)"
                    ).matches;

                    target.scrollIntoView({
                        behavior: reduceMotion ? "auto" : "smooth",
                        block: "start"
                    });
                }
            });
        }
    );


    // PENCARIAN MOTIF BATIK

    const searchInput = document.getElementById("story-search-input");
    const searchClear = document.getElementById("story-search-clear");
    const searchStatus = document.getElementById("story-search-status");
    const storyCount = document.getElementById("story-count");
    const emptyState = document.getElementById("story-empty-state");
    const emptyReset = document.getElementById("story-empty-reset");

    const storyCards = Array.from(
        document.querySelectorAll(".story-card")
    );

    function filterStories() {
        if (!searchInput) return;

        const query = searchInput.value
            .trim()
            .toLocaleLowerCase("id-ID");

        let visibleCount = 0;

        storyCards.forEach(function (card) {
            const title = card.querySelector(".card-title h3");
            const description = card.querySelector(".card-description");
            const location = card.querySelector(".card-meta");
            const searchableText = [
                title?.textContent || "",
                description?.textContent || "",
                location?.textContent || ""
            ].join(" ").toLocaleLowerCase("id-ID");
            const matches = searchableText.includes(query);
            card.hidden = !matches;
            if (matches) visibleCount++;
        });

        if (storyCount) {
            storyCount.textContent = query
                ? `${visibleCount} dari ${storyCards.length} Cerita`
                : `${storyCards.length} Cerita`;
        }

        if (searchStatus) {
            searchStatus.textContent = query
                ? `${visibleCount} cerita ditemukan.`
                : "";
        }

        if (searchClear) {
            searchClear.hidden = !query;
        }

        // Maskot menangis muncul hanya jika pencarian tidak menemukan hasil.
        if (emptyState) {
            emptyState.hidden = !query || visibleCount !== 0;
        }
    }

    if (searchInput) {
        searchInput.addEventListener("input", filterStories);
    }

    if (searchClear && searchInput) {
        searchClear.addEventListener("click", function () {
            searchInput.value = "";
            filterStories();
            searchInput.focus();
        });
        searchClear.hidden = true;
    }

    if (emptyReset && searchInput) {
        emptyReset.addEventListener("click", function () {
            searchInput.value = "";
            filterStories();
            searchInput.focus();
        });
    }

    // MODAL BACA CERITA
    const modal = document.getElementById("story-modal");
    const content = document.getElementById("story-modal-content");
    const closeButton = document.getElementById("story-modal-close");
    function closeModal() {
        if (modal?.open) {
            modal.close();
        }
    }

    if (modal && content) {
        document.querySelectorAll(
            ".story-button[data-story-url]"
        ).forEach(function (button) {
            button.addEventListener("click", async function () {
                const url = button.dataset.storyUrl;
                if (!url || button.disabled) return;
                modal.showModal();
                content.innerHTML =
                    "<p class='story-modal-loading'>Memuat cerita...</p>";

                try {
                    const response = await fetch(url, {
                        headers: {
                            "X-Requested-With": "XMLHttpRequest"
                        }
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}`);
                    }
                    content.innerHTML = await response.text();
                } catch (error) {
                    console.error("Gagal memuat cerita:", error);
                    content.innerHTML =
                        "<p class='story-modal-error'>Cerita gagal dimuat. Silakan coba kembali.</p>";
                }
            });
        });

        if (closeButton) {
            closeButton.addEventListener("click", closeModal);
        }

        modal.addEventListener("click", function (event) {
            if (event.target === modal) {
                closeModal();
            }
        });
    }
});
