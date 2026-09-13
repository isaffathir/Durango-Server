using System.Collections.Generic;

namespace DurangoServer.Core;

// ข้อมูลธรรมชาติของเกม (generated จาก resources.assets TextAsset `natural` + `emotions` + `prototype_data`)
// - Map: natural type (11002-15001) → ไอเทมที่จะได้ (prototype/ชื่อ/ไอคอนจริงของเกม)
// - EmoticonIds/MotionIds: รายชื่ออิโมจิและท่าทางทั้งหมด (ตอบ GetAvailableEmotions)
public static class NaturalData
{
    public struct GenEntry
    {
        public string Prototype;
        public string Name;
        public string Icon;
    }

    public static readonly string[] EmoticonIds = new[]
    {
        "smile", "wink", "surprise", "love", "sad", "angry", "up", "down", "left", "right",
        "left_up", "right_up", "left_down", "right_down", "ok", "no", "sos", "danger",
        "peace", "go_away", "heart", "broken_heart", "dislike", "like"
    };

    public static readonly string[] MotionIds = new[]
    {
        "heart", "fashion", "sit3", "santa", "fright", "cheerup", "thumbup", "flatter", "dance_sway", "dance6",
        "sad", "school3", "ceremony_e", "anger", "school2", "welcome_b", "fear", "dance_pray", "school4", "ginyu4",
        "ginyu5", "ginyu2", "ginyu3", "no", "spring_picnic", "cheerup_d", "dino", "dance11", "dance10", "disgust",
        "dance12", "heart2", "cheerup2", "cheerup3", "power3", "thumbdown", "ginyu", "spray_money", "power2", "welcome",
        "fashion2", "power", "joy", "spoiled_child", "fashion3", "dance3", "ttaemiri", "witch", "dance_tribe", "dance7",
        "thumbup2", "dance9", "dance8", "sit2", "ceremony_d", "ceremony_c", "ceremony_b", "ceremony_a", "dance_flap",
        "ok", "dance2", "boring", "school1", "sit", "bow", "Alien", "despair", "afterschool", "clap", "dance",
        "headache", "dance5", "dance4"
    };

    public static readonly Dictionary<int, GenEntry[]> Map = new Dictionary<int, GenEntry[]>
    {
        { 11002, new[] { new GenEntry { Prototype = "stem", Name = "Batang", Icon = "icon_nat_fiber_reed" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "wheat_seed", Name = "Benih gandum", Icon = "icon_nat_seed" } } },
        { 11004, new[] { new GenEntry { Prototype = "fruit_berry", Name = "Buah beri", Icon = "tag_material_fruit" }, new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 11009, new[] { new GenEntry { Prototype = "fruit_berry", Name = "Buah beri", Icon = "tag_material_fruit" }, new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "corn_seed", Name = "Benih jagung", Icon = "icon_nat_seed" } } },
        { 11013, new[] { new GenEntry { Prototype = "fruit_berry", Name = "Buah beri", Icon = "tag_material_fruit" }, new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "onion_seed", Name = "Benih bawang", Icon = "icon_nat_seed" } } },
        { 11018, new[] { new GenEntry { Prototype = "wildberry", Name = "Beri liar", Icon = "icon_nat_fruit_wildberry" }, new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "pumpkin_seed", Name = "Benih labu", Icon = "icon_nat_seed" } } },
        { 11021, new[] { new GenEntry { Prototype = "flax", Name = "Tanaman rami", Icon = "icon_nat_fiber_flax" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "flax_seed", Name = "Benih rami", Icon = "icon_nat_seed" } } },
        { 11026, new[] { new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 11031, new[] { new GenEntry { Prototype = "fruit_berry", Name = "Buah beri", Icon = "tag_material_fruit" }, new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "potato_seed", Name = "Benih kentang", Icon = "icon_nat_seed" } } },
        { 11032, new[] { new GenEntry { Prototype = "stem", Name = "Batang", Icon = "icon_nat_fiber_reed" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "rice_seed", Name = "Benih padi", Icon = "icon_nat_seed" } } },
        { 12000, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 12003, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 12118, new[] { new GenEntry { Prototype = "fish", Name = "Ikan", Icon = "icon_nat_fish" } } },
        { 12119, new[] { new GenEntry { Prototype = "fish", Name = "Ikan", Icon = "icon_nat_fish" } } },
        { 12120, new[] { new GenEntry { Prototype = "fish", Name = "Ikan", Icon = "icon_nat_fish" } } },
        { 12121, new[] { new GenEntry { Prototype = "clam_shell", Name = "Cangkang kerang", Icon = "icon_nat_clam" } } },
        { 12124, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 13000, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 13006, new[] { new GenEntry { Prototype = "clay", Name = "Tanah liat", Icon = "icon_nat_clay" } } },
        { 13014, new[] { new GenEntry { Prototype = "rubber", Name = "Karet", Icon = "material_rubber" }, new GenEntry { Prototype = "metal_brass", Name = "Kuningan", Icon = "icon_nat_mine_zinc" } } },
        { 13044, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 13045, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 13046, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 13047, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 14004, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 14005, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 14014, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 14017, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 14029, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" } , new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 15001, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },

        // ── [4 ก.ย. 2026] บั๊ก #12 "ยังไม่มีเมล็ดพันธุ์พืชให้ลองปลูก" ──
        // ข้อมูลเกมมี seed 55 ชนิด + ระบบปลูก (crop_data 53 ชนิด) พร้อมใช้ แต่ **ไม่มีที่ไหนดรอปเมล็ดเลย**
        // ⇒ ระบบไร่นาใช้ไม่ได้ทั้งระบบ · ให้พืชป่าดรอปเมล็ดตามชนิดของมัน (เหมือนเก็บเมล็ดจากต้นจริง)
        // (เมล็ดถูกเติมเข้าไปในชนิดที่ "เกิดจริงบนเกาะ" ด้านบนแล้ว — 11021 flax, 11002/11032 กก, 11018 เบอร์รีป่า)

        // ── [4 ก.ย. 2026] ของธรรมชาติบนเกาะหิมะ (sn20snow) — บั๊ก "ทุกต้นทุกก้อนมีแต่ใบไม้" ──
        // เดิมชนิดพวกนี้ไม่มีในตารางเลย ⇒ ตกไป fallback ที่ให้ "Daun" อย่างเดียว แม้แต่ก้อนหิน
        { 14013, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" }, new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 14016, new[] { new GenEntry { Prototype = "wood_bough", Name = "Ranting", Icon = "icon_nat_wood_branch" }, new GenEntry { Prototype = "wood_log", Name = "Kayu gelondongan", Icon = "icon_nat_wood_log" }, new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 11039, new[] { new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" }, new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 11046, new[] { new GenEntry { Prototype = "stem", Name = "Batang", Icon = "icon_nat_fiber_reed" }, new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } , new GenEntry { Prototype = "cotton_seed", Name = "Benih kapas", Icon = "icon_nat_seed" } } },
        { 11047, new[] { new GenEntry { Prototype = "wood_bush", Name = "Semak", Icon = "icon_nat_fiber_straw" }, new GenEntry { Prototype = "leaf", Name = "Daun", Icon = "icon_nat_leaf" } } },
        { 13042, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 12031, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "stone_big", Name = "Batu besar", Icon = "icon_nat_mine_rock" } } },
        { 12034, new[] { new GenEntry { Prototype = "stone", Name = "Batu", Icon = "icon_nat_mine_stone" }, new GenEntry { Prototype = "clam_shell", Name = "Cangkang kerang", Icon = "icon_nat_clam" } } },
    };
}