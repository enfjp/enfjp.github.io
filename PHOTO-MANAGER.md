# Photo manager

The public gallery is still static and remains on GitHub Pages. The owner editor is at `/admin/`. No server, external CMS, paid account, OAuth secret, or token is embedded in this repository.

## Owner authorization

Create a **fine-grained personal access token** in your own GitHub account. Select resource owner `enfjp`; choose **Only select repositories**, then `enfjp.github.io`; grant **Contents: Read and write** only. A 30-day expiration is a reasonable starting point. Paste the token into the editor, not into ChatGPT, source files, screenshots, or issue comments. Keep a copy in a password manager only if needed. Refreshing, logging out, or inactivity clears the editor's in-memory token. The editor has no persistent credential storage.

The HTML interface is public. The credential is sent only to `https://api.github.com`, and GitHub enforces repository permissions. A guessed admin URL is not authorization. The account check permits `enfjp`; it is not a replacement for GitHub's access control. Revoking or expiring the token prevents future authenticated requests. GitHub tokens have real write powers: use the smallest repository scope and avoid untrusted browser extensions.

## Everyday use

Open the editor and connect. Changes remain in that tab until **保存并发布**. Review the confirmation before committing. Editing a title or place, changing a cover, and adding or removing a photo from Selected do not change the original photo bytes.

Upload up to 20 JPEG/PNG/WebP files per selection. Each source is decoded once and independently resized to a maximum long edge of 800, 1400, and 2048 pixels, with no enlargement or composition changes. Browser Canvas produces sRGB-oriented WebP output at quality settings 0.88, 0.90, and 0.92; exported sizes vary. Keep the source master and visually check the browser output before publishing. The editor does not identify people or automatically select the best photographs. Titles and alternative text must be entered; original file names are not public captions. Exact duplicate source-file hashes are rejected; visually similar photographs still need human review.

**下架** removes a photo from public gallery pages and the built site's image directory while retaining its catalog entry and source WebP files, allowing **恢复展示**. **删除** additionally removes the entry and unused WebP files from the current repository version. Neither operation deletes Google Drive files or local masters. Neither guarantees erasure from Git history, caches, prior artifacts, or other people's copies. A public repository is not private image storage.

Topic is the first level: Wild / Land / On the road. Place is the second level. Add or rename places in the editor. All photos referencing a renamed place update together. A place cannot be removed while referenced, including by hidden photos. Only places with published photos appear in public navigation. Each topic/place page shows up to 24 photos and uses Previous / More links, not photo sequence labels.

## Publication

The editor writes a single Git commit for a group of changes. It checks the catalog version and refuses non-fast-forward updates instead of overwriting concurrent work. Failed uploads can leave unreachable Git objects, but do not add them to a published catalog. Keep the tab open until submission completes.

`Publish photo library` builds and validates the gallery on source changes, commits generated `docs` files using the built-in workflow token, and explicitly requests a Pages build. The source remains **Deploy from a branch → main → /docs**. Workflow permissions are `contents: write` and `pages: write`; no long-lived token is needed in Actions. The editor distinguishes a Git commit from a confirmed website update by checking the public catalog's SHA-256 digest. A queued or failed deployment must not be described as live.

The renderer intentionally preserves non-gallery pages, including manual privacy edits. Use `python3 tools/migrate_photo_catalog.py`, `python3 tools/publish_gallery.py`, and `python3 tools/test_gallery.py` to validate. `tools/build.py` remains a separate full-site rebuild; carefully review its changes when rebuilding academic pages.

At 800 MB of active photo variants, the editor warns. The build blocks photo bytes above 950 MB. This is a safety budget, not a substitute for measuring the entire site's size against GitHub Pages limits. The Selected list is a subset; adding 700 images does not add 700 images to the first page.

## QA scope

Local standard-library checks cover the catalog, safe paths, generated topic/place membership, all internal references, source/output byte equality, empty and hidden collections, Selected subsets, and escaping. Offline Chromium checks cover responsive layouts, editor state changes, actual Canvas WebP encoding and the viewer. Authenticated API responses in local browser tests are synthetic; they do not establish that an owner's real token works. Managed browser policy prevented live network navigation, so no live-browser or physical-device acceptance is claimed.

Relevant primary documentation: GitHub personal-access-token management; GitHub REST Git trees/references and Pages build requests; MDN Canvas `toBlob`.
