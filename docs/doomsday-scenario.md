# The scenario this is actually for

**Three neighbours, three apartments, one building. The power is intermittent,
the internet is gone, and the phones have no bars.** Each flat has an old
laptop running the suite. They need to tell each other things.

Everything in the suite is judged against this. A feature that does not help
here is decoration, and a feature that *hinders* here is a defect however well
it behaves on an ordinary Tuesday.

**Status: adopted (panel, 2026-10-15).** Convened after the suite had been
built for months without anyone stating the scenario it was built for.

---

## What the disaster-research literature actually says

The panel's first job was to correct the picture the design had been assuming.

| | |
|---|---|
| **Tierney** (disaster sociology) | The persistent myths are panic, looting and helpless passivity, and they are wrong. What dominates is improvisation and mutual aid by people who are already there. Designing a household system around controlling access is solving a problem the evidence says is rare, at the cost of the thing that is universal: people urgently needing to pass specific local information. |
| **Quarantelli** (Disaster Research Center) | Emergent groups form *across* existing social lines. The people who end up coordinating are whoever is present, often strangers before the event. A system keyed to pre-registered individuals excludes exactly the person who turns out to matter. |
| **Solnit** (mutual aid) | Altruism is the norm, not the exception. The design posture should be "help them say it", not "verify them first". |
| **Clarke** (worst-case planning) | Beware the *fantasy document*: a plan that reads beautifully and has never been exercised. Any capability claimed but untested should be labelled as untested, loudly, because in the event nobody has time to discover it was aspirational. |

## What this settles

**1. Identity is the apartment, not the person — and that is now evidence-based.**
Quarantelli's finding is the argument: the useful fact is *which flat is still
talking*, not *who is holding the laptop*. "3B says the stairwell is blocked"
is actionable; "ron says the stairwell is blocked" requires knowing where Ron
is. The node-identity decision was made on other grounds and this ratifies it.

**2. Sign-in had to go, and this is why.**
Tierney and Solnit together: gating a household channel defends against a
threat the literature says is rare, and it blocks the thing that is certain.
A neighbour who cannot authenticate is still a neighbour with information.
*Connect first; gate later, if ever, and on purpose.*

**3. `link_hosting_proven` must stay loud.**
Clarke's fantasy document, exactly. Every node currently claims it *could*
host a wifi link and not one has ever done it. That claim is worth nothing
until a drill proves it, and the interface must say so in those terms rather
than showing a hopeful green.

**4. The information that matters is local, specific and perishable.**
Not "how is everyone", but "is the stairwell passable", "the water is back on
the third floor", "I have a working radio". This favours a single rolling
channel over private threads: in a building, almost everything worth saying is
worth saying to everyone.

**Vote 4-0** on all four.

> **Minority (Clarke), recorded.** Adopting the scenario on paper is itself a
> fantasy document until the suite is exercised under it — three machines,
> router off, mains off, for an afternoon. Until that happens this file
> describes an intention.

## On the blockchain question

Raised and **declined, with the useful half kept.**

What a blockchain adds is global consensus ordering among parties who do not
trust each other, paid for in coordination and energy. Three neighbours who
can see each other's front doors have no such problem, and nothing in the
literature suggests disaster communication fails for want of Byzantine fault
tolerance.

What is genuinely worth borrowing is the part that is not the blockchain:
**content addressing and an append-only log.** Each message's identity is
already a hash of its own content, which is what makes replication idempotent
and tamper-evident. The next step is a per-author hash chain — each message
naming its predecessor — which buys gap detection and cheap sync by comparing
head hashes, with no consensus at all. That is Git's model, and Secure
Scuttlebutt's, and it is the right size for a building.

## The exercise this file is waiting on

1. Router off, mains off, three machines on battery.
2. One node raises a wifi link; the other two join it. This is the step that
   has never been performed and the one everything else assumes.
3. A message from each flat reaches the other two.
4. One machine is switched off for ten minutes, then returns and catches up.
5. Record what the battery actually did.

Until step 2 passes, `link_hosting_proven` stays `unknown` and the suite
should keep saying so.
