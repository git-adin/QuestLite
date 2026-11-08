"""Read-only search for ambiguous pickup-item requirements in installed Forever data.

Usage: python tools/audit_item_gates.py PATH_TO_QUESTIEDB
Reuses the offline integration fixture (including its checks). Writes review data,
never automatic overrides: sourceItemId normally means a quest-provided item.
"""
from pathlib import Path
import contextlib
import io
import json
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
database = sys.argv[1]
sys.argv = [str(ROOT / 'tests/check_installed_database.py'), database]
with contextlib.redirect_stdout(io.StringIO()):
    fixture = runpy.run_path(sys.argv[0])
api = fixture['provider']
quest, item = api[b'Quest'], api[b'Item']


def plain(value):
    if isinstance(value, bytes):
        return value.decode('utf-8')
    if hasattr(value, 'items'):
        return {str(k): plain(v) for k, v in value.items()}
    return value


reverse_starters = {}
for item_id in item.GetAllIds().values():
    quest_id = item.Get(item_id, b'startQuest')
    if quest_id and quest_id > 0:
        reverse_starters.setdefault(quest_id, []).append(item_id)
    item.InvalidateCache(item_id)

rows = []
quest_count = source_count = 0
for quest_id in quest.GetAllIds().values():
    quest_count += 1
    source = quest.Get(quest_id, b'sourceItemId')
    starters = quest.Get(quest_id, b'startedBy')
    required = quest.Get(quest_id, b'requiredSourceItems')
    reverse = reverse_starters.get(quest_id, [])
    if source and source > 0:
        source_count += 1
    if starters and (starters[1] or starters[2]) and not required and ((source and source > 0) or reverse):
        row = {'id': quest_id, 'name': plain(quest.name(quest_id)), 'sourceItemId': source,
               'reverseStarterItems': reverse}
        for key in ['startedBy', 'finishedBy', 'requiredLevel', 'questLevel', 'objectivesText',
                    'objectives', 'preQuestSingle', 'preQuestGroup', 'parentQuest',
                    'availableStartingWith', 'nextQuestInChain', 'questFlags', 'specialFlags']:
            row[key] = plain(quest.Get(quest_id, key.encode()))
        if source and source > 0:
            row['item'] = {key: plain(item.Get(source, key.encode())) for key in
                           ['name', 'npcDrops', 'objectDrops', 'itemDrops', 'startQuest', 'questRewards']}
            item.InvalidateCache(source)
        rows.append(row)
    quest.InvalidateCache(quest_id)

looted = sum(bool(row.get('item') and any(row['item'].get(key)
             for key in ['npcDrops', 'objectDrops', 'itemDrops'])) for row in rows)
mixed = sum(bool(row['reverseStarterItems']) for row in rows)
report = {'questCount': quest_count, 'sourceItemQuestCount': source_count,
          'candidateCount': len(rows), 'lootedSourceCandidateCount': looted,
          'mixedStarterCandidateCount': mixed, 'candidates': rows}
destination = ROOT / 'dist/item-gate-audit.json'
destination.parent.mkdir(exist_ok=True)
destination.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(f'{quest_count} quests; {source_count} source-item entries; {len(rows)} review candidates.')
print(f'{looted} looted-source candidates; {mixed} mixed item/NPC or object starter candidates. These are leads, not confirmed bugs.')
print(destination)
