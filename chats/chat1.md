# Wireframes for spec design

_Started 2026-10-31 00:52 UTC_

---

## User

Create me a few wireframes for this spec
Follow contemporary UX design
Keep it simple to use and intuitive
Focus on information that causes action; user wanting to come back later for more

## Assistant

_[tool: read_file]_

_[tool: read_skill_prompt]_

_[tool: list_files]_

_[tool: read_file]_

_[tool: dc_write]_

_[tool: ready_for_verification]_

I've made eight wireframes on one canvas:

- **1a, 1b, 1c:** three takes on the Brief home page, each built around acting on what's new:
  - **1a** puts the top story first, with the key numbers and the map underneath.
  - **1b** is an inbox of what's changed since your last visit.
  - **1c** is the phone version at 375 px wide.
- **1d to 1h:** the update flow, the item panel that leads to the Hansard source, Themes, Explore, and the login and first-run screens.

**1b** includes two features the spec doesn't ask for, both meant to bring people back: **"Following"** (track a topic you care about) and **"Coming up"** (upcoming sitting days). Please confirm you want them before they go any further.

The Coverage page isn't wireframed yet.

## User

Found issues — fixing…

## Assistant

_[tool: grep]_

_[tool: dc_html_str_replace]_

_[tool: ready_for_verification]_

I've stopped the short labels, dates and links from breaking across two lines, in all the wireframes at once. Longer lines of text still wrap as before. It's being checked again now.

## User

This wireframe is not intitive at all, focus on a more fluent 2 type design system 

Ask users which jurisdiction they are from but give them the ability to switch

Create new wireframe options

## User

Found issues — fixing…

## User

<artifact-content-authored-by-others/>
Found issues — fixing…

## Assistant

_[tool: dc_html_str_replace]_

_[tool: ready_for_verification]_

I've fixed the text running over the edges in the round-2 wireframes. My earlier fix for wrapping labels was also stopping titles from wrapping, so the story cards in 2c and the mobile cards in 2f overlapped or got cut off. That fix now only applies to round 1. It's being checked again now.

## User

Found issues — fixing…

## Assistant

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: ready_for_verification]_

I've fixed the 2c labels that were breaking. It's being checked again now.

- **Story cards:** the "Mentions VAGO" pill and the chamber and date line now stay on one line each. If space is tight, the date line moves below the pill as a whole.
- **Number tiles:** the change under each number now reads "▲ 4" instead of "▲ 4 vs previous", so it no longer overlaps "See items ›".
- **2e pills:** the pills in the details panel now stay on one line each.

I didn't change 2f, because its cards don't have the pill-and-date row that caused the problem.

## User

Update wireframes for updated MD file
Remove Check for updates, but keep scope indicator saying when updates was last done

Make the wireframe interactive so I can see what the user experiences. 

Make the app visble from both mobile and desktop for the user.

## Assistant

_[tool: read_file]_

_[tool: dc_write]_

_[tool: dc_write]_

_[tool: dc_write]_

_[tool: read_file]_

_[tool: dc_write]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

Now the drawer, menus, sign-in modal and toast.

_[tool: dc_html_str_replace]_

Now the shell that shows desktop and mobile side by side.

_[tool: dc_write]_

_[tool: show_html]_

_[tool: ready_for_verification]_

I've built the interactive prototype from the updated spec. It shows desktop and phone side by side, and a toggle at the top switches between "Desktop + mobile", "Desktop" and "Mobile". It's being checked now.

- **No login page:** the app opens straight to "Which jurisdiction are you from?" and a choice of start page. You can switch jurisdiction any time from the top bar.
- **Sign-in only for refreshing:** there's no "Check for updates" banner. The top bar instead shows "Updated today, 6:00 am · Hansard to Thu 29 Oct". Clicking it shows the status of each parliament and a "Refresh" button. Refreshing asks you to sign in first (username acag, any password in the prototype). It then shows progress for each parliament, a summary, and the new items.
- **Other jurisdictions:** I added a new **Compare** tab, shown in more detail below. Comparisons also appear in other places:
  - The home page has a "Raised elsewhere, not yet here" card.
  - The headline-number tiles show where you rank, such as "2nd of 9 · others' median 5".
  - Item cards note "Also raised in NSW, Qld".
  - Developments has a "Meanwhile, at other audit offices" section.
  - Each gap shows which other offices have that topic planned or audited.
- **The Compare tab** holds:
  - "You vs others' median" for the four headline numbers.
  - Early signals from other parliaments, and issues you share with them.
  - A topics-by-parliament heatmap with your column outlined.
  - Each issue opens a panel showing mentions and program coverage in all 9 jurisdictions, with a sample quote.

**Choices you may want to change:**
- Compare is a new tab that isn't in the spec. Phones now have six bottom tabs with smaller labels.
- I styled it to look like Fluent 2 by hand. The project's attached design system is still Classical, which this prototype doesn't use.
- "Restart first run" at the top clears the saved jurisdiction and start page so you can see the first-run screen again. Desktop and mobile otherwise keep their own state.
- All data is invented for the prototype. The Hansard and office-website links go to the real parliament and office sites.

## User

Found issues — fixing…

## Assistant

_[tool: dc_html_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: ready_for_verification]_

I've fixed the uneven rows in the "Across parliaments" panel. When a parliament has no mentions, "Not raised", "Not sitting" or "Not checked" now sits on one line where the bar would be. The narrow column only shows the count. This applies on both desktop and mobile; it's being checked again now.

## User

Update wireframe with share button to refer people to URL

App URL should have get parameters to take users to a page with filter and other selections made rather than have them click around if url is shared

Collpase the download button into a single button especially on mobile so that interface is less cluttered

Do an overall UX review to make interface easier to read

## Assistant

_[tool: run_script]_

_[tool: ready_for_verification]_

I've added share links, collapsed the download buttons into one Export menu, and made a pass to make the interface easier to read. It's being checked now.

**Share and links**
- Every page now has a **Share** button. The item, issue and gap panels have one too.
- The share window shows what the link includes (for example "Compare · Victoria · Last 2 weeks"). It has Copy link, Email and Teams. There's also a prototype-only button that opens the link on the other device preview, so you can see what the recipient lands on.
- Links carry the page and selections, for example `?view=mentions&jur=NSW&period=4w&tab=reports&office=NSW&unmentioned=1`. They include the page, jurisdiction, period, filters, search, sentiment and any open panel. Opening one goes straight to that view and skips the first-run questions.
- If the recipient's saved jurisdiction is different, a slim bar offers "Switch to [your jurisdiction]". If they haven't set one yet, it offers "Set my jurisdiction". Opening a link never overwrites their own saved jurisdiction.
- The desktop address bar in the prototype frame shows the shareable link and updates as you click.

**Export**
- Copy, Word and PDF are now a single **Export ▾** button next to Share. It opens a small menu on desktop and a bottom sheet on phones.
- Gaps (CSV/Word) and Explore (CSV) use the same button, and Mentions gained a CSV export (the spec calls for one).

**Readability**
- Every page now opens the same way: a short line giving the scope, the title, one plain-language sentence, then Share and Export on the right.
- **Phone:**
  - The header is now one row: name, search, jurisdiction and the ⋯ menu.
  - The period and "last updated" chips moved into the page header.
  - The bottom bar has 5 tabs with larger labels; Explore is reached from the search icon in the header.
- **Simpler cards:**
  - Headline cards no longer repeat the sentiment reason; it's still in the item panel.
  - The number tiles now read "3 positive · 1 negative" instead of a longer list.
- There's slightly more spacing between sections and taller line height throughout.

## User

Rename header from Gaps to Potential Gaps

## Assistant

_[tool: grep]_

_[tool: run_script]_

_[tool: ready_for_verification]_

The Gaps tab is now called "Potential Gaps". The new name also appears on the start-page choice in first run, the phone's bottom bar, and the labels in the share window. The "Gaps" button on the Australia map is unchanged.

The phone's bottom bar now has a longer label in one of its five slots, so it's being checked for crowding.

## User

Rename Potential gaps

## Assistant

_[tool: run_script]_

_[tool: ready_for_verification]_

The tab now reads "Potential gaps", with a lower-case "g". The same label is used on the first-run start-page choice, the phone's bottom bar and the share window.

## User

Update to include ability for people to look at this by Sector e.g. Health, Education, Local government, etc. Come up with sectors that make sense across ACAG

## Assistant

_[tool: run_script]_

_[tool: snip]_

_[tool: grep]_

_[tool: run_script]_

_[tool: grep]_

_[tool: ready_for_verification]_

I've added the sector view, pinned Continue on the first-run screen and removed the time from the update indicator. These are being checked now.

**Whole picture or one sector**
- The app opens on **All sectors**, so every page starts with the whole picture.
- A **Sector** filter now sits next to the period picker. On phones it's a chip under the page title.
- Picking a sector filters every page and shows in the page heading, for example "Victoria · VAGO · 17–31 Oct · Health". Share links carry it too (`&sector=health`).
- There are 16 sectors, based on the spec's themes:
  - Health; Education and training; Transport and infrastructure; Housing and homelessness
  - Justice, police and corrections; Child protection and family services; Disability and NDIS; Local government
  - Environment, water and energy; Digital, data and cyber; Public finance and budget; Procurement, grants and contracts
  - Integrity and governance; Public sector workforce; Emergency management; First Nations outcomes
- Brief has a new **By sector** card listing your top sectors with "+N elsewhere". Selecting one filters every page, and selecting it again clears it.
- Compare's heatmap is now **Sectors across parliaments**. Selecting a sector name there also filters the app.
- If a sector has nothing this period, the page says so plainly and offers "Show all sectors".
- I added six cross-parliament example issues so more sectors have data. One example is council finances for Local government.

**Other changes**
- **First-run screen:** Continue now sits in a bar fixed to the bottom of the screen, so you never need to scroll to reach it. Until a jurisdiction is picked, the bar says "Choose your jurisdiction to continue".
- **Update indicator:** it now shows the date only, "Updated Sat 31 Oct · Hansard to Thu 29 Oct" (phones show "Updated 31 Oct"). I also removed "at 6:00 am" from the "Coming up" note so it matches.

## User

Found issues — fixing…

## Assistant

_[tool: run_script]_

_[tool: ready_for_verification]_

I've shortened the desktop header so it fits in one row again. The new sector picker had pushed the new-items count and the ⋯ menu past the right edge. The fix is being checked now.

- **Update label:** now just "Updated Sat 31 Oct · WA not checked". "Hansard to Thu 29 Oct" still appears in the update status popover and under the Brief title.
- **New-items count:** now reads "9 new" instead of "9 new since Mon 26 Oct".
- **Pickers:** the jurisdiction and sector pickers are slightly narrower, and their drop-down menus still line up under them.

