# Google Ads — Master Negative Keyword List

**Drafted:** 2026-04-10 evening
**Purpose:** Apply at campaign level to every Google Ads campaign on 8-Bit Legacy. Prevents the majority of budget waste from irrelevant queries. Iterate weekly based on search terms report.

**How to use:** Paste the lists below into Google Ads → Campaigns → Keywords → Negative keywords → Add negative keywords. Use **phrase match** by default (broader than exact, narrower than broad). Flip specific terms to **broad match** if you want to catch every variant.

---

## Category 1 — Piracy / emulation / free content (CRITICAL)

These are the highest-volume waste terms for any retro game search. Add first.

```
rom
roms
romhack
rom hack
rom hacks
emulator
emulators
emulation
emulated
iso
isos
download
downloads
downloadable
free
freeware
warez
torrent
torrents
pirated
piracy
crack
cracked
cracking
patch
patched
patchfile
dump
dumped
repro
reproduction
repro cart
repro cartridge
bootleg
bootlegged
fake
replica
replicas
counterfeit
counterfeits
knockoff
knock off
flash cart
flashcart
everdrive
ezflash
r4 card
```

## Category 2 — Research / content / not buying

Users here are reading, not shopping. Don't bid on them.

```
review
reviews
reviewed
rating
ratings
walkthrough
walkthroughs
playthrough
playthroughs
guide
guides
strategy guide
cheats
cheat codes
cheat code
tips
tips and tricks
hints
wiki
wikia
price
prices
pricing
worth
value
values
how much
what is
when was
release date
released
released date
developer
developers
history
ost
soundtrack
soundtracks
music
ending
endings
spoilers
best game
best games
top 10
top ten
ranked
ranking
rankings
youtube
twitch
stream
streaming
let's play
lets play
playthrough
gameplay
trailer
trailers
teaser
teasers
cutscene
cutscenes
intro
opening
```

## Category 3 — Competitor brand names

Don't pay to show your ad when someone explicitly searched for a competitor. Their brand loyalty already decided.

```
lukie games
lukiegames
dkoldies
dk oldies
dk old
dkolds
retroplace
retroplace.com
price charting
pricecharting
videogamesnewyork
video games new york
gamestop
game stop
gamestop.com
ebay
ebay.com
amazon
amazon.com
walmart
target
best buy
retrogamingworld
retro gaming world
stone age gamer
stoneagegamer
cex
cex.co.uk
j2games
j2 games
gohastings
hastings
second spin
secondspin
retrons
retron
```

## Category 4 — Hardware mods / region swaps / modder intent

Users shopping for modded hardware or region-free kits aren't the target buyer. Different audience, different economics.

```
modded
mod chip
modchip
region free
region-free
region mod
multi region
multiregion
hdmi mod
rgb mod
osd mod
freeloader
action replay
gameshark
game genie
dev cart
development
devkit
dev kit
repair service
repair kit
repair shell
replacement shell
new shell
clear shell
custom shell
recap
recapped
capacitor kit
capacitor
capacitors
replacement lens
laser replacement
new laser
```

## Category 5 — Merchandise / collectibles (non-game)

These crawl in from retro gaming adjacency but aren't our catalog.

```
poster
posters
print
prints
t-shirt
tshirt
t shirt
shirt
shirts
hoodie
hoodies
sweatshirt
mug
mugs
pin
pins
enamel pin
keychain
keychains
sticker
stickers
decal
decals
funko
funko pop
pop figure
amiibo
amiibos
statue
statues
figure
figurine
figurines
plush
plushie
plushies
lego
lego set
cosplay
costume
costumes
bedsheet
blanket
pillow
```

## Category 6 — Parts / broken / for-parts

Users shopping for broken units looking for parts are NOT our buyers.

```
broken
not working
doesn't work
doesnt work
for parts
parts only
as is
as-is
damaged
cracked
missing
incomplete
project
repair project
to fix
needs work
scrap
junk
non working
nonworking
non-working
dead
won't turn on
wont turn on
blinking light
```

## Category 7 — Research / compatibility queries

High volume, zero intent.

```
compatible
compatibility
works with
will work
difference between
vs
versus
which is better
should i
should i buy
is it good
any good
worth it
worth buying
worth the money
reddit
forum
discord
quora
stack exchange
```

## Category 8 — Mobile / app / digital edition

People searching for mobile ports or digital re-releases aren't retro buyers.

```
android
ios
iphone
ipad
app
app store
google play
play store
mobile
phone
tablet
switch port
switch version
nintendo switch online
nso
steam
pc version
pc download
virtual console
digital download
digital edition
digital copy
psn
ps now
ps plus
xbox live
game pass
gamepass
```

## Category 9 — Age / audience exclusions

Protects margin on queries that skew toward non-buyers.

```
for kids
kids games
children
child
toddler
educational
learning
school
classroom
homework
```

## Category 10 — Non-commercial intent phrases

```
what
who
when
why
how to
how do
explain
meaning
definition
define
tutorial
lesson
lecture
documentary
podcast about
```

---

## Total count

~400 terms across 10 categories. Worth 30 minutes to paste in, then 5 minutes/week to expand based on the search terms report.

## Important exclusions (do NOT add these as negatives)

- **"cheap"** — cheap game buyers ARE the target audience for under-$20 items
- **"used"** — every product we sell is used; this is correct intent
- **"vintage" / "classic" / "retro"** — core category keywords
- **"complete"** — users searching "pokemon crystal complete in box" are our CIB buyers
- **"sealed"** — Pokemon sealed products are a product line
- **"shipping"** — this is buyer intent, not waste
- **"deal" / "sale" / "discount"** — commercial intent, want to show up here
- Console names ("nintendo", "playstation", "n64") — core categories
- Franchise names ("zelda", "mario", "sonic", "pokemon") — core catalog

## Weekly update process

Every Monday, pull the search terms report:
1. Sort by Impressions desc
2. Read the top 50 terms
3. Any term that's not a buying intent → add to the appropriate category above
4. Any term that IS a buying intent → leave it (even if 0 conversions yet — needs more data)

This list is a starting floor. It grows to ~700–1000 terms after 90 days as real search data flows in.

## Phrase vs exact vs broad match

Default recommendation: **phrase match** for most terms.

- **Phrase match** `"rom"` blocks "download rom", "nes rom", "rom hack" — broad enough to catch variants.
- **Exact match** `[rom]` only blocks the literal word "rom" — too narrow, misses "roms".
- **Broad match** `+rom` blocks anything related to rom — too broad, could block legitimate "rom stark collectibles" or similar.

Exceptions (use exact match so they don't over-block):
- `[free]` — phrase match "free" would block "free shipping" queries, which are good intent.
- `[review]` — phrase match "review" would block "review policy" etc.

Everything else → phrase match by default.
