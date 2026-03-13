import pyxel
import random

pyxel.init(320, 192)

# Drawing Terrains to image bank 0
# Plain (3) with some variety/flowers (7, 11) - more dense and varied grass dots
pyxel.images[0].rect(0, 0, 16, 16, 3)
for _ in range(6):
    pyxel.images[0].pset(random.randint(1, 14), random.randint(1, 14), 11)
for _ in range(4):
    pyxel.images[0].pset(random.randint(2, 13), random.randint(2, 13), 7)
pyxel.images[0].pset(8, 8, 7)

# Forest (11) with trunk and leaves - more volume to tree canopy
pyxel.images[0].rect(16, 0, 16, 16, 3) # Ground
pyxel.images[0].rect(20, 4, 8, 12, 11) # Tall Broad leaves
pyxel.images[0].rect(18, 8, 12, 6, 11) # Wide Broad leaves
pyxel.images[0].rect(23, 12, 2, 4, 4)  # Trunk
# Tree highlights
pyxel.images[0].pset(20, 6, 3)
pyxel.images[0].pset(26, 8, 3)
pyxel.images[0].pset(22, 10, 3)

# River (12) with light blue highlights - more prominent wave patterns
pyxel.images[0].rect(32, 0, 16, 16, 12)
pyxel.images[0].line(32, 4, 47, 4, 6)
pyxel.images[0].line(32, 12, 47, 12, 6)
pyxel.images[0].pset(35, 2, 7)
pyxel.images[0].pset(42, 8, 7)
pyxel.images[0].pset(38, 14, 7)

# Sea (1) with white crests
pyxel.images[0].rect(48, 0, 16, 16, 1)
pyxel.images[0].pset(52, 4, 7)
pyxel.images[0].pset(60, 10, 7)
pyxel.images[0].pset(50, 12, 7)
pyxel.images[0].pset(58, 2, 7)

# Player Units (Spear, Cav, Arch) - BLUE/WHITE (12, 7, 6)
# Spear
pyxel.images[0].rect(0, 16, 16, 16, 0) # Clear
pyxel.images[0].rect(4, 20, 8, 10, 12) # Body
pyxel.images[0].rect(6, 18, 4, 4, 7)   # Head/Helmet
pyxel.images[0].line(5, 18, 10, 18, 5) # Helmet visor/crest
pyxel.images[0].line(13, 14, 13, 31, 13) # Spear pole (longer)
pyxel.images[0].pset(13, 14, 7)         # Spear tip

# Cav
pyxel.images[0].rect(16, 16, 16, 16, 0)
pyxel.images[0].rect(18, 22, 12, 8, 4)  # Horse body
pyxel.images[0].rect(20, 24, 8, 4, 5)   # Horse armor detail
pyxel.images[0].rect(22, 18, 6, 6, 12)  # Rider body
pyxel.images[0].rect(24, 16, 4, 4, 7)   # Rider head
pyxel.images[0].pset(25, 16, 5)         # Helmet detail

# Arch
pyxel.images[0].rect(32, 16, 16, 16, 0)
pyxel.images[0].rect(36, 20, 8, 10, 6)  # Body
pyxel.images[0].rect(38, 18, 4, 4, 7)   # Head
pyxel.images[0].rect(43, 22, 2, 6, 4)   # Quiver
pyxel.images[0].pset(43, 21, 7)         # Arrows in quiver
pyxel.images[0].rect(46, 18, 1, 12, 4)  # Bow (more distinct)
pyxel.images[0].pset(45, 24, 7)         # Arrow on bow

# Enemy Units (Spear, Cav, Arch) - RED/ORANGE (8, 2, 10)
# Spear
pyxel.images[0].rect(0, 32, 16, 16, 0)
pyxel.images[0].rect(4, 36, 8, 10, 8)  # Body
pyxel.images[0].rect(6, 34, 4, 4, 2)   # Head
pyxel.images[0].line(5, 34, 10, 34, 10) # Helmet visor/crest
pyxel.images[0].line(13, 30, 13, 47, 13) # Spear pole (longer)
pyxel.images[0].pset(13, 30, 10)       # Spear tip

# Cav
pyxel.images[0].rect(16, 32, 16, 16, 0)
pyxel.images[0].rect(18, 38, 12, 8, 2) # Horse
pyxel.images[0].rect(20, 40, 8, 4, 4)  # Horse armor detail
pyxel.images[0].rect(22, 34, 6, 6, 8) # Rider body
pyxel.images[0].rect(24, 32, 4, 4, 10) # Rider head
pyxel.images[0].pset(25, 32, 8)        # Helmet detail

# Arch
pyxel.images[0].rect(32, 32, 16, 16, 0)
pyxel.images[0].rect(36, 36, 8, 10, 10) # Body
pyxel.images[0].rect(38, 34, 4, 4, 2)  # Head
pyxel.images[0].rect(43, 38, 2, 6, 4)  # Quiver
pyxel.images[0].pset(43, 37, 2)        # Arrows in quiver
pyxel.images[0].rect(46, 34, 1, 12, 4) # Bow (more distinct)
pyxel.images[0].pset(45, 40, 2)        # Arrow on bow

# Sounds
# Hit
pyxel.sounds[0].set("c3e3g3c4", "n", "7", "s", 10)
# Move
pyxel.sounds[1].set("c2", "p", "2", "v", 5)
# Magic/Skill
pyxel.sounds[2].set("c4a4e4c4", "s", "4", "f", 15)
# Select
pyxel.sounds[3].set("e3", "p", "6", "v", 5)
# Death / Explosion
pyxel.sounds[4].set("c2c1", "n", "77", "f", 20)

pyxel.save("/Volumes/meiMacMedia/app/AI/AIGame/pyxel/demo1/assets/resource.pyxres")
