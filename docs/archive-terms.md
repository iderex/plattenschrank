# Archive terms and the acknowledgements they require

Issue #74. This document holds one entry per archive this pipeline reads, so an
operator who publishes a result can find out which obligations came with the
data rather than guessing.

Everything below was read from the archives' own pages on 2026-08-08. Each entry
names the page it came from, so a reader can re-read it rather than trusting
this file. Where a page does not state something, this document says it does not
state it and quotes nothing, because a summary of an absent term is an invention.

## The state of the four, in one table

| Archive | Licence stated | Redistribution of images | Acknowledgement requested | Persistent identifier |
| --- | --- | --- | --- | --- |
| DASCH | Not stated on the citing page | Not stated on the citing page | Yes, exact sentence given | Yes, a reference paper with a DOI |
| APPLAUSE | Yes, CC0 1.0 Universal | Follows from the licence, not stated in words | Yes, exact sentence given | Yes, a data release DOI |
| NAROO | Not established, the site did not answer | Not established | Not established | Not established |
| DFBS | Not stated, one sentence about access | Not stated | Not stated | Not stated |

One of the four publishes a licence. That is the finding this document exists to
record, and it is the opposite of the assumption the issue was written under,
which was that each archive publishes under its own terms and asks for its own
citation. Two of them ask for a citation. One states a licence. One could not be
read at all from here.

## DASCH

Read from `https://dasch.cfa.harvard.edu/citing/`.

The acknowledgement is stated as a sentence to include in a paper. Both halves
were checked against the page rather than reconstructed:

    This work has made use of data provided by Digital Access to a Sky Century @ Harvard (DASCH)

    which has been partially supported by NSF grants AST-0407380, AST-0909073, and AST-1313370

The page asks that a reference paper be cited, and it gives a DOI for it, so a
persistent identifier exists. It names further references that apply
conditionally, for work that discusses the scanner or the photometry method.
Which of those a given paper owes is a judgement about that paper and this
document does not make it.

The page states no licence and says nothing about redistributing images. The
words are absent rather than unclear: `license`, `licence` and `redistribut` do
not appear on it. It links to a Harvard terms of use page, which is where a
redistribution answer would be if there is one. That page returned HTTP 403 to
this route, so its contents are not established here and nothing in this
document should be read as reporting them.

## APPLAUSE

Read from `https://www.plate-archive.org/metadata/applause_dr4/`, the metadata
page for data release 4.

The licence is stated on the page as `CC0 1.0 Universal (CC0 1.0)`.

Redistribution of the images therefore is permitted, and that sentence is a
consequence of the licence rather than something the page says. The word
`redistribut` does not appear on it, and neither does `public domain`. What is
established is the licence name; what follows from it is the reader's inference
and this document marks it as one.

A DOI for the release is given on the page:

    https://doi.org/10.17876/plate/dr.4

An acknowledgement sentence is given, naming the funder and the participating
institutes. Its opening and its closing were checked against the page:

    Funding for APPLAUSE has been provided by DFG

    Tartu Observatory

The middle of that sentence names several institutes and was not checked word
for word, so it is not reproduced here. The sentence has to be taken from the
page rather than from this file. That is the honest position and it is also the
safer one, because an acknowledgement copied approximately acknowledges the
wrong people.

This entry covers data release 4. Earlier releases have their own metadata pages
and their own DOIs, and whether they carry the same licence was not checked.

## NAROO

Not established. The site did not answer this route:

    curl -sS -o /dev/null --max-time 20 https://naroo.obspm.fr/
    curl: (6) Could not resolve host: naroo.obspm.fr

    curl -sS -o /dev/null --max-time 20 https://nsdb.obspm.fr/
    curl: (28) Connection timed out after 20000 milliseconds

This is not a general network failure, and saying so matters because "the
network was down" and "these two hosts did not answer" are different findings.
The host that serves the observatory itself answered from the same shell at the
same time:

    curl -sS -o /dev/null -w '%{http_code}\n' --max-time 20 https://www.obspm.fr/
    301

So the two names above either moved, are served from somewhere this route cannot
reach, or are no longer in use. Which of those it is decides how this entry gets
filled in, and none of them is established here.

Nothing about NAROO's terms, redistribution, citation or identifier is recorded
in this document, and no entry for it should be inferred from the other three.

## DFBS

Read from `https://www.aras.am/Dfbs/dfbs.html`.

One sentence on the page bears on access, and it is quoted rather than
summarised because summarising it is exactly how it would become a permission it
does not grant:

    The DFBS is free for the astronomical community

That is a statement about who may use it. It is not a licence, it does not say
whether the images may be redistributed, and it names no condition. The page
carries none of `license`, `licence`, `copyright`, `redistribut`, `acknowledg`,
`cite` or `DOI`.

So for this archive there is no licence to record, no redistribution answer, no
requested acknowledgement and no persistent identifier, and the reason is that
the archive does not publish them rather than that nobody looked. The page names
a contact for questions about use of the survey, and asking is what fills this
entry in.

## What an operator should take from this

Two of the four archives tell you what to write in a paper. One of the four
tells you what you may do with the data. For the other two, an operator who
intends to redistribute images or to publish a derived catalogue is not covered
by anything written down, and the position to take is that permission has not
been established rather than that it is absent or present.

This matters beyond politeness. The decision that trained weights are not
tracked here already turns on what the archives permit, and the question of
whether archival images may be redistributed as test fixtures is entry 3 of #1,
which is the maintainer's and is not answered by this document. What this
document does is replace a guess about the four with a measurement of what each
one actually says.

## The condition this document does not yet satisfy

Issue #74 asks for two things and this is one of them. The other is that the
software carry it: a catalogue export has to emit the acknowledgement text for
exactly the archives whose data is present in the export, proved by a test over
a mixed-collection fixture and over a single-collection fixture.

There is nothing to add that to:

    git ls-files src/ tests/

returns nothing at the commit that adds this document. So the obligations above
are written down and nothing carries them into an output, and issue #74 stays
open until the export emits them and a test proves it does.

Two of the entries above also have to be filled in before an export could be
correct for all four collections, because an export cannot emit an
acknowledgement that has not been established. NAROO and DFBS are those two.
