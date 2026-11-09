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
for file in ['Core.lua', 'Diagnostics.lua', 'AvailabilityPolicy.lua', 'AvailabilityPolicyData.lua', 'Database.lua', 'DropChances.lua']:
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
    assert(not required or #required==0,'Earthen Echo provider fixture changed')
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
    for _,race in ipairs({2,5,6,8,34}) do
        player.race=race
        assert(guide.test.Eligible(98251,player),'Horde race incorrectly rejected: '..race)
    end
''')
print('Screenshot classification: SoD Warrior turn-ins hidden; Horde/Alliance masks verified (including race 34); A Void Path requires turn-in.')
lua.execute(b'''
    local chain={91858,91859,91860,91861,91862,96204,95034,95036,95111,95125,95126,95140}
    local player={active={},skills={},level=26,race=5,class=2,confirmed={}}
    for index,id in ipairs(chain) do
        assert(LibQuestieDB.Quest.name(id),'Missing Paladin chain record '..id)
        assert(LibQuestieDB.Quest.Get(id,'requiredClasses')==2,'Paladin mask changed '..id)
        assert(LibQuestieDB.Quest.Get(id,'requiredRaces')==16,'Undead mask changed '..id)
        if index>1 then
            local previous=chain[index-1]
            local oldCompleted,oldDone=completed[previous],done[previous]
            completed[previous]=nil; player.confirmed={[id]=true}
            assert(not guide.test.Eligible(id,player),'Paladin future step leaked '..id)
            player.active[previous]=true; done[previous]=true
            assert(not guide.test.Eligible(id,player),'Paladin objective completion bypassed turn-in '..id)
            player.active[previous]=nil; completed[previous]=true
            assert(guide.test.Eligible(id,player),'Paladin turn-in failed to unlock '..id)
            player.class=1; assert(not guide.test.Eligible(id,player),'Paladin restriction bypassed '..id)
            player.class=2; player.race=1
            assert(not guide.test.Eligible(id,player),'Undead restriction bypassed '..id)
            player.race=5; completed[previous]=oldCompleted; done[previous]=oldDone
        end
        assert(not LibQuestieDB.Quest.Get(id,'preQuestSingle'),'Provider prerequisite fixture changed '..id)
        assert(not LibQuestieDB.Quest.Get(id,'preQuestGroup'),'Provider prerequisite fixture changed '..id)
        LibQuestieDB.Quest.InvalidateCache(id)
    end
''')
print('Undead Paladin chain: all eleven missing prerequisite links require turn-in; confirmed offers respect chain, class and race masks; provider unchanged.')
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
        assert(not LibQuestieDB.Quest.Get(95774,'preQuestSingle'), 'Provider data was changed')
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
print('Installed QuestieDB integration passed (offline Lua 5.1).')
