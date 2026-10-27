/* Impact Tracker: animasi angka statistik dan pencarian aktivitas.
   Halaman tetap lengkap tanpa JavaScript; skrip ini hanya tambahan. */
(function () {
    "use strict";

    // ---------- Count-up angka statistik ----------
    var reduceMotion = window.matchMedia &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function animateCount(el) {
        var target = parseInt(el.textContent.replace(/\D/g, ""), 10);
        if (isNaN(target) || target <= 0) {
            return;
        }
        var duration = 900;
        var start = null;
        el.setAttribute("aria-label", String(target));

        function step(timestamp) {
            if (start === null) {
                start = timestamp;
            }
            var progress = Math.min((timestamp - start) / duration, 1);
            var eased = 1 - Math.pow(1 - progress, 3);
            el.textContent = String(Math.round(target * eased));
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                el.textContent = String(target);
            }
        }
        window.requestAnimationFrame(step);
    }

    if (!reduceMotion) {
        document.querySelectorAll("[data-count-up]").forEach(animateCount);
    }

    // ---------- Pencarian aktivitas ----------
    var input = document.getElementById("impactActivitySearch");
    var list = document.getElementById("impactActivityList");
    var noResults = document.getElementById("impactActivityNoResults");
    if (!input || !list) {
        return;
    }

    var items = Array.prototype.slice.call(
        list.querySelectorAll("[data-activity-item]")
    );
    var hint = document.querySelector(".impact-activity-search-hint");

    function filterActivity() {
        var query = input.value.trim().toLowerCase();
        var visible = 0;

        items.forEach(function (item) {
            var match = !query ||
                item.textContent.toLowerCase().indexOf(query) !== -1;
            item.hidden = !match;
            if (match) {
                visible += 1;
            }
        });

        if (noResults) {
            noResults.hidden = visible !== 0;
        }
        if (hint) {
            hint.textContent = query
                ? "Menampilkan " + visible + " dari " + items.length + " aktivitas."
                : "Menampilkan seluruh aktivitas terbaru.";
        }
    }

    input.addEventListener("input", filterActivity);
})();