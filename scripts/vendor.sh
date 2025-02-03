#!/bin/bash

npm install
mkdir -p src/web/vendor/lightbox2/css
mkdir -p src/web/vendor/lightbox2/js
mkdir -p src/web/vendor/lightbox2/images
cp node_modules/lightbox2/dist/css/lightbox.min.css src/web/vendor/lightbox2/css/
cp node_modules/lightbox2/dist/js/lightbox-plus-jquery.min.js src/web/vendor/lightbox2/js/
cp -r node_modules/lightbox2/dist/images src/web/vendor/lightbox2/
