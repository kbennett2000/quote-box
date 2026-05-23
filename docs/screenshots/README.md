# Screenshots

This directory holds the images referenced from the docs files. The
images aren't in git — capture them after you've installed quote-box
and have it running with at least a handful of quotes and two
profiles.

The four docs files (`install.md`, `user-guide.md`, `troubleshooting.md`,
`admin.md`) reference these paths with `![alt](screenshots/name.png)`
Markdown. Until the PNGs are added, those references will render as
broken images on GitHub — that's expected. The docs are written to
read primarily after install, not on the project page.

## What to capture

Capture each of these on the device you'd recommend in the
documentation (a laptop screen at roughly 1200–1400 pixels wide is
the target). Crop generously around the relevant UI; don't include
the browser chrome unless it matters.

| File | What to show |
| --- | --- |
| `profile-picker.png` | The "Who's reading?" page with at least one existing profile button and the new-profile form below it |
| `browse.png` | The full browse page: filter bar, tag cloud, and three or four quote cards visible |
| `browse-filtered.png` | The browse page with two tag chips selected (showing the accent color) and the **Clear filters** button visible |
| `detail.png` | A quote detail page with author, source, tag chips, and the notes section visible — pick a quote with a couple of existing notes |
| `add-quote-form.png` | The empty add-quote form, with the tag chip input visible and ready |
| `edit-quote-form.png` | The edit form prefilled with a real quote, showing the **Delete** button on the right |
| `notes-section.png` | A close-up of the notes section showing two profiles' notes — one with **Edit**/**Delete** buttons (the current profile's) and one without |
| `tags-page.png` | The tags-management page with the sorted-by-count list and the Rename/Delete actions visible |
| `display-mode.png` | A quote in display mode at near-fullscreen — the dark theme, large serif text, attribution below |

## Capturing on different platforms

- **Ubuntu**: the built-in Screenshot app (search for "Screenshot" in
  Activities), or **Shift + Print Screen** for a region selection.
- **macOS**: **Cmd + Shift + 4** for a region selection.
- **Windows**: the Snipping Tool, or **Win + Shift + S**.

## After capturing

Save each file as PNG with the exact filename listed above. Resize
to roughly 1200 pixels wide if your screenshot is larger — that's
enough resolution for a docs site while keeping file sizes
reasonable. There's no automated check; commit them when they look
right.

Once added, all four docs files will render with inline images and
no further code changes are needed.
