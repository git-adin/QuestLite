"""Extract compact Forever display policy from local Questie reference files.

Usage: python tools/build_availability_policy.py QUESTIE_DIR QUESTIEDB_DIR
Only IDs present in the installed Forever DB are retained. Runtime has no Questie
dependency. Reference Lua is evaluated with a restricted, data-only environment.
"""
import base64
import hashlib
from pathlib import Path
import re
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import cbor2
from lupa.lua51 import LuaRuntime

questie, database = map(Path, sys.argv[1:3])
def toc_version(path):
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if line.startswith('## Version:'):
            return line.split(':', 1)[1].strip()
    raise RuntimeError(f'Missing version metadata: {path}')

questie_version = toc_version(questie / 'Questie_Forever.toc')
database_version = toc_version(database / 'QuestieDB_Forever.toc')
guide_version = toc_version(ROOT / 'QuestLite/QuestLite.toc')
meta = {}
for line in (database / 'QuestieDB_Forever.toc').read_text(encoding='utf-8-sig').splitlines():
    if line.startswith('## ') and ': ' in line:
        key, value = line[3:].split(': ', 1)
        meta[key] = value
encoded = meta['X-Quest-IDS']
if encoded.startswith('~'):
    encoded = ''.join(meta[f'X-Quest-IDS-{i}'] for i in range(1, int(encoded.strip('~')) + 1))
present = set(cbor2.loads(zlib.decompress(base64.b64decode(encoded))))
source = (questie / 'Database/Corrections/QuestieQuestBlacklist.lua').read_text(encoding='utf-8-sig')
lua = LuaRuntime(unpack_returned_tuples=True)
env = lua.execute('''
    local modules={Expansions={Current=1,Era=1,Classic=1,Tbc=2,Wotlk=3,Cata=4,MoP=5}}
    local function module(name)
        modules[name]=modules[name] or {}; return modules[name]
    end
    return {QuestieLoader={CreateModule=function(_,name) return module(name) end,
        ImportModule=function(_,name) return module(name) end},
        Questie={IsForever=true,IsClassic=true},table=table,pairs=pairs,ipairs=ipairs,
        modules=modules}
''')
execute = lua.eval('function(code, env, ...) local f=assert(loadstring(code)); setfenv(f,env); return f(...) end')
execute(source, env)
blacklist = env.modules.QuestieQuestBlacklist
expected_event_groups = {'AQWarEffortQuests', 'InvasionQuests'}
actual_event_groups = {str(name) for name, value in blacklist.items()
                       if str(name).endswith('Quests') and hasattr(value, 'items')}
assert actual_event_groups == expected_event_groups, f'Unreviewed event groups: {actual_event_groups ^ expected_event_groups}'
rows = blacklist.Load(blacklist)
hidden = {int(id) for id, flag in rows.items() if flag and id in present}
for id, flag in blacklist.InvasionQuests.items():
    if flag and id in present:
        hidden.add(int(id))
# AQ War Effort is an independent category in Questie, not part of its
# ordinary hidden-quest or holiday tables. Include signets and supply turn-ins.
aq_ids = {int(id) for id, flag in blacklist.AQWarEffortQuests.items() if flag and id in present}
hidden.update(aq_ids)
# Holiday quest files contain data registrations only; no calendar UI is loaded.
event_ids = set()
holiday_groups = {}
env.modules.QuestieEvent = lua.table(eventQuests=lua.table())
for file in sorted((questie / 'Database/Corrections/Holidays/quests').glob('*.lua')):
    before = len(env.modules.QuestieEvent.eventQuests)
    execute(file.read_text(encoding='utf-8-sig'), env)
    holiday_groups[file.stem] = {int(env.modules.QuestieEvent.eventQuests[i][2])
                               for i in range(before + 1, len(env.modules.QuestieEvent.eventQuests) + 1)
                               if env.modules.QuestieEvent.eventQuests[i][2] in present}
for _, row in env.modules.QuestieEvent.eventQuests.items():
    if row[2] in present:
        event_ids.add(int(row[2]))
hidden.update(event_ids)
# Cross-check database event categories as well as hand-maintained ID lists.
# This catches new Forever event quests not yet registered in Questie's lists.
namespace = lua.table(Enum=lua.table())
execute((database / 'src/corrections/enum/quests.lua').read_text(encoding='utf-8-sig'), env, 'QuestieDB', namespace)
execute((database / 'src/meta/questMeta.lua').read_text(encoding='utf-8-sig'), env, 'QuestieDB', namespace)
event_sort_names = ['WINTER_VEIL', 'HARVEST_FESTIVAL', 'CHILDRENS_WEEK', 'LOVE_IS_IN_THE_AIR',
                    'PILGRIMS_BOUNTY', 'NOBLEGARDEN', 'BREWFEST', 'MIDSUMMER', 'LUNAR_FESTIVAL',
                    'DARKMOON_FAIRE', 'DAY_OF_THE_DEAD', 'SEASONAL', 'HALLOWS_END', 'INVASION', 'AHN_QIRAJ_WAR']
enum_source = (database / 'src/corrections/enum/quests.lua').read_text(encoding='utf-8-sig')
holiday_section = enum_source.split('-- Holidays and recurring events', 1)[1].split('-- Classic and Wrath', 1)[0]
declared_holiday_sorts = set(re.findall(r'^\s*([A-Z_]+)\s*=\s*-\d+', holiday_section, re.M))
assert not (declared_holiday_sorts - set(event_sort_names)), f'Unreviewed holiday categories: {declared_holiday_sorts - set(event_sort_names)}'
event_sorts = {int(namespace.Enum.sortKeys[name]): name for name in event_sort_names}
zone_field = int(namespace.Meta.Quest['keys']['zoneOrSort'])
category_groups = {name: set() for name in event_sort_names}
new_category_ids = []
def stored(key):
    value = meta.get(key)
    if value and value.startswith('~'):
        value = ''.join(meta[f'{key}-{i}'] for i in range(1, int(value.strip('~')) + 1))
    return value
for id in sorted(present):
    scalar = stored(f'X-Quest-{id}-S')
    if not scalar:
        continue
    row = cbor2.loads(base64.b64decode(scalar))
    sort = row.get(zone_field) if isinstance(row, dict) else (row[zone_field - 1] if len(row) >= zone_field else None)
    if sort in event_sorts:
        category_groups[event_sorts[sort]].add(id)
        if id not in hidden:
            new_category_ids.append(id)
        hidden.add(id)
execute((questie / 'Database/Corrections/QuestieNPCBlacklist.lua').read_text(encoding='utf-8-sig'), env)
npc_rows = env.modules.QuestieNPCBlacklist.Load(env.modules.QuestieNPCBlacklist)
hidden_givers = sorted(int(id) for id, flag in npc_rows.items() if flag)

professions = (questie / 'Modules/QuestieProfessions.lua').read_text(encoding='utf-8-sig')
text = re.sub(r'--[^\n]*', '', professions)
start = text.index('{', text.index('QuestieProfessions.rankKeys ='))
depth = 0
for end in range(start, len(text)):
    depth += (text[end] == '{') - (text[end] == '}')
    if depth == 0:
        ranks = lua.eval(text[start:end + 1])
        break

lines = ['-- SPDX-License-Identifier: GPL-3.0-or-later',
         '-- GENERATED by tools/build_availability_policy.py; do not hand-edit.',
         f'-- Source: installed Questie v{questie_version}; QuestieDB Forever v{database_version}',
         '-- QuestieQuestBlacklist.lua SHA256: ' + hashlib.sha256(source.encode()).hexdigest(),
         '-- Classic/Forever context only; other-expansion branches are not imported.',
         '-- Seasonal/hidden entries can be restored by an explicit server offer.',
         'local _, ns = ...', 'ns.pickupPolicy.hidden = {']
ids = sorted(hidden)
for start in range(0, len(ids), 12):
    lines.append('    ' + ','.join(f'[{id}]=true' for id in ids[start:start + 12]) + ',')
lines += ['}', 'ns.pickupPolicy.eventSorts = {' + ','.join(f'[{id}]=true' for id in sorted(event_sorts)) + '}',
          'ns.pickupPolicy.aq = {' + ','.join(f'[{id}]=true' for id in sorted(aq_ids)) + '}',
          'ns.pickupPolicy.hiddenGivers = {' + ','.join(f'[{id}]=true' for id in hidden_givers) + '}',
          'ns.professionRankSpells = {']
for skill, spells in sorted(ranks.items()):
    lines.append(f'    [{int(skill)}] = {{' + ','.join(str(int(v)) for _, v in sorted(spells.items())) + '},')
lines += ['}', '']
output = ROOT / 'QuestLite/AvailabilityPolicyData.lua'
output.write_text('\n'.join(lines), encoding='utf-8')
print(f'{len(hidden)} applicable hidden/conditional quest IDs; {len(event_ids)} holiday IDs; {len(list(ranks.items()))} profession rank tables')
print(f'{len(aq_ids)} AQ War Effort/commendation quests included as a separate event category')
print(f'{len(holiday_groups)} holiday registration files and {len(event_sorts)} database event categories checked; newly covered IDs: {new_category_ids}')
print(f'{len(hidden_givers)} applicable NPC display exclusions; Wrath achievement examples in Forever DB: {len(present.intersection({14101,14102,14104,14105,14107,14108}))}')
print(output)

report = [f'# Event coverage audit - {guide_version}', '',
          f'Checked against the installed Questie v{questie_version} and QuestieDB Forever v{database_version}.',
          'Counts overlap across lists and database categories; they are not additive.', '',
          '## Separate event lists', '',
          '| Group | IDs present in Forever |', '| --- | ---: |',
          f'| AQ War Effort / commendations | {len(aq_ids)} |',
          f'| Scourge Invasion list | {sum(1 for id, flag in blacklist.InvasionQuests.items() if flag and id in present)} |',
          '', '## All holiday registration files', '',
          '| Registration file | IDs present in Forever |', '| --- | ---: |']
for name, ids in sorted(holiday_groups.items()):
    report.append(f'| {name} | {len(ids)} |')
report += ['', '## Database categories checked independently', '',
           '| Category | Tagged quests | Uncovered after generation |', '| --- | ---: | ---: |']
for name, ids in category_groups.items():
    report.append(f'| {name} | {len(ids)} | {len(ids - hidden)} |')
report += ['', '## Previously missed category entries', '',
           'The database-category pass additionally found IDs: ' + ', '.join(map(str, new_category_ids)) + '.',
           'The composed-database check identifies 98977 (Mossheart the Elder),',
           '98983 (Frostleaf the Elder), and 98471 (Message from the Supreme Magister).', '',
           '## Ongoing safeguards and limits', '',
           '- Generation fails if Questie adds an unreviewed separate event Quests table, or QuestieDB adds a holiday category in its holiday enum section.',
           '- Holiday files are discovered automatically, including files whose quests are absent from Forever.',
           '- Runtime filtering checks the composed quest category too, covering new quests in reviewed event categories after a DB update.',
           '- Persistent battlegrounds, class/profession sorts, raid zones, and ordinary campaigns are not treated as temporary holidays.',
           '- Anniversary and Pirates Day appear in reference comments, but have no separate registered quest list in this installed version. Categorized seasonal entries remain covered.',
           '- No SoD-only Blackrock Eruption or Nightmare Incursion quest categories occur in the installed Forever data; their realm-specific phase assumptions are not imported.',
           '- This verifies all event groups found in these local references and metadata, not unknown server-only events with no IDs or event tags.',
           '- Strict mode still requires a current NPC offer for event pickups. Automatic calendar/realm activation is not implemented; use the broad view to browse events beforehand.', '']
(ROOT / 'QuestLite/EventCoverage.md').write_text('\n'.join(report), encoding='utf-8')
