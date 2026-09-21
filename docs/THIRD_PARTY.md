# Third-party artwork

The Gallery includes 24 static SVGs selected from two open-source collections
listed on [FreeIcons](https://www.freeicons.org/). Files were obtained from the
original maintainers, not scraped previews, and adapted to SVGDrawer's viewport
and navy stroke. Geometry is retained; these imports support part customization
but do not claim parametric geometry or the customizable badge.

| Collection | Added | Coverage | Original source and terms |
|---|---:|---|---|
| [Lucide on FreeIcons](https://www.freeicons.org/icons/lucide) | 12 | Processor, circuit board, memory, drive, router, network/workflow, code/chart documents, folder and database | [Lucide repository](https://github.com/lucide-icons/lucide), [license](https://github.com/lucide-icons/lucide/blob/main/LICENSE): ISC, with MIT notices for Feather-derived icons |
| [Tabler on FreeIcons](https://www.freeicons.org/icons/tabler-icons) | 12 | Desktop/laptop/mobile devices, server bays, cloud networking, USB, antenna, Bluetooth, histogram, wave traces and exchange arrows | [Tabler repository](https://github.com/tabler/tabler-icons), [MIT license](https://github.com/tabler/tabler-icons/blob/main/LICENSE) |

Every imported symbol carries its own provenance in `symbol.json`, upstream license
text in `LICENSE.txt`, and the source URL plus license notices inside `source.svg`'s
`desc`. Keeping notices per symbol lets individual folders, Gallery backups and
trash/restore remain self-contained. These are attribution records, not file inventories.

Exported SVGs retain the embedded notices. Python PNG export carries the same text
in its PNG Description metadata. If another application strips metadata, redistribute
the applicable upstream notice alongside the artwork. Saved static variants retain
the source notice; recipes keep the source symbol ID or sanitized SVG as appropriate.

The five clarified existing display names describe adjustable geometry: processor
pin rows, laptop keyboard rows, database tiers, perspective server bays and selectable
waveform displays. Their original IDs and rendering controls remain unchanged.
Use names, descriptions and tags to communicate these distinctions; collection and
style labels alone are not semantic identity.
