# Readwise sync is not idempotent

**Don't run a Readwise sync to "test" something.** `Readwise: Sync Book` / `Sync All` is
**not idempotent**. It rewrites each highlight's `readwiseNote` from the Readwise API's
copy, which clobbers any wikilink paths that were fixed up locally. Measured on
`Readwise/Mastery` on 2026-10-11: full-path links fell from **220 to 140**, e.g.
`[[Z/Active Experimentation]]` became `[[Active Experimentation]]` — converting resolved
links back into aspiring ones, undoing exactly what `fix-links.py` exists to do (see SKILL.md).
`## My Notes` genuinely is preserved, as the page claims; only `readwiseNote` is
overwritten. Assume `Zotero: Sync` has the same shape and don't fire it casually either.

**Recovery is counter-intuitive:** managed revisions commits the damaged version within
~30 s, so `git checkout -- <page>` restores the **damaged** copy. Go back one commit:

```bash
git -C space show '<sync-commit>^:Readwise/<Book>.md' > 'space/Readwise/<Book>.md'
```

Verify by counting `rg -c '\[\[Z/|\[\[Readwise/'` against the pre-sync commit. Grepping
two or three sample link names is not enough — it produced a false "reverted cleanly"
reading once.
