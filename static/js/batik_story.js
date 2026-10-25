
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
