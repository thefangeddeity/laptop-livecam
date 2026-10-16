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
