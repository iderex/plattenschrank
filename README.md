# plattenschrank

Over 500,000 digitised plates exist across DASCH, APPLAUSE, NAROO and DFBS, and the machine learning they need differs fundamentally from the CCD-survey kind: non-linear photometric response, artefact morphology that resembles signal, overlapping spectra, label scarcity and distribution shift between collections. The unworked part is the objective-prism plates, millions of low-resolution spectra from 1900 to 1990 that nobody evaluates because the extraction was never automated.

Planning happens on the issue tracker first. Every decision that shapes
the architecture is written down there with its reasons before the code
that depends on it exists.

Before running this on plates whose envelopes and logbooks carry people's names,
read [docs/data-protection.md](docs/data-protection.md). It says what stays on
your host, what this software will not decide for you, and which of those
statements a check holds up and which nothing does.

See [NOTICE.md](NOTICE.md) for the intended-use notice.
