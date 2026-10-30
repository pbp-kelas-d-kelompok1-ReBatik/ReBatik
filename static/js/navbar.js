/* ReBatik navbar: mega menu Marketplace, dropdown user, side drawer mobile */
(function () {
    "use strict";

    var nav = document.getElementById("rbNav");
    if (!nav) return;

    var megaTrigger = document.getElementById("rbMegaTrigger");
    var mega = document.getElementById("rbMega");
    var userTrigger = document.getElementById("rbUserTrigger");
    var userMenu = document.getElementById("rbUserMenu");
    var burger = document.getElementById("rbBurger");
    var drawer = document.getElementById("rbDrawer");
    var backdrop = document.getElementById("rbDrawerBackdrop");
    var closeBtn = document.getElementById("rbDrawerClose");

    var canHover = window.matchMedia("(hover: hover) and (pointer: fine)");
    var hoverTimer = null;

    function setPanel(trigger, panel, open) {
        if (!trigger || !panel) return;
        panel.hidden = !open;
        trigger.setAttribute("aria-expanded", open ? "true" : "false");
    }

    function closePanels(except) {
        if (except !== "mega") setPanel(megaTrigger, mega, false);
        if (except !== "user") setPanel(userTrigger, userMenu, false);
    }

    /* ---------- Mega menu ---------- */
    if (megaTrigger && mega) {
        var megaItem = megaTrigger.parentElement;

        // Hover (desktop mouse): buka saat kursor masuk, tutup dengan jeda singkat.
        function openMega() {
            clearTimeout(hoverTimer);
            closePanels("mega");
            setPanel(megaTrigger, mega, true);
        }

        function scheduleCloseMega() {
            clearTimeout(hoverTimer);
            hoverTimer = setTimeout(function () {
                setPanel(megaTrigger, mega, false);
            }, 160);
        }

        [megaItem, mega].forEach(function (el) {
            el.addEventListener("mouseenter", function () {
                if (canHover.matches) openMega();
            });
            el.addEventListener("mouseleave", function () {
                if (canHover.matches) scheduleCloseMega();
            });
        });

        // Klik / tap / keyboard: klik pertama membuka panel, klik kedua pindah ke Marketplace.
        megaTrigger.addEventListener("click", function (e) {
            if (megaTrigger.getAttribute("aria-expanded") !== "true") {
                e.preventDefault();
                openMega();
            }
        });

        megaTrigger.addEventListener("keydown", function (e) {
            if (e.key === "ArrowDown") {
                e.preventDefault();
                openMega();
                var first = mega.querySelector("a");
                if (first) first.focus();
            }
        });
    }

    /* ---------- Dropdown user ---------- */
    if (userTrigger && userMenu) {
        userTrigger.addEventListener("click", function () {
            var open = userTrigger.getAttribute("aria-expanded") !== "true";
            closePanels("user");
            setPanel(userTrigger, userMenu, open);
        });
    }

    document.addEventListener("click", function (e) {
        if (!nav.contains(e.target)) closePanels();
        else if (
            mega && !mega.contains(e.target) && !(megaTrigger && megaTrigger.contains(e.target)) &&
            userMenu && !userMenu.contains(e.target) && !(userTrigger && userTrigger.contains(e.target))
        ) {
            closePanels();
        }
    });

    /* ---------- Drawer mobile ---------- */
    function setDrawer(open) {
        if (!drawer || !burger) return;
        drawer.classList.toggle("is-open", open);
        drawer.setAttribute("aria-hidden", open ? "false" : "true");
        burger.setAttribute("aria-expanded", open ? "true" : "false");
        if (backdrop) backdrop.hidden = !open;
        document.body.classList.toggle("rb-no-scroll", open);

        if (open && closeBtn) closeBtn.focus();
        if (!open && burger) burger.focus();
    }

    if (burger) burger.addEventListener("click", function () { setDrawer(true); });
    if (closeBtn) closeBtn.addEventListener("click", function () { setDrawer(false); });
    if (backdrop) backdrop.addEventListener("click", function () { setDrawer(false); });

    /* ---------- Escape + resize ---------- */
    document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;

        if (drawer && drawer.classList.contains("is-open")) {
            setDrawer(false);
            return;
        }

        var wasOpen =
            (userTrigger && userTrigger.getAttribute("aria-expanded") === "true") ||
            (megaTrigger && megaTrigger.getAttribute("aria-expanded") === "true");

        if (wasOpen) {
            var focusTarget =
                userTrigger && userTrigger.getAttribute("aria-expanded") === "true"
                    ? userTrigger
                    : megaTrigger;
            closePanels();
            if (focusTarget) focusTarget.focus();
        }
    });

    window.addEventListener("resize", function () {
        if (window.innerWidth > 960 && drawer && drawer.classList.contains("is-open")) {
            setDrawer(false);
        }
    });
})();
