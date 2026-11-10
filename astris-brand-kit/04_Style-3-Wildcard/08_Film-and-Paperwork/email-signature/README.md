# Email signature (Wildcard (Risograph))

| File | What it is |
|---|---|
| `astris-wildcard-email-signature.html` | The signature: a small table with inline styles, so it survives Gmail and Outlook. |
| `astris-wildcard-email-signature.txt` | Plain-text version, for mail apps that don't do HTML. |
| `images/astris-wildcard-signature-logo-168x168.png` | The logo tile (168 x 168 px, shown at 84 x 84 so it is sharp on phones). |

Everything in [SQUARE BRACKETS] comes from `brand-config.json`. Fill in your details there once, then run
`python3 code/build.py paper` and every signature, card and letterhead updates.

## 1. Host the image

Email can't load a picture from your computer, so the logo has to live at a public web address.
Once this kit is pushed to GitHub, every file has one. The pattern is:

```
https://raw.githubusercontent.com/[YOUR-GITHUB-NAME]/[YOUR-REPO]/[BRANCH]/astris-brand-kit/04_Style-3-Wildcard/08_Film-and-Paperwork/email-signature/images/astris-wildcard-signature-logo-168x168.png
```

Open the HTML file in a text editor and replace `images/astris-wildcard-signature-logo-168x168.png` with that full address.
(The repo must be public for the picture to show. Any other image host works the same way.)
This image is a normal file in the repo, not a Git LFS file, so the raw link serves the real picture.

## 2. Paste it into your mail app

**Gmail:** open the HTML file in your browser, select the whole signature, copy. In Gmail go to Settings, See all settings,
General, Signature, Create new, and paste. Save changes at the bottom of the page.

**Outlook (desktop):** open the HTML file in your browser, select all, copy. In Outlook go to File, Options, Mail, Signatures,
New, and paste into the box. If the picture is missing, check step 1.

**Outlook on the web:** Settings, Mail, Compose and reply, then paste into the signature box.

**Apple Mail:** Mail, Settings, Signatures, add a new one, paste, and untick "Always match my default message font".

## Good to know

- Signatures can't carry custom fonts reliably: mail apps fall back to Arial if the brand font isn't installed. That is expected.
- Keep the picture under 100 KB (this one is) so it loads straight away.
