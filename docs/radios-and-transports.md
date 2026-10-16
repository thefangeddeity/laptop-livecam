# What each radio can actually do, and why the house went quiet

Two questions, both answered by measurement rather than by what a driver
advertises. Everything below was taken on 2026-10-16 from the three nodes.

---

## "If Androids can transmit WiFi, why can't a laptop?"

They can. Two of the three nodes list `AP` among their supported interface
modes, which is the mode a phone's hotspot runs in:

| node     | chip / driver        | supported modes                                            |
|----------|----------------------|------------------------------------------------------------|
| tanzania | RTL8821CE, `rtw88`   | IBSS, managed, **AP**, AP/VLAN, monitor                    |
| tina     | RTL8188CE, `rtl8192ce` | IBSS, managed, **AP**, AP/VLAN, monitor, **mesh point**, P2P-GO, P2P-client |
| ariana   | Broadcom (macOS)     | client only — no AP, no IBSS, no 802.11s from userspace    |

So the capability is there on the Linux nodes. What is missing is one line
further down, and it is the whole answer:

```
$ iw phy phy0 info | grep -A1 'interface combinations'
	interface combinations are not supported
```

Both cards say that. It means the radio can run **one** interface at a time.
It can be a client, or it can be an access point. It cannot be both.

That is the real difference from a phone, and it is not about Linux or about
laptops. A phone hotspot keeps working because the phone has a *second* radio
for its uplink — the cellular modem. It serves wifi to you on one radio and
reaches the internet on another. A phone forced to use its wifi radio for both
has the same problem, which is why tethering over wifi while staying on wifi
is awkward on phones too. Some newer chipsets advertise concurrency
(`#channels <= 1` combinations, or two-radio designs); these two do not.

So a laptop here can transmit wifi, at the price of being on no network while
it does. For a household where the router is the thing that died, that trade
is worth taking — one node becomes the AP, the rest join it, and the mesh runs
over that. For a household where the radios work and the *internet* died, it
is the wrong trade: everyone is already on the LAN.

What is NOT yet true, and should not be claimed:

- `hostapd` is installed on neither Linux node.
- No node has ever raised an AP. `link_hosting_proven` is `unknown` on all
  three, and `unknown` is not `false` — it means nobody has tried.
- The Realtek drivers' AP support is **advertised, not measured**. rtw88 and
  rtl8192ce both have a history of AP mode working in a narrow set of
  channels and widths and failing outside it. Until a node has actually
  beaconed and carried a client, this stays a driver claim.
- ariana cannot host at all. macOS has not exposed AP or IBSS from userspace
  since Internet Sharing moved behind entitlements, and the legacy `airport`
  tool has been gutted — its `--help` no longer lists an IBSS or create
  option. Hosting from ariana would need the GUI, not a script.

The drill that would settle it needs someone at the keyboard, because the
node running it drops off the network the moment it starts.

---

## "Turned off tanzania's wifi but still no messages over BLE or mDNS, why?"

Three separate reasons. The first is the one that mattered.

### 1. The bridge was installed everywhere and scheduled nowhere

elemesh was delivering the whole time. With the wifi off, ariana's link table
showed a live Bluetooth link to tanzania, heard seconds ago, up for sixteen
minutes. Messages were crossing. They landed in elemesh's own database.

Every UI in the suite — the viewer's Messages card, the full client — reads the
*messenger's* SQLite. Nothing reads elemesh. `message-buffer` exists precisely
to move records between the two, it was installed on all three nodes, and it
had never run on any of them. The proof was the absence of its delivery
ledger: the file it writes on every single run did not exist on any node.

So the mesh worked, the viewer worked, and the two were not connected.

Fixed: `livecam-buffer.timer` on the Linux nodes and `com.livecam.buffer` on
ariana, every 5s, enabled and running.

### 2. tina has no Bluetooth at all

Not disabled — absent. `bluez` is not installed, there is no
`/sys/class/bluetooth`, no Bluetooth device on the PCI or USB buses, and
elemesh logs the consequence every time it starts:

```
WARN elemesh: ble transport down, retrying: no Bluetooth adapter:
  org.bluez was not provided by any .service files
```

tina is a LAN-only node. When the wifi goes, tina leaves the mesh entirely —
and tina is the only node serving TLS. A USB Bluetooth dongle is the whole fix
and costs about what a sandwich costs; until then, plan for two nodes off-LAN,
not three.

### 3. mDNS is discovery, not a transport

`mdns-announce` publishes a service record so peers can find each other. It
carries no messages. Nothing can arrive "over mDNS" — a message arrives over
the LAN path that mDNS helped find, and with the wifi off there is no LAN
path. BLE was the only transport in play, and point 1 explains the silence.

---

## The defect this uncovered: one message, two rows

With the bridge finally running, three messages were sent — one from each node
— and the stores held six rows. Every message appeared twice.

A message is addressed by the hash of its content *and its timestamp*, which
is what lets two nodes agree they hold the same message with no coordinator.
But elemesh stamped everything with its own clock on write. Measured directly:

```
POST /v1/rooms/test/messages  {"text":"...","ts_ms":1700000000000}
  -> {"ts_ms":1792119384300}        # its own clock, the supplied one ignored
```

So the same message arriving over the LAN and over the mesh had two
timestamps, two hashes, and became two messages.

Two fixes, and the second is the real one:

- **The buffer no longer relays what it did not author.** elemesh replicates
  between nodes by itself; a node re-publishing a message it merely heard was
  pointless as well as destructive. Each message now reaches the mesh exactly
  once, from the node that said it.
- **elemesh honours a supplied timestamp.** `POST` takes an optional `ts_ms`.
  Omitted, nothing changes. Supplied, it is kept — except a stamp in the
  future, which is clamped to now, because `ts_ms` drives both ordering and
  the retention cutoff and one far enough ahead would sort above every real
  message and never be pruned. A skewed clock should still be heard; it
  should not get to pin itself to the top.

That second fix is what makes store-and-hold honest. A message written while
the radios were off now reaches the mesh carrying *the time it was said*,
not the time the radios came back.

It was still not enough, and the reason is worth keeping. With the mesh
honouring the timestamp to the **millisecond**, the store kept
**microseconds** — so `.630540` came home as `.630000`, a different string,
a different hash, one more duplicate. Behind that sat the real problem: three
separate pieces of code computed a message's id, and they agreed only by
accident of formatting.

So identity is now defined once and the same way in all three:

```
id = sha256( room | author | EPOCH_MILLISECONDS | text )
```

Milliseconds because that is the coarsest precision any transport here
promises, and an identity is only as fine as its least precise carrier. The
same change makes `+00:00`, `Z` and a bare naive stamp hash alike, which
matters because this fleet has emitted all three for the same instant.

`canonical_ms` therefore exists three times — in `server.py`, in `sync-peers`
and in `message-buffer` — and the three must stay identical. That is a seam,
and it is written down in all three places rather than left to be found.

### Measured after

| | sent | ariana | tanzania | tina | each mesh |
|---|---|---|---|---|---|
| before any fix | 3 | 6 | 6 | 8 | 3 |
| after the export guard | 3 | 7 | 7 | 7 | 3 |
| after honouring ts_ms | 3 | 8 | 8 | 8 | 6 |
| after unifying identity | 3 | **3** | **3** | **3** | **3** |

Held at three across twelve buffer ticks and six sync ticks, in the right
order, attributed to the right node.

---

## Still open

- **ariana's AP drill.** `link_hosting_proven` is `unknown` on all three. The
  drill needs someone at the keyboard because the node running it leaves the
  network to do it.
- **tina's Bluetooth.** A USB dongle is the entire fix. Until then, two nodes
  off-LAN, not three.
- **`/usr/lib/ele-messenger/server.py` is package-owned** (ele-messenger
  1.3.6-1) on tanzania. The live copy carries the fix now; the next package
  upgrade reverts it. Needs a version bump and a rebuild.
- **Three divergent checkouts of the messenger.** The same commit message
  appears in three repos under three different SHAs, and only tanzania's has
  the mesh daemon and the recent work. ariana's has no remote at all and
  tracks `ele.db` and `__pycache__`. The fix is one source of truth with the
  other two tracking it; it touches a running deployment, so it is its own
  job.
- **The buffer rescans the whole room every tick.** Fine at household volume,
  measured at no load. Each mesh message carries a `cursor`, which is the
  incremental read this should use before the store gets large.
