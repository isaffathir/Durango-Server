"""Ancora — the tutorial island, laid out to fit the client's built-in Ancora guide.

The 5.2.1 client ships the whole Ancora tutorial (PlayGuide/tutorial_play_guide_flow + _event): K's CPR,
the dog Pia leading the way north, dates by the train, the stream, the brachiosaurus lake, the thorn-vine
obstacle, Charlie's bonfire, the survivors' shipyard and the escape raft. Everything in it is positioned
in *world tiles* that are hard-coded in the client (Dog_SetPOI_Tile ...) or placed through terrain
landmarks (trigger volumes, thorn bushes, NPCs, animals, props). This script builds a terrain whose
geography matches those coordinates and places the landmarks so the guide plays out as in the original:

  spawn (60,55) near the train wreck → dog waypoints (63,60) (74,67) (80,78) (94,87) (125,96) (134,110)
  (139,115) (144,118) (186,119) (211,118), farewell (195,119) → raft at (208..211,115..118)

Server-side props (tutorial bonfire 9001, escape raft 9000) go through pois.yml camp_artifacts.

Usage (from tools/terraingen):  python ancoragen.py [--out ../../server/data/terrains/extracted] [--id ancora01]
"""
import argparse, json, math, os, random, struct
from collections import deque

from terraingen import Noise, signed_distance, to_sbytes, png_write, B, ROCK, BIOME_COLOR

W = H = 256
TROP, GRASS, BEACH, LAKE, OCEAN = B['TropicalForest'], B['Grassland'], B['SandBeach'], B['Lake'], B['WarmOcean']

# ── the story path (world tiles) ──────────────────────────────────────────────────────
ENTRY = (60, 55)
DOG_PATH = [(60, 55), (63, 60), (74, 67), (80, 78), (94, 87), (125, 96), (134, 110), (138, 113), (139, 115),
            (144, 118), (151, 118), (160, 119), (186, 119), (195, 119), (205, 118), (209, 116)]
CORRIDOR = 3.0            # tiles either side of the path guaranteed walkable

# land = union of ellipses (cx, cy, rx, ry) — a crescent running from the train (SW) to the shipyard (NE)
BLOBS = [(66, 58, 28, 24), (94, 90, 22, 18), (124, 102, 24, 18), (148, 121, 22, 9), (178, 121, 24, 8), (210, 116, 24, 10)]
LAKES = [(86, 88, 4.5), (124, 104, 7.0), (219, 110, 2.5)]          # stream pond · brachio lake · shipyard pond
GRASS_PATCHES = [(62, 56, 14), (151, 118, 7), (175, 118, 6)]
# thorn-vine wall: rock from x0..x1 at rows y0..y1, open only at the gap (filled with thorn bushes)
WALL = dict(x0=96, x1=180, y0=113, y1=115, gap=(137, 139))
BOAT_TILE, BOAT_SIZE = (208, 115), 4
BONFIRE_TILE = (151, 118)

# ── landmark library ───────────────────────────────────────────────────────────────────
LM = {}
def lm(id_, prefab): LM[id_] = prefab
lm(1, 'Models/Ancora/Props/thornbush.prefab')
lm(2, 'Models/Ancora/Props/raft_big_underconstruct.prefab')
TRIGGERS = ['trigger_arrive_firststep', 'trigger_gather_fruits', 'trigger_arrive_river', 'trigger_wash_yourself',
            'trigger_arrive_lake', 'trigger_sound_brachio_01', 'trigger_sound_brachio_02', 'trigger_arrive_brachio',
            'trigger_arrive_obstacle', 'trigger_fatigue_full', 'trigger_arrive_bonfire', 'trigger_arrive_victims',
            'trigger_arrive_overpass', 'trigger_arrive_madman', 'trigger_phenaco_safari', 'trigger_arrive_beach',
            'trigger_arrive_shipyard', 'trigger_arrive_eastlake', 'trigger_manipulate_start', 'trigger_depart_ancora']
for i, t in enumerate(TRIGGERS): lm(10 + i, f'Models/Ancora/Triggers/{t}.prefab')
NPCS = ['F_NPC_Player_First', 'M_NPC_Player_Cook_A', 'M_NPC_Player_Cook_B', 'M_NPC_Player_Cook_C', 'M_NPC_Player_Cook_D',
        'F_NPC_Player_Cook_E', 'M_NPC_Player_Cook_F', 'F_NPC_Player_Cook_G', 'F_NPC_Player_Cook_H', 'F_NPC_Player_Cook_I',
        'M_NPC_Player_Cook_J', 'M_NPC_Player_Worker_A', 'F_NPC_Player_Worker_B', 'M_NPC_Player_Worker_C', 'F_NPC_Player_Worker_D',
        'M_NPC_Player_Worker_E', 'M_NPC_Player_Overpass_A', 'F_NPC_Player_Overpass_A', 'M_NPC_Player_Madman',
        'M_NPC_Player_Homeless_A', 'M_NPC_Player_Search']
for i, n in enumerate(NPCS): lm(40 + i, f'Models/Ancora/NPC/{n}.prefab')
for i, n in enumerate(['bag01_ancora', 'bag02_ancora', 'bag03_ancora', 'bag04_ancora', 'bag05_ancora', 'bag06_ancora']):
    lm(70 + i, f'Models/Ancora/NPC/{n}.prefab')
ANIMALS = ['Brachio_ancora', 'BrachioSmall_ancora', 'Phenaco_group', 'Compso_ancora', 'Edmontosaurus_ancora']
for i, n in enumerate(ANIMALS): lm(80 + i, f'Models/Ancora/Animals/{n}.prefab')
lm(90, 'Models/Landmark/Static/ST_train_wreckage_01_a.prefab')
lm(91, 'Models/Landmark/Static/ST_train_wreckage_01_b.prefab')
lm(92, 'Models/Landmark/Static/ST_train_wreckage_01_c.prefab')
lm(93, 'Models/Landmark/Static/ST_highway_01.prefab')
BY_NAME = {v.split('/')[-1][:-7]: k for k, v in LM.items()}

def R(deg): return int(round((deg % 360) / 2)) & 0xFF        # LandmarkInfo.Rotate = degrees / 2

# (prefab short name, x, y, rotation degrees)
PLACEMENTS = [
    # train wreck south of the spawn, running east-west
    ('ST_train_wreckage_01_a', 58, 49, 90), ('ST_train_wreckage_01_b', 66, 49, 90), ('ST_train_wreckage_01_c', 50, 50, 90),
    # trigger volumes: boxes are long along local X → rotate 90 when the path runs east-west
    ('trigger_arrive_firststep', 66, 63, 0), ('trigger_gather_fruits', 71, 66, 0),
    ('trigger_arrive_river', 84, 82, 0), ('trigger_wash_yourself', 90, 85, 90),
    ('trigger_arrive_lake', 106, 90, 90), ('trigger_sound_brachio_01', 113, 93, 90), ('trigger_sound_brachio_02', 120, 95, 90),
    ('trigger_arrive_brachio', 129, 100, 0), ('trigger_arrive_obstacle', 138, 111, 0),
    ('trigger_fatigue_full', 142, 117, 90), ('trigger_arrive_bonfire', 147, 118, 90),
    ('trigger_arrive_victims', 160, 119, 90), ('trigger_arrive_overpass', 166, 119, 90), ('trigger_arrive_madman', 174, 119, 90),
    ('trigger_phenaco_safari', 180, 119, 90), ('trigger_arrive_beach', 186, 119, 90), ('trigger_arrive_shipyard', 199, 118, 90),
    ('trigger_arrive_eastlake', 216, 113, 0), ('trigger_manipulate_start', 208, 112, 0), ('trigger_depart_ancora', 210, 117, 0),
    # thorn vines close the only gap in the rock wall
    ('thornbush', 137, 114, 0), ('thornbush', 138, 114, 20), ('thornbush', 139, 114, 340),
    # brachiosaurs in the lake, an edmontosaurus grazing, compsognathus near the start
    ('Brachio_ancora', 124, 104, 200), ('BrachioSmall_ancora', 128, 101, 160), ('Edmontosaurus_ancora', 112, 100, 90),
    ('Compso_ancora', 70, 60, 45), ('Phenaco_group', 183, 116, 0),
    # Charlie's bonfire camp (server places the bonfire artifact itself at BONFIRE_TILE)
    ('F_NPC_Player_First', 152, 119, 250), ('M_NPC_Player_Cook_B', 150, 120, 120), ('F_NPC_Player_Cook_H', 153, 116, 300),
    ('M_NPC_Player_Homeless_A', 148, 121, 0), ('M_NPC_Player_Cook_A', 149, 116, 60), ('bag01_ancora', 154, 120, 0), ('bag02_ancora', 147, 119, 0),
    # the overpass with the confused survivors
    ('ST_highway_01', 168, 125, 90), ('M_NPC_Player_Overpass_A', 168, 121, 0), ('F_NPC_Player_Overpass_A', 170, 120, 330),
    ('M_NPC_Player_Madman', 175, 121, 180), ('M_NPC_Player_Search', 178, 116, 90), ('bag03_ancora', 171, 121, 0),
    # the shipyard: raft under construction + the survivors building it (Worker_E = "leader-like person", id 502)
    ('raft_big_underconstruct', 210, 117, 0),
    ('M_NPC_Player_Worker_E', 206, 117, 90), ('M_NPC_Player_Worker_A', 212, 114, 270), ('M_NPC_Player_Worker_C', 205, 113, 45),
    ('F_NPC_Player_Worker_B', 213, 119, 250), ('F_NPC_Player_Worker_D', 204, 120, 130), ('M_NPC_Player_Cook_D', 211, 121, 200),
    ('F_NPC_Player_Cook_E', 202, 116, 90), ('M_NPC_Player_Cook_F', 203, 118, 60), ('F_NPC_Player_Cook_G', 214, 117, 270),
    ('F_NPC_Player_Cook_I', 207, 120, 180), ('M_NPC_Player_Cook_J', 201, 113, 30), ('M_NPC_Player_Cook_C', 215, 112, 300),
    ('bag04_ancora', 204, 115, 0), ('bag05_ancora', 213, 121, 0), ('bag06_ancora', 200, 118, 0),
]

# naturals (entity types from natural.json; all of them survive tropical_forest/grassland/beach/lake)
DATE_PALM = 14003
STONES, ROCKS = [13038, 13039], [12159, 12160, 12161, 12165, 12167, 12168, 12171, 12172]
REEDS = [11033, 11003]
STICK_BUSHES = [11025, 11008]
BEACH_BUSH, BEACH_TREE = 11031, 14021
LOG_TREES = [14009, 14020, 14024]
GRASSES = [11028, 11029]


def dist_to_path(x, y, path):
    best = 1e9
    for (ax, ay), (bx, by) in zip(path, path[1:]):
        vx, vy, wx, wy = bx - ax, by - ay, x - ax, y - ay
        L = vx * vx + vy * vy
        t = 0 if L == 0 else max(0.0, min(1.0, (wx * vx + wy * vy) / L))
        px, py = ax + t * vx, ay + t * vy
        best = min(best, math.hypot(x - px, y - py))
    return best


def generate(out_dir, island_id, seed, region_template, tile_set, color_set, naturals_path):
    rnd = random.Random(seed)
    noise = Noise(seed)
    N = W * H
    idx = lambda x, y: x + y * W
    inb = lambda x, y: 0 <= x < W and 0 <= y < H

    # ── land ────────────────────────────────────────────────────────────────────────
    land = [False] * N
    for y in range(H):
        for x in range(W):
            if x < 6 or y < 6 or x >= W - 6 or y >= H - 6:
                continue
            for cx, cy, rx, ry in BLOBS:
                wob = 1.0 + 0.06 * noise.fbm(x / 9.0, y / 9.0, 3)
                if ((x - cx) / (rx * wob)) ** 2 + ((y - cy) / (ry * wob)) ** 2 <= 1.0:
                    land[idx(x, y)] = True
                    break
    # the story corridor is always land
    for y in range(H):
        for x in range(W):
            if dist_to_path(x, y, DOG_PATH) <= CORRIDOR + 1.5:
                land[idx(x, y)] = True
    # largest component only
    comp = [-1] * N; best, best_size, cid = -1, 0, 0
    for i in range(N):
        if land[i] and comp[i] == -1:
            q = deque([i]); comp[i] = cid; n = 0
            while q:
                j = q.popleft(); n += 1; jx, jy = j % W, j // W
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = jx + dx, jy + dy
                    if inb(nx, ny) and land[idx(nx, ny)] and comp[idx(nx, ny)] == -1:
                        comp[idx(nx, ny)] = cid; q.append(idx(nx, ny))
            if n > best_size: best, best_size = cid, n
            cid += 1
    for i in range(N):
        if land[i] and comp[i] != best: land[i] = False
    ocean_sd = signed_distance([not l for l in land], W, H)

    # ── lakes (never on the corridor itself) ─────────────────────────────────────────
    lake = [False] * N
    for cx, cy, r in LAKES:
        for y in range(int(cy - r - 2), int(cy + r + 3)):
            for x in range(int(cx - r - 2), int(cx + r + 3)):
                if inb(x, y) and land[idx(x, y)] and ocean_sd[idx(x, y)] >= 4 \
                        and math.hypot(x - cx, y - cy) + 0.8 * noise.fbm(x / 4.0, y / 4.0, 2) <= r \
                        and dist_to_path(x, y, DOG_PATH) > CORRIDOR:
                    lake[idx(x, y)] = True
    lake_sd = signed_distance(lake, W, H)

    # ── the thorn-vine wall (rock) ───────────────────────────────────────────────────
    rock = [False] * N
    for y in range(WALL['y0'], WALL['y1'] + 1):
        for x in range(WALL['x0'], WALL['x1'] + 1):
            if WALL['gap'][0] <= x <= WALL['gap'][1]:
                continue
            if land[idx(x, y)] and not lake[idx(x, y)]:
                rock[idx(x, y)] = True
    # a few decorative boulders well away from the path
    for _ in range(40):
        x, y = rnd.randrange(W), rnd.randrange(H)
        if land[idx(x, y)] and not lake[idx(x, y)] and ocean_sd[idx(x, y)] >= 5 and dist_to_path(x, y, DOG_PATH) > 9:
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    if inb(x + dx, y + dy) and land[idx(x + dx, y + dy)] and rnd.random() < 0.7:
                        rock[idx(x + dx, y + dy)] = True
    cliff_sd = signed_distance(rock, W, H)

    # ── elevation / climate / fertility ──────────────────────────────────────────────
    elev, temps, hums, fert = bytearray(N), bytearray(N), bytearray(N), bytearray(N)
    for y in range(H):
        for x in range(W):
            i = idx(x, y)
            if land[i]:
                h = 14 + min(36, ocean_sd[i] * 3) + 6 * noise.fbm(x / 14.0, y / 14.0, 3)
                if lake[i]: h -= 6
                if rock[i]: h += 14
                elev[i] = max(1, min(255, int(h)))
            temps[i] = max(1, min(255, int(190 + 12 * noise.fbm(x / 50.0 + 3, y / 50.0 + 3, 2))))
            hums[i] = max(0, min(255, int(180 + 40 * noise.fbm(x / 30.0, y / 30.0, 3) + (25 if lake_sd[i] < 5 else 0))))
            fert[i] = max(0, min(63, int(30 + 12 * noise.fbm(x / 18.0 + 5, y / 18.0 + 5, 3)))) if land[i] and not rock[i] else 0

    # ── biomes ───────────────────────────────────────────────────────────────────────
    biomes = bytearray(N)
    for y in range(H):
        for x in range(W):
            i = idx(x, y)
            if not land[i]:
                biomes[i] = OCEAN
            elif lake[i]:
                biomes[i] = LAKE
            elif ocean_sd[i] <= 3:
                biomes[i] = BEACH
            else:
                biomes[i] = TROP
                for gx, gy, gr in GRASS_PATCHES:
                    if math.hypot(x - gx, y - gy) + 1.5 * noise.fbm(x / 6.0, y / 6.0, 2) <= gr:
                        biomes[i] = GRASS
            if rock[i]:
                biomes[i] |= ROCK

    # ── vertex grids ─────────────────────────────────────────────────────────────────
    V = W + 1
    ocean_v = bytearray(V * V)
    for vy in range(V):
        for vx in range(V):
            worst = 0
            for tx, ty in ((vx, vy), (vx - 1, vy), (vx, vy - 1), (vx - 1, vy - 1)):
                tx = min(max(tx, 0), W - 1); ty = min(max(ty, 0), H - 1)
                sd = ocean_sd[idx(tx, ty)]
                if sd < 0: worst = max(worst, min(255, 40 + (-sd) * 18))
            ocean_v[vx + vy * V] = worst
    rivers_v = bytes(V * V * 3)

    # ── landmarks ────────────────────────────────────────────────────────────────────
    blocked = set()                       # tiles that must stay free of naturals
    landmarks = bytearray()
    for name, x, y, rot in PLACEMENTS:
        if name not in BY_NAME:
            raise SystemExit(f'unknown landmark {name}')
        i = idx(x, y)
        if not land[i]:
            raise SystemExit(f'landmark {name} at {x},{y} is in the sea')
        landmarks += struct.pack('<HHHBhhhBBB', x, y, BY_NAME[name], R(rot), 0, 0, 0, 51, 51, 51)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                blocked.add((x + dx, y + dy))
    for x in range(BOAT_TILE[0] - 1, BOAT_TILE[0] + BOAT_SIZE + 1):
        for y in range(BOAT_TILE[1] - 1, BOAT_TILE[1] + BOAT_SIZE + 1):
            blocked.add((x, y))
    blocked.add(BONFIRE_TILE)
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            blocked.add((ENTRY[0] + dx, ENTRY[1] + dy))

    # ── naturals ─────────────────────────────────────────────────────────────────────
    garden = bytearray(); used = set()
    def free(x, y, keep_path=1.0):
        i = idx(x, y)
        return inb(x, y) and land[i] and not rock[i] and not lake[i] and ocean_sd[i] >= 1 \
            and (x, y) not in blocked and (x, y) not in used and dist_to_path(x, y, DOG_PATH) > keep_path
    def put(tid, x, y):
        garden.extend(struct.pack('<HHH', x, y, tid)); used.add((x, y))
    def scatter(tids, count, cx, cy, r, keep_path=1.0, pred=None, tries=400):
        n = 0
        for _ in range(tries):
            if n >= count: break
            a, d = rnd.uniform(0, 2 * math.pi), math.sqrt(rnd.random()) * r
            x, y = int(round(cx + d * math.cos(a))), int(round(cy + d * math.sin(a)))
            if free(x, y, keep_path) and (pred is None or pred(x, y)):
                put(rnd.choice(tids), x, y); n += 1
        return n
    counts = {}
    counts['dates'] = scatter([DATE_PALM], 10, 63, 57, 8, keep_path=1.5)
    for cx, cy, r in LAKES:
        counts['reeds'] = counts.get('reeds', 0) + scatter(REEDS, int(8 + r * 3), cx, cy, r + 2.5, keep_path=0.8,
                                                           pred=lambda x, y: 0 < lake_sd[idx(x, y)] <= 3)
    # stones and rocks along the whole route, densest before the obstacle and at the shipyard
    for (ax, ay), (bx, by) in zip(DOG_PATH, DOG_PATH[1:]):
        seg = max(1, int(math.hypot(bx - ax, by - ay) / 6))
        for k in range(seg):
            cx, cy = ax + (bx - ax) * (k + 0.5) / seg, ay + (by - ay) * (k + 0.5) / seg
            counts['stones'] = counts.get('stones', 0) + scatter(STONES, 2, cx, cy, 6, keep_path=1.2)
            counts['rocks'] = counts.get('rocks', 0) + scatter(ROCKS, 1, cx, cy, 6, keep_path=1.5)
            counts['sticks'] = counts.get('sticks', 0) + scatter(STICK_BUSHES, 1, cx, cy, 7, keep_path=1.5)
            counts['grass'] = counts.get('grass', 0) + scatter(GRASSES, 1, cx, cy, 7, keep_path=1.2)
    counts['stones'] += scatter(STONES, 14, 134, 108, 7, keep_path=1.2) + scatter(STONES, 14, 208, 110, 9, keep_path=1.2)
    counts['rocks'] += scatter(ROCKS, 6, 132, 107, 7, keep_path=1.5) + scatter(ROCKS, 6, 206, 110, 9, keep_path=1.5)
    counts['sticks'] += scatter(STICK_BUSHES, 8, 209, 110, 9, keep_path=1.5)
    counts['logtrees'] = scatter(LOG_TREES, 16, 212, 109, 9, keep_path=2.0) + scatter(LOG_TREES, 8, 160, 112, 9, keep_path=2.0) \
        + scatter(LOG_TREES, 6, 110, 96, 9, keep_path=2.0)
    beach_pred = lambda x, y: (biomes[idx(x, y)] & 0x3F) == BEACH
    counts['beach'] = scatter([BEACH_BUSH, BEACH_TREE], 30, 190, 122, 40, keep_path=1.5, pred=beach_pred, tries=1500)
    # background vegetation everywhere else
    counts['bg'] = 0
    for _ in range(2200):
        x, y = rnd.randrange(W), rnd.randrange(H)
        if free(x, y, 2.5) and rnd.random() < 0.55:
            b = biomes[idx(x, y)] & 0x3F
            pool = GRASSES + STICK_BUSHES + LOG_TREES + STONES if b in (TROP, GRASS) else ([BEACH_BUSH, BEACH_TREE] if b == BEACH else None)
            if pool:
                put(rnd.choice(pool), x, y); counts['bg'] += 1

    # ── sanity: every story tile is walkable land ───────────────────────────────────
    for x, y in DOG_PATH + [(WALL['gap'][0] + 1, WALL['y0'] - 1), (WALL['gap'][0] + 1, WALL['y1'] + 1)]:
        i = idx(x, y)
        assert land[i] and not rock[i] and not lake[i], f'story tile {x},{y} not walkable'
    for x in range(BOAT_TILE[0], BOAT_TILE[0] + BOAT_SIZE):
        for y in range(BOAT_TILE[1], BOAT_TILE[1] + BOAT_SIZE):
            assert land[idx(x, y)] and not rock[idx(x, y)] and not lake[idx(x, y)], f'boat tile {x},{y} not land'
    # the wall really seals the island: flood from the spawn must not reach the shipyard without the gap
    def reaches(block_gap):
        seen = [False] * N; q = deque([idx(*ENTRY)]); seen[q[0]] = True
        while q:
            j = q.popleft(); jx, jy = j % W, j // W
            if (jx, jy) == BOAT_TILE: return True
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = jx + dx, jy + dy
                if not inb(nx, ny): continue
                k = idx(nx, ny)
                if seen[k] or not land[k] or rock[k]: continue
                if block_gap and WALL['y0'] <= ny <= WALL['y1'] and WALL['gap'][0] <= nx <= WALL['gap'][1]: continue
                seen[k] = True; q.append(k)
        return False
    assert reaches(False), 'shipyard unreachable even through the gap'
    if reaches(True):
        print('  WARNING: the thorn-vine gap can be bypassed (wall does not seal the island)')

    # ── write ────────────────────────────────────────────────────────────────────────
    out = os.path.join(out_dir, island_id); os.makedirs(out, exist_ok=True)
    def w(name, data): open(os.path.join(out, name), 'wb').write(bytes(data))
    w('whole.biomes', biomes); w('whole.elevations', elev); w('whole.temperatures', temps); w('whole.humidities', hums); w('fertilities', fert)
    w('oceans.dm', to_sbytes(ocean_sd)); w('cliffs.dm', to_sbytes(cliff_sd)); w('lakes.dm', to_sbytes(lake_sd))
    w('rivers.dm', to_sbytes([99] * N)); w('scoops.dm', to_sbytes([99] * N))
    w('whole.ocean', ocean_v); w('whole.rivers', rivers_v); w('whole.garden', garden); w('whole.landmarks', landmarks)
    info = {
        'tile_count': [W, H], 'is_cold_ocean': False, 'lake_type': 0, 'river_type': 0, 'ocean_type': 0,
        'lake_biome': 'tropical_forest', 'river_biome': 'tropical_forest', 'ocean_biome': 'warm_ocean',
        'region_template': region_template, 'tile_set': tile_set, 'color_set': color_set,
        'entry_points': [[ENTRY[0], ENTRY[1]]],
        'landmarks': [{'id': k, 'prefab': v} for k, v in sorted(LM.items())],
        'global_landmarks': [], 'indicators': [], 'time_zone': [0, 0],
    }
    open(os.path.join(out, 'info.yml'), 'w', encoding='utf-8').write(json.dumps(info, indent=2))
    # block-style YAML only: the server's TerrainYaml.cs reads "- x / - y" pairs, not inline [x, y]
    pois = ('warpholes: []\nrifts: []\nport_points: []\ncraters: []\nscoop_slots: []\ncamp_artifacts:\n'
            f'- entity_type: 9001\n  tile:\n  - {BONFIRE_TILE[0]}\n  - {BONFIRE_TILE[1]}\n'
            f'- entity_type: 9000\n  tile:\n  - {BOAT_TILE[0]}\n  - {BOAT_TILE[1]}\n')
    open(os.path.join(out, 'pois.yml'), 'w', encoding='utf-8').write(pois)
    open(os.path.join(out, 'herds.yml'), 'w', encoding='utf-8').write('herds:\n  land: []\n  beach: []\n  ocean: []\n  lake_shallow: []\n')

    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            i = idx(x, y); b = biomes[i]
            col = BIOME_COLOR.get(b & 0x3F, (255, 0, 255))
            if b & ROCK == ROCK: col = (110, 100, 95)
            elif land[i]: sh = 0.75 + 0.25 * elev[i] / 255; col = tuple(int(c * sh) for c in col)
            else: d = ocean_v[x + y * V]; col = tuple(max(0, int(c * (1 - d / 400))) for c in col)
            if (x, y) in used: col = tuple(max(0, c - 40) for c in col)
            if dist_to_path(x, y, DOG_PATH) < 0.6: col = (255, 255, 255)
            row += bytes(col)
        rows.append(row)
    for name, x, y, rot in PLACEMENTS:
        c = (255, 0, 0) if name.startswith('trigger') else ((255, 128, 0) if name.startswith('thorn') else (0, 0, 255))
        rows[y][x * 3:x * 3 + 3] = bytes(c)
    for (x, y), c in ((ENTRY, (255, 255, 0)), (BONFIRE_TILE, (255, 100, 0)), (BOAT_TILE, (0, 255, 255))):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                rows[y + dy][(x + dx) * 3:(x + dx) * 3 + 3] = bytes(c)
    png_write(os.path.join(out, 'preview.png'), W, H, rows)
    print(f"Ancora '{island_id}' {W}x{H}: land {sum(land)} tiles, rock {sum(rock)}, lake {sum(lake)}, "
          f"landmarks {len(PLACEMENTS)}, naturals {len(garden) // 6} {counts}")
    print(f'  -> {out}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--id', default='ancora01'); ap.add_argument('--seed', type=int, default=180107)
    ap.add_argument('--region-template', default='i01ancora180107')
    ap.add_argument('--tile-set', default=''); ap.add_argument('--color-set', default='')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(__file__), '..', '..', 'server', 'data', 'terrains', 'extracted'))
    ap.add_argument('--naturals', default=None)
    a = ap.parse_args()
    generate(os.path.abspath(a.out), a.id, a.seed, a.region_template, a.tile_set, a.color_set, a.naturals)


if __name__ == '__main__':
    main()
