"""Durango island generator.

Produces a complete server/data/terrains/extracted/<id>/ folder in the on-disk
format the game's terrain pipeline uses (as read by ServerCore/TerrainStore.cs
and served to the client by Gateway.cs):

  whole.biomes        W*H bytes    biome id (low 6 bits, Shared.Region.Biome) | 0xC0 = rock/cliff flag
  whole.elevations    W*H bytes    ground height per tile
  whole.temperatures  W*H bytes    1..255
  whole.humidities    W*H bytes    0..255
  fertilities         W*H bytes
  oceans.dm           W*H sbytes   signed distance to coast (negative = in the sea)
  cliffs.dm           W*H sbytes   signed distance to cliff (negative = inside rock)
  lakes.dm            W*H sbytes   signed distance to lake (negative = in lake)
  rivers.dm           W*H sbytes   signed distance to river
  scoops.dm           W*H sbytes   signed distance to dig spots
  whole.ocean         (W+1)*(H+1) bytes  water depth per vertex (0 = dry)
  whole.rivers        (W+1)*(H+1)*3 bytes river mask per vertex (0 = none)
  whole.garden        N*6 bytes    naturals: x u16, y u16, entity_type u16 (tile coords)
  whole.landmarks     N*16 bytes   LandmarkInfo records (x,y,id,rotate,offX,offY,offZ,scaleXYZ)
  info.yml            JSON (TerrainInfoJson)
  pois.yml, herds.yml YAML subset read by TerrainYaml.cs

Usage:
  python terraingen.py --id myisle01 --seed 42 [--size 256] [--biome temperate|tropical|desert|snow|volcanic]
                       [--out ../../server/data/terrains/extracted] [--naturals ../../server/data/assets/entity_types/natural.json]
"""
import argparse, json, math, os, random, struct, zlib
from collections import deque

# Shared.Region.Biome
B = dict(TemperateForest=0, TropicalForest=1, Desert=2, Tundra=3, SnowField=4, Grassland=5, SwampMud=6,
         Volcanic=7, PebbleBeach=9, SandBeach=10, ColdOcean=11, WarmOcean=12, River=13, Lake=14, Lava=15)
BIOME_NAME = {v: k for k, v in B.items()}
# survivability keys used in natural.json
SURV_KEY = {0: 'temperate_forest', 1: 'tropical_forest', 2: 'desert', 3: 'tundra', 4: 'snow_field', 5: 'grassland',
            6: 'swamp_mud', 7: 'volcanic', 9: 'pebble_beach', 10: 'sand_beach', 11: 'cold_ocean', 12: 'warm_ocean',
            13: 'river', 14: 'lake', 15: 'lava'}
ROCK = 0xC0

CLIMATES = {
    # main biome, secondary (higher/inland) biome, beach biome, ocean biome, temperature center, humidity center
    'temperate': dict(main=B['TemperateForest'], alt=B['Grassland'], beach=B['SandBeach'], ocean=B['WarmOcean'], temp=150, hum=140, cold=False),
    'tropical':  dict(main=B['TropicalForest'], alt=B['SwampMud'],   beach=B['SandBeach'], ocean=B['WarmOcean'], temp=200, hum=210, cold=False),
    'desert':    dict(main=B['Desert'],          alt=B['Grassland'], beach=B['SandBeach'], ocean=B['WarmOcean'], temp=220, hum=40,  cold=False),
    'snow':      dict(main=B['SnowField'],       alt=B['Tundra'],    beach=B['PebbleBeach'], ocean=B['ColdOcean'], temp=40, hum=120, cold=True),
    'volcanic':  dict(main=B['Volcanic'],        alt=B['Grassland'], beach=B['PebbleBeach'], ocean=B['WarmOcean'], temp=230, hum=90, cold=False),
    # Ancora: the train-wreck starter island. Grass and sparse forest under permanent volcanic ash (weather comes from
    # the region template i01ancora*), gentle relief, a wide beach on the north side where K waits.
    'ancora':    dict(main=B['Grassland'],       alt=B['TemperateForest'], beach=B['SandBeach'], ocean=B['WarmOcean'], temp=140, hum=120, cold=False),
}

# ----------------------------------------------------------------------------- noise
class Noise:
    def __init__(self, seed):
        rnd = random.Random(seed)
        self.p = list(range(256)); rnd.shuffle(self.p); self.p += self.p
    @staticmethod
    def fade(t): return t * t * t * (t * (t * 6 - 15) + 10)
    @staticmethod
    def grad(h, x, y):
        h &= 3
        u = x if h < 2 else y; v = y if h < 2 else x
        return (u if h & 1 == 0 else -u) + (v if h & 2 == 0 else -v)
    def perlin(self, x, y):
        xi, yi = int(math.floor(x)) & 255, int(math.floor(y)) & 255
        xf, yf = x - math.floor(x), y - math.floor(y)
        u, v = self.fade(xf), self.fade(yf); p = self.p
        aa, ab = p[p[xi] + yi], p[p[xi] + yi + 1]
        ba, bb = p[p[xi + 1] + yi], p[p[xi + 1] + yi + 1]
        x1 = self.grad(aa, xf, yf) + u * (self.grad(ba, xf - 1, yf) - self.grad(aa, xf, yf))
        x2 = self.grad(ab, xf, yf - 1) + u * (self.grad(bb, xf - 1, yf - 1) - self.grad(ab, xf, yf - 1))
        return x1 + v * (x2 - x1)          # roughly -1..1
    def fbm(self, x, y, octaves=5, lac=2.0, gain=0.5):
        amp, freq, s, norm = 1.0, 1.0, 0.0, 0.0
        for _ in range(octaves):
            s += amp * self.perlin(x * freq, y * freq); norm += amp
            amp *= gain; freq *= lac
        return s / norm

# ----------------------------------------------------------------------------- helpers
def signed_distance(inside, W, H, cap=99):
    """Signed distance field in tiles: negative inside `inside` region, positive outside.
    BFS from the boundary both ways. Returns list of ints clamped to [-cap, cap]."""
    INF = 10 ** 6
    dist_out = [INF] * (W * H)   # distance from outside cells to the region
    dist_in = [INF] * (W * H)    # distance from inside cells to the outside
    q_out, q_in = deque(), deque()
    for y in range(H):
        for x in range(W):
            i = x + y * W
            if inside[i]:
                # boundary inside cell if any 4-neighbour is outside (or map edge)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if not (0 <= nx < W and 0 <= ny < H) or not inside[nx + ny * W]:
                        dist_in[i] = 1; q_in.append(i); break
            else:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < W and 0 <= ny < H and inside[nx + ny * W]:
                        dist_out[i] = 1; q_out.append(i); break
    def bfs(q, dist, want_inside):
        while q:
            i = q.popleft(); x, y = i % W, i // W; d = dist[i] + 1
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < W and 0 <= ny < H:
                    j = nx + ny * W
                    if inside[j] == want_inside and dist[j] > d:
                        dist[j] = d; q.append(j)
    bfs(q_out, dist_out, False); bfs(q_in, dist_in, True)
    out = [0] * (W * H)
    any_inside = any(inside)
    for i in range(W * H):
        if inside[i]:
            out[i] = -min(dist_in[i], cap)
        else:
            out[i] = min(dist_out[i], cap) if any_inside else cap
    return out

def to_sbytes(vals):
    return bytes((v & 0xFF) for v in vals)

def png_write(path, W, H, rgb_rows):
    raw = b''.join(b'\x00' + bytes(row) for row in rgb_rows)
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
                + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))

BIOME_COLOR = {0: (46, 120, 50), 1: (20, 140, 60), 2: (220, 200, 120), 3: (150, 160, 140), 4: (240, 245, 250), 5: (130, 190, 80),
               6: (90, 80, 50), 7: (70, 40, 40), 9: (170, 170, 160), 10: (240, 225, 160), 11: (40, 70, 140), 12: (30, 110, 190),
               13: (60, 140, 220), 14: (50, 120, 200), 15: (255, 90, 0)}

# ----------------------------------------------------------------------------- generator
def generate(args):
    W = H = args.size
    rnd = random.Random(args.seed)
    noise, moist = Noise(args.seed), Noise(args.seed * 7919 + 1)
    clim = CLIMATES[args.biome]

    # --- land mask + elevation -------------------------------------------------------
    cx, cy = W / 2, H / 2
    ang_noise = Noise(args.seed * 31 + 7)
    elev_f = [0.0] * (W * H)
    land = [False] * (W * H)
    for y in range(H):
        for x in range(W):
            dx, dy = (x - cx) / (W / 2), (y - cy) / (H / 2)
            r = math.hypot(dx, dy)
            ang = math.atan2(dy, dx)
            # wobbly coastline: radius varies with angle
            coast = 0.72 + 0.16 * ang_noise.fbm(math.cos(ang) * 1.7 + 3, math.sin(ang) * 1.7 + 3, 3)
            n = noise.fbm(x / 48.0, y / 48.0, 5)
            e = (coast - r) * 1.6 + n * 0.35            # >0 = land
            elev_f[x + y * W] = e
            land[x + y * W] = e > 0

    # remove tiny islets: keep the largest connected component only
    comp = [-1] * (W * H); best, best_size = -1, 0; cid = 0
    for i in range(W * H):
        if land[i] and comp[i] == -1:
            q = deque([i]); comp[i] = cid; n = 0
            while q:
                j = q.popleft(); n += 1; jx, jy = j % W, j // W
                for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = jx + ddx, jy + ddy
                    if 0 <= nx < W and 0 <= ny < H:
                        k = nx + ny * W
                        if land[k] and comp[k] == -1: comp[k] = cid; q.append(k)
            if n > best_size: best, best_size = cid, n
            cid += 1
    for i in range(W * H):
        if land[i] and comp[i] != best: land[i] = False
    if best_size < W * H * 0.15:
        raise SystemExit(f"island too small ({best_size} tiles) — try another --seed")

    ocean_sd = signed_distance([not l for l in land], W, H)      # negative in the sea

    # --- lake (optional): a depression well inland -----------------------------------
    lake = [False] * (W * H)
    if args.lake:
        inland = [i for i in range(W * H) if land[i] and ocean_sd[i] >= 14]
        if inland:
            c = rnd.choice(inland); lx, ly = c % W, c // W; lr = rnd.uniform(4, 7)
            for y in range(H):
                for x in range(W):
                    if land[x + y * W] and math.hypot(x - lx, y - ly) + noise.fbm(x / 6, y / 6, 2) * 1.5 < lr:
                        lake[x + y * W] = True
    lake_sd = signed_distance(lake, W, H)

    # --- elevation bytes: 0 in the sea, rising inland, plus noise ---------------------
    elev = bytearray(W * H)
    max_in = max(1, max(ocean_sd))
    for i in range(W * H):
        if land[i] and not lake[i]:
            base = min(1.0, ocean_sd[i] / max_in) ** 0.8
            h = 8 + 90 * base + 25 * (elev_f[i] + 0.5) + 10 * noise.fbm((i % W) / 12.0, (i // W) / 12.0, 3)
            elev[i] = max(1, min(255, int(h)))
        elif lake[i]:
            elev[i] = max(1, int(8 + 40 * min(1.0, ocean_sd[i] / max_in)))

    # --- cliffs: steep slopes inland become rock ------------------------------------
    rock = [False] * (W * H)
    for y in range(1, H - 1):
        for x in range(1, W - 1):
            i = x + y * W
            if not land[i] or lake[i] or ocean_sd[i] < 4: continue
            slope = max(abs(elev[i] - elev[i + 1]), abs(elev[i] - elev[i - 1]), abs(elev[i] - elev[i + W]), abs(elev[i] - elev[i - W]))
            if slope >= args.cliff_slope or noise.fbm(x / 9.0 + 50, y / 9.0 + 50, 3) > 0.42:
                rock[i] = True
    cliff_sd = signed_distance(rock, W, H)

    # --- temperature / humidity / fertility -----------------------------------------
    temps, hums, fert = bytearray(W * H), bytearray(W * H), bytearray(W * H)
    for y in range(H):
        for x in range(W):
            i = x + y * W
            t = clim['temp'] - elev[i] * 0.25 + 25 * noise.fbm(x / 60.0 + 9, y / 60.0 + 9, 2)
            hm = clim['hum'] + 60 * moist.fbm(x / 40.0, y / 40.0, 4) + (20 if lake_sd[i] < 6 else 0) + (15 if ocean_sd[i] < 5 else 0)
            temps[i] = max(1, min(255, int(t))); hums[i] = max(0, min(255, int(hm)))
            f = 16 + 14 * moist.fbm(x / 20.0 + 3, y / 20.0 + 3, 3) + (8 if 3 <= ocean_sd[i] <= 12 else 0)
            fert[i] = max(0, min(63, int(f))) if land[i] and not rock[i] else 0

    # --- biomes -------------------------------------------------------------------
    biomes = bytearray(W * H)
    for i in range(W * H):
        if not land[i]:
            biomes[i] = clim['ocean']
        elif lake[i]:
            biomes[i] = B['Lake']
        elif ocean_sd[i] <= 2:
            biomes[i] = clim['beach'] if not (clim['cold'] and ocean_sd[i] == 1) else B['PebbleBeach']
        else:
            hm = hums[i]
            if args.biome == 'volcanic' and elev[i] > 140: biomes[i] = B['Lava'] if noise.fbm(i % W / 5, i // W / 5, 2) > 0.5 else B['Volcanic']
            elif hm > clim['hum'] + 22: biomes[i] = clim['main']
            elif hm < clim['hum'] - 22: biomes[i] = clim['alt']
            else: biomes[i] = clim['main'] if noise.fbm((i % W) / 30.0 + 77, (i // W) / 30.0 + 77, 3) > -0.05 else clim['alt']
        if rock[i]:
            biomes[i] |= ROCK

    # --- vertex grids: ocean depth, rivers ----------------------------------------
    V = W + 1
    ocean_v = bytearray(V * V)
    for vy in range(V):
        for vx in range(V):
            # a vertex is wet if any adjacent tile is sea; depth grows with distance from coast
            worst = 0
            for tx, ty in ((vx, vy), (vx - 1, vy), (vx, vy - 1), (vx - 1, vy - 1)):
                tx = min(max(tx, 0), W - 1); ty = min(max(ty, 0), H - 1)
                sd = ocean_sd[tx + ty * W]
                if sd < 0: worst = max(worst, min(255, 40 + (-sd) * 18))
            ocean_v[vx + vy * V] = worst
    rivers_v = bytes(V * V * 3)
    river_sd = [99] * (W * H)
    scoop_sd = [99] * (W * H)

    # --- naturals (whole.garden) from natural.json ----------------------------------
    garden = bytearray()
    natural_count = 0
    if args.naturals and os.path.exists(args.naturals):
        nat = json.load(open(args.naturals, encoding='utf-8'))
        by_biome = {}
        for tid, n in nat.items():
            if not n.get('active', True): continue
            cid_ = str(n.get('collectible_id', '')); sprite = str(n.get('sprite_name', '')).lower()
            if not cid_ or 'warp' in sprite or 'city_prop' in sprite or 'season' in cid_ or 'faction' in cid_ or 'event' in cid_:
                continue
            if not any(k in cid_ for k in ('tree', 'grass', 'stone', 'berry', 'bush', 'flower', 'herb', 'mushroom', 'clay', 'wood', 'ore', 'fruit', 'root', 'vine', 'reed', 'palm')):
                continue
            surv = n.get('survivability') or {}
            for bid, key in SURV_KEY.items():
                if surv.get(key):
                    by_biome.setdefault(bid, []).append((int(tid), n))
        placed = set()
        for y in range(H):
            for x in range(W):
                i = x + y * W
                if not land[i] or rock[i] or lake[i] or ocean_sd[i] <= 1: continue
                if rnd.random() > args.density: continue
                cands = by_biome.get(biomes[i] & 0x3F)
                if not cands: continue
                # try a few candidates so strict per-species ranges don't leave the island bare
                for _ in range(4):
                    tid, n = rnd.choice(cands)
                    mo = n.get('min_distance_from_ocean', -32); Mo = n.get('max_distance_from_ocean', 32)
                    if not (mo <= ocean_sd[i] <= Mo): continue
                    if fert[i] < n.get('min_fertility', 0) * 0.5: continue
                    garden += struct.pack('<HHH', x, y, tid); placed.add(i); natural_count += 1
                    break
    landmarks = bytes()

    # --- POIs: entry/port on the beach, warpholes/rifts inland ------------------------
    beach = [i for i in range(W * H) if land[i] and 1 <= ocean_sd[i] <= 2 and not rock[i]]
    inland = [i for i in range(W * H) if land[i] and ocean_sd[i] >= 6 and not rock[i] and not lake[i] and cliff_sd[i] >= 2]
    rnd.shuffle(beach); rnd.shuffle(inland)
    def pick(pool, n, min_sep=18):
        out = []
        for i in pool:
            x, y = i % W, i // W
            if all(math.hypot(x - ox, y - oy) >= min_sep for ox, oy in out):
                out.append((x, y))
                if len(out) == n: break
        return out
    # entry: beach tile whose inland neighbour is walkable, prefer south side
    entry = sorted(beach, key=lambda i: -(i // W))[0]; entry = (entry % W, entry // W)
    warpholes = pick(inland, 5, 30); rifts = pick([i for i in inland if (i % W, i // W) not in warpholes], 2, 40)
    camp = pick([i for i in inland if math.hypot(i % W - entry[0], i // W - entry[1]) < 30], 1, 1) or [warpholes[0]]
    poi_tiles = set(warpholes + rifts + camp)
    herd_pool = [i for i in inland if (i % W, i // W) not in poi_tiles]; rnd.shuffle(herd_pool)
    herd_land = pick(herd_pool, 120, 5); herd_beach = pick(beach, 60, 5)
    sea = [i for i in range(W * H) if not land[i] and -8 <= ocean_sd[i] <= -3]; rnd.shuffle(sea); herd_ocean = pick(sea, 60, 5)
    lake_tiles = [i for i in range(W * H) if lake[i]]; rnd.shuffle(lake_tiles); herd_lake = pick(lake_tiles, 20, 2)

    # --- write everything ----------------------------------------------------------
    out = os.path.join(args.out, args.id); os.makedirs(out, exist_ok=True)
    def w(name, data): open(os.path.join(out, name), 'wb').write(bytes(data))
    w('whole.biomes', biomes); w('whole.elevations', elev); w('whole.temperatures', temps); w('whole.humidities', hums); w('fertilities', fert)
    w('oceans.dm', to_sbytes(ocean_sd)); w('cliffs.dm', to_sbytes(cliff_sd)); w('lakes.dm', to_sbytes(lake_sd))
    w('rivers.dm', to_sbytes(river_sd)); w('scoops.dm', to_sbytes(scoop_sd))
    w('whole.ocean', ocean_v); w('whole.rivers', rivers_v); w('whole.garden', garden); w('whole.landmarks', landmarks)
    info = {
        'tile_count': [W, H], 'is_cold_ocean': clim['cold'],
        'lake_type': 0, 'river_type': 0, 'ocean_type': 0,
        'lake_biome': 'lake', 'river_biome': 'river', 'ocean_biome': 'cold_ocean' if clim['cold'] else 'warm_ocean',
        'region_template': args.region_template, 'tile_set': args.tile_set, 'color_set': args.color_set,
        'entry_points': [[entry[0], entry[1]]], 'landmarks': [], 'global_landmarks': [], 'indicators': [], 'time_zone': [0, 0],
    }
    open(os.path.join(out, 'info.yml'), 'w', encoding='utf-8').write(json.dumps(info, indent=2))
    # block-style YAML only: the server's TerrainYaml.cs reads "- - x / - y" pairs (the game's own format), not inline [x, y]
    def yml_points(name, pts): return f"{name}:\n" + ''.join(f"- - {x}\n  - {y}\n" for x, y in pts) if pts else f"{name}: []\n"
    pois = (yml_points('warpholes', warpholes) + yml_points('rifts', rifts) + yml_points('port_points', [entry]) + 'craters: []\nscoop_slots: []\n'
            + 'camp_artifacts:\n' + ''.join(f"- entity_type: 9450\n  tile:\n  - {x}\n  - {y}\n" for x, y in camp))
    open(os.path.join(out, 'pois.yml'), 'w', encoding='utf-8').write(pois)
    herds = 'herds:\n' + ''.join('  ' + line + '\n' for grp, pts in (('land', herd_land), ('beach', herd_beach), ('ocean', herd_ocean), ('lake_shallow', herd_lake))
                                  for line in yml_points(grp, pts).rstrip('\n').split('\n'))
    open(os.path.join(out, 'herds.yml'), 'w', encoding='utf-8').write(herds)

    # preview
    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            i = x + y * W; b = biomes[i]
            col = BIOME_COLOR.get(b & 0x3F, (255, 0, 255))
            if b & ROCK == ROCK: col = (110, 100, 95)
            elif land[i]: sh = 0.75 + 0.25 * elev[i] / 255; col = tuple(int(c * sh) for c in col)
            else: d = ocean_v[x + y * V]; col = tuple(max(0, int(c * (1 - d / 400))) for c in col)
            if i in placed if args.naturals else False: col = tuple(max(0, c - 40) for c in col)
            row += bytes(col)
        rows.append(row)
    for (x, y), c in [(entry, (255, 255, 0))] + [(p, (255, 0, 0)) for p in warpholes] + [(p, (255, 0, 255)) for p in rifts]:
        for ddx in (-1, 0, 1):
            for ddy in (-1, 0, 1):
                if 0 <= x + ddx < W and 0 <= y + ddy < H: rows[y + ddy][(x + ddx) * 3:(x + ddx) * 3 + 3] = bytes(c)
    png_write(os.path.join(out, 'preview.png'), W, H, rows)

    land_n = sum(land); rock_n = sum(rock)
    print(f"island '{args.id}' {W}x{H} seed={args.seed} climate={args.biome}")
    print(f"  land {land_n} tiles ({100 * land_n / (W * H):.1f}%), rock {rock_n}, lake {sum(lake)}, naturals {natural_count}")
    print(f"  entry {entry}, warpholes {len(warpholes)}, rifts {len(rifts)}, herd spots land/beach/ocean/lake {len(herd_land)}/{len(herd_beach)}/{len(herd_ocean)}/{len(herd_lake)}")
    print(f"  -> {out}")

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--id', required=True); ap.add_argument('--seed', type=int, default=1); ap.add_argument('--size', type=int, default=256)
    ap.add_argument('--biome', choices=sorted(CLIMATES), default='temperate')
    ap.add_argument('--lake', action='store_true', default=True); ap.add_argument('--no-lake', dest='lake', action='store_false')
    ap.add_argument('--density', type=float, default=0.06, help='natural object probability per land tile')
    ap.add_argument('--cliff-slope', type=int, default=22)
    ap.add_argument('--region-template', default='ri35te171228'); ap.add_argument('--tile-set', default='temperate'); ap.add_argument('--color-set', default='temperate')
    ap.add_argument('--out', default=os.path.join(here, '..', '..', 'server', 'data', 'terrains', 'extracted'))
    ap.add_argument('--naturals', default=os.path.join(here, '..', '..', 'server', 'data', 'assets', 'entity_types', 'natural.json'))
    generate(ap.parse_args())

if __name__ == '__main__':
    main()
