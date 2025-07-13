import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorker from "pdfjs-dist/build/pdf.worker.min.js?url";

// Type declaration for Promise.withResolvers polyfill
interface PromiseWithResolvers<T> {
    promise: Promise<T>;
    resolve: (value: T | PromiseLike<T>) => void;
    reject: (reason?: any) => void;
}

declare global {
    interface PromiseConstructor {
        withResolvers?<T>(): PromiseWithResolvers<T>;
    }
}

// Polyfill for Promise.withResolvers (for older environments like Anki)
if (!Promise.withResolvers) {
    Promise.withResolvers = function<T>(): PromiseWithResolvers<T> {
        let resolve: (value: T | PromiseLike<T>) => void;
        let reject: (reason?: any) => void;
        const promise = new Promise<T>((res, rej) => {
            resolve = res;
            reject = rej;
        });
        return { promise, resolve: resolve!, reject: reject! };
    };
}

// Configure PDF.js worker
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorker;

export class MobilePDFViewer {
    private overlay!: HTMLElement;
    private container!: HTMLElement;
    private canvas!: HTMLCanvasElement;
    private ctx!: CanvasRenderingContext2D;
    private pdfDoc: any = null;
    private pageNum = 1;
    private pageRendering = false;
    private pageNumPending: number | null = null;
    private scale = 1.0;
    private initialScale = 1.0;
    private rotation = 0;
    private lastTouchDistance = 0;
    private isPanning = false;
    private panStartX = 0;
    private panStartY = 0;
    private panCurrentX = 0;
    private panCurrentY = 0;
    private controls!: HTMLElement;
    private pageInfo!: HTMLElement;
    private loadingIndicator!: HTMLElement;
    private errorMessage!: HTMLElement;

    constructor() {
        this.createOverlay();
        this.setupEventListeners();
    }

    private createOverlay() {
        this.overlay = document.createElement("div");
        this.overlay.id = "appendix-pdf-overlay";
        this.overlay.className = "pdf-overlay";

        // Create container
        this.container = document.createElement("div");
        this.container.className = "pdf-container";

        // Create canvas
        this.canvas = document.createElement("canvas");
        this.canvas.className = "pdf-canvas";
        this.ctx = this.canvas.getContext("2d")!;

        // Create controls
        this.controls = document.createElement("div");
        this.controls.className = "pdf-controls";
        this.controls.innerHTML = `
            <button class="pdf-btn pdf-close" title="Close">×</button>
            <button class="pdf-btn pdf-prev" title="Previous Page">‹</button>
            <span class="pdf-page-info">1 / 1</span>
            <button class="pdf-btn pdf-next" title="Next Page">›</button>
            <button class="pdf-btn pdf-zoom-out" title="Zoom Out">−</button>
            <button class="pdf-btn pdf-zoom-in" title="Zoom In">+</button>
            <button class="pdf-btn pdf-rotate" title="Rotate">⟲</button>
            <button class="pdf-btn pdf-reset" title="Reset View">⌂</button>
        `;

        // Create page info
        this.pageInfo = this.controls.querySelector(".pdf-page-info") as HTMLElement;

        // Create loading indicator
        this.loadingIndicator = document.createElement("div");
        this.loadingIndicator.className = "pdf-loading";
        this.loadingIndicator.innerHTML = `
            <div class="pdf-spinner"></div>
            <div>Loading PDF...</div>
        `;

        // Create error message
        this.errorMessage = document.createElement("div");
        this.errorMessage.className = "pdf-error hidden";
        this.errorMessage.innerHTML = `
            <div>Failed to load PDF</div>
            <button class="pdf-btn pdf-retry">Retry</button>
        `;

        // Assemble the overlay
        this.container.appendChild(this.canvas);
        this.container.appendChild(this.loadingIndicator);
        this.container.appendChild(this.errorMessage);
        this.overlay.appendChild(this.container);
        this.overlay.appendChild(this.controls);

        document.body.appendChild(this.overlay);
    }

    private setupEventListeners() {
        // Control buttons
        this.controls.addEventListener("click", (e) => {
            const target = e.target as HTMLElement;
            if (target.classList.contains("pdf-close")) {
                this.close();
            } else if (target.classList.contains("pdf-prev")) {
                this.onPrevPage();
            } else if (target.classList.contains("pdf-next")) {
                this.onNextPage();
            } else if (target.classList.contains("pdf-zoom-in")) {
                this.zoomIn();
            } else if (target.classList.contains("pdf-zoom-out")) {
                this.zoomOut();
            } else if (target.classList.contains("pdf-rotate")) {
                this.rotate();
            } else if (target.classList.contains("pdf-reset")) {
                this.resetView();
            } else if (target.classList.contains("pdf-retry")) {
                this.retry();
            }
        });

        // Close on overlay click
        this.overlay.addEventListener("click", (e) => {
            if (e.target === this.overlay) {
                this.close();
            }
        });

        // Touch events for pinch zoom and pan
        this.canvas.addEventListener("touchstart", this.handleTouchStart.bind(this));
        this.canvas.addEventListener("touchmove", this.handleTouchMove.bind(this));
        this.canvas.addEventListener("touchend", this.handleTouchEnd.bind(this));

        // Mouse events for desktop
        this.canvas.addEventListener("wheel", this.handleWheel.bind(this));
        this.canvas.addEventListener("mousedown", this.handleMouseDown.bind(this));
        this.canvas.addEventListener("mousemove", this.handleMouseMove.bind(this));
        this.canvas.addEventListener("mouseup", this.handleMouseUp.bind(this));

        // Keyboard events
        document.addEventListener("keydown", this.handleKeyDown.bind(this));
    }

    private handleTouchStart(e: TouchEvent) {
        e.preventDefault();
        if (e.touches.length === 2) {
            // Start pinch zoom
            this.lastTouchDistance = this.getTouchDistance(e.touches);
        } else if (e.touches.length === 1) {
            // Start pan
            this.isPanning = true;
            this.panStartX = e.touches[0].clientX;
            this.panStartY = e.touches[0].clientY;
        }
    }

    private handleTouchMove(e: TouchEvent) {
        e.preventDefault();
        if (e.touches.length === 2) {
            // Pinch zoom
            const distance = this.getTouchDistance(e.touches);
            if (this.lastTouchDistance > 0) {
                const ratio = distance / this.lastTouchDistance;
                this.scale = Math.max(0.5, Math.min(5, this.scale * ratio));
                this.renderPage(this.pageNum);
            }
            this.lastTouchDistance = distance;
        } else if (e.touches.length === 1 && this.isPanning) {
            // Pan
            this.panCurrentX = e.touches[0].clientX - this.panStartX;
            this.panCurrentY = e.touches[0].clientY - this.panStartY;
            this.updateCanvasTransform();
        }
    }

    private handleTouchEnd(e: TouchEvent) {
        if (e.touches.length === 0) {
            this.isPanning = false;
            this.lastTouchDistance = 0;
        }
    }

    private handleWheel(e: WheelEvent) {
        e.preventDefault();
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        this.scale = Math.max(0.5, Math.min(5, this.scale * zoomFactor));
        this.renderPage(this.pageNum);
    }

    private handleMouseDown(e: MouseEvent) {
        if (e.button === 0) {
            this.isPanning = true;
            this.panStartX = e.clientX;
            this.panStartY = e.clientY;
        }
    }

    private handleMouseMove(e: MouseEvent) {
        if (this.isPanning) {
            this.panCurrentX = e.clientX - this.panStartX;
            this.panCurrentY = e.clientY - this.panStartY;
            this.updateCanvasTransform();
        }
    }

    private handleMouseUp() {
        this.isPanning = false;
    }

    private handleKeyDown(e: KeyboardEvent) {
        if (!this.overlay.classList.contains("active")) return;

        switch (e.key) {
            case "Escape":
                this.close();
                break;
            case "ArrowLeft":
                this.onPrevPage();
                break;
            case "ArrowRight":
                this.onNextPage();
                break;
            case "+":
            case "=":
                this.zoomIn();
                break;
            case "-":
                this.zoomOut();
                break;
            case "r":
                this.rotate();
                break;
            case "0":
                this.resetView();
                break;
        }
    }

    private getTouchDistance(touches: TouchList): number {
        const dx = touches[0].clientX - touches[1].clientX;
        const dy = touches[0].clientY - touches[1].clientY;
        return Math.sqrt(dx * dx + dy * dy);
    }

    private updateCanvasTransform() {
        this.canvas.style.transform =
            `translate(${this.panCurrentX}px, ${this.panCurrentY}px) rotate(${this.rotation}deg)`;
    }

    private parsePageFromUrl(url: string): number {
        try {
            const urlObj = new URL(url, window.location.origin);
            const pageParam = urlObj.searchParams.get("page");

            if (pageParam) {
                const pageNum = parseInt(pageParam, 10);
                // Return valid page number (will be validated against PDF bounds later)
                return pageNum > 0 ? pageNum : 1;
            }
        } catch (error) {
            console.warn("Error parsing URL for page parameter:", error);
        }

        return 1; // Default to page 1
    }

    private getCleanPdfUrl(url: string): string {
        try {
            const urlObj = new URL(url, window.location.origin);
            // Remove the page parameter to get clean PDF URL
            urlObj.searchParams.delete("page");
            return urlObj.toString();
        } catch (error) {
            console.warn("Error cleaning PDF URL:", error);
            return url;
        }
    }

    async open(url: string) {
        this.overlay.classList.add("active");
        this.showLoading();

        try {
            const requestedPage = this.parsePageFromUrl(url);
            const cleanUrl = this.getCleanPdfUrl(url);

            const loadingTask = pdfjsLib.getDocument(cleanUrl);
            this.pdfDoc = await loadingTask.promise;

            // Validate and set the starting page
            const maxPages = this.pdfDoc.numPages;
            this.pageNum = Math.min(Math.max(1, requestedPage), maxPages);

            // Calculate initial scale using actual PDF dimensions
            this.scale = await this.calculateInitialScaleWithPdf();
            this.initialScale = this.scale;
            this.rotation = 0;
            this.panCurrentX = 0;
            this.panCurrentY = 0;

            this.renderPage(this.pageNum);
            this.hideLoading();
        } catch (error) {
            console.error("Error loading PDF:", error);
            this.showError();
        }
    }

    private calculateInitialScale(): number {
        const containerWidth = this.container.clientWidth;
        const containerHeight = this.container.clientHeight;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // Use viewport dimensions if container dimensions are not reliable
        const effectiveWidth = containerWidth > 0 ? containerWidth : viewportWidth;
        const effectiveHeight = containerHeight > 0 ? containerHeight : viewportHeight;

        // More aggressive scaling for mobile devices
        if (viewportWidth < 768) {
            // Account for padding and controls (roughly 60px for controls)
            const availableHeight = effectiveHeight - 120;
            const availableWidth = effectiveWidth - 20; // 10px margin on each side

            // For mobile, we want to use more of the screen
            // Start with a scale that uses 90% of available width
            const widthBasedScale = (availableWidth * 0.9) / 612; // Standard A4 width
            const heightBasedScale = (availableHeight * 0.9) / 792; // Standard A4 height

            // Use the smaller scale to ensure it fits, but minimum of 1.0 for readability
            return Math.max(1.0, Math.min(widthBasedScale, heightBasedScale));
        }
        return 1.0;
    }

    private async calculateInitialScaleWithPdf(): Promise<number> {
        if (!this.pdfDoc) {
            return this.calculateInitialScale();
        }

        try {
            // Get the first page to determine actual PDF dimensions
            const page = await this.pdfDoc.getPage(1);
            const viewport = page.getViewport({ scale: 1.0 });

            const containerWidth = this.container.clientWidth;
            const containerHeight = this.container.clientHeight;
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;

            // Use viewport dimensions if container dimensions are not reliable
            const effectiveWidth = containerWidth > 0 ? containerWidth : viewportWidth;
            const effectiveHeight = containerHeight > 0 ? containerHeight : viewportHeight;

            // Detect iOS devices for special handling
            const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent)
                || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

            // More aggressive scaling for mobile devices
            if (viewportWidth < 768) {
                // For full screen experience, use almost all available space
                let availableHeight = effectiveHeight - 60; // Only account for controls
                let availableWidth = effectiveWidth - 10; // Minimal margin

                // iOS specific adjustments for full screen
                if (isIOS) {
                    // iOS safari has additional viewport considerations
                    // Use window.visualViewport if available for more accurate sizing
                    if (window.visualViewport) {
                        availableHeight = window.visualViewport.height - 60;
                        availableWidth = window.visualViewport.width - 10;
                    }
                    // For full screen, use almost entire viewport
                    availableHeight = Math.max(availableHeight, viewportHeight - 60);
                    availableWidth = Math.max(availableWidth, viewportWidth - 10);
                }

                // Calculate scale based on actual PDF dimensions - be more aggressive
                const widthBasedScale = (availableWidth * 0.98) / viewport.width;
                const heightBasedScale = (availableHeight * 0.98) / viewport.height;

                // Use the larger scale to fill the screen as much as possible
                const calculatedScale = Math.min(widthBasedScale, heightBasedScale);

                // For iOS, prioritize filling the screen over minimum readability
                const minScale = isIOS ? Math.max(1.0, calculatedScale * 0.8) : 1.2;
                const finalScale = Math.max(minScale, calculatedScale);

                // Debug logging for mobile scaling
                console.log("PDF Viewer Scale Debug:", {
                    isIOS,
                    viewportWidth,
                    viewportHeight,
                    effectiveWidth,
                    effectiveHeight,
                    availableWidth,
                    availableHeight,
                    pdfWidth: viewport.width,
                    pdfHeight: viewport.height,
                    widthBasedScale,
                    heightBasedScale,
                    calculatedScale,
                    minScale,
                    finalScale,
                });

                return finalScale;
            }
            return 1.0;
        } catch (error) {
            console.error("Error calculating scale with PDF:", error);
            return this.calculateInitialScale();
        }
    }

    private async renderPage(num: number) {
        if (this.pageRendering) {
            this.pageNumPending = num;
            return;
        }

        this.pageRendering = true;

        try {
            const page = await this.pdfDoc.getPage(num);
            const viewport = page.getViewport({ scale: this.scale, rotation: this.rotation });

            // Set canvas dimensions to match viewport
            this.canvas.height = viewport.height;
            this.canvas.width = viewport.width;

            // For mobile devices, ensure canvas takes up significant screen space
            if (window.innerWidth < 768) {
                const minWidth = window.innerWidth * 0.95;
                const minHeight = (window.innerHeight - 80) * 0.95; // Account for controls

                if (viewport.width < minWidth) {
                    this.canvas.style.width = minWidth + "px";
                }
                if (viewport.height < minHeight) {
                    this.canvas.style.height = minHeight + "px";
                }
            }

            // For high-DPI displays (like iOS), scale the canvas for better quality
            const devicePixelRatio = window.devicePixelRatio || 1;
            if (devicePixelRatio > 1) {
                if (!this.canvas.style.width) {
                    this.canvas.style.width = viewport.width + "px";
                }
                if (!this.canvas.style.height) {
                    this.canvas.style.height = viewport.height + "px";
                }
                this.canvas.width = viewport.width * devicePixelRatio;
                this.canvas.height = viewport.height * devicePixelRatio;
                this.ctx.scale(devicePixelRatio, devicePixelRatio);
            }

            const renderContext = {
                canvasContext: this.ctx,
                viewport: viewport,
            };

            await page.render(renderContext).promise;

            this.pageRendering = false;

            if (this.pageNumPending !== null) {
                this.renderPage(this.pageNumPending);
                this.pageNumPending = null;
            }

            this.updatePageInfo();
        } catch (error) {
            console.error("Error rendering page:", error);
            this.pageRendering = false;
        }
    }

    private updatePageInfo() {
        this.pageInfo.textContent = `${this.pageNum} / ${this.pdfDoc.numPages}`;
    }

    private onPrevPage() {
        if (this.pageNum <= 1) return;
        this.pageNum--;
        this.renderPage(this.pageNum);
    }

    private onNextPage() {
        if (this.pageNum >= this.pdfDoc.numPages) return;
        this.pageNum++;
        this.renderPage(this.pageNum);
    }

    private zoomIn() {
        this.scale = Math.min(5, this.scale * 1.2);
        this.renderPage(this.pageNum);
    }

    private zoomOut() {
        this.scale = Math.max(0.5, this.scale / 1.2);
        this.renderPage(this.pageNum);
    }

    private rotate() {
        this.rotation = (this.rotation + 90) % 360;
        this.renderPage(this.pageNum);
    }

    private resetView() {
        this.scale = this.initialScale;
        this.rotation = 0;
        this.panCurrentX = 0;
        this.panCurrentY = 0;
        this.updateCanvasTransform();
        this.renderPage(this.pageNum);
    }

    private close() {
        this.overlay.classList.remove("active");
        this.pdfDoc = null;
        this.pageNum = 1;
        this.scale = 1.0;
        this.rotation = 0;
        this.panCurrentX = 0;
        this.panCurrentY = 0;
        this.updateCanvasTransform();
        this.hideError();
    }

    private showLoading() {
        this.loadingIndicator.classList.remove("hidden");
        this.errorMessage.classList.add("hidden");
        this.canvas.classList.add("hidden");
    }

    private hideLoading() {
        this.loadingIndicator.classList.add("hidden");
        this.canvas.classList.remove("hidden");
    }

    private showError() {
        this.hideLoading();
        this.errorMessage.classList.remove("hidden");
    }

    private hideError() {
        this.errorMessage.classList.add("hidden");
    }

    private retry() {
        // This would need the URL to be stored to retry
        this.hideError();
        this.close();
    }
}
