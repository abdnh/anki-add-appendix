(() => {
    const scriptId = "lightbox-script";
    if (!document.getElementById(scriptId)) {
        const script = document.createElement("script");
        script.id = scriptId;
        script.src = "lightbox-plus-jquery.min.js";
        document.currentScript.insertAdjacentElement("afterend", script);
    }

    const pdfOverlayId = "appendi-pdf-overlay";
    if (!document.getElementById(pdfOverlayId)) {
        const overlay = document.createElement("div");
        overlay.id = pdfOverlayId;
        overlay.addEventListener("click", () => {
            overlay.style.display = "none";
        });
        document.body.appendChild(overlay);
    }

    document.querySelectorAll(".appendix-link").forEach((el) => {
        if (el.href.endsWith(".pdf")) {
            el.addEventListener("click", (e) => {
                e.preventDefault();
                const overlay = document.getElementById(pdfOverlayId);
                overlay.innerHTML = `<iframe src="viewer.html?file=${el.href}"></iframe>`;
                overlay.style.display = "block";
            });
        } else {
            el.dataset.lightbox = "image";
            el.dataset.title = el.textContent;
        }
    });
})();
