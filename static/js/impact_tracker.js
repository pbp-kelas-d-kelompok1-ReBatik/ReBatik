
/* ReBatik Impact Tracker - interaksi tanpa dependency eksternal. */
(function () {
    "use strict";

    // 1. Animasi angka statistik
    function initCountUp() {
        const counters = document.querySelectorAll("[data-count-up]");
        if (!counters.length) return;

        const formatter = new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 0
        });

        function animateCounter(element) {
            if (element.dataset.animated === "true") return;

            const raw = (element.textContent || "").trim();
            const target = Number(raw.replace(/[^0-9-]/g, ""));

            if (!Number.isFinite(target) || target < 0) return;

            element.dataset.animated = "true";

            if (
                window.matchMedia(
                    "(prefers-reduced-motion: reduce)"
                ).matches
            ) {
                element.textContent = formatter.format(target);
                return;
            }

            const duration = 850;
            const startTime = performance.now();

            function frame(now) {
                const progress = Math.min(
                    (now - startTime) / duration,
                    1
                );

                const eased = 1 - Math.pow(1 - progress, 3);

                element.textContent = formatter.format(
                    Math.round(target * eased)
                );

                if (progress < 1) {
                    window.requestAnimationFrame(frame);
                }
            }

            window.requestAnimationFrame(frame);
        }

        if (!("IntersectionObserver" in window)) {
            counters.forEach(animateCounter);
            return;
        }

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        animateCounter(entry.target);
                        observer.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.35 }
        );

        counters.forEach((counter) => observer.observe(counter));
    }

    // 2. Animasi batang grafik
    function initChartBars() {
        const bars = document.querySelectorAll(".impact-chart__seg");
        if (!bars.length) return;

        bars.forEach((bar) => {
            const finalHeight = bar.style.height;
            bar.dataset.finalHeight = finalHeight || "0%";
            bar.style.height = "0%";
        });

        function reveal() {
            bars.forEach((bar, index) => {
                window.setTimeout(() => {
                    bar.style.height = bar.dataset.finalHeight;
                }, Math.min(index * 18, 360));
            });
        }

        if (
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches
        ) {
            bars.forEach((bar) => {
                bar.style.height = bar.dataset.finalHeight;
            });
            return;
        }

        if (!("IntersectionObserver" in window)) {
            reveal();
            return;
        }

        const chart = document.querySelector(".impact-chart");
        if (!chart) return;

        const observer = new IntersectionObserver(
            (entries) => {
                if (entries.some((entry) => entry.isIntersecting)) {
                    reveal();
                    observer.disconnect();
                }
            },
            { threshold: 0.15 }
        );

        observer.observe(chart);
    }

    // 3. Pencarian aktivitas tanpa reload halaman
    function initActivitySearch() {
        const input = document.getElementById("impactActivitySearch");
        const list = document.getElementById("impactActivityList");
        const noResults = document.getElementById(
            "impactActivityNoResults"
        );
        const hint = document.querySelector(
            ".impact-activity-search-hint"
        );

        if (!input || !list) return;

        const items = Array.from(
            list.querySelectorAll("[data-activity-item]")
        );

        const normalize = (value) =>
            value.toLocaleLowerCase("id-ID").trim();

        input.addEventListener("input", function () {
            const query = normalize(input.value);
            let visible = 0;

            items.forEach((item) => {
                const matches = normalize(
                    item.textContent || ""
                ).includes(query);

                item.hidden = !matches;

                if (matches) visible += 1;
            });

            if (noResults) {
                noResults.hidden = visible !== 0;
            }

            if (hint) {
                hint.textContent = query
                    ? `Menampilkan ${visible} dari ${items.length} aktivitas.`
                    : "Menampilkan seluruh aktivitas terbaru.";
            }
        });
    }

    // 4. Scroll halus untuk tautan bagian Impact Tracker
    function initSmoothAnchorLinks() {
        if (
            window.matchMedia(
                "(prefers-reduced-motion: reduce)"
            ).matches
        ) {
            return;
        }

        document
            .querySelectorAll('a[href^="#impact-"]')
            .forEach((link) => {
                link.addEventListener("click", (event) => {
                    const target = document.querySelector(
                        link.getAttribute("href")
                    );

                    if (!target) return;

                    event.preventDefault();

                    target.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });

                    history.replaceState(
                        null,
                        "",
                        link.getAttribute("href")
                    );
                });
            });
    }

    // Jalankan semua fitur setelah HTML siap
    document.addEventListener("DOMContentLoaded", function () {
        initCountUp();
        initChartBars();
        initActivitySearch();
        initSmoothAnchorLinks();
    });
})();
