"""VEO-LAB: the workflow that governs measurement methodology.

VEO's scoring specifications are data, authored by VEO-LAB and published under a version
and a checksum. This package is how a specification gets from a draft to a published
methodology, and what happens to scores that were computed under an older one.

Four rules hold the whole thing together, and each of them is enforced by code rather
than by convention:

1. **A published version is immutable.** Not "shouldn't be edited" — cannot be. Every
   score VEO has ever shown cites a version and a checksum; if the bytes behind one of
   those checksums could move, every historical report becomes unfalsifiable. Changing a
   specification means creating a new version. (:mod:`veo.lab.versions`)
2. **Re-scoring preserves both numbers.** When an old result is recomputed under a new
   specification, the original and the recomputed value are both kept, each labelled with
   the version and checksum that produced it. (:mod:`veo.lab.rescore`)
3. **A checksum mismatch is a hard error.** A stored specification that does not hash to
   its recorded checksum is refused, never repaired. (:mod:`veo.lab.versions`)
4. **Publishing requires the golden fixtures to have been run** and to have passed, for
   the exact checksum being published. (:mod:`veo.lab.golden`)

The router in :mod:`veo.lab.router` is deliberately not mounted here; see
``INTEGRATION_REQUEST.md``.
"""
