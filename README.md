# Full-resolution storyboard PDFs for Krita

Keep the scene names and existing Storyboard Docker comments when making a portfolio PDF. The exporter reads the scene order from your saved Krita project and pairs each scene with a full-resolution PNG from Render Animation. Images and notes stay on your computer.

## Export a storyboard

1. Save your project as a `.kra` file. The default PDF includes all saved comment fields, including fields hidden in the Storyboard Docker. Use `--images-only` for a copy that omits these comments and the scene names.
2. In Krita, choose **File → Render Animation**. Export a **PNG image sequence** at the pixel dimensions you want, in an empty folder. Turn off **Only Unique Frames**. Record the base name, first frame, and **Start numbering at** settings.
3. Unzip the exporter and open a terminal in the folder containing `storyboard_pdf.py`. The exporter runs outside Krita, so it works independently of Krita’s Python plugins. With Python 3.9 or later installed, create a virtual environment for its two dependencies. On Ubuntu or macOS, run:

   ```sh
   python3 -m venv .venv
   . .venv/bin/activate
   python -m pip install Pillow reportlab
   ```

   If Ubuntu says `ensurepip` is unavailable, install `python3-venv` using Ubuntu’s package manager, then repeat the commands above. On Windows PowerShell, you can use the virtual environment directly:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install Pillow reportlab
   ```

4. Run the exporter. For example, if your PNG sequence starts at timeline frame 8 and Krita named that first file `shot0100.png`, use this command.

   ```sh
   python storyboard_pdf.py "pitch.kra" "png-sequence" "pitch-review.pdf" --base shot --first-frame 8 --numbering-start 100
   ```

   In Windows PowerShell, use `.\.venv\Scripts\python.exe` in place of `python` in the export command. The script reads the saved project and rendered PNGs directly. If Krita’s Storyboard Docker produced an empty, incomplete, or missing PDF or SVG, you can start from step 1 with the original `.kra`. Check that the PNGs from step 2 show all the layers you want before exporting.

Timeline frame 12 in this example uses `shot0104.png`. The exporter starts a page for each scene that begins in the selected range. It keeps the PNG pixel dimensions while fitting the image on a landscape A4 page. Notes can continue onto another page. Use `--last-frame` to set an inclusive timeline end. A missing scene PNG stops the export and identifies the missing file.

For Korean or other text outside Western European characters, add `--font` followed by the path to a TrueType font that contains those characters and permits embedding. For example, on Windows with Malgun Gothic installed, add `--font "C:\Windows\Fonts\malgun.ttf"`. Choose a new output filename for every export.

To fill each PDF page with a single panel, add `--images-only` to the command. Each page follows the image's aspect ratio, with a ten-inch long edge and all source pixels preserved. This mode skips scene names, frame numbers and comments. Text drawn into the artwork stays visible.

## Verification

The command read an original three-scene Krita test document and used nonzero timeline and output numbers to pair two scenes with separately generated 3840 × 2160 PNGs. Both embedded images retained their dimensions and matched the intended scenes. A separate copy of the test index with Korean comments preserved both comments as selectable PDF text. The original test document contained no comments. The download includes the exporter and this guide.

This independent tool was developed with generative AI. Krita is a separate project. [Krita’s image sequence guide](https://docs.krita.org/en/reference_manual/render_animation.html)
