# ADR-0012: Career matching

**Status:** deferred (2026-10-17)

A transparent matcher needs job requirements to compare against a profile. With ~1 visible
tag per job, any "match score" would mostly reflect title words and location and would
overstate what is known. The navigation therefore has no "Kecocokan Karier" entry.

The planned baseline (after ADR-0011's extraction exists): explicit filters (role family,
location, employment type, experience) plus weighted skill overlap, returning matched and
missing skills per job, never presented as a probability of being hired, and evaluated on
a reviewed set of personas before being called accurate.
