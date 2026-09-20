// file: src/http/internal/globe/play/3-poly/index.js
export {}

const globeView = /** @type {any} */ (document.querySelector("globe-view"));

globeView.addEventListener("globe-ready", () => {
    globeView.addPolygon([
        [0, 0],
        [0, 90],
        [90, 0],
    ]);
});