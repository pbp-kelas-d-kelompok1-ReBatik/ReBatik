document.addEventListener("DOMContentLoaded", function () {

    const typingElement = document.getElementById("typing-text");

    if (typingElement) {
        const message = typingElement.textContent.trim();

        if (message) {
            typingElement.textContent = "";

            let index = 0;
            let deleting = false;

            function typeWriter() {
                if (window.matchMedia(
                    "(prefers-reduced-motion: reduce)"
                ).matches) {
                    typingElement.textContent = message;
                    return;
                }

                if (!deleting) {
                    index++;
                    typingElement.textContent =
                        message.substring(0, index);

                    if (index >= message.length) {
                        deleting = true;
                        setTimeout(typeWriter, 2400);
                    } else {
                        setTimeout(typeWriter, 65);
                    }
                } else {
                    index--;
                    typingElement.textContent =
                        message.substring(0, index);

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


    document.querySelectorAll(".love input").forEach(function (input) {
        input.addEventListener("change", function () {
            const favorite = input.closest(".love");

            if (favorite) {
                favorite.classList.toggle(
                    "is-loved",
                    input.checked
                );
            }
        });
    });


    document.querySelectorAll('a[href="#story-section"]').forEach(
        function (link) {
            link.addEventListener("click", function (event) {
                const target = document.getElementById("story-section");

                if (target) {
                    event.preventDefault();

                    target.scrollIntoView({
                        behavior: window.matchMedia(
                            "(prefers-reduced-motion: reduce)"
                        ).matches ? "auto" : "smooth",
                        block: "start"
                    });
                }
            });
        }
    );

});


document.addEventListener("DOMContentLoaded", function () {
    const modal = document.getElementById("story-modal");
    const modalContent = document.getElementById("story-modal-content");
    const closeButton = document.getElementById("story-modal-close");

    if (!modal || !modalContent) {
        console.error("Modal cerita batik tidak ditemukan.");
        return;
    }

    document.querySelectorAll(".story-button[data-story-url]").forEach(function (button) {
        button.addEventListener("click", async function () {
            const url = button.dataset.storyUrl;

            modalContent.innerHTML = "<p>Memuat cerita batik...</p>";
            modal.showModal();

            try {
                const response = await fetch(url);

                if (!response.ok) {
                    throw new Error("HTTP " + response.status);
                }

                modalContent.innerHTML = await response.text();
            } catch (error) {
                console.error("Gagal memuat cerita:", error);
                modalContent.innerHTML =
                    "<p>Cerita gagal dimuat. Silakan periksa URL dan server Django.</p>";
            }
        });
    });

    if (closeButton) {
        closeButton.addEventListener("click", function () {
            modal.close();
        });
    }

    modal.addEventListener("click", function (event) {
        if (event.target === modal) {
            modal.close();
        }
    });
});
