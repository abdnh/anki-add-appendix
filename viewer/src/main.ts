import "lightbox2/dist/css/lightbox.min.css";
import "lightbox2/dist/js/lightbox-plus-jquery.min.js";
import "./style.css";

const pdfOverlayId = "appendix-pdf-overlay";
if (!document.getElementById(pdfOverlayId)) {
    const overlay = document.createElement("div");
    overlay.id = pdfOverlayId;
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) {
            overlay.style.display = "none";
        }
    });
    document.body.appendChild(overlay);
}

document.querySelectorAll<HTMLAnchorElement>(".appendix-link").forEach((el) => {
    if (el.classList.contains("processed")) {
        return;
    }
    if (el.href.endsWith(".pdf")) {
        el.addEventListener("click", (e) => {
            e.preventDefault();
            const overlay = document.getElementById(pdfOverlayId);
            overlay!.innerHTML = "";
            const container = document.createElement("div");
            container.style.width = "100%";
            container.style.height = "100%";
            container.style.position = "relative";
            const obj = document.createElement("object");
            obj.data = el.href;
            obj.type = "application/pdf";
            obj.style.width = "100%";
            obj.style.height = "100%";
            obj.style.position = "absolute";
            obj.style.top = "0";
            obj.style.left = "0";
            obj.style.border = "none";
            obj.style.backgroundColor = "white";
            obj.style.padding = "20px";
            obj.style.boxSizing = "border-box";
            const embed = document.createElement("embed");
            embed.src = el.href;
            embed.type = "application/pdf";
            embed.style.width = "100%";
            embed.style.height = "100%";
            obj.appendChild(embed);
            container.appendChild(obj);
            overlay!.appendChild(container);
            overlay!.style.display = "block";
        });
    } else {
        el.dataset.lightbox = "image";
        el.dataset.title = el.textContent!!;
    }
    el.classList.add("processed");
});
