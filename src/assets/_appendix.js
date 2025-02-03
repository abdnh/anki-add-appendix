(() => {
    const scriptId = "lightbox-script";
    if (!document.getElementById(scriptId)) {
        const script = document.createElement("script");
        script.id = scriptId;
        script.src = "lightbox-plus-jquery.min.js";
        document.currentScript.insertAdjacentElement("afterend", script);
    }

    document.querySelectorAll(".appendix-link").forEach((el) => {
        if (el.href.endsWith(".pdf")) {
            // TODO: load pdf viewer
            return;
        }
        el.dataset.lightbox = "image";
        el.dataset.title = el.textContent;
    });
})();
