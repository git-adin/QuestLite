"""Read-only integration check against an installed QuestieDB Forever artifact.

Usage: python tests/check_installed_database.py PATH_TO_QUESTIEDB
Requires lupa and cbor2. All WoW functions are emulated; this is not an in-game test.
"""
import base64
from pathlib import Path
import sys
import zlib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
import cbor2
from lupa.lua51 import LuaRuntime

database = Path(sys.argv[1])
toc = (database / 'QuestieDB_Forever.toc').read_bytes().decode('utf-8-sig')
metadata = {}
files = []
for line in toc.splitlines():
    if line.startswith('## ') and ': ' in line:
        key, value = line[3:].split(': ', 1)
        metadata[key.encode()] = value.encode()
    elif line.strip() and not line.startswith('#'):
        files.append(line.strip())

lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
lua.execute((ROOT / 'tests/wow_mock.lua').read_bytes())
lua.globals()[b'pinTemplateMouseEnabled'] = ET.parse(
    ROOT / 'QuestLite/Pins.xml').getroot()[0].attrib.get('enableMouse') == 'true'


def to_lua(value):
    if isinstance(value, dict):
        return lua.table_from({to_lua(k): to_lua(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return lua.table_from([to_lua(v) for v in value])
    if isinstance(value, str):
        return value.encode('utf-8')
    return value


g = lua.globals()
g[b'py_metadata'] = lambda addon, key: metadata.get(key)
g[b'py_base64'] = base64.b64decode
g[b'py_inflate'] = lambda value, method: zlib.decompress(value)
g[b'py_cbor'] = lambda value: to_lua(cbor2.loads(value))
lua.execute(b'''
    C_AddOns.GetAddOnMetadata=function(...) return py_metadata(...) end
    C_EncodingUtil={DecodeBase64=function(...) return py_base64(...) end,
        DecompressString=function(...) return py_inflate(...) end,
        DeserializeCBOR=function(...) return py_cbor(...) end}
    GetLocale=function() return 'enUS' end
    UnitFactionGroup=function() return 'Alliance' end
    UnitClassBase=function() return 'WARRIOR',1 end
''')
sample_horde = '--undead-paladin' in sys.argv
if sample_horde:
    lua.execute(b'''
        UnitFactionGroup=function() return 'Horde' end
        UnitClassBase=function() return 'PALADIN',2 end
        UnitLevel=function() return 22 end
        UnitRace=function() return 'Undead','Scourge',5 end
        UnitClass=function() return 'Paladin','PALADIN',2 end
    ''')
provider = lua.table()
for file in files:
    try:
        lua.execute((database / file.replace('\\', '/')).read_bytes(), b'QuestieDB', provider)
    except Exception as error:
        raise RuntimeError(f'Loading {file}: {error}') from error

ns = lua.table()
ns[b'testing'] = True
for file in ['Core.lua', 'QuestVisibility.lua', 'Diagnostics.lua', 'AvailabilityPolicy.lua', 'AvailabilityPolicyData.lua', 'ForeverDBCorrections.lua', 'Database.lua', 'Options.lua', 'DropChances.lua', 'QuestItems.lua', 'MinimapButton.lua']:
    lua.execute((ROOT / 'QuestLite' / file).read_bytes(), b'QuestLite', ns)
g[b'guide'] = ns
lua.execute(b'''
    guide.LoadSettings()
    guide.db.showLowLevel=true -- Availability audit intentionally covers all quest levels.
    local ok,reason=guide.InitDatabase(); assert(ok,reason)
    checkpoints=0; function Checkpoint() checkpoints=checkpoints+1 end
    emitted=0; kinds={}
    function Emit(id,kind,label,x,y)
        assert(type(id)=='number' and type(kind)=='string')
        assert(x>=0 and x<=1 and y>=0 and y<=1)
        emitted=emitted+1; kinds[kind]=true
    end
''')
lua.execute(b'''
    function NativeRequirements(id)
        return table.concat(LibQuestieDB.Quest.Get(id,'preQuestSingle') or {},',')..'/'..
            table.concat(LibQuestieDB.Quest.Get(id,'preQuestGroup') or {},',')
    end
    nativeRequirements={}
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        nativeRequirements[id]=NativeRequirements(id)
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    function CheckNativeRequirements(id)
        assert(NativeRequirements(id)==nativeRequirements[id],'Provider prerequisite mutated '..id)
    end
    eventCategoryCount=0
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        local sort=LibQuestieDB.Quest.Get(id,'zoneOrSort')
        if guide.pickupPolicy.eventSorts[sort] then
            eventCategoryCount=eventCategoryCount+1
            assert(guide.pickupPolicy.hidden[id], 'Composed database event missed static policy: '..id)
        end
        LibQuestieDB.Quest.InvalidateCache(id)
    end
''')
print(f'Composed database event-category audit: {g[b"eventCategoryCount"]} tagged quests, zero uncovered IDs.')
lua.execute(b'''
    guide.InitDropChances()
    local support=LibQuestieDB.Support.Get('QuestieClassicItemDrops')
    -- Trusted fixture decoding is confined to this offline comparison. The
    -- production addon parses row data and never executes support strings.
    local function Decode(value) return type(value)=='table' and value or assert(loadstring(value))() end
    local wow,server=Decode(support.wowheadData),Decode(support.cmangosData)
    local corrections=LibQuestieDB.Support.Get('QuestieItemDropCorrections').Era
    local function Valid(v) return type(v)=='number' and v>=0 and v<=100 end
    local function Expected(item,npc)
        local c=corrections[item] and corrections[item][npc]
        local w=wow[item] and wow[item][npc]
        local s=server[item] and server[item][npc]
        if Valid(c) then return c end
        if c==-1 and Valid(w) then return w end
        if c==-2 and Valid(s) then return s end
        if Valid(s) then return s end
        if Valid(w) then return w end
    end
    dropPairsChecked=0
    for _,data in ipairs({wow,server,corrections}) do
        for item,row in pairs(data) do
            for npc in pairs(row) do
                assert(guide.testDropChances.Rate(item,npc)==Expected(item,npc), 'Drop mismatch '..item..':'..npc)
                dropPairsChecked=dropPairsChecked+1
            end
        end
    end
    local objectives=LibQuestieDB.Quest.Get(33,'objectives')
    local item=objectives[3][1][1]
    local npc
    for _,id in ipairs(LibQuestieDB.Item.npcDrops(item)) do
        if guide.testDropChances.Rate(item,id) then npc=id; break end
    end
    assert(npc,'No known source for Wolves Across the Border fixture')
    local oldActive=active; active={33}; Fire('QUEST_LOG_UPDATE')
    local tip=CreateFrame('GameTooltip'); tip:SetOwner(UIParent,'ANCHOR_NONE')
    guide.testDropChances.ItemTooltip(tip,{id=item})
    assert(#tip.lines>1 and table.concat(tip.lines,' '):find('%%'),'No item drop-rate tooltip')
    tip:SetOwner(UIParent,'ANCHOR_NONE')
    local itemName=LibQuestieDB.Item.name(item)
    AddNativeTooltipLine(tip,'0/8 '..itemName)
    guide.testDropChances.UnitTooltip(tip,{guid='Creature-0-1-0-0-'..npc..'-00001'})
    assert(#tip.lines==1 and tip.lines[1]:find(itemName..' (',1,true),'No inline NPC drop-rate tooltip')
    active=oldActive; Fire('QUEST_LOG_UPDATE')
''')
print(f'Drop-rate integration: {g[b"dropPairsChecked"]} source/correction pairs matched; active quest item and NPC tooltips passed.')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(98823)=='Earthen Echo')
    assert(LibQuestieDB.Quest.Get(98823,'sourceItemId')==287958)
    local required=LibQuestieDB.Quest.Get(98823,'requiredSourceItems')
    CheckNativeRequirements(98823)
    local oldLevel,oldFaction,oldRace,oldClass,oldItems=UnitLevel,UnitFactionGroup,UnitRace,UnitClass,C_Item
    UnitLevel=function() return 31 end
    UnitFactionGroup=function() return 'Horde' end
    UnitRace=function() return 'Undead','Scourge',5 end
    UnitClass=function() return 'Paladin','PALADIN',2 end
    local inventoryCount=0
    C_Item={GetItemCount=function(id) return id==287958 and inventoryCount or 0 end}
    local zones=LibQuestieDB.Support.Get('ZoneDB').private
    local mappings={}
    guide.test.MergeMap(mappings,zones.areaIdToUiMapId)
    guide.test.MergeMap(mappings,zones.areaIdToUiMapIdOverride)
    local mapID
    for area in pairs(LibQuestieDB.Npc.spawns(9087)) do if mappings[area] then mapID=mappings[area]; break end end
    assert(mapID,'Earthen Echo giver has no mapped location')
    local function Visible()
        local found=false
        guide.BuildMap(mapID,function(id) if id==98823 then found=true end end,Checkpoint)
        return found
    end
    assert(not Visible(),'Earthen Echo appeared before Elder Knowledge turn-in')
    inventoryCount=1; assert(not Visible(),'A provided relic bypassed prerequisite turn-in')
    local oldCompleted=completed[95664]
    completed[95664]=true; inventoryCount=0
    assert(Visible(),'Earthen Echo stayed hidden after prerequisite turn-in without provided relic')
    completed[95664]=oldCompleted
    assert(not LibQuestieDB.Quest.Get(98823,'requiredSourceItems'),'Provider requirement was mutated')
    UnitLevel,UnitFactionGroup,UnitRace,UnitClass,C_Item=oldLevel,oldFaction,oldRace,oldClass,oldItems
''')
print('Earthen Echo: actual giver hidden before Elder Knowledge turn-in, unlocked afterward without requiring the provided relic; provider unchanged.')
lua.execute(b'''
    local function AllowedID(mask,limit)
        if not mask or mask==0 then return 1 end
        for id=1,limit do if math.floor(mask/2^(id-1))%2==1 then return id end end
        error('No eligible race/class in fixture')
    end
    for _,pair in ipairs({{98823,95664},{98824,95810},{95883,95884},{95885,95883},
        {92458,92432},{92459,92458},{96984,92434},{97287,96984}}) do
        local id,previous=pair[1],pair[2]
        assert(LibQuestieDB.Quest.name(id) and LibQuestieDB.Quest.name(previous))
        local oldCompleted=completed[previous]; completed[previous]=nil
        local player={active={},skills={},level=80,
            race=AllowedID(LibQuestieDB.Quest.Get(id,'requiredRaces'),40),
            class=AllowedID(LibQuestieDB.Quest.Get(id,'requiredClasses'),20),confirmed={[id]=true}}
        assert(not guide.test.Eligible(id,player),'Missing prerequisite correction '..id)
        player.active[previous]=true; done[previous]=true
        assert(not guide.test.Eligible(id,player),'Objectives skipped turn-in '..id)
        player.active[previous]=nil; completed[previous]=true
        assert(guide.test.Eligible(id,player),'Completed prerequisite did not unlock '..id)
        completed[previous]=oldCompleted; done[previous]=nil
        LibQuestieDB.Quest.InvalidateCache(id); LibQuestieDB.Quest.InvalidateCache(previous)
    end
''')
print('Eight verified item-related prerequisite relationships passed (six local corrections, two native provider links).')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(528)=='Battle of Hillsbrad')
    assert(LibQuestieDB.Quest.name(98094)=='Scout Support')
    assert(LibQuestieDB.Quest.name(98095)=='Valuable Vantages')
    for _,pair in ipairs({{98094,528},{98095,98094}}) do
        local id,previous=pair[1],pair[2]
        local nativePrevious=table.concat(LibQuestieDB.Quest.Get(id,'preQuestSingle') or {},',')
        local oldCompleted,oldDone=completed[previous],done[previous]
        completed[previous]=nil
        local player={active={},skills={},level=25,race=5,class=2,confirmed={[id]=true}}
        assert(not guide.test.Eligible(id,player),'Scout chain leaked before predecessor '..id)
        player.active[previous]=true; done[previous]=true
        assert(not guide.test.Eligible(id,player),'Scout chain unlocked before turn-in '..id)
        player.active[previous]=nil; completed[previous]=true
        assert(guide.test.Eligible(id,player),'Scout chain failed to unlock '..id)
        player.race=1; assert(not guide.test.Eligible(id,player),'Scout chain bypassed faction mask '..id)
        completed[previous]=oldCompleted; done[previous]=oldDone
        CheckNativeRequirements(id)
        LibQuestieDB.Quest.InvalidateCache(id)
    end
''')
print('Scout Support and Valuable Vantages: actual provider records respect prerequisite turn-ins and faction restrictions.')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(95495)=='The Hermit Tanner')
    assert(LibQuestieDB.Quest.name(95621)=='Trouble in the Valley')
    assert(LibQuestieDB.Quest.name(95508)=='Unwelcome Guests')
    for _,pair in ipairs({{95621,95495},{95508,95621}}) do
        local id,previous=pair[1],pair[2]
        local nativePrevious=table.concat(LibQuestieDB.Quest.Get(id,'preQuestSingle') or {},',')
        local oldCompleted,oldDone=completed[previous],done[previous]
        completed[previous]=nil
        local player={active={},skills={},level=18,race=5,class=2,confirmed={[id]=true}}
        assert(not guide.test.Eligible(id,player),'Premature Walton pickup '..id)
        player.active[previous]=true; done[previous]=true
        assert(not guide.test.Eligible(id,player),'Walton objective completion bypassed turn-in '..id)
        player.active[previous]=nil; completed[previous]=true
        assert(guide.test.Eligible(id,player),'Walton pickup failed to unlock '..id)
        player.race=96; player.class=3
        assert(guide.test.Eligible(id,player),'Horde Skyborne Hunter incorrectly blocked '..id)
        player.race=1
        assert(not guide.test.Eligible(id,player),'Walton faction restriction bypassed '..id)
        completed[previous]=oldCompleted; done[previous]=oldDone
        assert(table.concat(LibQuestieDB.Quest.Get(id,'preQuestSingle') or {},',')==nativePrevious,'Shared Walton provider row modified')
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    assert(not guide.chainPrerequisiteOverrides[95495],"Unverified Vrang prerequisites were invented")
''')
print('Walton: Hermit Tanner -> Trouble in the Valley -> Unwelcome Guests turn-ins verified; Vrang requirements unchanged.')
lua.execute(b'''
    local originals={}
    for _,id in ipairs({544,545,93680}) do
        originals[id]={completed[id],done[id]}; completed[id]=nil; done[id]=nil
    end
    assert(LibQuestieDB.Quest.name(92434)=='Blood in the Streets')
    assert(nativeRequirements[545]=='544/' or nativeRequirements[545]=='/544,93680','Unexpected Patrols requirements')
    local player={active={},skills={},level=35,race=96,class=3,confirmed={[545]=true,[92434]=true}}
    assert(not guide.test.Eligible(545,player) and not guide.test.Eligible(92434,player))
    completed[544]=true; player.active[93680]=true; done[93680]=true
    assert(not guide.test.Eligible(545,player),'Key objectives bypassed turn-in')
    completed[93680]=true; player.active={}
    assert(guide.test.Eligible(545,player),'Native Prison Break In plus Key turn-ins did not unlock Patrols')
    player.active[545]=true; done[545]=true
    assert(not guide.test.Eligible(92434,player),'Patrol objectives bypassed turn-in')
    completed[545]=true; player.active={}
    assert(guide.test.Eligible(92434,player),'Attunement did not unlock after both turn-ins')
    completed[93680]=nil
    assert(guide.test.Eligible(92434,player)==(nativeRequirements[92434]~='/'),'Native entry requirements did not take precedence')
    for _,id in ipairs({544,545,93680}) do completed[id]=originals[id][1]; done[id]=originals[id][2] end
    CheckNativeRequirements(545); CheckNativeRequirements(92434)
''')
print('Horde Dalaran: native Prison Break In retained; Key and Patrols turn-ins enforced before entry, including confirmed offers.')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(6547)=='Warsong Scout Update')
    assert(guide.GetQuestSummary(6547).repeatable,'Warsong Scout Update not classified repeatable')
    assert(not guide.GetQuestSummary(33).repeatable,'Ordinary quest classified repeatable')
''')
print('Actual provider repeatable flags: Warsong Scout Update classified; ordinary quest remains regular.')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(78270)=='Goblin Lockpicks')
    local rawClass=LibQuestieDB.Quest.Get(78270,'requiredClasses')
    assert(rawClass==0 or rawClass==8,'Unexpected Goblin Lockpicks class data')
    local player={active={},skills={},level=23,race=5,class=3,confirmed={[78270]=true}}
    assert(not guide.test.Eligible(78270,player),'Goblin Lockpicks leaked for Hunter')
    guide.db.filterAvailable=false
    assert(not guide.test.Eligible(78270,player),'Broad view restored wrong-class Rogue quest')
    guide.db.filterAvailable=true; player.class=4
    local parent=LibQuestieDB.Quest.Get(78270,'parentQuest')
    if parent and parent>0 then
        assert(parent==78261,'Unexpected Goblin Lockpicks parent')
        assert(not guide.test.Eligible(78270,player),'Confirmed offer bypassed the active parent quest')
        player.active[parent]=true
    end
    assert(guide.test.Eligible(78270,player),'Eligible Rogue quest was incorrectly removed')
    player.confirmed={}
    for _,race in ipairs({1,5,95,96}) do
        player.race=race
        assert(guide.test.Eligible(78270,player),'Unverified faction gate added to Goblin Lockpicks')
    end
    assert(LibQuestieDB.Quest.Get(78270,'requiredClasses')==rawClass,'Shared provider was changed')
''')
print('Goblin Lockpicks: Rogue mask and active parent honored; both factions remain eligible when requirements pass.')
lua.execute(b'''
    assert(LibQuestieDB.Enum.raceMaskById[95]==4294967296)
    assert(LibQuestieDB.Enum.raceMaskById[96]==8589934592)
    local mapping={}
    local zones=LibQuestieDB.Support.Get('ZoneDB').private
    guide.test.MergeMap(mapping,zones.areaIdToUiMapId)
    guide.test.MergeMap(mapping,zones.areaIdToUiMapIdOverride)
    local mapID=mapping[16593]
    assert(mapID,'Zephras Isle mapping missing')
    local oldLevel,oldRace,oldClass,oldFaction=UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    UnitLevel=function() return 10 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    local tameMask=LibQuestieDB.Quest.Get(94978,'requiredRaces')
    assert(tameMask==4294967296 or tameMask==12884901888,'Unexpected Skyborne taming race mask')
    for _,race in ipairs({95,96}) do
        local eligible=race==95 or tameMask==12884901888
        UnitRace=function() return 'Skyborne','Skyborne',race end
        UnitFactionGroup=function() return race==95 and 'Alliance' or 'Horde' end
        local player={active={},skills={},level=10,race=race,class=3,confirmed={}}
        assert(guide.test.Eligible(94978,player)==eligible,'Skyborne taming ignored native race mask '..race)
        local found=false
        guide.BuildMap(mapID,function(id,kind,label,x,y)
            if id==94978 then
                found=true
                assert(kind=='pickup' and label=="Quel'ana Quickgale")
                assert(math.abs(x-.5956)<.0001 and math.abs(y-.7263)<.0001)
            end
        end,Checkpoint)
        assert(found==eligible,'Unexpected Skyborne hunter trainer marker '..race)
        for _,pair in ipairs({{94979,94978},{94013,94979},{94050,94013}}) do
            local id,previous=pair[1],pair[2]
            local oldCompleted=completed[previous]; completed[previous]=nil
            player.confirmed={[id]=true}
            assert(not guide.test.Eligible(id,player),'Skyborne future chain step leaked '..id)
            completed[previous]=true
            assert(LibQuestieDB.Quest.Get(id,'requiredRaces')==tameMask,'Unexpected race mask for taming step '..id)
            assert(guide.test.Eligible(id,player)==eligible,'Native hunter chain ignored race or prerequisite '..id)
            completed[previous]=oldCompleted
        end
        local oldTameCompleted=completed[94978]
        player.confirmed={[94007]=true}; player.active={[94978]=true}
        assert(guide.test.Eligible(94007,player),'Valid referral hidden during taming')
        player.active={}; completed[94978]=true
        assert(guide.test.Eligible(94007,player),'Valid referral hidden after completed taming')
        local referralVisible=false
        guide.BuildMap(mapID,function(id) if id==94007 then referralVisible=true end end,Checkpoint)
        assert(referralVisible,'Completed tame incorrectly removed Elayaa marker')
        completed[94978]=nil; player.confirmed={[94978]=true}; player.active={[94007]=true}
        assert(guide.test.Eligible(94978,player)==eligible,'Unlinked referral changed taming eligibility')
        player.active={}; player.confirmed={}
        assert(guide.test.Eligible(94978,player)==eligible,'Optional referral changed taming eligibility')
        completed[94978]=oldTameCompleted
        assert(LibQuestieDB.Quest.Get(94007,'breadcrumbForQuestId')==0,'Provider breadcrumb was modified')
        player.class=1
        assert(not guide.test.Eligible(94978,player),'Skyborne non-Hunter admitted')
        player.class=3; player.race=1
        assert(not guide.test.Eligible(94978,player),'Human admitted to Skyborne quest')
        player.race=race; player.level=9
        assert(not guide.test.Eligible(94978,player),'Hunter quest minimum level bypassed')
    end
    UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldLevel,oldRace,oldClass,oldFaction
    assert(LibQuestieDB.Quest.Get(94978,'requiredRaces')==tameMask,'Provider mask was modified')
''')
print('Skyborne Hunters: trainer marker at 59.56,72.63 follows the native race mask; class, level and chain gates preserved.')
print('Skyborne Hunter referral: remains valid after taming starts/completes; no invented breadcrumb restrictions.')
lua.execute(b'''
    local player={active={},skills={},level=25,race=5,class=2,confirmed={}}
    local sodIDs={78132,78133,78134}
    for _,id in ipairs(sodIDs) do
        assert(LibQuestieDB.Quest.Get(id,'requiredClasses')==0,'Provider class fixture changed')
        assert(not guide.test.Eligible(id,player),'SoD quest leaked for Paladin '..id)
        player.class=1; player.confirmed[id]=true
        assert(not guide.test.Eligible(id,player),'SoD quest leaked for Warrior in strict mode '..id)
        guide.db.filterAvailable=false
        assert(guide.test.Eligible(id,player),'Broad Warrior classification path not exercised '..id)
        assert(guide.GetQuestSummary(id).classification=='Season of Discovery / Warrior')
        player.class=2
        assert(not guide.test.Eligible(id,player),'Broad view bypassed corrected class restriction '..id)
        guide.db.filterAvailable=true; player.confirmed={}
        assert(LibQuestieDB.Quest.Get(id,'requiredClasses')==0,'Shared provider class metadata was mutated')
    end
    assert(guide.test.Eligible(98251,player),'Ordinary Horde Never Coming Back was incorrectly hidden')
    assert(not guide.test.Eligible(98252,player),'A Void Path leaked before prerequisite')
    player.active[98251]=true; done[98251]=true
    assert(not guide.test.Eligible(98252,player),'A Void Path unlocked before turn-in')
    player.active[98251]=nil; done[98251]=nil; completed[98251]=true
    assert(guide.test.Eligible(98252,player),'A Void Path failed to unlock after turn-in')
    completed[98251]=nil
    player.race=1
    assert(not guide.test.Eligible(98251,player) and not guide.test.Eligible(98252,player),'Horde quests leaked for Alliance')
    player.confirmed={[98251]=true,[98252]=true}
    assert(not guide.test.Eligible(98251,player) and not guide.test.Eligible(98252,player),'Confirmed offers bypassed faction masks')
    player.confirmed={}
    guide.db.filterAvailable=false
    assert(not guide.test.Eligible(98251,player) and not guide.test.Eligible(98252,player),'Broad view bypassed faction mask')
    guide.db.filterAvailable=true
    for _,race in ipairs({2,5,6,8,96}) do
        player.race=race
        assert(guide.test.Eligible(98251,player),'Horde race incorrectly rejected: '..race)
    end
''')
print('Screenshot classification: SoD Warrior turn-ins hidden; Horde/Alliance masks verified (including actual Skyborne race 96); A Void Path requires turn-in.')
lua.execute(b'''
    local chain={91858,91859,91860,91861,91862,96204,95034,95036,95111,95125,95126,95140}
    local player={active={},skills={},level=26,race=5,class=2,confirmed={}}
    for index,id in ipairs(chain) do
        assert(LibQuestieDB.Quest.name(id),'Missing Paladin chain record '..id)
        assert(LibQuestieDB.Quest.Get(id,'requiredClasses')==2,'Paladin mask changed '..id)
        local raceMask=LibQuestieDB.Quest.Get(id,'requiredRaces')
        local widened=id==91858 or id==91859 or id==91860 or id==91862 or id==96204 or id==95111 or id==95125 or id==95126
        assert(raceMask==16 or (widened and raceMask==8589934770),'Unexpected Paladin race mask '..id)
        if index>1 then
            local previous=chain[index-1]
            local oldCompleted,oldDone=completed[previous],done[previous]
            completed[previous]=nil; player.confirmed={[id]=true}
            assert(not guide.test.Eligible(id,player),'Paladin future step leaked '..id)
            player.active[previous]=true; done[previous]=true
            assert(not guide.test.Eligible(id,player),'Paladin objective completion bypassed turn-in '..id)
            player.active[previous]=nil; completed[previous]=true
            assert(guide.test.Eligible(id,player),'Paladin turn-in failed to unlock '..id)
            player.race=96
            assert(guide.test.Eligible(id,player)==(raceMask==8589934770),'Native Horde-wide mask not respected '..id)
            player.race=5
            player.class=1; assert(not guide.test.Eligible(id,player),'Paladin restriction bypassed '..id)
            player.class=2; player.race=1
            assert(not guide.test.Eligible(id,player),'Undead restriction bypassed '..id)
            player.race=5; completed[previous]=oldCompleted; done[previous]=oldDone
        end
        CheckNativeRequirements(id)
        LibQuestieDB.Quest.InvalidateCache(id)
    end
''')
print('Undead Paladin chain: eleven prerequisite links require turn-in; confirmed offers respect chain, class and race masks; provider unchanged.')
lua.execute(b'''
    for _,id in ipairs({92459,97287}) do
        local native=LibQuestieDB.Quest.Get(id,'preQuestSingle') or {}
        if #native==2 then
            local player={active={},skills={},level=40,race=id==92459 and 95 or 96,class=3,confirmed={[id]=true}}
            local oldA,oldB=completed[native[1]],completed[native[2]]
            completed[native[1]]=nil; completed[native[2]]=true
            assert(guide.test.Eligible(id,player),'Local fallback narrowed native alternative '..id)
            completed[native[2]]=nil; player.active[native[2]]=true; done[native[2]]=true
            assert(not guide.test.Eligible(id,player),'Unturned native alternative unlocked '..id)
            done[native[2]]=nil; completed[native[1]]=oldA; completed[native[2]]=oldB
            CheckNativeRequirements(id)
        end
    end
''')
print('Native Dalaran OR alternatives retain precedence over older local fallback gates.')
lua.execute(b'''
    local oldRep,oldA,oldB=C_Reputation,completed[93224],completed[93225]
    completed[93224]=true; completed[93225]=nil
    local standing=-1
    C_Reputation={GetFactionDataByID=function() return {currentStanding=standing} end}
    for _,id in ipairs({93226,93227,94872,94873}) do
        local requirement=LibQuestieDB.Quest.Get(id,'requiredMinRep')
        assert(requirement and requirement[2]==0,'Native Neutral reputation gate missing')
        local player={level=60,race=id<94000 and 95 or 96,class=3,active={},skills={},skillsKnown=true}
        standing=-1
        assert(not guide.test.Eligible(id,player),'Hostile Buying Friendship pickup leaked')
        standing=0
        assert(guide.test.Eligible(id,player),'Neutral Buying Friendship pickup blocked')
        CheckNativeRequirements(id)
    end
    C_Reputation,completed[93224],completed[93225]=oldRep,oldA,oldB
    local chain={991,1023,1024,1026,1027,1028,1055,1029,1030,1045,1046}
    for index=2,#chain do
        local id,previous=chain[index],chain[index-1]
        local requirements=LibQuestieDB.Quest.Get(id,'preQuestSingle')
        assert(requirements and #requirements==1 and requirements[1]==previous,'Raene native chain changed')
        local old=completed[previous]; completed[previous]=nil
        local player={level=60,race=95,class=3,active={[previous]=true},skills={},confirmed={[id]=true}}
        assert(not guide.test.Eligible(id,player),'Active Raene prerequisite bypassed turn-in')
        player.active={}; completed[previous]=true
        assert(guide.test.Eligible(id,player),'Native Raene turn-in did not unlock next step')
        completed[previous]=old; CheckNativeRequirements(id)
    end
    for _,id in ipairs({76156,76160,76240}) do
        assert(LibQuestieDB.Quest.Get(id,'requiredRaces')==32,'Earthmother native Tauren mask changed')
        local player={level=60,race=96,class=3,active={},skills={},confirmed={[id]=true}}
        assert(not guide.test.Eligible(id,player),'Earthmother wrong-race offer leaked')
    end
    local modera=LibQuestieDB.Npc.spawns(269127)
    assert(modera and modera[130] and math.abs(modera[130][1][1]-68.62)<.05
        and math.abs(modera[130][1][2]-45.13)<.05,'Native Modera location correction missing')
''')
print('QuestieDB: Neutral reputation boundary, native Raene chain turn-ins, Tauren-only Earthmother masks and Modera location verified.')
lua.execute(b'''
    local rawCompendiumRace=LibQuestieDB.Quest.Get(1049,'requiredRaces')
    assert(rawCompendiumRace==162 or rawCompendiumRace==8589934754,'Unexpected Compendium native mask')
    local classIDs={1,2,3,4,5,7,8,9,11}
    local raceIDs={1,2,3,4,5,6,7,8,95,96}
    local masks=LibQuestieDB.Enum.raceMaskById
    local function Has(mask,flag) return math.floor(mask/flag)%2==1 end
    local classFallbacks={[96136]=64,[93797]=128,[98341]=1024,[98404]=1024,[98738]=1024}
    characterMaskChecks=0
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        local class=LibQuestieDB.Quest.Get(id,'requiredClasses') or 0
        if class==0 then class=classFallbacks[id] or 0 end
        local race=LibQuestieDB.Quest.Get(id,'requiredRaces') or 0
        if id==1049 and race==162 then race=8589934754 end
        local validRace,validClass=1,1
        for _,r in ipairs(raceIDs) do if race==0 or Has(race,masks[r]) then validRace=r; break end end
        for _,c in ipairs(classIDs) do if class==0 or Has(class,2^(c-1)) then validClass=c; break end end
        local player={active={},skills={},level=60,race=validRace,class=validClass,confirmed={[id]=true}}
        for _,strict in ipairs({true,false}) do
            guide.db.filterAvailable=strict
            if class>0 then
                for _,c in ipairs(classIDs) do
                    if not Has(class,2^(c-1)) then
                        player.class=c
                        assert(not guide.test.Eligible(id,player),'Wrong-class pickup '..id..'/'..c)
                        characterMaskChecks=characterMaskChecks+1
                    end
                end
            end
            player.class=validClass
            if race>0 then
                for _,r in ipairs(raceIDs) do
                    if not Has(race,masks[r]) then
                        player.race=r
                        assert(not guide.test.Eligible(id,player),'Wrong-race pickup '..id..'/'..r)
                        characterMaskChecks=characterMaskChecks+1
                    end
                end
            end
            player.race=validRace
        end
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    guide.db.filterAvailable=true
    for id,mask in pairs(classFallbacks) do
        local raw=LibQuestieDB.Quest.Get(id,'requiredClasses')
        local player={active={},skills={},level=60,race=96,class=3,confirmed={[id]=true}}
        assert(not guide.test.Eligible(id,player),'Missing class mask leaked to Hunter '..id)
        assert(LibQuestieDB.Quest.Get(id,'requiredClasses')==raw,'Shared class mask mutated')
    end
    local oldLevel,oldRace,oldClass,oldFaction=UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    UnitLevel=function() return 35 end
    UnitRace=function() return 'Skyborne','Skyborne',96 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    UnitFactionGroup=function() return 'Horde' end
    local function Visible(mapID,id,wanted)
        local seen=false
        guide.BuildMap(mapID,function(qid,kind,label,x,y)
            if qid==id then
                seen=true
                if id==1049 then assert(label=='Sage Truthseeker' and math.abs(x-.344)<.0001) end
            end
        end,Checkpoint)
        assert(seen==wanted,'Screenshot pickup wrong '..id)
    end
    Visible(1456,1049,true); Visible(1412,96136,false)
    UnitClass=function() return 'Shaman','SHAMAN',7 end
    Visible(1412,96136,true)
    UnitRace=function() return 'Undead','Scourge',5 end
    Visible(1456,1049,false)
    UnitRace=function() return 'Skyborne','Skyborne',95 end
    UnitFactionGroup=function() return 'Alliance' end
    Visible(1456,1049,false)
    assert(LibQuestieDB.Quest.Get(1049,'requiredRaces')==rawCompendiumRace,'Compendium native mask mutated')
    UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldLevel,oldRace,oldClass,oldFaction
''')
print(f'Character mask audit: {g[b"characterMaskChecks"]} wrong-class/race rejections across all installed quest records, strict/broad and confirmed offers.')
print('Actual screenshot quests: Skyborne Hunter sees Compendium in Thunder Bluff and no Call of Air; Skyborne Shaman sees Call of Air; Forsaken/Alliance remain excluded.')
lua.execute(b'''
    correctedPvPCount=0
    for id,tag in pairs(guide.questTagOverrides) do
        assert(guide.IsPvPQuest(id)==(tag==41),'Imported Questie tag correction differs '..id)
        if tag==41 then
            correctedPvPCount=correctedPvPCount+1
            guide.db.hidePvPQuests=true
            local player={active={},skills={},level=60,race=96,class=3,confirmed={[id]=true}}
            assert(not guide.test.Eligible(id,player),'Corrected PvP pickup escaped filter '..id)
            guide.db.filterAvailable=false
            assert(not guide.test.Eligible(id,player),'Broad mode restored corrected PvP pickup '..id)
            guide.db.filterAvailable=true
        end
    end
    guide.db.hidePvPQuests=false
    assert(correctedPvPCount>0)
''')
print(f'Questie tag integration: {g[b"correctedPvPCount"]} PvP corrections hidden in strict/broad pickup paths; other corrected tags preserved.')
lua.execute(b'''
    local titles={['A Donation of Wool']=true,['A Donation of Silk']=true,
        ['A Donation of Mageweave']=true,['A Donation of Runecloth']=true,['Additional Runecloth']=true}
    clothDonationCount=0
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        if titles[LibQuestieDB.Quest.name(id)] then
            assert(guide.clothDonationQuests[id],'Unreviewed cloth donation ID '..id)
            clothDonationCount=clothDonationCount+1
            guide.db.hideClothQuests=true
            for _,strict in ipairs({true,false}) do
                guide.db.filterAvailable=strict
                local player={active={},skills={},level=60,race=96,class=3,confirmed={[id]=true}}
                assert(not guide.test.Eligible(id,player),'Cloth pickup escaped toggle '..id)
            end
        end
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    for id in pairs(guide.clothDonationQuests) do
        assert(titles[LibQuestieDB.Quest.name(id)],'Non-donation included in cloth toggle '..id)
    end
    assert(clothDonationCount==50)
    guide.db.hideClothQuests=false; guide.db.filterAvailable=true
''')
print(f'Cloth donation integration: {g[b"clothDonationCount"]} standard/Skyborne donation IDs verified; strict/broad and confirmed offers respect the toggle.')
lua.execute(b'''
    local titles={['Conflict at Darkspear Islands']=true,['Darkspear Islands Clash']=true,
        ['The Battle for Darkspear Islands!']=true}
    additionalPvPCount=0
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        if titles[LibQuestieDB.Quest.name(id)] then
            assert(guide.IsPvPQuest(id),'Darkspear variant missed '..id)
            additionalPvPCount=additionalPvPCount+1
            guide.db.hidePvPQuests=true
            for _,strict in ipairs({true,false}) do
                guide.db.filterAvailable=strict
                assert(not guide.test.Eligible(id,{active={},skills={},level=60,race=96,class=3,confirmed={[id]=true}}))
            end
        end
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    for id in pairs(guide.additionalPvPQuests) do assert(titles[LibQuestieDB.Quest.name(id)]) end
    assert(additionalPvPCount==22)
    local oldLevel,oldRace,oldClass,oldFaction=UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    UnitLevel=function() return 49 end
    UnitRace=function() return 'Skyborne','Skyborne',96 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    UnitFactionGroup=function() return 'Horde' end
    guide.db.filterAvailable=false
    local function Visible(hidden)
        guide.db.hidePvPQuests=hidden
        local found={}
        guide.BuildMap(1454,function(id) found[id]=true end,Checkpoint)
        assert((not not found[98887])==not hidden,'Actual Conflict pickup filter failed')
        assert((not not found[98890])==not hidden,'Actual zone-less Conflict variant filter failed')
    end
    Visible(false); Visible(true); Visible(false)
    guide.db.filterAvailable=true; guide.db.hidePvPQuests=false
    UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldLevel,oldRace,oldClass,oldFaction
''')
print(f'Darkspear Islands PvP integration: {g[b"additionalPvPCount"]} Horde/Alliance mark and victory variants classified; actual Warbringer pickups obey the toggle.')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(95288)=="Smuggler's Paradise")
    local oldLevel,oldRace,oldClass,oldFaction=UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    local oldActive,oldDone=active,done
    local originals={}
    for _,id in ipairs({93788,93976,94925,94928,95288}) do originals[id]=completed[id]; completed[id]=nil end
    UnitLevel=function() return 50 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    local mappings={}
    guide.test.MergeMap(mappings,LibQuestieDB.Support.Get('ZoneDB').private.areaIdToUiMapId)
    guide.test.MergeMap(mappings,LibQuestieDB.Support.Get('ZoneDB').private.areaIdToUiMapIdOverride)
    local mapID=mappings[16591]; assert(mapID,'Riverglades mapping missing')
    for _,race in ipairs({95,96}) do
        UnitRace=function() return 'Skyborne','Skyborne',race end
        UnitFactionGroup=function() return race==96 and 'Horde' or 'Alliance' end
        local previous=race==96 and 93976 or 94928
        active={}; done={}
        local function Check(wanted)
            local found=false
            guide.BuildMap(mapID,function(id,kind,label,x,y)
                if id==95288 then
                    found=true; assert(kind=='pickup' and label=='Friz Frazzlespark')
                    assert(math.abs(x-.771)<.000001 and math.abs(y-.529)<.000001)
                end
            end,Checkpoint)
            assert(found==wanted,'Actual Smuggler faction lead failed '..race)
        end
        Check(false)
        local hints=table.concat(guide.GetPrerequisiteHints(95288),' ')
        assert(hints:find(race==96 and 'Kreza Darkthorn' or 'Watcher Cornelius',1,true),'Wrong prerequisite pickup giver')
        active={previous}; done[previous]=true; Check(false)
        hints=table.concat(guide.GetPrerequisiteHints(95288),' ')
        assert(hints:find('Friz Frazzlespark',1,true),'Active lead did not point to turn-in')
        active={}; completed[previous]=true; Check(true)
        assert(#guide.GetPrerequisiteHints(95288)==0,'Completed lead still suggested')
        completed[previous]=nil
    end
    for id,value in pairs(originals) do completed[id]=value end
    for _,id in ipairs({93788,93976,94925,94928,95288}) do
        if originals[id]==nil then completed[id]=nil end
        CheckNativeRequirements(id)
    end
    UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldLevel,oldRace,oldClass,oldFaction
    active,done=oldActive,oldDone
''')
print('Smuggler integration: either faction introduction must be turned in; actual Friz pickup and prerequisite pickup/return guidance verified without mutating native data.')
lua.execute(b'''
    assert(LibQuestieDB.Quest.name(95183)=='Step One: Rock')
    assert(LibQuestieDB.Quest.name(95420)=='Land of Giants')
    assert(LibQuestieDB.Quest.name(95424)=='Might Makes Right')
    local oldLevel,oldRace,oldClass,oldFaction=UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    local oldCompleted,oldMight,oldActive,oldDone=completed[95420],completed[95424],active,done
    UnitLevel=function() return 45 end
    UnitRace=function() return 'Skyborne','Skyborne',96 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    UnitFactionGroup=function() return 'Horde' end
    local mappings={}
    guide.test.MergeMap(mappings,LibQuestieDB.Support.Get('ZoneDB').private.areaIdToUiMapId)
    guide.test.MergeMap(mappings,LibQuestieDB.Support.Get('ZoneDB').private.areaIdToUiMapIdOverride)
    local mapID=mappings[16591]
    local function Check(wanted)
        local seen={}
        guide.BuildMap(mapID,function(id,kind,label) if id==95183 then seen[label]=true end end,Checkpoint)
        assert((not not seen.Hamur)==wanted,'Actual Hamur introduction gate failed')
        assert((not not seen.Gorgegut)==wanted,'Actual Gorgegut introduction gate failed')
    end
    completed[95420]=nil; completed[95424]=nil; active={}; done={}; Check(false)
    local matches=guide.FindQuestMatches('step one',20)
    assert(#matches==1 and matches[1]==95183,'Actual prerequisite search missed screenshot quest')
    guide.OpenQuestGuide(95183)
    assert(QuestLiteOptions.selected==95183 and QuestLiteOptions.tab=='guide')
    assert(QuestLiteOptions.rows[1].button:IsShown(),'Actual prerequisite route was empty')
    QuestLiteOptions:Hide()
    active={95420}; done[95420]=true; Check(false)
    local hints=table.concat(guide.GetPrerequisiteHints(95183),' ')
    assert(hints:find('Land of Giants',1,true) and hints:find('Clugfist',1,true),'Introduction turn-in guidance missing')
    active={95424}; completed[95420]=true; Check(false)
    hints=table.concat(guide.GetPrerequisiteHints(95183),' ')
    assert(hints:find('Might Makes Right',1,true) and hints:find('Clugfist',1,true))
    done[95424]=true; Check(false)
    active={}; completed[95424]=true; Check(true)
    CheckNativeRequirements(95183); CheckNativeRequirements(95420); CheckNativeRequirements(95424)
    completed[95420],completed[95424],active,done=oldCompleted,oldMight,oldActive,oldDone
    UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldLevel,oldRace,oldClass,oldFaction
''')
print('Step One: Rock integration: both giver markers wait for Might Makes Right turn-in, with Land of Giants guidance and native requirements preserved.')
lua.execute(b'''
    local quest=LibQuestieDB.Quest
    assert(quest.name(3504)=='Betrayed' and quest.Get(3504,'requiredLevel')==44
        and quest.Get(3504,'questLevel')==53)
    assert(quest.startedBy(3504)[1][1]==4485)
    local player={level=45,race=96,class=3,active={},skills={},skillsKnown=true}
    local oldFilter,oldCompleted=guide.db.filterAvailable,completed[3504]
    completed[3504]=nil; guide.db.filterAvailable=true
    assert(not guide.test.Eligible(3504,player),'Unverified Belgrom pickup leaked')
    guide.db.filterAvailable=false
    assert(guide.test.Eligible(3504,player),'Betrayed was removed from broad browsing')
    guide.db.filterAvailable=true; player.confirmed={[3504]=true}
    assert(guide.test.Eligible(3504,player),'Real offer was not allowed at level 45')
    player.race=95
    assert(not guide.test.Eligible(3504,player),'Confirmed offer bypassed faction restriction')
    assert(guide.GetQuestLevelDescription(3504)=='Quest level 53 | Minimum pickup level: 44')
    CheckNativeRequirements(3504)
    completed[3504],guide.db.filterAvailable=oldCompleted,oldFilter
    quest.InvalidateCache(3504)
''')
print('Betrayed integration: native minimum 44/difficulty 53 preserved; strict mode requires an offer and still enforces faction eligibility.')
lua.execute(b'''
    local oldLevel,oldActive,oldDone=UnitLevel,active,done
    UnitLevel=function() return 60 end; active={}; done={}
    local maps={}
    guide.test.MergeMap(maps,LibQuestieDB.Support.Get('ZoneDB').private.areaIdToUiMapId)
    guide.test.MergeMap(maps,LibQuestieDB.Support.Get('ZoneDB').private.areaIdToUiMapIdOverride)
    for _,id in ipairs({351,485,635,2766}) do
        local finishers=LibQuestieDB.Quest.finishedBy(id)
        local entity=finishers[1] and finishers[1][1] and LibQuestieDB.Npc or LibQuestieDB.Object
        local entityID=entity==LibQuestieDB.Npc and finishers[1][1] or finishers[2][1]
        local found=false
        for area,points in pairs(entity.spawns(entityID)) do
            if maps[area] then
                guide.BuildMap(maps[area],function(questID,kind,label,x,y,confirmed,zone,sx,sy,dropStarter)
                    if questID==id then
                        found=true
                        assert(kind=='pickup' and dropStarter=='destination')
                        assert(label==entity.name(entityID),'Zone drop is not labelled with its finisher')
                        local matched=false
                        for _,point in ipairs(points) do
                            if math.abs(x-point[1]/100)<.00001 and math.abs(y-point[2]/100)<.00001 then matched=true end
                        end
                        assert(matched,'Destination is not at the native finisher coordinates')
                    end
                end,Checkpoint)
            end
        end
        assert(found,'Actual zone-drop destination missing: '..id)
        CheckNativeRequirements(id)
    end
    UnitLevel,active,done=oldLevel,oldActive,oldDone
''')
print('Zone-drop destinations: all three OOX quests and Pendant of Myzrael point to native NPC/object finishers without changing pickup eligibility.')
lua.execute(b'''
    local steps,more=guide.GetNextChainSteps(351)
    local found=false
    for _,entry in ipairs(steps) do
        if entry.id==648 then
            found=true
            assert(entry.name=='Rescue OOX-17/TN!' and entry.location:find('OOX-17/TN',1,true))
        end
    end
    assert(found and not more,'Actual OOX next quest missing')
    CheckNativeRequirements(351); CheckNativeRequirements(648)
    guide.OpenQuestGuide(351,'next')
    assert(QuestLiteOptions.guideMode=='next' and QuestLiteOptions.rows[1].button:IsShown())
    QuestLiteOptions:Hide()
''')
print('Next-chain guide: actual OOX delivery links to rescue quest with known pickup location; native provider data preserved.')
lua.execute(b'''
    local oldItems,oldLevel,oldRace,oldClass,oldFaction=C_Item,UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    local oldActive,oldDone,oldDrops=active,done,guide.db.itemDropLocations
    local itemID=LibQuestieDB.Quest.startedBy(94316)[3][1]
    assert(itemID==264116)
    local owned=0
    C_Item={GetItemCount=function(id,bank) assert(bank==false); return id==itemID and owned or 0 end}
    local player={level=60,race=96,class=3,active={},skills={},skillsKnown=true}
    local count=0
    for id in pairs(guide.craftsmanWritQuests) do
        count=count+1
        local name=LibQuestieDB.Quest.name(id)
        assert(name and name:find("Craftsman's Writ:",1,true)==1,'Incorrect writ classification')
        assert(guide.test.Eligible(id,player)==(id==94316),'Writ pickup classification incorrect: '..id)
        CheckNativeRequirements(id)
    end
    assert(count==150)
    owned=1; assert(guide.test.Eligible(94316,player),'Owned screenshot writ was lost')
    UnitLevel=function() return 60 end
    UnitRace=function() return 'Skyborne','Skyborne',96 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    UnitFactionGroup=function() return 'Horde' end
    active={}; done={}; guide.db.itemDropLocations=true
    local function Check(wanted,ready)
        local found=false
        guide.BuildMap(1447,function(id,kind,label,x,y,confirmed,zone,sx,sy,dropStarter)
            if id==94316 then
                found=true
                assert(label=='Archmage Xylem')
                assert(kind==(ready and 'turnin' or 'pickup'))
                assert(dropStarter==nil,'Verified Xylem pickup mislabeled as item-start reference')
            end
        end,Checkpoint)
        assert(found==wanted,'Actual Xylem writ marker incorrect')
    end
    Check(true)
    owned=0; guide.db.itemDropLocations=false; Check(true)
    active={94316}; done[94316]=true; guide.db.itemDropLocations=false; Check(true,true)
    C_Item,UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldItems,oldLevel,oldRace,oldClass,oldFaction
    active,done,guide.db.itemDropLocations=oldActive,oldDone,oldDrops
''')
print('Craftsman writ integration: 149 retain owned-starter gates; verified Xylem order is an ordinary NPC pickup without a writ, ready turn-in preserved.')
lua.execute(b'''
    for _,row in ipairs({{2856,2854,82656,96},{2849,2847,82657,95}}) do
        local id,intro,duplicate,race=unpack(row)
        local skill=LibQuestieDB.Quest.Get(id,'requiredSkill')
        local required=LibQuestieDB.Quest.Get(id,'preQuestSingle')
        assert(skill[1]==165 and skill[2]==225 and required[1]==intro)
        assert(not LibQuestieDB.Quest.Get(duplicate,'requiredSkill'))
        local player={level=60,race=race,class=3,active={},skills={[165]=225},confirmed={[duplicate]=true}}
        assert(not guide.test.Eligible(duplicate,player),'SoD Wild Leather duplicate leaked')
        guide.db.filterAvailable=false; assert(guide.test.Eligible(duplicate,player))
        guide.db.filterAvailable=true
        local old,oldSkill=completed[intro],C_SkillInfo
        C_SkillInfo=C_SkillInfo or {}; completed[intro]=nil
        assert(not guide.test.Eligible(id,player),'Normal Wild Leather prerequisite bypassed')
        completed[intro]=true; player.skills[165]=224
        assert(not guide.test.Eligible(id,player),'Normal Wild Leather skill gate bypassed')
        player.skills[165]=225
        assert(guide.test.Eligible(id,player),'Normal Wild Leather quest was suppressed')
        completed[intro],C_SkillInfo=old,oldSkill
        CheckNativeRequirements(id); CheckNativeRequirements(duplicate)
    end
''')
print('Wild Leather Vest: SoD duplicates excluded in strict mode; actual normal Horde/Alliance prerequisite and Leatherworking 225 gates preserved.')
lua.execute(b'''
    local groups={Duskwood=0,Hinterlands=0,Feralas=0}
    local player={level=60,race=96,class=3,active={},skills={},confirmed={}}
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        local name=LibQuestieDB.Quest.name(id) or ''
        local zone=name:match('^(%a+) Mission [IVX]+:')
        if groups[zone] then
            groups[zone]=groups[zone]+1
            assert(guide.pickupPolicy.sod[id],'Native incursion mission missed '..id)
            player.confirmed={[id]=true}
            assert(not guide.test.Eligible(id,player),'Native incursion offer bypassed season rule '..id)
            assert(guide.GetQuestSummary(id).classification=='Season of Discovery')
            CheckNativeRequirements(id)
        end
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    assert(groups.Duskwood==18 and groups.Hinterlands==18 and groups.Feralas==18,'Incursion mission inventory changed')
    for _,id in ipairs({76156,76160,76240,2849,2856,98251,98252}) do assert(not guide.pickupPolicy.sod[id]) end
''')
print('SoD coverage: all 54 Duskwood/Hinterlands/Feralas missions blocked even with confirmed observations; reused Forever quests preserved.')
lua.execute(b'''
    local oldRace,oldClass,oldFaction,oldActive,oldDone=UnitRace,UnitClass,UnitFactionGroup,active,done
    local oldCompleted=completed[54]
    UnitRace=function() return 'Human','Human',1 end
    UnitClass=function() return 'Warrior','WARRIOR',1 end
    UnitFactionGroup=function() return 'Alliance' end
    active={}; done={}; completed[54]=nil
    assert(LibQuestieDB.Quest.Get(54,'sourceItemId')==745)
    assert(LibQuestieDB.Item.Get(745,'class')==12)
    guide.InitQuestItems()
    local tip=CreateFrame('GameTooltip'); tip:SetOwner(UIParent,'ANCHOR_NONE')
    tip:AddLine(LibQuestieDB.Item.name(745))
    guide.testQuestItems.Tooltip(tip,{id=745}); Tick(1000)
    assert(#tip.lines==2 and tip.lines[2]:find('Keep:',1,true),'Unfinished real quest item was labelled disposable')
    completed[54]=true; Fire('QUEST_TURNED_IN',54); Tick(1000)
    assert(#tip.lines==2 and tip.lines[2]:find('safe to discard for known quests',1,true),'Completed real quest-provided item missed')
    active={54}; done[54]=true; Fire('QUEST_LOG_UPDATE'); Tick(1000)
    assert(tip.lines[2]:find('active quest',1,true),'Ready real quest allowed deletion before turn-in')
    tip:Hide()
    UnitRace,UnitClass,UnitFactionGroup,active,done=oldRace,oldClass,oldFaction,oldActive,oldDone
    completed[54]=oldCompleted
    guide.RefreshQuestItemSafety()
    CheckNativeRequirements(54)
''')
print('Quest cleanup integration: actual Marshal McBride documents stay Keep until Report to Goldshire is turned in; ready quests remain protected.')
lua.execute(b'''
    local oldLevel,oldActive,oldDone=UnitLevel,active,done
    local oldGUID,oldGossip=UnitGUID,C_GossipInfo
    local oldMain,oldOasis=completed[1560],completed[97540]
    UnitLevel=function() return 60 end
    active={}; done={}; completed[1560]=nil; completed[97540]=nil
    local function Spawns()
        local rows={}
        for area,points in pairs(LibQuestieDB.Npc.spawns(5955)) do
            for _,point in ipairs(points) do rows[#rows+1]=area..':'..point[1]..','..point[2] end
        end
        table.sort(rows); return table.concat(rows,';')
    end
    local original=Spawns()
    local function Check(wanted,ready)
        local found=false
        guide.BuildMap(1446,function(id,kind,label,x,y)
            if id==97540 then
                found=true
                assert(label=='Tooga' and x==.41 and y==.54,'Oasis location override missed')
                assert(kind==(ready and 'turnin' or 'pickup'))
            end
            if id==1560 and kind=='pickup' then assert(x~=.41 or y~=.54,'Main Tooga spawn moved') end
        end,Checkpoint)
        assert(found==wanted,'Oasis appeared without an actual offer')
    end
    guide.ClearOfferObservations(); Check(false)
    active={1560}; Check(false)
    local steps=guide.GetNextChainSteps(1560)
    local linked=false
    for _,entry in ipairs(steps) do
        if entry.id==97540 then linked=entry.action=='During escort' and entry.location:find('41.0, 54.0',1,true) end
    end
    assert(linked,'Oasis escort-stop guide link missing')
    UnitGUID=function() return 'Creature-0-1-0-0-5955-000001' end
    C_GossipInfo={GetAvailableQuests=function() return {{questID=97540}} end}
    assert(guide.ObserveQuestOffers('GOSSIP_SHOW')); Check(true)
    active={1560,97540}; done[97540]=true; Check(true,true)
    assert(Spawns()==original,'Shared Tooga spawn data mutated')
    CheckNativeRequirements(1560); CheckNativeRequirements(97540)
    UnitLevel,active,done,UnitGUID,C_GossipInfo=oldLevel,oldActive,oldDone,oldGUID,oldGossip
    completed[1560],completed[97540]=oldMain,oldOasis
    guide.ClearOfferObservations()
''')
print('Oasis integration: offer-confirmed side quest uses Tanaris 41,54 during Tooga escort; shared NPC and prerequisite data preserved.')
lua.execute(b'''
    local oldItems=C_Item
    local owned=0
    C_Item={GetItemCount=function(id,bank)
        assert(bank==false); return id==274041 and owned or 0
    end}
    local player={level=60,race=96,class=3,active={},skills={},skillsKnown=true}
    guide.ClearOfferObservations()
    for _,id in ipairs({96376,96377,96379}) do
        local q=LibQuestieDB.Quest
        assert(q.name(id)=='State Secrets')
        player.race=id==96377 and 1 or 96
        local was=completed[id]; completed[id]=nil
        owned=0
        assert(not guide.test.Eligible(id,player),'State Secrets without Document Box: '..id)
        owned=1
        assert(guide.test.Eligible(id,player),'Tradeable Document Box delivery hidden: '..id)
        owned=nil
        assert(not guide.test.Eligible(id,player),'Unknown bag count allowed State Secrets')
        assert(guide.GetQuestSummary(id).availabilityNote:find('Document Box',1,true))
        CheckNativeRequirements(id)
        completed[id]=was
    end
    C_Item=oldItems
''')
print('State Secrets integration: all three native variants require a bag Document Box; buying one works without rescue-chain completion, provider data preserved.')
lua.execute(b'''
    local oldRep=C_Reputation
    local standing=-1
    C_Reputation={GetFactionDataByID=function(id) assert(id==576); return {currentStanding=standing} end}
    local p={level=60,race=96,class=3,active={},skills={},skillsKnown=true}
    local count=0
    for id in pairs(guide.questReputationRequirements) do
        count=count+1
        assert(LibQuestieDB.Quest.name(id),'Unknown Timbermaw correction ID')
        CheckNativeRequirements(id)
    end
    assert(count==18 and not guide.questReputationRequirements[86746]
        and not guide.questReputationRequirements[86747])
    for _,id in ipairs({86813,86812,86791,92065,92066}) do
        local was=completed[id]; completed[id]=nil
        standing=-1; assert(not guide.test.Eligible(id,p),'Hostile Timbermaw pickup leaked: '..id)
        standing=0; assert(guide.test.Eligible(id,p),'Neutral Timbermaw quest hidden: '..id)
        assert(guide.GetQuestSummary(id).availabilityNote:find('Neutral reputation',1,true))
        completed[id]=was
    end
    C_Reputation=oldRep
''')
print('Timbermaw integration: 18 documented Neutral requirements, all five screenshot quests checked across the boundary; native rows and reputation-building introductions preserved.')
lua.execute(b'''
    local oldHome,oldFish,oldShark=completed[91488],completed[91610],completed[91611]
    completed[91488],completed[91610],completed[91611]=nil,nil,nil
    local p={level=60,race=96,class=3,active={},skills={[356]=1},skillsKnown=true}
    assert(LibQuestieDB.Quest.name(91611)=='Deadliest Catch')
    assert(not guide.test.Eligible(91611,p),'Kurll shark quest skipped prerequisite')
    completed[91488]=true
    assert(guide.test.Eligible(91610,p),'Kurll squid quest missing after hide turn-in')
    p.active[91610]=true
    assert(not guide.test.Eligible(91611,p),'Accepted squid quest unlocked shark quest')
    p.active[91610]=nil; completed[91610]=true
    assert(guide.test.Eligible(91611,p),'Fishing 1 and squid turn-in did not unlock shark quest')
    p.skills={}; assert(not guide.test.Eligible(91611,p),'Kurll pickup without Fishing')
    assert(guide.GetQuestSummary(91611).availabilityNote:find('Fishing (skill 1)',1,true))
    for _,id in ipairs({89228,91488,91610,91611}) do CheckNativeRequirements(id) end
    completed[91488],completed[91610],completed[91611]=oldHome,oldFish,oldShark
''')
print('Kurll integration: Home on the Range -> Winter Frontier Fishery -> Deadliest Catch; Fishing 1 and prerequisite turn-in required, provider data preserved.')
lua.execute(b'''
    local oldA,oldB,oldC=completed[3505],completed[3506],completed[3507]
    local oldActive,oldDone,oldRace=active,done,UnitRace
    completed[3505],completed[3506],completed[3507]=true,nil,nil
    active={}; done={}; UnitRace=function() return 'Skyborne','Skyborne',96 end
    local p={level=60,race=96,class=3,active={},skills={},skillsKnown=true}
    assert(not guide.test.Eligible(3506,p),'Legacy tome pickup leaked')
    local steps=guide.GetNextChainSteps(3505)
    local found=false
    for _,row in ipairs(steps) do
        assert(row.id~=3506,'Legacy Betrayed reverse link leaked')
        if row.id==91497 then found=true end
    end
    assert(found,'Revised Seals of the Sindorei route missing')
    steps=guide.GetNextChainSteps(91497)
    local gambit,tome=false,false
    for _,row in ipairs(steps) do
        if row.id==91500 then gambit=true end
        if row.id==91538 then tome=true end
    end
    assert(gambit and tome,'Screenshot branch missing from revised chain')
    completed[3506]=true; assert(not guide.test.Eligible(3507,p),'Legacy finale leaked')
    for _,id in ipairs({3505,3506,3507,91497,91500,91531,91538,91547}) do CheckNativeRequirements(id) end
    completed[3505],completed[3506],completed[3507]=oldA,oldB,oldC
    active,done,UnitRace=oldActive,oldDone,oldRace
''')
print('Betrayed integration: legacy 3506/3507 hidden as unconfirmed pickups; revised Seals -> Gambit plus Tome branch retained, native data preserved.')
lua.execute(b'''
    local oldA,oldB,oldC=completed[91734],completed[91735],completed[91737]
    completed[91734],completed[91735],completed[91737]=nil,nil,nil
    local p={level=60,race=96,class=3,active={},skills={},skillsKnown=true}
    local names={[91734]='Andron Gant',[91735]="Jes'rimon",[91737]='Magatha Grimtotem'}
    local found=0
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        if LibQuestieDB.Quest.name(id)=='Remote Contact' then
            assert(names[id],'Unhandled Remote Contact variant: '..id); found=found+1
            p.confirmed=nil
            assert(not guide.test.Eligible(id,p),'Unconfirmed Remote Contact leaked: '..id)
            p.confirmed={[id]=true}
            assert(guide.test.Eligible(id,p),'Actual referral offer was lost: '..id)
            assert(guide.GetQuestSummary(id).availabilityNote:find(names[id],1,true))
        end
    end
    assert(found==3)
    for _,id in ipairs({91734,91735,91737,3517,3518}) do CheckNativeRequirements(id) end
    completed[91734],completed[91735],completed[91737]=oldA,oldB,oldC
''')
print('Remote Contact integration: all three native variants require current offers; actual offers restore pickups, alternatives and Jediga prerequisites remain native.')
lua.execute(b'''
    guide.InitBreadcrumbWarnings()
    local sample,rows
    for _,id in ipairs(LibQuestieDB.Quest.GetAllIds()) do
        if LibQuestieDB.Quest.Get(id,'breadcrumbs') then
            local found=guide.GetSkippedBreadcrumbs(id)
            if #found>0 then sample,rows=id,found; break end
        end
        LibQuestieDB.Quest.InvalidateCache(id)
    end
    assert(sample,'No applicable native breadcrumb warning fixture')
    local old=guide.db.breadcrumbWarnings
    guide.db.breadcrumbWarnings=true
    local before=#messages
    Fire('QUEST_ACCEPTED',1,sample)
    assert(#messages>before,'Native breadcrumb acceptance produced no warning')
    assert(messages[before+1]:find(rows[1].name,1,true))
    assert(messages[before+1]:find(rows[1].location,1,true))
    CheckNativeRequirements(sample)
    for _,row in ipairs(rows) do CheckNativeRequirements(row.id) end
    guide.db.breadcrumbWarnings=old
''')
print('Breadcrumb warning integration: actual applicable native breadcrumb warns on QUEST_ACCEPTED with name and pickup location; provider data unchanged.')
if sample_horde:
    lua.execute(b'''
        observed={}; function Collect(id,kind,label,x,y,confirmed)
            observed[id]=observed[id] or {kind=kind,label=label,confirmed=confirmed}
        end
        guide.BuildMap(1458,Collect,Checkpoint)
        filteredCount=0; for _ in pairs(observed) do filteredCount=filteredCount+1 end
        for id in pairs(guide.pickupPolicy.collection) do assert(not observed[id], 'Library catalog leaked: '..id) end
        assert(not observed[9265], 'Inactive Scourge investigation leaked')
        guide.db.filterAvailable=false; observed={}
        guide.BuildMap(1458,Collect,Checkpoint)
        broadCount=0; for _ in pairs(observed) do broadCount=broadCount+1 end
        assert(observed[78145] and observed[84398] and observed[78150] and observed[9265])
        guide.db.filterAvailable=true
        local npcID=LibQuestieDB.Quest.startedBy(9265)[1][1]
        UnitGUID=function() return 'Creature-0-1-0-0-'..npcID..'-000001' end
        C_GossipInfo={GetAvailableQuests=function() return {{questID=9265}} end}
        assert(guide.ObserveQuestOffers('GOSSIP_SHOW'))
        observed={}; guide.BuildMap(1458,Collect,Checkpoint)
        assert(observed[9265] and observed[9265].confirmed,'Real server offer did not restore event quest')
        guide.ClearOfferObservations()
        observed={}; guide.BuildMap(1458,Collect,Checkpoint)
        assert(not observed[9265])
        observed={}; guide.BuildMap(1454,Collect,Checkpoint)
        orgFiltered=0
        for id in pairs(observed) do
            orgFiltered=orgFiltered+1
            assert(not guide.pickupPolicy.aq[id], 'Orgrimmar AQ leak '..id)
        end
        guide.db.filterAvailable=false; observed={}; guide.BuildMap(1454,Collect,Checkpoint)
        orgAQ=0
        for id in pairs(observed) do if guide.pickupPolicy.aq[id] then orgAQ=orgAQ+1 end end
        assert(orgAQ>0 and observed[8580] and (observed[8549] or observed[8550]), 'Screenshot examples not exercised')
        guide.db.filterAvailable=true
        observed={}; guide.BuildMap(1413,Collect,Checkpoint)
        assert(observed[4921] and not observed[95774], 'Olgra leaked before Lost in Battle')
        active[1]=4921; done[4921]=true
        observed={}; guide.BuildMap(1413,Collect,Checkpoint)
        assert(not observed[95774], 'Olgra unlocked before prerequisite turn-in')
        completed[4921]=true; active[1]=nil
        observed={}; guide.BuildMap(1413,Collect,Checkpoint)
        assert(not observed[4921] and observed[95774], 'Olgra did not unlock after turn-in')
        CheckNativeRequirements(95774)
        guide.db.showLowLevel=false; guide.db.levelsBelow=5
        observed={}; guide.BuildMap(1413,Collect,Checkpoint)
        local normal={}; levelFilteredCount=0
        for id in pairs(observed) do
            local level=LibQuestieDB.Quest.Get(id,'questLevel') or 0
            assert(level<=0 or level>=17,'Pickup below configured cutoff: '..id)
            LibQuestieDB.Quest.InvalidateCache(id)
            normal[id]=true; levelFilteredCount=levelFilteredCount+1
        end
        guide.db.showLowLevel=true
        observed={}; guide.BuildMap(1413,Collect,Checkpoint)
        local addedLowLevel=false
        for id in pairs(normal) do assert(observed[id],'Low-level toggle removed available quest') end
        for id in pairs(observed) do
            local level=LibQuestieDB.Quest.Get(id,'questLevel') or 0
            if level>0 and level<17 then addedLowLevel=true end
            LibQuestieDB.Quest.InvalidateCache(id)
        end
        assert(addedLowLevel,'Low-level toggle did not restore eligible low-level quests')
    ''')
    print(f'Level 22 undead paladin, Undercity: {g[b"broadCount"]} broad pickup quests -> {g[b"filteredCount"]} filtered')
    print('All library catalog entries and inactive quest 9265 hidden; explicit NPC offer restores 9265.')
    print(f'Orgrimmar: {g[b"orgAQ"]} AQ candidates in broad view; all excluded in filtered view ({g[b"orgFiltered"]} other candidates).')
    print('Mankrik chain: Lost in Battle -> Her Name Is Olgra verified before acceptance, before turn-in and after turn-in.')
    print(f'Barrens level cutoff: {g[b"levelFilteredCount"]} available quests at level 17+; low-level toggle restores older quests.')
    print('Installed Forever availability regression passed.')
    sys.exit(0)
# Diverse starting zones plus city, transformed zones and high-level areas.
for map_id in [1429, 1411, 1412, 1438, 1426, 1420, 1453, 1423, 1433]:
    lua.execute(b'emitted=0; guide.BuildMap(...,Emit,Checkpoint)', map_id)
    print(f'Map {map_id}: {g[b"emitted"]} valid location emissions')

# Real active quests: Elwynn wolves, item drops and a completed quest turn-in.
lua.execute(b'''
    active={7,33,21}; done[7]=true
    emitted=0; kinds={}
    guide.BuildMap(1429,Emit,Checkpoint)
    assert(kinds.turnin and kinds.pickup and not kinds.objective)
''')
print(f'Active quest check: {g[b"emitted"]} emissions; pickups and turn-ins present; no objective markers')
# Exercise the actual map scheduler with the installed provider as well. A
# Python CBOR bridge is slower than native client decoding, so report this as
# an offline benchmark rather than an in-game timing guarantee.
lua.execute((ROOT / 'QuestLite/Map.lua').read_bytes(), b'QuestLite', ns)
lua.execute((ROOT / 'QuestLite/Minimap.lua').read_bytes(), b'QuestLite', ns)
lua.execute(b'''
    debugprofilestop=function() return os.clock()*1000 end
    guide.InitMap()
    coldTicks=0
    while #WorldMapFrame.pins==0 and coldTicks<240 do Tick(1); coldTicks=coldTicks+1 end
    assert(#WorldMapFrame.pins>0, guide.mapStatus)
    -- Let the final native-style scan publish before testing the cache.
    Tick(200)
    coldMarkerCount=#WorldMapFrame.pins
    local builds=0; local original=guide.BuildMap
    guide.BuildMap=function(...) builds=builds+1; return original(...) end
    WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
    WorldMapFrame:Show(); WorldMapFrame.provider:OnShow()
    assert(#WorldMapFrame.pins==coldMarkerCount)
    Tick(20); assert(builds==0,'Warm reopen queried installed database')
    local pin=WorldMapFrame.pins[1]
    assert(pin:GetScript('OnEnter'),'Native hover was not wired')
    pin:GetScript('OnEnter')(pin)
    assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip:NumLines()>1)
    assert(QuestLiteTooltip.owner==pin and QuestLiteTooltip.strata=='TOOLTIP')
    pin:GetScript('OnLeave')(pin)
    assert(not QuestLiteTooltip:IsShown())
    local target=WorldMapFrame.pins[1]
    EnableMinimapMock(); miniPX,miniPY=target.x,target.y
    guide.InitMinimap(); Tick(200)
    local found=false
    for _,frame in ipairs(frames) do
        if frame.point and frame.point[2]==Minimap and frame:IsShown() and frame.Icon then
            assert(frame:GetScript('OnEnter') and frame:GetScript('OnLeave'))
            frame:GetScript('OnEnter')(frame)
            assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip:NumLines()>1)
            frame:GetScript('OnLeave')(frame)
            found=true; break
        end
    end
    assert(found,'Installed quest data produced no nearby minimap marker')
''')
print(f'Offline scheduler: cold map published in {g[b"coldTicks"]} ticks; warm reopen immediate, zero scans')
print('Native-style enter/leave event path rendered installed quest data and hid the tooltip.')
print('Minimap marker and hover passed with installed quest data and emulated player geometry.')
lua.execute(b'''
    WorldMapFrame.mapID=1436 -- Westfall: Captain Sander's item-drop starter.
    guide.RequestMap(nil,'FORCE_REFRESH'); Tick(250)
    sanderMarkers=0
    for _,pin in ipairs(WorldMapFrame.pins) do
        if pin.quests[136] then
            sanderMarkers=sanderMarkers+1
            assert(pin.quests[136].dropStarter,'Actual treasure-map starter not classified')
        end
    end
    local raw,firstX,firstY=0
    guide.BuildMap(1436,function(id,kind,label,x,y)
        if id==136 then raw=raw+1; firstX,firstY=firstX or x,firstY or y end
    end,Checkpoint)
    sanderRawSources=raw
    assert(raw>100,'Expected dense coastal source fixture missing')
    assert(sanderMarkers>0 and sanderMarkers<=3,'Captain Sander world-map clutter regression')
    miniMapID=1436; miniPX,miniPY=firstX,firstY
    Fire('ZONE_CHANGED_NEW_AREA'); Tick(250)
    local nearby=0
    for _,pin in pairs(guide.testMinimapActive) do
        if pin.data.quests[136] then nearby=nearby+1 end
    end
    assert(nearby==1,'Actual Captain Sander minimap source clutter regression')
''')
print(f'Captain Sander: {g[b"sanderRawSources"]} actual source locations condensed to {g[b"sanderMarkers"]} world-map markers.')
print('Captain Sander minimap: one nearby item-drop source marker, using actual provider data.')
lua.execute(b'''
    local count=0
    for id,row in pairs(guide.questFieldOverrides) do
        local raw=LibQuestieDB.Quest.Get(id,'questLevel')
        local expected=raw==row.questLevel.was and row.questLevel.value or raw
        assert(guide.GetQuestSummary(id).level==expected,'Observed/new-provider level precedence failed '..id)
        assert(LibQuestieDB.Quest.Get(id,'questLevel')==raw,'Provider level was mutated')
        count=count+1
    end
    assert(count==19)
    local oldLevel,oldRace,oldClass,oldFaction=UnitLevel,UnitRace,UnitClass,UnitFactionGroup
    local oldActive,oldDone=active,done
    UnitLevel=function() return 30 end
    UnitRace=function() return 'Skyborne','Skyborne',96 end
    UnitClass=function() return 'Hunter','HUNTER',3 end
    UnitFactionGroup=function() return 'Horde' end
    active={}; done={}
    local function SpawnFingerprint()
        local rows={}
        for area,points in pairs(LibQuestieDB.Npc.spawns(14242) or {}) do
            for _,point in ipairs(points) do rows[#rows+1]=area..':'..point[1]..':'..point[2] end
        end
        table.sort(rows); return table.concat(rows,',')
    end
    local originalSpawn=SpawnFingerprint()
    local spawns=LibQuestieDB.Npc.spawns(14242)
    local expectedX,expectedY=.48,.775
    if spawns and next(spawns) then
        assert(spawns[17] and spawns[17][1],'Sulhasa no longer in the Barrens')
        expectedX,expectedY=spawns[17][1][1]/100,spawns[17][1][2]/100
    end
    local found=false
    guide.BuildMap(1413,function(id,kind,label,x,y)
        if id==98093 then
            found=true; assert(kind=='pickup' and label=='Sulhasa')
            assert(math.abs(x-expectedX)<.000001 and math.abs(y-expectedY)<.000001,'Sulhasa native/fallback precedence failed')
        end
    end,Checkpoint)
    assert(found,'Field to Clear missing its Sulhasa location')
    assert(SpawnFingerprint()==originalSpawn,'Provider Sulhasa row was modified')
    active={78127}; done[78127]=true
    local function Library(mapID,name,wanted)
        local visible=false
        guide.BuildMap(mapID,function(id,kind,label)
            if id==78127 then visible=true; assert(kind=='turnin' and label==name) end
        end,Checkpoint)
        assert(visible==wanted,'Wrong library capital for '..name)
    end
    Library(1458,'Owen Thadd',true); Library(1453,'Owen Thadd',false)
    UnitRace=function() return 'Human','Human',1 end
    UnitFactionGroup=function() return 'Alliance' end
    Library(1453,'Garion Wendell',true); Library(1458,'Garion Wendell',false)
    assert(LibQuestieDB.Quest.Get(78127,'finishedBy')[1][1]==211033,'Provider library giver list was modified')
    UnitLevel,UnitRace,UnitClass,UnitFactionGroup=oldLevel,oldRace,oldClass,oldFaction
    active,done=oldActive,oldDone
''')
print('ForeverDB comparison fixes: 19 guarded level corrections, native-or-fallback Sulhasa pickup, and Horde/Alliance library turn-ins verified; provider unchanged.')
print('Installed QuestieDB integration passed (offline Lua 5.1).')

lua.execute(b'''
    local oldLevel=UnitLevel; UnitLevel=function() return 40 end
    assert(LibQuestieDB.Item.name(4614)=='Pendant of Myzrael')
    local raw,firstX,firstY=0
    guide.BuildMap(1417,function(id,kind,label,x,y)
        if id==635 then raw=raw+1; firstX,firstY=firstX or x,firstY or y end
    end,Checkpoint)
    assert(raw>0,'Pendant source fixture missing')
    WorldMapFrame.mapID=1417; miniMapID=1417; miniPX,miniPY=firstX,firstY
    guide.RequestMap(nil,'FORCE_REFRESH'); Tick(250)
    local function Count()
        local world,mini=0,0
        for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[635] then world=world+1 end end
        for _,pin in pairs(guide.testMinimapActive) do if pin.data.quests[635] then mini=mini+1 end end
        return world,mini
    end
    local world,mini=Count(); assert(world>0 and mini>0,'Pendant source markers missing before toggle')
    guide.db.itemDropLocations=false; guide.RequestMap(); Tick(250)
    world,mini=Count(); assert(world==0 and mini==0,'Pendant toggle failed on a map')
    guide.db.itemDropLocations=true; guide.RequestMap(); Tick(250)
    world,mini=Count(); assert(world>0 and mini>0,'Pendant sources did not return')
    UnitLevel=oldLevel
''')
print('Actual Pendant of Myzrael: source toggle hides/restores world-map and minimap markers.')

lua.execute(b'''
    local oldLevel=UnitLevel; UnitLevel=function() return 40 end
    guide.SetQuestHidden(635,true); Tick(250)
    for _,pin in ipairs(WorldMapFrame.pins) do assert(not pin.quests[635],'Hidden Pendant world marker survived') end
    for _,pin in pairs(guide.testMinimapActive) do assert(not pin.data.quests[635],'Hidden Pendant minimap marker survived') end
    guide.SetQuestHidden(635,false); Tick(250)
    local restored=false
    for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[635] then restored=true end end
    assert(restored,'Restored Pendant pickup failed to return')
    UnitLevel=oldLevel
''')
print('Per-quest hiding: actual Pendant pickup removed from both maps and restored, independently of drop-source toggle.')
