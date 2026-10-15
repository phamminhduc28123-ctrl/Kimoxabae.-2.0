# Kimoxabae.-2.0


✅❌
To do, To do, To do, To dooooooo


Lets Fucking Go!!!!!
- ✅Add all icons Jsons date
- About me Page layout:
  + ✅ Skript
  + ❌Json Animation
  + ❌Logik Trigger Skript
  + ❌Code
- Illustration view mechanism: (done) 
  + ✅legacy section and upcoming section.
  + ✅Image upload 2 weeks ago are in Upcoming section: with caption and so. Grid viewer
  + ✅Dots River (legacy)
  + ✅Each image is a circle. blurred on the edge placed on a stream. When hovered on the image stop and get clearer.
  + ❌Clicked on open the image and the link.
  + ❌Fractal Noise Bug
- Blog phone layout fix:
  + ❌ Stack optoion
  + ❌ Thumbnail crop
- ❌Blog Font overwrite 
- ❌ Music content collect
- ❌ Storyboard parallax bug fix, add Storyline funcion/bar
- ❌ WebGL 3d Function test
- ❌ Blog Google Translate funtion plugin
- ❌ Google Analytic Built in
- Photography Page:
  + ✅Layout
  + ❌Hero?

## Adding illustrations

Add full-resolution JPG, JPEG, PNG, WebP, or GIF files to `illu/` and push them to `main`. The content workflow creates a 50%-dimension preview in `illu/preview/`; keep the original file there at full resolution for the upcoming section and fullscreen display.

Once an illustration has been on `main` for one calendar month, the daily workflow moves the original and its preview into `illu legacy/` and `illu legacy/preview/`, then updates the illustration manifest. Its age is based on the image's first commit date on `main`, not its file modification time. A matching caption in `illu/descriptions.txt` moves with the image.

Use filenames that are unique across `illu/` and `illu legacy/`; collisions stop the workflow rather than overwrite existing files. Do not add generated previews to the manifest or resize originals manually. The content workflow can also be started with **Actions → Update content manifests → Run workflow**.
  
