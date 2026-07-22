# Adding the RoomCleaner showcase to your portfolio site

`index.html` is **fully self-contained** — one file, no build step, no external
assets (the CAD render, charts, and simulations are all inline). Three ways to
integrate it into a portfolio site, best first:

## Option A — dedicated project page (recommended)
Copy `showcase/index.html` into your portfolio repo, e.g.:

```
portfolio/
  projects/
    roomcleaner/
      index.html      <- this file, unchanged
```

Link to it from your projects grid: `/projects/roomcleaner/`. Because it's
self-contained it inherits nothing and breaks nothing — your site's styles and
this page's styles never touch.

## Option B — iframe embed inside an existing page

```html
<iframe src="/projects/roomcleaner/index.html"
        style="width:100%;height:90vh;border:0;border-radius:12px"
        title="RoomCleaner — interactive project showcase"
        loading="lazy"></iframe>
```

Good when you want it inside your site's chrome; the live sim and force
explorer work fine in an iframe.

## Option C — project card + link
Keep a screenshot card on your projects grid and link out to the hosted page
(GitHub Pages: `https://<you>.github.io/RoomCleaner/showcase/`).

## Doing this with Claude in your portfolio repo's chat
In that session, say:

> Add the repo `Jaspario1199/RoomCleaner` and copy `showcase/index.html` into
> my portfolio as a project page at /projects/roomcleaner/, then add a card for
> it on my projects grid (title: "RoomCleaner — autonomous cable robot";
> one-liner: "A ceiling-mounted cable robot that finds and picks up laundry —
> live simulation, real statics, CAD, and firmware").

Claude there can pull this file (and any repo images) once the repo is added
as a source.

## Customizing
- Byline is in the footer (`Jasper Buntinx`) — edit freely.
- The BOM prices default to hidden; the "show est. pricing" button reveals them.
- Stats in the hero (`payload`, `tests`, `$230`, …) are plain HTML — keep them
  in sync with the project as it evolves.
