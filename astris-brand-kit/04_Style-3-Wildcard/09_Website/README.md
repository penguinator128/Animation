# Website starter (Wildcard (Risograph))

| File | What it is |
|---|---|
| `favicons/` | `favicon.ico` (16, 32 and 48 px inside), `favicon-32.png`, `apple-touch-icon-180.png`, `icon-192.png`, `icon-512.png`, `favicon.svg`, `site.webmanifest`, and a check sheet |
| `astris-wildcard-og-image-1200x630.png` / `.jpg` | The picture that shows when a link to your site is shared |
| `astris-wildcard-website-hero-desktop-mockup.jpg` | A picture of how the top of the site could look on a computer |
| `astris-wildcard-website-hero-mobile-mockup.jpg` | The same on a phone |
| `tokens.css` / `tokens.json` | The style's colours, fonts, sizes and spacing as variables |
| `astris-grain-512.png` | A small seamless grain tile for the page background |
| `preview.html` | A static page built from the tokens. Open it in a browser (keep it inside the kit folder so it can find the fonts) |

The hero mock-ups are pictures, not a working site. `preview.html` is a real, static page you can start from.

## Favicons: paste this into your page's `<head>`

```html
<link rel="icon" href="/favicon.ico" sizes="48x48">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon-180.png">
<link rel="manifest" href="/site.webmanifest">
```

Put the files from `favicons/` at the top level of your site.
The 16, 32 and 48 px icons use the logo without its sprocket holes, because at that size the holes turn to blur.
The larger icons and the SVG use the full logo.

## Sharing image

```html
<meta property="og:title" content="ASTRIS PRODUCTIONS">
<meta property="og:image" content="https://[WEBSITE]/astris-wildcard-og-image-1200x630.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
```

## Tokens

Link `tokens.css`, then use the variables: `background: var(--astris-bg); color: var(--astris-fg); font-family: var(--astris-font-display);`
`tokens.json` holds the same values for design tools and build scripts.

Fonts: Anton and Space Grotesk are free (SIL Open Font License). The files are in `code/fonts/`, and both are on Google Fonts. See `fonts.md` at the top of the kit.
