#!/bin/bash

npm install
mkdir -p src/web/vendor/lightbox2/css
mkdir -p src/web/vendor/lightbox2/js
mkdir -p src/web/vendor/lightbox2/images
cp node_modules/lightbox2/dist/css/lightbox.min.css src/web/vendor/lightbox2/css/
cp node_modules/lightbox2/dist/js/lightbox-plus-jquery.min.js src/web/vendor/lightbox2/js/
cp -r node_modules/lightbox2/dist/images src/web/vendor/lightbox2/
if [ ! -f build/pdfjs.zip ]; then
    curl https://github.com/mozilla/pdf.js/releases/download/v4.10.38/pdfjs-4.10.38-dist.zip -L -o build/pdfjs.zip
fi
unzip -o build/pdfjs.zip -d build/pdfjs
mkdir -p src/web/vendor/pdfjs/build
mkdir -p src/web/vendor/pdfjs/web
cp build/pdfjs/build/*.mjs src/web/vendor/pdfjs/build/
cp -r build/pdfjs/web/standard_fonts src/web/vendor/pdfjs/web/
cp -r build/pdfjs/web/images src/web/vendor/pdfjs/web/
cp -r build/pdfjs/web/viewer.html src/web/vendor/pdfjs/web/viewer.html
cp -r build/pdfjs/web/viewer.css src/web/vendor/pdfjs/web/viewer.css
cp -r build/pdfjs/web/viewer.mjs src/web/vendor/pdfjs/web/viewer.mjs
