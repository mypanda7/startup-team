---
name: optimize-image
description: Shrink a raster image or a folder of them (modern format plus a recompressed fallback) without trusting the tool blindly - dry run first, compare the result with the original by eye, and apply only on the owner's OK. Use when the owner names an image or a public assets folder to optimise, or a page is heavy because of its images.
---

# Optimise an image

Three steps, in this order, never skipped: **dry run, verify by eye, apply on the owner's 1**.

## The project must say (in its CLAUDE.md)
- The image tool or script to use, and where it runs (many machines have no image tooling).
- Which folders hold hand-managed images, and which are already optimised by the build (leave
  those alone).
- How images are served and cached (a cache keyed by file name changes what "replace in place"
  means).
- The widest size an image is displayed at, if it is known.

If it names no tool, use one already installed on this machine and say which. Do not install
anything.

## Before optimising: prune
An image referenced by no page, stylesheet or script is dead weight. Propose deleting it instead
of optimising it. Deleting is a change like any other: list the files and get the owner's 1.

## Step 1: dry run (writes nothing)
Run the tool in report-only mode, or convert into the scratch folder, never over the source.
Show the owner a table: per image the original size, the new-format size, the fallback size, the
dimensions and the percentage saved, then the total.

Skip, and say that you skipped: vector images, icons and favicons, logos the brand rules say not
to touch, files already in the modern format, files too small to matter (a dozen kilobytes or
less), and any result that would be BIGGER than the original.

## Step 2: verify by eye (the trust gate; mandatory before applying)
For the largest savings, and for anything that looks risky:
1. Encode the original at the chosen quality and decode it back.
2. Scale both the original and the result down identically, flatten any transparency onto the
   same background, and write both as plain images into the scratch folder.
3. LOOK at both. The optimised one must be indistinguishable from the original at the size it
   is shown.

Call out degradation in words. What to expect:
- **Photos, screenshots, interface mock-ups**: lossy compression at a normal quality is clean.
  Apply.
- **Smooth gradients, glows, large flat fills**: lossy compression BANDS them. Do not convert.
  Recommend a stylesheet gradient instead (no bytes, no banding, same position), or, if it must
  stay an image, raise the quality well up and verify again.
- **Oversized dimensions** (a banner several times wider than it is ever shown): propose a
  maximum dimension of about twice the display width and dry-run again. Resizing usually saves
  more than the format does.
- **Transparency and text in the image**: check edges and small type at full size.

Report the verdict per image: the saving, and "verified intact" or "would band: use a gradient".

## Step 3: apply (only on the owner's 1)
1. Write the new-format file and recompress the fallback in place.
2. Show exactly what changed (the file list and sizes). The original is recoverable from version
   control; if the folder is not tracked, keep a copy of the originals in the scratch folder
   and say where.
3. **Wire the markup. This is not automatic.** Use a picture element with the modern format as
   the source and the fallback as the image, or point straight at the modern file if the owner
   accepts dropping old browsers. Keep the width and height attributes so the page does not
   shift.
4. For an image you decided to replace with a stylesheet gradient: make that edit instead,
   remove the asset, and move its position onto the element that draws the gradient.
5. Look at the page in a real browser at the project's breakpoints, as `team-workflow` step 7
   says for any screen change.

Local edits and one local commit are within the chain. Purging a cache, uploading to storage or
a network, and deploying are outside the working copy: `devops` PROPOSE and the owner's 1.

## Notes
- A cache that keeps a file for a long time by its name will keep serving the OLD image after an
  in-place replace. A new file name (the modern-format file has one) sidesteps that; the
  fallback needs a purge or a new name.
- Never run this over a folder the build pipeline already optimises: you would compress twice
  and gain nothing.
- Never convert a batch without looking at a sample. A table of percentages is not a check.
