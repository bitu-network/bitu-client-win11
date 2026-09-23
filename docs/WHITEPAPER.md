# file: docs/WHITEPAPER.md
# BITU: A Disk-Portable Mesh Network with Trust-Based Data Currency

**Working draft v0.1 — design rationale, not a finished protocol specification.**
This document captures the reasoning behind BITU as discussed so far. Several
mechanisms below are described at the level of "what problem this solves and
why it should work," not as exact wire formats or algorithms. Open questions
are marked explicitly in the final section.

---

## 1. Motivation

Two largely separate problems motivate BITU:

1. **Portable, hardware-independent node identity.** Existing peer-to-peer
   and mesh systems typically tie identity to a machine, an account, or a
   network address. BITU ties identity to a *pod* — a physical drive (or a
   volume nested inside one) — that can be unplugged from one machine and
   plugged into another without losing its identity, its data, or its
   position in the network.

2. **An incentive-compatible alternative to proof-of-work.** Bitcoin's
   security model burns real-world energy on arbitrary computation. BITU
   proposes rewarding participants instead for storing and transferring
   real data, and for doing so honestly, using a trust-based credit system
   rather than a mined, globally-scarce token.

These two problems turn out to be complementary: a pod's cryptographic
identity is what makes it possible to keep a durable, portable ledger of who
owes whom, regardless of which machine or network a pod is currently
attached to.

---

## 2. Pod Identity

A **pod** is a mounted volume — a drive letter, or a volume nested in a
folder of another (e.g. `D:\pod_1`), used to keep "My Computer" down to one
icon per physical disk while still partitioning a large disk into several
independent pods.

Each pod that opts into BITU generates an **Ed25519 keypair**:

- The **public key** is the pod's permanent identity across the entire
  system — the only identifier anything else is allowed to be indexed by.
- The **private key** is protected at rest using **Windows DPAPI**, tied to
  the current Windows user account. This was chosen deliberately over
  hardware security modules or TPM-backed keys: it requires no specialized
  hardware, works on any Windows machine, and still prevents casual theft
  of the raw key file (it's only decryptable by the same Windows account
  that generated it).

Explicitly rejected as identifiers:

- **MAC address** — Windows randomizes per-network Wi-Fi MAC addresses by
  default, and a machine may have several NICs. Not stable, not unique.
- **IP address** — DHCP-assigned, NAT-dependent, meaningless across
  subnets or over time.

Both MAC and IP are used only as **transient "reachable-at" hints**,
learned from a cryptographically verified reply, never trusted as identity
in themselves.

---

## 3. The Router

### 3.1 Scope: per-machine, not per-pod

A single machine may host several pods (several physical or logical
drives). Rather than each pod running its own networking stack, BITU uses
one **machine-level router process** shared by all pods on that machine.

This is a deliberate choice, not just a convenience: a single Wi-Fi adapter
can only be associated with one network at a time. Several per-pod router
processes would contend over the same physical adapter, causing conflicting
reconnect attempts rather than achieving real parallelism. A shared router
can still dispatch across *all* available adapters concurrently and
multiplex many pods' traffic over one already-established connection.

The router itself has **no identity of its own**. It is pure plumbing: when
challenged, it signs responses using whichever local pod's private key
matches the request, so one machine running several pods can represent
several distinct identities to the mesh simultaneously.

### 3.2 Discovery: broadcast + challenge-response

Rather than trusting any observed network address, discovery works as a
signed challenge-response:

1. A node broadcasts a **challenge**: a random nonce, addressed either to a
   specific public key or to `*` (anyone).
2. Any node holding a matching private key signs the nonce and replies.
3. The challenger verifies the signature against the claimed public key.
   Only on success does it record the sender's address as a **transient
   reachable-at hint** for that public key.

The same signing mechanism authenticates message delivery: a `deliver`
message carries a signature over its payload, verified against the
claimed sender's public key before being accepted.

### 3.3 Routing table and store-and-forward

The routing table (public key → currently-known address) is kept
**entirely in memory** and rebuilt from blank on every router start. This
was a deliberate simplification: the table is cheap to relearn by
rescanning and re-challenging, so persisting it (in JSON or SQLite) was
judged not worth the complexity for now. If a longer-lived hint is ever
needed, a small "last-known-good address" field could be kept without much
cost — this remains a possible future refinement, not a current feature.

Each node maintains a small **per-peer outbound queue**: if a message's
recipient isn't currently reachable, the message is queued rather than
dropped, and flushed automatically the next time that peer is (re)verified
via a challenge response. This gives basic store-and-forward behavior
without needing the recipient to be online at send time.

### 3.4 Beyond one network: WLAN hopping and mesh bridging

The current prototype covers LAN (always live) and whichever single WLAN
the machine happens to be associated with. The larger vision extends this
in two ways:

- **WLAN hopping.** A machine that knows the credentials to (or can freely
  join) several nearby Wi-Fi networks can periodically hop between them,
  broadcasting and listening briefly on each, and merging newly-learned
  reachable-at hints into its routing table each hop. Two nodes hopping
  independently only find each other if their dwell windows overlap; a
  fixed, wall-clock-synced hop schedule across a shared set of networks is
  the working assumption for making this reliable, though the exact
  scheduling algorithm is unresolved (see Open Questions).
- **Internet as a bridge.** A node with both Wi-Fi mesh reachability and a
  conventional internet connection can relay between physically disjoint
  WLAN clusters, gossiping routing-table entries across the bridge. Taken
  to its logical extreme, enough such nodes could connect isolated
  neighborhood meshes into a city-wide, and eventually global, network —
  contingent on solving ordinary internet-scale problems like NAT
  traversal, which have not yet been addressed in this design.

Priority for which networks to attempt is intended to favor **open
networks and ones Windows already has saved credentials for**, since these
require no new user action to join.

### 3.5 Testing without hardware

Because a machine's router loads *all* of that machine's local pod
identities into one process, two pods on the same physical machine can
address each other through the router and their traffic still round-trips
through the real socket stack (including loopback), exercising the same
discovery, signing, and delivery code path a genuine cross-machine
exchange would use. This is the intended way to validate protocol
correctness without needing multiple physical machines or networks.

---

## 4. The Ledger: Bits and Bits-IOUs (BIOUs)

### 4.1 Basic model: pairwise debt edges

BITU's economic layer is a **credit network**, structurally similar to
historical trust-line systems (e.g. hawala networks, or Ripple's original
design) rather than a shared token pool like Bitcoin. Between any two
public keys, there exists **at most one debt state**: either A owes B *n*
bits, or B owes A *n* bits — never both, never more than one edge.

Debt edges update in two ways:

- **Automated**, for data exchange: transferring data or successfully
  answering a storage-verification challenge (see 4.3) updates the edge
  between the two parties automatically.
- **Manual**, for goods and services outside the data layer: two parties
  can agree to adjust their edge directly, the same way one might record
  an informal IOU.

A bit is only earned for a *completed, verified* transfer or a *correctly
answered* challenge — never for merely claiming to hold or intend to send
data. This closes the obvious "claim credit and never deliver" failure
mode.

### 4.2 Trust horizons and Sybil resistance

Each participant maintains a personal **trust horizon**: the set of public
keys (and the debt paths through them) they're willing to have exposure
to. Bits are only meaningful *within* a trust horizon — "any bit within
your trust horizon is equally valuable to any other bit within it," but
bits are **not** globally fungible across unconnected trust horizons.

This directly addresses Sybil attacks: generating unlimited fake public
keys is free, but fake identities sitting outside everyone's trust horizon
carry no economic weight — they cannot spend, borrow, or transact with
anyone who hasn't chosen to extend trust to them. The incentive structure
is self-balancing: extending your trust horizon too far to transact with
more people increases your own exposure to being defrauded by exactly
those newly-trusted parties, so the cost of being too permissive falls on
the person who was too permissive, not on the network as a whole.

This same logic extends to runaway or fraudulent debt edges: if two nodes
create an implausibly large debt edge between themselves, other nodes
observing this can simply exclude them from their trust horizon. A bad
edge is self-isolating rather than something the rest of the network has
to absorb — and critically, one's own exposure to a fraudulent edge is
bounded strictly by the *indirect debt paths* one actually has into it,
not by the edge's raw magnitude.

### 4.3 Proof of storage without specialized hardware

BITU is not, at its core, a storage-outsourcing system, though it can
support one as a feature. For data an owner wants durably archived by
other nodes (as opposed to popular data that gets replicated organically
because serving it is profitable), the following mechanism was proposed:

1. The data owner selects a large number (e.g. 1,000 to 1,000,000) of
   random byte offsets within the file.
2. Periodically, the owner asks the storing node for the value at one of
   these offsets — without revealing which offsets were sampled overall.
3. A node that genuinely retains the whole file can answer correctly.
4. A correct answer triggers a BIOU credit to the storing node, functioning
   as ongoing "storage rent."

This avoids requiring proof-of-work-style computation or specialized
hardware; a single lucky guess has a low but non-negligible chance of
success, which becomes negligible after repeated periodic challenges. It
degrades on highly compressible or redundant files, where a dishonest node
might reconstruct sampled values without holding the full file — using
challenges over hashes of random byte ranges rather than single raw bytes
is a noted refinement for such cases, not yet incorporated.

### 4.4 Data loss and durability

Because storage itself is unpaid by default (only successful transfers and
answered challenges earn credit), a piece of data that nobody finds worth
requesting *and* whose owner never paid for sampled-storage redundancy has
no built-in protection against permanent loss if its only holder
disappears. This is treated as an acceptable edge case: by construction,
if neither the network nor the owner valued the data enough to make
serving or protecting it worthwhile, its loss carries limited real cost.
Data that *is* valuable either gets organically replicated (because
serving it pays) or explicitly protected by the owner paying for sampled
storage across multiple nodes — which also gives an early warning (a
failed challenge) before total loss, rather than only after.

### 4.5 Inflation and issuance

Any two connected parties can mint a new debt edge between themselves
simply by agreeing a transfer occurred — there is no global cap on
issuance. This does not, however, behave like unconstrained currency
inflation, because of how the credit-network structure composes:

- Issuance **outside** one's trust horizon has no effect on the value of
  bits **inside** it — a disconnected sub-graph's inflation is simply
  invisible and irrelevant to an outside observer.
- Issuance **inside** one's trust horizon, between two other trusted
  parties, is bounded in its effect: since exposure to any given edge is
  limited to one's actual indirect debt paths into it, an outrageous edge
  between two other parties devalues nothing for a third party unless that
  third party is actually exposed to it through a debt path — and per 4.2,
  a sufficiently outrageous edge tends to get pruned from others' trust
  horizons before it can propagate harm.

### 4.6 Bridging disconnected trust horizons

Two parties with no existing bridge between their trust horizons are not
permanently unable to transact. Because creating a debt edge requires no
permission, token, or gatekeeper — only mutual agreement between two public
keys — either party can simply become the bridge themselves by
establishing a direct edge. As trust clusters grow, the likelihood of a
pre-existing bridge between any two of them is also expected to increase,
but even total absence of one is not a structural barrier, only a
temporary state either side can resolve unilaterally.

---

## 5. Comparison to Existing Systems

| | Bitcoin | Typical PoW/PoS crypto | Filecoin/Storj-style storage networks | BITU |
|---|---|---|---|---|
| Sybil resistance | Mining cost | Stake cost | Storage proof + stake | Trust-horizon exclusion (social, not capital-based) |
| Resource incentivized | Arbitrary hashing (energy) | Varies | Real storage | Real storage + real transfer, tied to genuine demand |
| Value fungibility | Global | Global | Global (token) | Local to trust horizon only |
| Issuance | Fixed schedule, capped | Varies | Token-specific rules | Unbounded but exposure-bounded per party |
| Governance/backing | None (protocol) | Varies | Foundation-backed | None — no company, office, or issuer |
| Regulatory posture | Established asset class, still contested | Varies | Registered entities in most cases | Fully decentralized OSS mesh protocol; regulatory status untested |

BITU's clearest advantages over Bitcoin specifically are (a) rewarding
genuinely useful work (storage and transfer) rather than arbitrary
computation, and (b) a credit-network structure that avoids the
early-miner hoarding dynamic, since value only accrues through actual
reciprocal exchange rather than through capturing a fixed, dwindling
issuance schedule early. It does **not** resolve price volatility in any
formal sense (no peg, no redemption guarantee) beyond the informal
argument that its issuance mechanics differ structurally from a
speculative asset market — this remains a claim rather than a proven
property.

---

## 6. Open Questions (Explicitly Unresolved)

This whitepaper is a rationale document, not a specification. The
following are known gaps, to be addressed in a future revision:

- **Wire protocol details** beyond the broadcast challenge/response/deliver
  message types already prototyped (`src/cli/router.py`) — no formal
  schema, versioning, or error handling has been specified.
- **Debt edge data structure**: exact fields, signing/authentication of an
  edge update, revocation, and dispute handling when two parties disagree
  about the current state of an edge.
- **Trust horizon computation**: how a node actually computes and updates
  its own trust horizon algorithmically — this has so far been discussed
  only as a human/social judgment, not a concrete algorithm or data
  structure.
- **WLAN hop scheduling**: how independently-hopping nodes converge their
  dwell windows in practice (fixed wall-clock rotation was proposed but
  not designed in detail).
- **NAT traversal** for internet-bridged nodes — not addressed at all.
- **Per-pod network access policy**: the idea of gating which adapters a
  pod may use based on its position in the debt ledger (e.g. throttling
  network access for a pod in significant debt) was raised as a promising
  direction but not designed.
- **Byte-sampling proof refinement** for low-entropy/compressible files
  (hash-of-range challenges instead of raw byte values).
- **Persistence boundary**: whether any part of the routing table (e.g. a
  last-known-good address) should be persisted for faster warm starts, vs.
  the current fully-in-memory, rebuild-from-blank approach.
- **Regulatory posture**: acknowledged as unresolved and likely
  irresolvable in the abstract; deferred as a non-blocking concern for a
  fully decentralized, no-office, open-source protocol.

---

*End of v0.1 draft. Intended to be dropped back into a future discussion
as the baseline for producing a more complete specification.*
