New-Item -ItemType Directory -Path "src/web/dist" -Force
Push-Location -Path "viewer"
npm run build
Copy-Item -Path "dist/appendix-viewer.js" -Destination "../src/web/dist/_appendix-viewer.js"
Pop-Location
