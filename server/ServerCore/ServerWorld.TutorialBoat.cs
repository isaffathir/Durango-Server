using System;
using System.Collections.Generic;
using System.Linq;
using Messages;

namespace DurangoServer.Core;

/// <summary>
/// [isaf] Ancora escape raft — one shared building session per raft (entity type 9000). The materials
/// themselves live in the normal per-artifact material store (<see cref="TryReserveArtifactMaterials"/>),
/// so they survive restarts; only the participant list is in memory (the client re-joins on touch).
/// </summary>
public partial class ServerWorld
{
    private readonly Dictionary<string, HashSet<string>> _tutorialBoatCrews = new Dictionary<string, HashSet<string>>(StringComparer.Ordinal);
    private readonly object _tutorialBoatLock = new object();

    /// <summary>Add a player to the raft's crew. Returns true when newly added.</summary>
    public bool JoinTutorialBoat(string boatEntityId, string playerEntityId)
    {
        if (string.IsNullOrEmpty(boatEntityId) || string.IsNullOrEmpty(playerEntityId))
        {
            return false;
        }
        lock (_tutorialBoatLock)
        {
            if (!_tutorialBoatCrews.TryGetValue(boatEntityId, out HashSet<string> crew))
            {
                crew = new HashSet<string>(StringComparer.Ordinal);
                _tutorialBoatCrews[boatEntityId] = crew;
            }
            return crew.Add(playerEntityId);
        }
    }

    /// <summary>
    /// The session list the client shows on the raft tooltip / boat ToDos. Materials = how many items
    /// each blueprint slot ("log", "stem") already holds.
    /// </summary>
    public TutorialBoatSessions BuildTutorialBoatStatus(string boatEntityId)
    {
        string[] players;
        lock (_tutorialBoatLock)
        {
            players = _tutorialBoatCrews.TryGetValue(boatEntityId ?? string.Empty, out HashSet<string> crew)
                ? crew.ToArray()
                : Array.Empty<string>();
        }
        var materials = new Dictionary<string, int>(StringComparer.Ordinal);
        Dictionary<string, List<Item>> stored = GetArtifactMaterials(boatEntityId ?? string.Empty);
        if (stored != null)
        {
            foreach (KeyValuePair<string, List<Item>> kv in stored)
            {
                materials[kv.Key] = kv.Value?.Count ?? 0;
            }
        }
        return new TutorialBoatSessions
        {
            Sessions = new[]
            {
                new TutorialSession
                {
                    SessionId = (boatEntityId ?? "boat") + ":crew",
                    Players = players,
                    Materials = materials
                }
            }
        };
    }
}
