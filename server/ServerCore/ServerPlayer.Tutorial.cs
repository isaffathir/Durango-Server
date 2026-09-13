using System;
using System.Collections.Generic;
using System.Linq;
using Durango.Network;
using Messages;

namespace DurangoServer.Core;

/// <summary>
/// [isaf] Ancora tutorial support — the client (5.2.1) ships the whole Ancora guide (K, the dog Pia,
/// Charlie at the bonfire, the survivors at the shipyard) as play-guide flows that run whenever the
/// region role is <c>Tutorial</c>. The server only has to provide the few things the flows talk to:
///
///   * the shared escape raft (entity type 9000, blueprint <c>tutorial_boat</c>) — announced with
///     <see cref="AppearTutorialBoat"/>, joined with <see cref="ParticipateTutorialBoat"/>, filled with
///     <see cref="PutMaterialsIntoTutorialBoat"/> (4 logs + 6 stems, see BlueprintRequirements) and
///     sailed with DepartTutorial (ServerPlayer.Travel.cs)
///   * <see cref="TutorialEvent"/> — scripted survival beats sent by the guide (CustomCommand.cs):
///     init_health (lying on the beach), resurrect (after K's CPR), restore_food_k (K hands over a
///     survival ration), set_tired (fatigue spikes so the bonfire lesson makes sense)
/// </summary>
public partial class ServerPlayer
{
    public const ushort TutorialBoatEntityType = 9000;

    /// <summary>Wrap an artifact as the message TutorialIslandSystem expects, with the current session list.</summary>
    private AppearTutorialBoat MakeAppearTutorialBoat(AppearArtifact art)
    {
        return new AppearTutorialBoat
        {
            EntityId = art.EntityId,
            EntityType = art.EntityType,
            IsAlive = art.IsAlive,
            Tile = art.Tile,
            Size = art.Size,
            Height = art.Height,
            Floor = art.Floor,
            Stories = art.Stories,
            HasRoof = art.HasRoof,
            Rotation = art.Rotation,
            Display = art.Display,
            Tags = art.Tags,
            States = art.States,
            FounderEntityId = art.FounderEntityId ?? string.Empty,
            Status = _world.BuildTutorialBoatStatus(art.EntityId)
        };
    }

    private bool TryGetTutorialBoat(string entityId, out AppearArtifact boat)
    {
        boat = default;
        if (string.IsNullOrEmpty(entityId) || !_world.TryGetArtifact(entityId, out boat))
        {
            return false;
        }
        return boat.EntityType == TutorialBoatEntityType;
    }

    /// <summary>Every slot of the raft holds what the blueprint asks for.</summary>
    private bool IsTutorialBoatComplete(string entityId, out string state)
    {
        state = null;
        if (!TryGetTutorialBoat(entityId, out _))
        {
            state = "bukan rakit tutorial";
            return false;
        }
        if (!TryGetBuildSlots(entityId, out BlueprintRequirements.Slot[] slots, out string reason))
        {
            state = reason ?? "resep rakit tidak dikenal";
            return false;
        }
        Dictionary<string, List<Item>> stored = _world.GetArtifactMaterials(entityId) ?? new Dictionary<string, List<Item>>();
        var missing = new List<string>();
        for (int i = 0; i < slots.Length; i++)
        {
            int have = stored.TryGetValue(slots[i].Id, out List<Item> items) ? items.Count : 0;
            if (have < slots[i].Min)
            {
                missing.Add($"{TutorialSlotName(slots[i].Id)} {have}/{slots[i].Min}");
            }
        }
        if (missing.Count > 0)
        {
            state = "masih kurang " + string.Join(", ", missing);
            return false;
        }
        return true;
    }

    private static string TutorialSlotName(string slotId)
    {
        switch (slotId)
        {
            case "log": return "batang kayu";
            case "stem": return "batang alang-alang";
            default: return slotId;
        }
    }

    // ── ParticipateTutorialBoat ──────────────────────────────────────────────────────

    /// <summary>
    /// Sent automatically by the client the first time a player touches the raft while not in a
    /// session (TutorialIslandSystem.InteractionSystem_PreTouchTarget). We run one shared session per
    /// raft — everyone on Ancora builds the same boat, like the survivors in the story.
    /// </summary>
    private void HandleParticipateTutorialBoat(ParticipateTutorialBoat msg, PacketHeader header)
    {
        if (!TryGetTutorialBoat(msg.EntityId, out AppearArtifact boat))
        {
            Send(Aborts.Reason(), header.Seq);
            return;
        }
        if (!IsWithinReach(boat.Tile))
        {
            Send(new Info { Text = "Terlalu jauh dari rakit" }, header.Seq);
            Send(Aborts.Reason(), header.Seq);
            return;
        }
        bool joined = _world.JoinTutorialBoat(msg.EntityId, EntityId);
        if (joined)
        {
            Console.WriteLine("[tutorial] {0} ikut membangun rakit {1}", Name, msg.EntityId);
        }
        TutorialBoatSessions status = _world.BuildTutorialBoatStatus(msg.EntityId);
        Send(status, header.Seq);
        _world.BroadcastToViewers(msg.EntityId, status, this);
    }

    // ── PutMaterialsIntoTutorialBoat ────────────────────────────────────────────────

    /// <summary>
    /// Same rules as depositing into a normal construction site (slot tags, per-slot maximum,
    /// items must really be in the bag) but without the ownership check — the raft belongs to everyone.
    /// </summary>
    private void HandlePutMaterialsIntoTutorialBoat(PutMaterialsIntoTutorialBoat msg, PacketHeader header)
    {
        if (Dead)
        {
            Send(Aborts.Reason(), header.Seq);
            return;
        }
        if (!TryGetTutorialBoat(msg.EntityId, out AppearArtifact boat))
        {
            Console.WriteLine("[tutorial] PutMaterials ditolak {0}: bukan rakit {1}", Name, msg.EntityId);
            Send(Aborts.Reason(), header.Seq);
            return;
        }
        if (!IsWithinReach(boat.Tile))
        {
            Send(new Info { Text = "Terlalu jauh dari rakit" }, header.Seq);
            Send(Aborts.Reason(), header.Seq);
            return;
        }
        _world.JoinTutorialBoat(msg.EntityId, EntityId);

        bool hasSlots = TryGetBuildSlots(msg.EntityId, out BlueprintRequirements.Slot[] slots, out string slotsReason);
        List<string> itemIds = null;
        string reason = null;
        bool valid = hasSlots && ValidateBuildingDeposit(slots, _world.GetArtifactMaterials(msg.EntityId), msg.Materials,
            out itemIds, out reason);
        if (!valid)
        {
            string message = slotsReason ?? reason ?? "Bahan tidak valid";
            Console.WriteLine("[tutorial] PutMaterials ditolak {0}: {1}", Name, message);
            Send(new Info { Text = message }, header.Seq);
            Send(Aborts.Reason(), header.Seq);
            return;
        }

        var deposits = new Dictionary<string, List<Item>>();
        lock (_inventory)
        {
            foreach (KeyValuePair<string, string[]> pair in msg.Materials)
            {
                var items = new List<Item>();
                foreach (string id in pair.Value ?? Array.Empty<string>())
                {
                    int index = _inventory.FindIndex(x => x.Id == id);
                    if (index < 0)
                    {
                        Send(Aborts.Reason(), header.Seq);
                        return;
                    }
                    items.Add(_inventory[index]);
                }
                if (items.Count > 0)
                {
                    deposits[pair.Key] = items;
                }
            }
            foreach (string id in itemIds)
            {
                int index = _inventory.FindIndex(x => x.Id == id);
                if (index >= 0)
                {
                    _inventory.RemoveAt(index);
                }
            }
        }
        var maximums = new Dictionary<string, int>();
        for (int i = 0; i < slots.Length; i++)
        {
            maximums[slots[i].Id] = slots[i].Max;
        }
        if (!_world.TryReserveArtifactMaterials(msg.EntityId, deposits, maximums))
        {
            lock (_inventory)
            {
                foreach (KeyValuePair<string, List<Item>> pair in deposits)
                {
                    _inventory.AddRange(pair.Value);
                }
            }
            Send(new Info { Text = "Slot rakit itu sudah dipenuhi pemain lain" }, header.Seq);
            SendInventory();
            Send(Aborts.Reason(), header.Seq);
            return;
        }
        MarkDirty();
        SendInventory();

        var added = new List<Pair<string, int>>();
        foreach (KeyValuePair<string, List<Item>> pair in deposits)
        {
            // client prints T._(Item1) — the localized name of the *slot* ("log" / "stem") reads well enough
            added.Add(new Pair<string, int>(pair.Key, pair.Value.Count));
        }
        TutorialBoatSessions status = _world.BuildTutorialBoatStatus(msg.EntityId);
        string sessionId = status.Sessions != null && status.Sessions.Length > 0 ? status.Sessions[0].SessionId : msg.EntityId;
        var updated = new TutorialBoatMaterialUpdated
        {
            SessionId = sessionId,
            PlayerName = Name,
            Materials = added.ToArray()
        };
        Send(updated, header.Seq);
        Send(status, header.Seq);
        _world.BroadcastToViewers(msg.EntityId, updated, this);
        _world.BroadcastToViewers(msg.EntityId, status, this);
        Send(default(OK), header.Seq);
        Console.WriteLine("[tutorial] {0} memasukkan {1} ke rakit {2}", Name,
            string.Join(", ", added.Select(a => a.Item1 + " x" + a.Item2)), msg.EntityId);

        if (IsTutorialBoatComplete(msg.EntityId, out _))
        {
            _world.BroadcastToViewers(msg.EntityId, new Info { Text = "Rakit sudah lengkap! Sentuh rakit dan pilih Berlayar untuk meninggalkan Ancora." });
            Send(new Info { Text = "Rakit sudah lengkap! Sentuh rakit dan pilih Berlayar untuk meninggalkan Ancora." });
        }
    }

    // ── TutorialEvent ────────────────────────────────────────────────────────────────

    /// <summary>Scripted beats from the client guide — only honoured on a Tutorial island.</summary>
    private void HandleTutorialEvent(TutorialEvent msg, PacketHeader header)
    {
        if (GameServer.RegionRole != Shared.Region.Role.Tutorial)
        {
            return;
        }
        EnsureSurvival();
        switch ((msg.Event ?? string.Empty).Trim().ToLowerInvariant())
        {
            case "init_health":
                // washed up on the beach: barely alive, starving — K's CPR and ration fix both
                SetGaugeValue("life", Math.Max(1f, LifeMax * 0.08f));
                SetGaugeValue("stamina", Math.Max(1f, StaminaMax * 0.05f));
                SetGaugeValue("fatigue", 0f);
                break;
            case "resurrect":
                SetGaugeValue("life", LifeMax);
                break;
            case "restore_food_k":
                // K: "I'll give you an emergency ration" — the next guide step is to eat it
                if (!HasItemOfPrototype("ration_survival"))
                {
                    ModGiveItems("ration_survival", 1);
                }
                break;
            case "set_tired":
                // Charlie's bonfire lesson needs a tired pioneer (guide waits for fatigue <= 50%)
                SetGaugeValue("fatigue", FatigueMax);
                break;
            default:
                Console.WriteLine("[tutorial] event tidak dikenal dari {0}: {1}", Name, msg.Event);
                return;
        }
        Console.WriteLine("[tutorial] {0} event {1}", Name, msg.Event);
    }

    private bool HasItemOfPrototype(string prototypeId)
    {
        lock (_inventory)
        {
            for (int i = 0; i < _inventory.Count; i++)
            {
                if (string.Equals(_inventory[i].Prototype, prototypeId, StringComparison.Ordinal))
                {
                    return true;
                }
            }
        }
        return false;
    }
}
