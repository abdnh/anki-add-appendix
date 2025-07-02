New-Item -ItemType Directory -Path "src/web/dist" -Force
Copy-Item -Path "viewer/dist/appendix-viewer.js" -Destination "src/web/dist/_appendix-viewer.js"
