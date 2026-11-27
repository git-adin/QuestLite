"""Read-only comparison of installed ForeverDB and QuestieDB with QuestLite policy.

Data from ForeverDB.net (https://foreverdb.net).
No third-party runtime is added to QuestLite. Reports are review candidates,
not automatically inferred requirements. Requires tests' lupa/cbor2 dependencies.
"""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import re
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('questiedb', type=Path)
parser.add_argument('foreverdb', type=Path)
parser.add_argument('--output', type=Path, default=ROOT / 'dist/foreverdb-comparison.json')
args = parser.parse_args()
sys.argv = [str(ROOT / 'tests/check_installed_database.py'), str(args.questiedb)]
with contextlib.redirect_stdout(io.StringIO()):
    context = runpy.run_path(sys.argv[0])
lua, provider, guide = context['lua'], context['provider'], context['ns']
forever = lua.table()
inputs = {}
for name in ('QuestClassic', 'QuestForever', 'QuestGuide', 'Meta'):
    path = args.foreverdb / 'Data' / f'{name}.lua'
    source = path.read_bytes()
    inputs[str(path)] = hashlib.sha256(source).hexdigest()
    # Only the generated data chunks; no ForeverDB event/UI/recording code.
    lua.execute(source, b'ForeverDB', forever)
quest, npc = provider[b'Quest'], provider[b'Npc']
known = set(quest.GetAllIds().values())


def string(value):
    return value.decode('utf-8') if isinstance(value, bytes) else value


def fields(value):
    return string(value).split('|') if value else []


def ids(value):
    return list(value.values()) if value is not None else []


def refs(text):
    return sorted(re.findall(r'([noi])(\d+)', text))


def native_refs(value):
    result = []
    for index, prefix in ((1, 'n'), (2, 'o'), (3, 'i')):
        for entity in ids(value[index]) if value is not None and value[index] is not None else []:
            result.append((prefix, str(entity)))
    return sorted(result)


def active_fallback(qid):
    single = ids(quest.Get(qid, b'preQuestSingle'))
    group = ids(quest.Get(qid, b'preQuestGroup'))
    return (not single and not group) or (qid == 545 and single == [544] and not group)


report = {'credit': 'Data from ForeverDB.net (https://foreverdb.net)', 'input_sha256': inputs,
          'counts': {'questiedb': len(known)}, 'missing_quests': [], 'previous_candidates': [],
          'giver_differences': [], 'level_differences': [], 'location_differences': [],
          'classic_requirement_differences': []}
for key in (b'qcQuests', b'qfQuests', b'qgQuests', b'qfNpcSpots', b'qfSeen', b'qfPoi'):
    report['counts'][key.decode()] = len(list(forever[key].keys()))
report['foreverdb_meta'] = {string(k): string(v) for k, v in forever[b'meta'].items()}
toc_path = args.questiedb / 'QuestieDB_Forever.toc'
report['input_sha256'][str(toc_path)] = hashlib.sha256(toc_path.read_bytes()).hexdigest()
report['questiedb_version'] = re.search(r'^## Version:\s*(.+)', toc_path.read_text(encoding='utf-8-sig'), re.M).group(1)
report['questlite_chain_coverage'] = []
for table_key, mode in ((b'chainPrerequisiteOverrides', 'all'), (b'chainAlternativeOverrides', 'any')):
    for qid, previous in sorted(guide[table_key].items()):
        row = fields(forever[b'qfQuests'][qid])
        report['questlite_chain_coverage'].append({'id': qid, 'title': string(quest.name(qid)),
            'local_requirements': ids(previous), 'mode': mode, 'fallback_active': active_fallback(qid),
            'native_single': ids(quest.Get(qid, b'preQuestSingle')),
            'native_group': ids(quest.Get(qid, b'preQuestGroup')), 'forever_sequence': int(row[8]) if row else None})
for qid, encoded in sorted(forever[b'qfQuests'].items()):
    row = fields(encoded)
    if len(row) not in (10, 11, 12, 13):
        raise ValueError(f'Unsupported ForeverDB quest row schema for {qid}: {len(row)} fields')
    title, level, minimum, _, starts, ends, witnesses, new, previous, _ = row[:10]
    # Inferred side is optional. The later offer-floor and class observations
    # do not change the indexes used for this report.
    side_hint = row[10] if len(row) >= 11 else ''
    common = {'id': qid, 'title': title or string(quest.name(qid)) or f'Quest {qid}', 'witnesses': int(witnesses), 'new': new == '1', 'inferred_side': side_hint}
    if qid not in known:
        report['missing_quests'].append(common | {'starts': starts, 'ends': ends,
            'disposition': 'review; no invented giver, location or restrictions'})
        continue
    get = lambda key: quest.Get(qid, key.encode())
    requirements = set(ids(get('preQuestSingle')) + ids(get('preQuestGroup')))
    if active_fallback(qid):
        requirements.update(ids(guide[b'chainPrerequisiteOverrides'][qid]))
        requirements.update(ids(guide[b'chainAlternativeOverrides'][qid]))
    for key in ('parentQuest', 'availableStartingWith', 'breadcrumbForQuestId'):
        if get(key): requirements.add(get(key))
    if int(previous) > 0 and int(previous) not in requirements:
        report['previous_candidates'].append(common | {'previous': int(previous),
            'previous_title': string(quest.name(int(previous))),
            'existing_single': ids(get('preQuestSingle')), 'existing_group': ids(get('preQuestGroup'))})
    for key, observed in (('startedBy', starts), ('finishedBy', ends)):
        if observed and refs(observed) != native_refs(get(key)):
            report['giver_differences'].append(common | {'field': key,
                'forever': refs(observed), 'questiedb': native_refs(get(key)),
                'disposition': 'preserve valid alternatives: observed subset' if set(refs(observed)).issubset(set(native_refs(get(key))))
                    else 'Horde library turn-in corrected' if guide[b'pickupPolicy'][b'collection'][qid] and key == 'finishedBy'
                        and refs(observed) == [('n', '211022')] and native_refs(get(key)) == [('n', '211033')] else 'review'})
    for key, observed in (('questLevel', int(level)), ('requiredLevel', int(minimum))):
        if observed > 0 and observed != get(key):
            override = guide[b'questFieldOverrides']
            correction = override[qid][key.encode()] if override is not None and override[qid] is not None else None
            effective = correction[b'value'] if correction is not None and correction[b'was'] == get(key) else get(key)
            report['level_differences'].append(common | {'field': key, 'forever': observed, 'questiedb': get(key), 'questlite': effective,
                'disposition': 'corrected' if effective == observed else 'preserve scaling' if get(key) is not None and get(key) <= 0 else 'review: multiple observers' if int(witnesses) >= 2 else 'review: single observer'})
    quest.InvalidateCache(qid)

mapping = {}
zone = provider[b'Support'].Get(b'ZoneDB')[b'private']
for key in (b'areaIdToUiMapId', b'areaIdToUiMapIdOverride'):
    table = lua.table()
    guide[b'test'][b'MergeMap'](table, zone[key])
    mapping.update(dict(table.items()))
for nid, encoded in sorted(forever[b'qfNpcSpots'].items()):
    native = []
    spawns = npc.spawns(nid)
    for area, points in spawns.items() if spawns is not None else []:
        for point in points.values():
            if mapping.get(area): native.append((mapping[area], point[1], point[2]))
    for token in string(encoded).split():
        packed = int(token, 36)
        mapid, remainder = divmod(packed, 1000000)
        x, y = remainder // 1000 / 10, remainder % 1000 / 10
        distances = [(x-nx)**2+(y-ny)**2 for m, nx, ny in native if m == mapid]
        if not distances or min(distances) > 100:
            report['location_differences'].append({'npc': nid, 'name': string(forever[b'qfNpcNames'][nid]),
                'map': mapid, 'x': x, 'y': y, 'nearest_distance': min(distances)**.5 if distances else None,
                'disposition': 'missing spawn fallback added' if nid == 14242 else 'review; roaming/alternate location not overwritten'})
    npc.InvalidateCache(nid)

for qid, encoded in sorted(forever[b'qcQuests'].items()):
    if qid not in known: continue
    row = fields(encoded)
    all_ids = sorted(int(v) for v in re.findall(r'-?\d+', row[6]))
    any_ids = sorted(int(v) for v in re.findall(r'-?\d+', row[7]))
    native_any = sorted(ids(quest.Get(qid, b'preQuestSingle')))
    native_all = sorted(abs(v) for v in ids(quest.Get(qid, b'preQuestGroup')))
    def expression(all_values, any_values):
        if len(all_values) == 1 and not any_values: return ('any', tuple(all_values))
        if not all_values: return ('any', tuple(any_values))
        return ('all_and_any', tuple(all_values), tuple(any_values))
    # QuestLite/Questie use preQuestSingle when present, otherwise preQuestGroup.
    if expression(all_ids, any_ids) != expression([] if native_any else native_all, native_any):
        if all_ids or any_ids:
            report['classic_requirement_differences'].append({'id': qid, 'title': row[0],
                'classic_all': all_ids, 'classic_any': any_ids,
                'questiedb_all': ids(quest.Get(qid, b'preQuestGroup')),
                'questiedb_any': ids(quest.Get(qid, b'preQuestSingle'))})
    quest.InvalidateCache(qid)
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
resolved = [row for row in report['level_differences'] if row['questlite'] == row['forever']]
for row in resolved:
    assert row['witnesses'] >= 2 and row['questiedb'] > 0, 'Unsupported/scaling level correction'
print(f'QuestLite resolves {len(resolved)} fixed-level differences; no sequence candidates auto-imported.')
print(json.dumps(report['counts']))
for key, value in report.items():
    if isinstance(value, list): print(f'{key}: {len(value)}')
print(args.output)
