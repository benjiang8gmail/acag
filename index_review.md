# Review of index.html, 1 November 2026

Page reviewed: `impact/Hansards/index.html` on `main`, which matched `C:\Claude\hansards\index.html` at the time. `hansards.html` and `HansardsAnalysis.html` carry the same data, so they shared these issues.

**Status: all corrections are applied and pushed to `main`.** "What was applied" says what changed. The sections after it are the findings as first reported.

## What was applied

| Figure | Before | Now |
|---|---:|---:|
| Mentions | 2,515 | 2,487 |
| Member contributions | 985 | 977 |
| Debates | 664 | 661 |
| Sitting days with a mention | 265 | 264 |
| Tasmanian mentions | 655 | 630 |
| Victorian mentions | 489 | 487 |
| Queensland mentions | 174 | 173 |
| Tasmanian transcripts read | 89 | 88 |

- **8 records removed, not just the 3 duplicates:** TAS-0144, 0145 and 0146 are the double count (23 mentions). VIC-0182, VIC-0223, TAS-0050, TAS-0053 and QLD-0017 are headings or procedural notices in debates that already have a speaker's record, so the page's own rule says they don't count (5 mentions). VIC-0182 and VIC-0223 turned out to be the headings of Mathew Hilakari's statements (VIC-0184, VIC-0229).
- **19 summaries corrected:** the 16 listed below, plus 3 more found in the re-read of WA and SA (WA-0082, SA-0006, SA-0030). 7 others were reworded because the speaker changed or the summary talked about the record itself (VIC-0035, VIC-0111, VIC-0162, VIC-0166, VIC-0230, SA-0108, ACT-0030).
- **Speakers:** the four that needed the transcript are now named: Bev McArthur (VIC-0230), Roma Britnell (VIC-0111, also moved from "Documents" to the Road maintenance debate), Sheena Watt (VIC-0162) and Mr Parton, who moved the censure motion (ACT-0030). VIC-0078 and VIC-0169 now show no speaker, under "Documents".
- **Longer text:** the NT overview and issue 2, WA gist 6, ACT gist 1 and the national summary were corrected, and Tasmanian gist 15 was removed.
- **Extracts, repeated text:** each repeated block was tested against its transcript. 31 were faults and are gone. 11 genuine repetitions in Hansard were left alone, and shorter repeats weren't changed.
- **Extracts, WA and SA:** all 214 debate pages were re-read in the browser, and every mention count matched. Skipped text now shows as a …, which 65 extracts need. WA-0081's real answer is restored, and witnesses' answers now follow their name lines.
- **Re-read of WA and SA:** the 70 records with skipped or changed text were re-read against the text the extracts skip. That found WA-0082, SA-0006 and SA-0030, and changed two sentiment labels in `hansards.html`: WA-0005 is now attack on the government, and SA-0036 is now praise of the government.
- **Sentiment now:** 488 attack (50%), 391 neutral (40%), 98 praise (10%). The Auditor-General is attacked in 7 contributions and praised in 20.
- **Page text:** the method notes now say a … marks skipped text, explain the 5 November gap, and describe this review.
- **Scripts:** `merge.js` removes long repeated blocks, `browser_wa_sa.js` marks skipped text, and `scan_tas.js` skips a transcript whose title page shows a different date in the window.

Checked afterwards: all 977 records match the JSON on all 17 fields, a rebuild is byte-identical, 218 displayed figures and all 977 displayed contributions matched in a browser, all summary and sentiment validators pass, and `hansards.html` and `HansardsAnalysis.html` both run alone and offline.

Still open:

- The real Tasmanian House of Assembly transcript for 5 November 2025 hasn't been read, because Parliament's search doesn't list one under that date. The page says so.
- In five debates a member has more than one record, because their mentions sit in separate turns. The page now says "normally one record".
- The other AI summaries were checked against their extracts, not whole speeches.

## Result

| Question | Result |
|---|---|
| Does the page match the JSON? | Yes, exactly. All 985 records match on 17 fields, a rebuild from the JSON is byte-identical, and 228 displayed figures plus every displayed contribution matched. The one difference is deliberate: TAS-0050 drops the electorate of the wrongly named speaker. |
| Is the JSON itself right? | Not entirely. One Tasmanian transcript is counted twice, and 12 records have a wrong or missing speaker. |
| Are the AI summaries accurate? | 969 of 985 (98.4%) needed no correction. 16 do (1.6%), and 5 of those change the meaning. |

## 1. Double counting in Tasmania

Parliament's search holds a file named "HA Wednesday 5 November 2025.docx" whose title page reads "Tuesday 2 December 2025". Its 1,514 paragraphs match the real 2 December transcript, apart from one. So the same debate appears twice in the data, and the real 5 November transcript was never read. The House sat on 4 and 6 November, so one probably exists, but Parliament's search doesn't list it under that date.

Records to remove: TAS-0144, TAS-0145 and TAS-0146, which are word-for-word copies of TAS-0099, TAS-0100 and TAS-0101. Their gist and their places in Tasmanian issues 1 and 3 go too.

| Figure | Shown now | Correct |
|---|---:|---:|
| Mentions | 2,515 | 2,492 |
| Member contributions | 985 | 982 |
| Debates | 664 | 663 |
| Sitting days with a mention | 265 | 264 |
| Tasmanian mentions | 655 | 632 |
| November 2025 mentions | 444 | 421 |
| Tasmanian transcripts read | 89 | 88 |

These figures reflect removing the duplicate alone. The final figures are in "What was applied". The national text survives: the top three parliaments are still about 62%, and October 2026 is still the busiest month.

## 2. Summaries to correct

### These change the meaning

| Record | Problem | Proposed summary |
|---|---|---|
| WA-0081 | Says the member was told it was "too early to be definitive" on section 82 notices. The live Hansard shows the Auditor-General answered, "In 2025, it is two section 82s and this year it is one in progress". "Too early" answered a later question on public sector reform. The extract dropped the lines in between, so it needs repairing too. | Asked how many section 82 notifications were processed in 2024–25 and this year to date. The Treasurer referred the question to the Auditor-General, who said two in 2025 and one in progress in 2025–26. |
| VIC-0044 | Says the member said ministers first learned of the "secret tax" from the report. The member says the "entire cabinet" knew and mocks Minister Dimopoulos's claim. | Cited the Auditor-General's Office as acknowledging $1 billion of a claimed $2 billion Suburban Rail Loop saving was never funded, and said the whole cabinet knew of the 'secret tax', mocking Minister Dimopoulos's claim to have first heard of it in the Auditor-General's report. |
| WA-0024 | Says Mr Goiran argued an oversight mechanism exists. He was reading out another member's 2004 dissent (confirmed in the raw record). | Read from a 2004 report a member's dissent that an oversight mechanism was already in place, since standing orders had the Legislative Council's Public Administration and Finance Committee consult regularly with officers including the Auditor General, and noted members differed on the question then. |
| WA-0077 | Calls Mr Whitby "an official". The extract names him and places him in the government. | Said Mr Whitby refused to tell Parliament what an operation cost and is the subject of an Auditor-General investigation under a section 82 notice, and looked forward to the opinion on whether that was reasonable and appropriate. |
| SA-0096 | Treats Report No. 1 of 2026 as being about the Auditor-General's pay. SA-0095 shows it is the Governor's salary review. | Determination No. 2 of 2026, on the remuneration of the Auditor-General, Electoral Commissioner, Deputy Electoral Commissioner and Health and Community Services Complaints Commissioner, tabled in the House of Assembly. |

### These overstate an audit finding

| Record | Summary says | Hansard says | Proposed change |
|---|---|---|---|
| NT-0014 | "lacks protection from executive influence" | "lacks adequate protection" | Change to "lacks adequate protection from executive influence". |
| SA-0050 | "did not... keep value-for-money evidence" | "did not retain sufficient evidence" | Change to "or retain sufficient value-for-money evidence". |
| VIC-0122 | "unverified eligibility decisions" | "problems showing how some eligibility decisions were verified" | Change to "problems showing how some eligibility decisions were verified". |

### Smaller slips

| Record | Problem | Proposed change |
|---|---|---|
| TAS-0010 | Says Ms Finlay "also asked about an inquiry". The question was the member for Franklin's. | End with "and said the answer to the member for Franklin's question on an inquiry was awaited". |
| TAS-0151 | Says the Custodial Inspector can already table reports. The bill is what would allow it. | Noted the Auditor-General, like the Ombudsman, can table their own reports, while supporting amendments to let the Custodial Inspector do so and to shorten the tabling period to seven or 14 days instead of 30. |
| VIC-0251 | Says funding for ecological regeneration was cut. The claim is that little transition money went to it. | Said the Auditor-General is currently examining the $875 million spent on the forestry transition program, while arguing that funding for Parks Victoria has been cut and that very little of the transition money went to ecological regeneration. |
| NSW-0001 | Places the wording under a heading that actually introduces the next item. | Delete "under a heading on contractual secrecy over aggregate carbon costs". |

### Says more than the extract shows

| Record | Problem | Proposed change |
|---|---|---|
| SA-0033 | Says the Auditor-General "did not assess". The member's quote starts mid-sentence, so Hansard doesn't show who did not assess. | Quote it as it stands: "...did not assess whether the concurrent employment arrangements were justified...". |
| TAS-0069 | Says this was a reason "the motion should not pass". The Hansard sentence is garbled, so that reading isn't certain. | Said the Premier and Treasurer dismissed the Auditor-General's opinion without satisfactory explanation, which the member said should not pass either; the Treasurer interjected about corporations law. |
| WA-0021 | Says "the information Mr Barber requested". The extract doesn't say who requested it. | Change to "the information requested". |
| ACT-0032 | Says "four agency groups". The extract cuts off after group D. | Change to "in a list of agency groups". |

## 3. Wrong or missing speakers

These mostly come from a heading or tabled list picking up the previous speaker. Several also sit under the wrong debate title.

| Record | Shown | Should be |
|---|---|---|
| VIC-0035 | Jess Wilson | Emma Kealy, whose point of order holds the mention |
| VIC-0078 | The Speaker, under "Council's agreement" | No speaker: it's a tabled documents list |
| VIC-0169 | Gary Maas, under "Electoral Amendment Bill 2025" | No speaker: it's a tabled documents list |
| VIC-0182 | Richard Riordan, under "International Women's Day" | No speaker: it's only a committee report heading |
| VIC-0223 | Brad Rowswell, under "Australia Day" | No speaker: it's only a committee report heading |
| VIC-0230 | Jaclyn Symes | The member who raised the point of order against the Treasurer (needs the transcript) |
| QLD-0017 | Miss Doolan | No speaker: it's only a procedural notice, like QLD-0011 |
| VIC-0166 | No speaker | Bev McArthur. Also remove "the text names Bev McArthur as speaker" from the summary. |
| SA-0108 | No speaker | Mr Telfer |
| VIC-0111 | No speaker, under "Documents" | Unnamed member and debate (needs the transcript) |
| VIC-0162 | No speaker | Unnamed member (needs the transcript) |
| ACT-0030 | No speaker | Unnamed member, apparently moving the censure motion (needs the transcript) |

## 4. Overviews, issues, gists and national text

| Where | Problem | Proposed change |
|---|---|---|
| NT overview and issue 2 | Say "Members cited" the 2025 independence report. All these records are one member, J Davis (Johnston). | Change to "The Member for Johnston cited". |
| WA gist 6 | Says two members asked whether the minister agreed with the findings. Only Mr Zempilas did; Ms Mettam asked about a status report. | One member asked whether the Minister for Mental Health agreed with its findings and another whether she had sought a status report on all 32 taskforce recommendations. |
| ACT gist 1 | Says the minister said findings were accepted. She said recommendations were; Mr Barr said findings were. | The Chief Minister said the minister had accepted the findings, and the minister said recommendations were accepted. |
| TAS gist 15 | Belongs to the duplicate debate. | Remove with the duplicate records. |
| National summary | Calls mental health one of WA's "largest threads". It ranks fourth of six there by contributions. | Change to "section 82 notices and the office's independence in WA", or leave as a judgement call. |

Every number in the national summary checked out against the data. The other 7 overviews, 44 issues and 61 gists had no problems. Tasmanian issues 1 and 3 read correctly but include the duplicate records from section 1.

## 5. Extracts

- **Silent gaps in WA and SA:** the extract for WA-0081 joined paragraphs that aren't next to each other, with no sign anything was skipped. `merge.js` joins these with a space. Up to 105 WA and SA records have several mention paragraphs, so the same thing could have happened there. The review can't see this from the extract alone, so these need re-reading against the live pages after the fix.
- **Repeated text:** 52 extracts repeat a block of text, because overlapping excerpts were merged. It looks wrong but doesn't change any count. They are NSW-0037, 0060, 0065, 0084, 0092, 0098; VIC-0015, 0017, 0029, 0047, 0050, 0055, 0088, 0118, 0128, 0136, 0148, 0156, 0165, 0177, 0186, 0204, 0213, 0227, 0232, 0259; QLD-0004, 0009, 0042, 0045, 0049, 0062, 0064, 0065, 0073, 0080; WA-0141, 0151; SA-0030, 0060, 0095, 0112; TAS-0100, 0145; ACT-0012, 0019, 0048, 0055, 0062; NT-0010, 0012, 0013.
- **More highlights than mentions:** 31 WA, SA and Tasmanian extracts show more highlights than their mention count, because the extract includes a neighbouring speaker's mention. That isn't an error.

## 6. Flags reviewed and not treated as errors

- **TAS-0014:** flagged because the extract doesn't mention TT-Line. The full transcript does ("it seems that he has been vindicated"), so the summary is right.
- **ACT-0004, ACT-0050, TAS-0047:** labelled "Seeks audit or referral". They discuss an audit or referral without seeking one. That's debatable given the label's use on the page, so I left them as they are.

## How this was checked

- **Page against JSON:** a script compared the page's built-in data with the JSON without using the build code. I then rebuilt the page in a scratch copy, and tested the displayed page in a browser.
- **Summaries:** eight independent AI reviewers, none of whom wrote the summaries, read all 985 against their extracts, plus 8 overviews, 47 issues and 64 gists. They flagged 35 records, and I read every flag against its source, going to the transcript, raw data or live Hansard where needed. I also re-read 25 random summaries they had cleared and found no errors.
- **Limits:** summaries were checked against their extracts, not whole speeches, so a summary can only be confirmed as far as its extract goes. I didn't re-open all 985 Hansard links; I confirmed they match the JSON and point to each parliament's site. The live site needs VAGO sign-in, so I reviewed the same file from GitHub.
