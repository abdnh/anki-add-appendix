import "lightbox2/dist/css/lightbox.min.css";
import "lightbox2/dist/js/lightbox-plus-jquery.min.js";
import { MobilePDFViewer } from "./pdf-viewer";
import "./style.css";

// Create the PDF viewer instance
const pdfViewer = new MobilePDFViewer();

// Process appendix links
document.querySelectorAll<HTMLAnchorElement>(".appendix-link").forEach((el) => {
    if (el.classList.contains("processed")) {
        return;
    }
    const url = new URL(el.href);
    if (url.pathname.endsWith(".pdf")) {
        el.addEventListener("click", (e) => {
            e.preventDefault();
            pdfViewer.open(el.href);
        });
    } else {
        el.dataset.lightbox = "image";
        el.dataset.title = el.textContent!!;
    }
    el.classList.add("processed");
});
