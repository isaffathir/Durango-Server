using System;
using System.Collections.Generic;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace DurangoServer.Core;

// ============================================================================
// QuestData.Json — quest tables loaded from data/quests/quests.json
//
// The C# tables in QuestData.cs remain as the built-in defaults. At startup
// Program.cs calls QuestData.LoadJson(dataDir):
//   · file missing  -> the built-in tables are exported to it (so the file
//                      documents the exact format) and used as-is
//   · file present  -> it replaces Story / Checklist / All / ById entirely
// Story text goes through the JSON "text" field (any language); the C# side
// keeps calling it Quest.Thai for source compatibility.
//
// Format:
// {
//   "main_category": "sunset",          // client shows this category as the epic/main tab
//   "checklist_category": "daily",      // daily-checklist tab (can be disabled by Features.QuestChecklist)
//   "raft_quest_id": "story_enter_safehouse",
//   "story":     [ { "id", "goal", "param", "count", "requires", "reward": {"exp","skill_points","items":{proto:count}}, "text" }, ... ],
//   "checklist": [ ... same shape ... ]
// }
// "goal" is a QuestData.Goal name (Gather, GatherItem, Hunt, Butcher, Craft, Cook, Build, Level, Eat, Plant,
// Harvest, Water, Fertilize, DrawWater, Equip, Repair, Store, LearnSkill, Revive, HuntRanged, Reach, Rest,
// WarpLocal, IslandTravel). "id" must exist in the game's quests_for_client table or the client draws nothing.
// ============================================================================
public static partial class QuestData
{
    public const string JsonRelativePath = "quests/quests.json";

    /// <summary>Where the active tables came from ("built-in" or the file path).</summary>
    public static string Source { get; private set; } = "built-in";

    private sealed class QuestJson
    {
        [JsonProperty("id")] public string Id;
        [JsonProperty("goal")] public string Goal;
        [JsonProperty("param")] public string Param;
        [JsonProperty("count")] public int Count = 1;
        [JsonProperty("requires")] public string Requires;
        [JsonProperty("reward")] public RewardJson Reward;
        [JsonProperty("text")] public string Text;
    }

    private sealed class RewardJson
    {
        [JsonProperty("exp")] public int Exp;
        [JsonProperty("skill_points")] public int SkillPoints;
        [JsonProperty("items")] public Dictionary<string, int> Items;
    }

    private sealed class FileJson
    {
        [JsonProperty("main_category")] public string MainCategory;
        [JsonProperty("checklist_category")] public string ChecklistCategory;
        [JsonProperty("raft_quest_id")] public string RaftQuestId;
        [JsonProperty("story")] public List<QuestJson> Story = new();
        [JsonProperty("checklist")] public List<QuestJson> Checklist = new();
    }

    /// <summary>
    /// Load quests from &lt;dataDir&gt;/quests/quests.json. Returns true when the JSON tables are active.
    /// Never throws: on any problem the built-in tables stay in place and the reason is printed.
    /// </summary>
    public static bool LoadJson(string dataDir)
    {
        string path = Path.Combine(dataDir ?? "data", JsonRelativePath);
        try
        {
            if (!File.Exists(path))
            {
                ExportBuiltIn(path);
                Console.WriteLine("[quest] {0} not found — exported the built-in tables there ({1} story, {2} checklist)",
                    path, BuiltInStory.Length, BuiltInChecklist.Length);
                return false;
            }
            FileJson file = JsonConvert.DeserializeObject<FileJson>(File.ReadAllText(path))
                            ?? throw new InvalidDataException("empty file");
            string main = string.IsNullOrWhiteSpace(file.MainCategory) ? MainCategory : file.MainCategory;
            string daily = string.IsNullOrWhiteSpace(file.ChecklistCategory) ? ChecklistCategory : file.ChecklistCategory;
            var story = Convert(file.Story, main, "story");
            var checklist = Convert(file.Checklist, daily, "checklist");
            Apply(story, checklist, string.IsNullOrWhiteSpace(file.RaftQuestId) ? RaftQuestId : file.RaftQuestId);
            Source = path;
            Console.WriteLine("[quest] loaded {0}: {1} story + {2} checklist quests", path, story.Length, checklist.Length);
            return true;
        }
        catch (Exception e)
        {
            Console.WriteLine("[quest] ⚠️ could not load {0}: {1} — using the built-in tables", path, e.Message);
            Apply(BuiltInStory, BuiltInChecklist, BuiltInRaftQuestId);
            Source = "built-in";
            return false;
        }
    }

    private static Quest[] Convert(List<QuestJson> list, string category, string section)
    {
        var result = new List<Quest>(list?.Count ?? 0);
        int n = 0;
        foreach (QuestJson q in list ?? new List<QuestJson>())
        {
            n++;
            if (q == null || string.IsNullOrWhiteSpace(q.Id))
            {
                throw new InvalidDataException($"{section}[{n}]: missing id");
            }
            if (!Enum.TryParse(q.Goal ?? "", true, out Goal goal))
            {
                throw new InvalidDataException($"{section}[{n}] {q.Id}: unknown goal '{q.Goal}'");
            }
            var items = new List<(string, int)>();
            if (q.Reward?.Items != null)
            {
                foreach (KeyValuePair<string, int> kv in q.Reward.Items)
                {
                    items.Add((kv.Key, kv.Value));
                }
            }
            var reward = new Reward(q.Reward?.Exp ?? 0, q.Reward?.SkillPoints ?? 0, items.ToArray());
            result.Add(new Quest(q.Id, category, goal, string.IsNullOrEmpty(q.Param) ? null : q.Param, q.Count,
                string.IsNullOrEmpty(q.Requires) ? null : q.Requires, reward, q.Text));
        }
        return result.ToArray();
    }

    /// <summary>Write the built-in tables as quests.json (pretty, UTF-8) — the reference copy of the format.</summary>
    public static void ExportBuiltIn(string path)
    {
        var file = new JObject
        {
            ["main_category"] = MainCategory,
            ["checklist_category"] = ChecklistCategory,
            ["raft_quest_id"] = BuiltInRaftQuestId,
            ["story"] = ToJson(BuiltInStory),
            ["checklist"] = ToJson(BuiltInChecklist),
        };
        Directory.CreateDirectory(Path.GetDirectoryName(path) ?? ".");
        File.WriteAllText(path, file.ToString(Formatting.Indented));
    }

    private static JArray ToJson(Quest[] quests)
    {
        var arr = new JArray();
        foreach (Quest q in quests)
        {
            var items = new JObject();
            foreach ((string proto, int count) in q.Prize.Items)
            {
                items[proto] = count;
            }
            arr.Add(new JObject
            {
                ["id"] = q.Id,
                ["goal"] = q.Kind.ToString(),
                ["param"] = q.Param,
                ["count"] = q.Count,
                ["requires"] = q.Requires,
                ["reward"] = new JObject { ["exp"] = q.Prize.Exp, ["skill_points"] = q.Prize.SkillPoints, ["items"] = items },
                ["text"] = q.Thai,
            });
        }
        return arr;
    }
}
