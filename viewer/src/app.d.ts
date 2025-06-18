export {};

declare global {
    interface Window {
        lightbox: { [name: string]: any };
    }
}
