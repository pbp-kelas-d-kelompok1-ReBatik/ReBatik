document.addEventListener("DOMContentLoaded", function () {
    const get = (id) => document.getElementById(id);
    const app = get("motif-app");
    const canvas = get("pattern-canvas");

    if (!app || !canvas) return;

    const ctx = canvas.getContext("2d");
    const motifImage = new Image();

    const gap = get("ctl-gap");
    const scale = get("ctl-scale");
    const layout = get("ctl-layout");
    const tint = get("ctl-tint");
    const rotation = get("ctl-rotation");
    const status = get("md-status");

    const resetButton = get("btn-reset");
    const downloadButton = get("btn-download");
    const shareButton = get("btn-share");
    const saveButton = get("btn-save");
    const generateButton = get("btn-generate");

    const swatches = [
        ...document.querySelectorAll("#swatches button[data-color]")
    ];

    const user = app.dataset.userName || "Sahabat ReBatik";
    const style = app.dataset.styleName || "Personal Style";
    const palette = app.dataset.paletteName || "My Palette";
    const motif = app.dataset.motifName || "Batik Nusantara";

    const colors = (app.dataset.paletteColors || "")
        .split(",")
        .map(color => color.trim())
        .filter(Boolean);

    let selectedColor = swatches[0]?.dataset.color || "#874a29";
    let imageReady = false;

    function message(text) {
        if (status) status.textContent = text;
    }

    function draw() {
        const w = canvas.width;
        const h = canvas.height;

        ctx.clearRect(0, 0, w, h);

        const backgrounds = {
            plain: "#f5e9d6",
            cream: "#f1dfc4",
            paper: "#ead8bc"
        };

        ctx.fillStyle = backgrounds[tint?.value] || backgrounds.plain;
        ctx.fillRect(0, 0, w, h);

        if (imageReady) {
            const s = Number(scale?.value || 100) / 100;
            const angle = Number(rotation?.value || 0) * Math.PI / 180;
            const ratio = motifImage.naturalHeight / motifImage.naturalWidth;

            if (layout?.value === "single") {
                const fit = Math.min(
                    w * 0.82 / motifImage.naturalWidth,
                    h * 0.82 / motifImage.naturalHeight
                ) * s;

                const tw = motifImage.naturalWidth * fit;
                const th = motifImage.naturalHeight * fit;

                ctx.save();
                ctx.translate(w / 2, h / 2);
                ctx.rotate(angle);
                ctx.drawImage(motifImage, -tw / 2, -th / 2, tw, th);
                ctx.restore();
            } else {
                const tw = Math.max(70, 230 * s);
                const th = tw * ratio;
                const density = Number(gap?.value || 50);
                const stepX = Math.max(20, tw * (2.1 - density / 100 * 0.85));
                const stepY = Math.max(20, th * (2.1 - density / 100 * 0.85));

                let row = 0;

                for (let y = -stepY; y < h + stepY; y += stepY) {
                    const staggered =
                        ["brick", "half_drop"].includes(layout?.value) && row % 2;

                    const offset = staggered ? stepX / 2 : 0;
                    const rowY = y +
                        (layout?.value === "half_drop" && row % 2 ? stepY / 2 : 0);

                    for (let x = -stepX; x < w + stepX; x += stepX) {
                        ctx.save();
                        ctx.translate(x + offset + tw / 2, rowY + th / 2);
                        ctx.rotate(angle);

                        if (layout?.value === "mirror" && row % 2) {
                            ctx.scale(-1, 1);
                        }

                        ctx.drawImage(motifImage, -tw / 2, -th / 2, tw, th);
                        ctx.restore();
                    }

                    row++;
                }
            }
        } else {
            ctx.fillStyle = "#874a29";
            ctx.textAlign = "center";
            ctx.font = "24px Georgia";
            ctx.fillText("Loading batik motif...", w / 2, h / 2);
        }

        if (get("gap-value")) get("gap-value").textContent = `${gap?.value || 50}%`;
        if (get("scale-value")) get("scale-value").textContent = `${scale?.value || 100}%`;
        if (get("rotation-value")) get("rotation-value").textContent = `${rotation?.value || 0}°`;

        swatches.forEach(button => {
            const active =
                button.dataset.color.toLowerCase() === selectedColor.toLowerCase();

            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", String(active));
        });
    }

    // ========================================
    // KARTU PERSONAL REBATIK
    // ========================================

    function makeCard() {
        const card = document.createElement("canvas");
        card.width = 1100;
        card.height = 1500;

        const c = card.getContext("2d");

        const ink = "#542f1c";
        const brown = "#874a29";
        const gold = "#c99a52";
        const cream = "#fffaf0";
        const muted = "#92765b";

        function rounded(x, y, w, h, r, fill, stroke, lineWidth = 2) {
            c.beginPath();
            c.roundRect(x, y, w, h, r);

            if (fill) {
                c.fillStyle = fill;
                c.fill();
            }

            if (stroke) {
                c.strokeStyle = stroke;
                c.lineWidth = lineWidth;
                c.stroke();
            }
        }

        function fitText(text, x, y, maxWidth, font, color) {
            c.font = font;
            c.fillStyle = color;
            c.textAlign = "left";

            let output = String(text || "");

            while (c.measureText(output).width > maxWidth && output.length > 3) {
                output = output.slice(0, -2) + "…";
            }

            c.fillText(output, x, y);
        }

        function flower(x, y, size, color) {
            c.save();
            c.translate(x, y);
            c.strokeStyle = color;
            c.lineWidth = 2;

            for (let i = 0; i < 8; i++) {
                c.rotate(Math.PI / 4);
                c.beginPath();
                c.ellipse(
                    0, -size * 0.55,
                    size * 0.22, size * 0.48,
                    0, 0, Math.PI * 2
                );
                c.stroke();
            }

            c.beginPath();
            c.arc(0, 0, size * 0.17, 0, Math.PI * 2);
            c.fillStyle = color;
            c.fill();
            c.restore();
        }

        function divider(y) {
            c.strokeStyle = "#e5cfad";
            c.lineWidth = 1.5;
            c.beginPath();
            c.moveTo(120, y);
            c.lineTo(515, y);
            c.moveTo(585, y);
            c.lineTo(980, y);
            c.stroke();
            flower(550, y, 12, gold);
        }

        // Latar ivory yang lebih bersih
        c.fillStyle = "#FFFCF6";
        c.fillRect(0, 0, 1100, 1500);

        // Bingkai utama
        rounded(78, 32, 944, 1436, 30, cream, gold, 2);
        rounded(88, 42, 924, 1416, 25, null, "#ead8b8", 1);

        flower(105, 125, 27, "#d8b779");
        flower(995, 180, 25, "#d8b779");
        flower(105, 1330, 23, "#d8b779");
        flower(995, 1360, 27, "#d8b779");

        // Header ReBatik
        flower(145, 95, 20, brown);

        c.textAlign = "left";
        c.fillStyle = brown;
        c.font = "52px Georgia";
        c.fillText("ReBatik", 182, 108);

        c.strokeStyle = "#dfc9a6";
        c.beginPath();
        c.moveTo(395, 95);
        c.lineTo(720, 95);
        c.stroke();

        flower(747, 95, 8, gold);

        c.fillStyle = "#8c673e";
        c.font = "bold 15px Georgia";
        c.fillText("CREATIVE STUDIO", 770, 101);

        // Judul
        c.textAlign = "center";
        c.fillStyle = ink;
        c.font = "bold 45px Georgia";
        c.fillText("Karya Batikmu, Cerita Gayamu", 550, 185);

        c.fillStyle = muted;
        c.font = "29px Georgia";
        c.fillText("Dipersonalisasi khusus untukmu", 550, 230);

        // Area motif: gambar memenuhi bingkai
        rounded(120, 270, 860, 620, 18, "#ead8b8", gold, 1.5);

        const targetX = 124;
        const targetY = 274;
        const targetW = 852;
        const targetH = 612;

        c.save();

        c.beginPath();
        c.roundRect(targetX, targetY, targetW, targetH, 15);
        c.clip();

        if (imageReady) {
            const sourceW = motifImage.naturalWidth;
            const sourceH = motifImage.naturalHeight;

            const sourceRatio = sourceW / sourceH;
            const targetRatio = targetW / targetH;

            let sx = 0;
            let sy = 0;
            let sw = sourceW;
            let sh = sourceH;

            if (sourceRatio > targetRatio) {
                sw = sourceH * targetRatio;
                sx = (sourceW - sw) / 2;
            } else {
                sh = sourceW / targetRatio;
                sy = (sourceH - sh) / 2;
            }

            c.drawImage(
                motifImage,
                sx, sy, sw, sh,
                targetX, targetY, targetW, targetH
            );
        }

        // Watermark ReBatik
        c.save();
        c.textAlign = "right";
        c.textBaseline = "bottom";
        c.font = "italic bold 34px Georgia";
        c.fillStyle = "rgba(255, 250, 240, 0.95)";
        c.shadowColor = "rgba(60, 35, 20, 0.65)";
        c.shadowBlur = 4;
        c.fillText("ReBatik", 950, 866, 220);
        c.restore();

        c.restore();

        // Pesan personal
        divider(915);

        // Pesan personal
        divider(915);
        rounded(120, 940, 860, 168, 22, "#fbf3e6", "#ead9bf", 1.5);
        flower(195, 1022, 32, brown);

        fitText(`${user}, style ${style}`, 250, 988, 690, "bold 27px Georgia", ink);
        fitText(`dan color palette ${palette}`, 250, 1031, 690, "26px Georgia", ink);
        fitText(`kamu cocok dengan motif ${motif}!`, 250, 1070, 690, "bold 26px Georgia", ink);

        c.textAlign = "left";
        c.fillStyle = muted;
        c.font = "italic 23px Georgia";
        c.fillText("Your style. Your colors. Your batik.", 250, 1097);

        // Chip style
        rounded(120, 1125, 230, 62, 31, cream, "#e5cfad", 1.5);
        flower(153, 1156, 12, brown);
        fitText(style.toUpperCase(), 180, 1162, 150, "bold 16px Georgia", ink);

        // Chip warna
        rounded(365, 1125, 370, 62, 31, cream, "#e5cfad", 1.5);

        const paletteColors = colors.length
            ? colors.slice(0, 5)
            : [selectedColor, "#874a29", "#c99357", "#716743", "#f1dfc4"];

        paletteColors.forEach((color, i) => {
            c.beginPath();
            c.arc(395 + i * 38, 1156, 13, 0, Math.PI * 2);
            c.fillStyle = color;
            c.fill();
            c.strokeStyle = "#dfc9a6";
            c.stroke();
        });

        fitText(palette.toUpperCase(), 590, 1162, 130, "bold 14px Georgia", ink);

        // Chip motif
        rounded(750, 1125, 230, 62, 31, cream, "#e5cfad", 1.5);
        flower(782, 1156, 15, brown);
        fitText(motif.toUpperCase(), 810, 1162, 155, "bold 14px Georgia", ink);

        // Footer
        divider(1220);

        c.textAlign = "left";
        c.fillStyle = muted;
        c.font = "20px Georgia";
        c.fillText("Made with ReBatik", 120, 1280);

        rounded(620, 1240, 185, 68, 34, cream, brown, 1.5);
        c.textAlign = "center";
        c.fillStyle = brown;
        c.font = "bold 20px Georgia";
        c.fillText("↓ Download", 712, 1282);

        rounded(820, 1240, 160, 68, 34, brown, "#a86b3b", 1.5);
        c.fillStyle = cream;
        c.fillText("↗ Share", 900, 1282);

        c.textAlign = "center";
        c.fillStyle = gold;
        c.font = "24px Georgia";
        c.fillText("✦", 550, 1370);

        c.fillStyle = muted;
        c.font = "italic 18px Georgia";
        c.fillText("Celebrating the beauty of Indonesian batik", 550, 1410);

        return card;
    }
    // ========================================
    // DOWNLOAD KARTU
    // ========================================

    function downloadCard() {
        if (!imageReady) {
            message("Tunggu sampai gambar motif berhasil dimuat.");
            return;
        }

        try {
            const card = makeCard();
            const link = document.createElement("a");

            link.download = "rebatik-karya-personal.png";
            link.href = card.toDataURL("image/png");

            document.body.appendChild(link);
            link.click();
            link.remove();

            message("Kartu ReBatik berhasil diunduh.");
        } catch (error) {
            console.error("Gagal mengunduh kartu:", error);
            message("Kartu gagal diunduh. Periksa Console browser.");
        }
    }

    // ========================================
    // POPUP SHARE
    // ========================================


    function openSharePopup() {
        if (!imageReady) {
            message("Tunggu sampai gambar motif berhasil dimuat.");
            return;
        }

        let modal = get("rebatik-share-modal");

        if (!modal) {
            modal = document.createElement("div");
            modal.id = "rebatik-share-modal";

            modal.innerHTML = `
            <div class="rb-backdrop"></div>

            <section class="rb-dialog" role="dialog"
                aria-modal="true"
                aria-labelledby="rb-share-title">

                <button type="button" class="rb-close"
                    aria-label="Tutup popup">×</button>

                <header class="rb-modal-header">
                    <div class="rb-eyebrow">
                        <span class="rb-line"></span>
                        ✿ &nbsp; ReBatik · CREATIVE STUDIO &nbsp; ✿
                        <span class="rb-line"></span>
                    </div>

                    <h2 id="rb-share-title">
                        Bagikan Karya Batikmu
                    </h2>

                    <p>Preview kartu personal ReBatik kamu.</p>
                </header>

                <div class="rb-main">
                    <aside class="rb-mascot-area">
                        <div class="rb-speech">
                            Ini dia<br>
                            karya batikmu!
                            <span>♡</span>
                        </div>

                        <img
                            class="rb-mascot"
                            src="/static/img/mascot/pointing.webp"
                            alt="Maskot beruang ReBatik"
                        >

                        <span class="rb-decoration rb-d1">✿</span>
                        <span class="rb-decoration rb-d2">✧</span>
                        <span class="rb-decoration rb-d3">✿</span>
                    </aside>

                    <div class="rb-preview-area">
                        <div class="rb-preview">
                            <canvas
                                id="rb-share-canvas"
                                width="1100"
                                height="1500">
                            </canvas>
                        </div>

                        <span class="rb-decoration rb-d4">✧</span>
                        <span class="rb-decoration rb-d5">✿</span>
                    </div>
                </div>

                <p id="rb-share-status" role="status">
                    Kartu ReBatik siap dibagikan.
                </p>

                <div class="rb-actions">
                    <button type="button" id="rb-share-back"
                        class="rb-btn rb-btn-outline">
                        Kembali
                    </button>

                    <button type="button" id="rb-share-download"
                        class="rb-btn rb-btn-primary">
                        <span>↓</span> Download Kartu
                    </button>

                    <button type="button" id="rb-share-send"
                        class="rb-btn rb-btn-primary">
                        <span>♧</span> Share Kartu
                    </button>
                </div>
            </section>
        `;

            document.body.appendChild(modal);

            const styleTag = document.createElement("style");
            // prettier-ignore
            styleTag.textContent = `
#rebatik-share-modal {
    display: none;
    position: fixed;
    inset: 0;
    z-index: 99999;
    padding: 16px;
    align-items: center;
    justify-content: center;
    font-family: Garamond, "EB Garamond", "Cormorant Garamond", Georgia, serif;
}

#rebatik-share-modal.is-open { display: flex; }
#rebatik-share-modal * { box-sizing: border-box; }
#rebatik-share-modal button { font-family: inherit; }

.rb-backdrop {
    position: absolute;
    inset: 0;
    background: rgba(37, 25, 17, 0.72);
    backdrop-filter: blur(5px);
}

.rb-dialog {
    position: relative;
    width: min(980px, 100%);
    max-height: 90vh;
    overflow-y: auto;
    padding: 20px 28px 18px;
    background: #fffcf6;
    border: 1px solid #e5d2b7;
    border-radius: 28px;
    box-shadow: 0 25px 90px rgba(0,0,0,.24);
    color: #542f1c;
    text-align: center;
}

.rb-close {
    position: absolute;
    top: 12px;
    right: 22px;
    background: transparent;
    border: none;
    font-size: 36px;
    line-height: 1;
    color: #542f1c;
    cursor: pointer;
    z-index: 3;
}

.rb-modal-header { margin-bottom: 8px; }

.rb-eyebrow {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: #874a29;
    font-size: 15px;
    font-weight: bold;
    letter-spacing: 3px;
}

.rb-line { width: 60px; height: 1px; background: #c99a52; }

.rb-modal-header h2 {
    font-size: clamp(28px, 3.2vw, 42px);
    font-weight: normal;
    margin: 6px 0 2px;
    color: #542f1c;
}

.rb-modal-header p {
    margin: 0;
    font-size: clamp(17px, 1.8vw, 22px);
    color: #92765b;
}

.rb-main {
    display: grid;
    grid-template-columns: 36% 64%;
    align-items: stretch;
    min-height: 500px;
    margin-top: 12px;
}

.rb-mascot-area {
    position: relative;
    min-height: 500px;
    display: flex;
    align-items: flex-end;
    justify-content: center;
}

.rb-speech {
    position: absolute;
    top: 10px;
    left: 5%;
    width: 85%;
    padding: 20px 12px;
    border: 2px solid #874a29;
    border-radius: 50%;
    background: #fffdf8;
    font-size: clamp(18px, 1.8vw, 24px);
    font-weight: bold;
    line-height: 1.2;
    color: #874a29;
    transform: rotate(-7deg);
    z-index: 2;
}

.rb-speech::after {
    content: "";
    position: absolute;
    bottom: -14px;
    left: 45%;
    width: 22px;
    height: 22px;
    background: #fffdf8;
    border-right: 2px solid #874a29;
    border-bottom: 2px solid #874a29;
    transform: rotate(45deg);
}

.rb-speech span { display: block; margin-top: 4px; font-size: 22px; }

.rb-mascot {
    position: relative;
    height: 500px;
    width: auto;
    max-width: 125%;
    object-fit: contain;
    object-position: bottom;
    z-index: 1;
}

.rb-preview-area {
    position: relative;
    min-width: 0;
    padding: 10px 16px;
    background: #f5e9d8;
    border: 1px solid #ead8bf;
    border-radius: 24px;
}

.rb-preview {
    height: 480px;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-color: #b8aa99 #fffaf2;
    scrollbar-width: thin;
    display: flex;
    justify-content: center;
    align-items: flex-start;
}

#rb-share-canvas {
    display: block;
    width: min(100%, 340px);
    height: auto;
    background: #fffaf0;
    border-radius: 16px;
    box-shadow: 0 5px 22px rgba(80,45,25,.12);
}

.rb-decoration {
    position: absolute;
    color: #d6a55c;
    pointer-events: none;
}

.rb-d1 { left: 0; top: 43%; font-size: 36px; }
.rb-d2 { right: 0; top: 50%; font-size: 30px; }
.rb-d3 { left: 5%; bottom: 4%; font-size: 28px; }
.rb-d4 { right: 8%; top: 20%; font-size: 38px; }
.rb-d5 { right: 6%; bottom: 10%; font-size: 32px; }

#rb-share-status {
    margin: 8px 0;
    font-size: 19px;
    color: #874a29;
}

.rb-actions {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 6px;
}

.rb-btn {
    min-height: 48px;
    padding: 8px 26px;
    border-radius: 999px;
    font-size: 20px;
    cursor: pointer;
    transition: transform .2s, box-shadow .2s;
}

.rb-btn:hover { transform: translateY(-2px); box-shadow: 0 5px 14px rgba(80,45,25,.12); }
.rb-btn-outline { border: 1.5px solid #874a29; color: #542f1c; background: #fffaf2; }
.rb-btn-primary { border: 1.5px solid #a96b40; color: white; background: #874a29; }
.rb-btn span { margin-right: 8px; font-size: 22px; }

@media (max-width: 800px) {
    .rb-dialog { padding: 18px 12px; border-radius: 20px; }
    .rb-main { grid-template-columns: 1fr; min-height: auto; }
    .rb-mascot-area { min-height: 200px; align-items: center; justify-content: flex-start; }
    .rb-mascot { height: 200px; max-width: 45%; }
    .rb-speech { top: 20px; left: 48%; width: min(200px, 48%); padding: 16px 8px; font-size: 17px; }
    .rb-preview-area { padding: 10px; }
    .rb-preview { height: 360px; }
    #rb-share-canvas { width: min(100%, 280px); }
    .rb-eyebrow { font-size: 12px; letter-spacing: 2px; }
    .rb-line { width: 25px; }
    .rb-btn { font-size: 17px; min-height: 44px; padding: 8px 16px; }
    #rb-share-status { font-size: 16px; }
}
`;

            document.head.appendChild(styleTag);

            const close = () => {
                modal.classList.remove("is-open");
                document.body.style.overflow = "";
            };

            modal.querySelector(".rb-close")
                .addEventListener("click", close);

            modal.querySelector(".rb-backdrop")
                .addEventListener("click", close);

            get("rb-share-back")
                .addEventListener("click", close);

            get("rb-share-download")
                .addEventListener("click", downloadCard);

            get("rb-share-send").addEventListener("click", async () => {
                try {
                    const blob = await new Promise((resolve, reject) => {
                        makeCard().toBlob(result => {
                            if (result) resolve(result);
                            else reject(new Error("Gagal membuat kartu."));
                        }, "image/png");
                    });

                    const file = new File(
                        [blob],
                        "rebatik-karya-personal.png",
                        { type: "image/png" }
                    );

                    if (
                        navigator.share &&
                        navigator.canShare?.({ files: [file] })
                    ) {
                        await navigator.share({
                            title: "Karya Batikku — ReBatik",
                            text: "Lihat karya batik personal ReBatik-ku!",
                            files: [file]
                        });
                    } else {
                        downloadCard();
                        get("rb-share-status").textContent =
                            "Browser belum mendukung share langsung. Kartu berhasil disiapkan untuk diunduh.";
                    }
                } catch (error) {
                    if (error.name !== "AbortError") {
                        console.error("Share gagal:", error);
                        get("rb-share-status").textContent =
                            "Gagal membagikan kartu. Coba download terlebih dahulu.";
                    }
                }
            });

            modal._close = close;
        }

        const card = makeCard();
        const preview = get("rb-share-canvas");

        preview.width = card.width;
        preview.height = card.height;
        preview.getContext("2d").drawImage(card, 0, 0);

        modal.classList.add("is-open");
        document.body.style.overflow = "hidden";

        get("rb-share-status").textContent =
            "Kartu ReBatik siap dibagikan.";
    }

    // ========================================
    // EVENT LISTENERS
    // ========================================

    swatches.forEach(button => {
        button.addEventListener("click", () => {
            selectedColor = button.dataset.color || selectedColor;
            draw();
            message("Warna desain diperbarui.");
        });
    });

    [gap, scale, layout, tint, rotation]
        .filter(Boolean)
        .forEach(control => {
            control.addEventListener("input", draw);
            control.addEventListener("change", draw);
        });

    if (generateButton) {
        generateButton.addEventListener("click", () => {
            draw();

            message(
                imageReady
                    ? "Pattern berhasil dibuat."
                    : "Gambar motif belum berhasil dimuat."
            );
        });
    }

    if (resetButton) {
        resetButton.addEventListener("click", () => {
            if (gap) gap.value = 50;
            if (scale) scale.value = 100;
            if (layout) layout.value = "single";
            if (tint) tint.value = "plain";
            if (rotation) rotation.value = 0;

            selectedColor = swatches[0]?.dataset.color || "#874a29";

            draw();
            message("Pengaturan berhasil direset.");
        });
    }

    if (downloadButton) {
        downloadButton.addEventListener("click", downloadCard);
    }

    if (shareButton) {
        shareButton.addEventListener("click", openSharePopup);
    }

    if (saveButton) {
        saveButton.addEventListener("click", () => {
            message("Save to Gallery belum terhubung ke backend Django.");
        });
    }

    // Pasang handler sebelum mengatur src gambar
    motifImage.onload = () => {
        imageReady = true;
        draw();
        message("Motif berhasil dimuat.");
    };

    motifImage.onerror = () => {
        imageReady = false;
        draw();
        message("Gambar gagal dimuat. Periksa URL gambar katalog.");
    };

    draw();
    motifImage.src = app.dataset.motifImage || "";
});