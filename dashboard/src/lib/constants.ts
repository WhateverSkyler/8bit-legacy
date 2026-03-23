export const CONSOLE_TAGS: Record<string, string> = {
  NES: "nes #nintendo",
  Nintendo: "nintendo",
  "Super Nintendo": "snes #supernintendo",
  SNES: "snes #supernintendo",
  "Nintendo 64": "n64 #nintendo64",
  N64: "n64 #nintendo64",
  "Game Boy": "gameboy #nintendo",
  "Game Boy Color": "gameboycolor #gbc",
  "Game Boy Advance": "gameboyadvance #gba",
  GameCube: "gamecube #nintendo",
  Wii: "wii #nintendo",
  "Sega Genesis": "segagenesis #sega",
  Genesis: "segagenesis #sega",
  "Sega Saturn": "segasaturn #sega",
  Dreamcast: "dreamcast #sega",
  PlayStation: "playstation #ps1 #sony",
  PS1: "playstation #ps1",
  "PlayStation 2": "ps2 #playstation2",
  PS2: "ps2 #playstation2",
  Xbox: "xbox #originalxbox",
  "Atari 2600": "atari #atari2600",
};

export const CONSOLE_OPTIONS = [
  "NES",
  "SNES",
  "Nintendo 64",
  "Game Boy",
  "Game Boy Color",
  "Game Boy Advance",
  "GameCube",
  "Sega Genesis",
  "Sega Saturn",
  "Dreamcast",
  "PlayStation",
  "PlayStation 2",
  "Xbox",
  "Atari 2600",
] as const;

export const POST_TEMPLATES = {
  new_arrival: {
    label: "New Arrival",
    captions: [
      "Just added to the shop! {product_name} for only ${price}. Tested, cleaned, and ready to play. Link in bio!",
      "New drop alert! {product_name} — ${price}. Every game is quality-checked before it ships. Shop now at 8bitlegacy.com",
      "{product_name} just hit the shelves for ${price}. Grab it before it's gone! Link in bio.",
    ],
    hashtags:
      "#retrogaming #{console_tag} #8bitlegacy #retrogames #vintagegaming #gamecollecting #gamecollector",
  },
  deal_of_the_day: {
    label: "Deal of the Day",
    captions: [
      "Deal of the Day! {product_name} — just ${price}. Compare that to what other retro stores charge... we'll wait. 8bitlegacy.com",
      "Today's pick: {product_name} for ${price}. Quality games, fair prices. That's the 8-Bit Legacy difference.",
      "Why overpay? {product_name} is just ${price} at 8-Bit Legacy. Every order quality-checked. Link in bio!",
    ],
    hashtags:
      "#retrogaming #{console_tag} #8bitlegacy #retrogamedeals #gamingdeals #cheapgames #retrocollecting",
  },
  nostalgia: {
    label: "Nostalgia",
    captions: [
      "Remember spending hours playing {product_name}? Those were the days. Relive the memories — ${price} at 8bitlegacy.com",
      "This one hits different. {product_name} — a certified classic. Pick it up for just ${price}. Link in bio.",
      "Tell us your favorite memory with {product_name}. This classic is available now for ${price}!",
    ],
    hashtags:
      "#retrogaming #{console_tag} #nostalgia #90sgaming #80sgaming #childhoodmemories #8bitlegacy #throwback",
  },
  collection_spotlight: {
    label: "Collection Spotlight",
    captions: [
      "Building your {console} collection? We've got you covered with tested, affordable games starting at prices way below the competition. 8bitlegacy.com",
      "The {console} library is stacked. Browse our full selection of tested games at 8bitlegacy.com — link in bio!",
      "Your {console} collection deserves better than eBay gambles. Every 8-Bit Legacy game is quality-checked before it ships.",
    ],
    hashtags:
      "#retrogaming #{console_tag} #gamecollection #gamecollecting #8bitlegacy #retrocollection",
  },
  did_you_know: {
    label: "Did You Know?",
    captions: [
      "Did you know? {trivia}\n\nShop retro games at fair prices: 8bitlegacy.com",
      "Gaming history: {trivia}\n\nWe carry thousands of retro titles at prices that don't make you cry. Link in bio!",
    ],
    hashtags:
      "#retrogaming #gamingtrivia #gaminghistory #8bitlegacy #retrogames #gamingfacts",
  },
} as const;

export const GAMING_TRIVIA = [
  "The original Super Mario Bros. cartridge has sold for over $2 million at auction — but you can play it for way less at 8-Bit Legacy.",
  "The Nintendo Entertainment System saved the video game industry after the crash of 1983.",
  "Sonic the Hedgehog was designed to be Sega's answer to Mario — and the rivalry defined a generation of gaming.",
  "The Game Boy sold over 118 million units worldwide. Its library of games is still one of the best ever.",
  "The Legend of Zelda was one of the first console games to include a battery-backed save feature.",
  "Street Fighter II is considered the game that popularized the fighting game genre worldwide.",
  "The N64 controller was the first major console controller with an analog stick.",
  "Pokemon Red and Blue were originally released in Japan in 1996 as Pocket Monsters Red and Green.",
  "The PlayStation was originally designed as a CD-ROM add-on for the Super Nintendo.",
  "Tetris is the best-selling game of all time with over 500 million copies sold across all platforms.",
  "The Sega Genesis was the first 16-bit console to gain significant traction in North America.",
  "Super Metroid is consistently ranked as one of the greatest video games ever made.",
  "The SNES had a secret chip in Star Fox called the Super FX chip that enabled 3D graphics.",
  "Donkey Kong was originally going to be a Popeye game, but Nintendo couldn't get the license.",
  "The Atari 2600 was the first console to use swappable game cartridges.",
];

export type PostTemplateKey = keyof typeof POST_TEMPLATES;
