"""Offline Lua 5.1 regression tests; run with Python and lupa installed."""
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.tools'))
from lupa.lua51 import LuaRuntime


class AddonTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute((ROOT / 'tests/wow_mock.lua').read_text())
        template = ET.parse(ROOT / 'QuestLite/Pins.xml').getroot()[0]
        self.lua.globals().pinTemplateMouseEnabled = template.attrib.get('enableMouse') == 'true'
        self.ns = self.lua.table(testing=True)
        for name in ['Core.lua', 'Diagnostics.lua', 'AvailabilityPolicy.lua', 'AvailabilityPolicyData.lua', 'Database.lua', 'DropChances.lua', 'Map.lua', 'Minimap.lua', 'SoftTarget.lua', 'LootSparkles.lua']:
            self.lua.execute((ROOT / 'QuestLite' / name).read_text(encoding='utf-8'), 'QuestLite', self.ns)
        self.lua.globals().ns = self.ns
        self.lua.execute("Fire('ADDON_LOADED','QuestLite'); Fire('PLAYER_LOGIN')")
        self.lua.execute("ns.db.showLowLevel=true")  # Existing cases isolate availability rules.

    def check(self, code):
        self.lua.execute(code)

    def test_toc_and_xml(self):
        for line in (ROOT / 'QuestLite/QuestLite.toc').read_text().splitlines():
            if line and not line.startswith('#'):
                self.assertTrue((ROOT / 'QuestLite' / line).is_file(), line)
        ET.parse(ROOT / 'QuestLite/Pins.xml')

    def test_blocked_action_recorder_filters_addons_bounds_history_and_prints_once(self):
        self.check("""
            local initial=#messages
            debugstack=function() return string.rep('trace ',400) end
            Fire('ADDON_ACTION_BLOCKED','OtherAddon','OtherAction()')
            assert(ns.db.blockedActions==nil and #messages==initial)
            for index=1,25 do Fire('ADDON_ACTION_BLOCKED','QuestLite','Action'..index..'()') end
            assert(#ns.db.blockedActions==10 and #messages==initial+1)
            assert(ns.db.blockedActions[1].action=='Action16()')
            assert(ns.db.blockedActions[10].action=='Action25()')
            assert(#ns.db.blockedActions[10].stack==1500)
            combat=true; Fire('ADDON_ACTION_FORBIDDEN','QuestLite','ProtectedAction()'); combat=false
            assert(ns.db.blockedActions[10].combat and ns.db.blockedActions[10].event=='ADDON_ACTION_FORBIDDEN')
            SlashCmdList.QUESTLITE('errors')
            assert(messages[#messages]:find('ProtectedAction()',1,true))
            SlashCmdList.QUESTLITE('errors clear')
            assert(ns.db.blockedActions==nil)
        """)

    def test_blocked_action_context_records_cvar_call_without_changing_pcall_behavior(self):
        self.check("""
            ns.currentAction='outer context'
            local setter=C_CVar.SetCVar
            C_CVar.SetCVar=function(name,value)
                Fire('ADDON_ACTION_BLOCKED','QuestLite','C_UnitAuras.GetAuraDataByIndex()')
                return setter(name,value)
            end
            cvars.outlineModeShowLootEffectWhenDisabled='0'
            Fire('CVAR_UPDATE','outlineModeShowLootEffectWhenDisabled'); Tick(100)
            local rows=ns.db.blockedActions
            assert(rows and rows[#rows].context=='SetCVar outlineModeShowLootEffectWhenDisabled')
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='1' and ns.currentAction=='outer context')
            local ok,err=ns.TryAction('test error',function() error('original failure') end)
            assert(not ok and err:find('original failure',1,true) and ns.currentAction=='outer context')
        """)

    def test_blocked_action_history_handles_corruption_and_secret_event_fields(self):
        self.check("""
            ns.db.blockedActions='damaged'
            SlashCmdList.QUESTLITE('errors'); assert(#ns.db.blockedActions==0)
            ns.db.blockedActions={{invalid=true},{event='ADDON_ACTION_BLOCKED',action='SavedAction()'}}
            SlashCmdList.QUESTLITE('errors'); assert(#ns.db.blockedActions==1)
            issecretvalue=function(value) return value=='SECRET' end
            Fire('ADDON_ACTION_BLOCKED','SECRET','SecretAction()')
            assert(#ns.db.blockedActions==1)
            Fire('ADDON_ACTION_BLOCKED','QuestLite','SECRET')
            assert(ns.db.blockedActions[2].action=='Unavailable')
        """)

    def test_drop_rate_source_precedence_missing_rows_and_formatting(self):
        self.check("""
            local d=ns.testDropChances
            assert(d.Rate(100,10)==40) -- explicit manual correction
            assert(d.Rate(100,11)==60) -- quest-only server data ahead of crowdsourcing
            assert(d.Rate(100,12)==.01) -- crowd data fallback
            assert(d.Rate(101,10)==75) -- correction references crowd source
            assert(d.Rate(102,10)==35) -- missing server reference falls back to crowd
            assert(d.Rate(103,10)==90)
            assert(d.Rate(104,10)==0) -- zero is known, not missing
            assert(d.Rate(101,11)==nil and d.Rate(999,10)==nil)
            assert(d.FormatRate(.01)=='<0.1%' and d.FormatRate(0)=='0%')
            assert(d.FormatRate(12.345)=='12.3%' and d.FormatRate(nil)=='Unknown')
        """)

    def test_drop_rate_data_is_not_executed_and_invalid_values_are_unknown(self):
        self.check("""
            mockDropData.wowheadData="return {[200]={[10]=25},[201]={[10]=100}}; error('executed support data')"
            mockDropData.cmangosData={[200]={[10]=101,[11]=math.huge,[12]=-1,[13]=0/0}}
            mockDropFixes.Era={[200]={[10]=-99,[11]=101}}
        """)
        self.lua.execute((ROOT / 'QuestLite/DropChances.lua').read_text(), 'QuestLite', self.ns)
        self.check("""
            ns.InitDropChances()
            local d=ns.testDropChances
            assert(d.Rate(200,10)==25 and d.Rate(201,10)==100)
            for _,npc in ipairs({11,12,13,999}) do assert(d.Rate(200,npc)==nil) end
        """)

    def test_drop_item_and_unit_tooltips_active_items_only_and_no_duplicates(self):
        self.check("""
            quests[1]={objectives={[3]={{100},{101},{104}}},requiredSourceItems={102}}
            active[1]=1; Fire('QUEST_LOG_UPDATE')
            items[100]={name='Quest tooth',npcDrops={10,11,12}}
            items[101]={name='Quest bone',npcDrops={10}}
            items[102]={name='Quest source',npcDrops={10}}
            items[104]={name='Known zero',npcDrops={10}}
            npcs[10]={name='Wolf'}; npcs[11]={name='Bear'}; npcs[12]={name='Boar'}
            local tip=CreateFrame('GameTooltip'); tip:SetOwner(UIParent,'ANCHOR_NONE')
            ns.testDropChances.ItemTooltip(tip,{id=100})
            assert(#tip.lines==4 and tip.lines[2]=='Wolf  40%')
            assert(tip.lines[3]=='Bear  60%' and tip.lines[4]=='Boar  <0.1%')
            ns.testDropChances.ItemTooltip(tip,{id=100}); assert(#tip.lines==4)
            tip:SetOwner(UIParent,'ANCHOR_NONE')
            AddNativeTooltipLine(tip,'Quest tooth') -- Quest title, not an objective.
            AddNativeTooltipLine(tip,'|cff8888885/5 Quest tooth|r')
            AddNativeTooltipLine(tip,'5/5 Quest tooth') -- Second party member.
            AddNativeTooltipLine(tip,'Quest bone: 0/1')
            AddNativeTooltipLine(tip,'0/1 Quest source')
            AddNativeTooltipLine(tip,'0/1 Known zero')
            ns.testDropChances.UnitTooltip(tip,{guid='Creature-0-1-0-0-10-000001'})
            assert(#tip.lines==6 and tip.lines[1]=='Quest tooth')
            assert(tip.lines[2]=='|cff8888885/5 Quest tooth (40%)|r')
            assert(tip.lines[3]=='5/5 Quest tooth (40%)')
            assert(tip.lines[4]=='Quest bone (75%): 0/1')
            assert(tip.lines[6]=='0/1 Known zero (0%)')
            ns.testDropChances.UnitTooltip(tip,{guid='Creature-0-1-0-0-10-000001'})
            assert(#tip.lines==6 and tip.lines[3]=='5/5 Quest tooth (40%)')
            tip:SetOwner(UIParent,'ANCHOR_NONE')
            ns.testDropChances.ItemTooltip(tip,{id=999}); assert(#tip.lines==0)
            ns.db.dropChances=false
            ns.testDropChances.ItemTooltip(tip,{id=100}); assert(#tip.lines==0)
            ns.db.dropChances=true
            active={}; Fire('QUEST_LOG_UPDATE')
            ns.testDropChances.ItemTooltip(tip,{id=100}); assert(#tip.lines==0)
        """)

    def test_drop_rates_unknowns_limits_and_restricted_tooltips(self):
        self.check("""
            quests[1]={objectives={[3]={{999}}}}; active[1]=1; Fire('QUEST_LOG_UPDATE')
            items[999]={name='Custom item',npcDrops={10}}
            local tip=CreateFrame('GameTooltip'); tip:SetOwner(UIParent,'ANCHOR_NONE')
            ns.testDropChances.ItemTooltip(tip,{id=999})
            assert(tip.lines[2]=='Unknown: no NPC drop-rate data')
            tip:SetOwner(UIParent,'ANCHOR_NONE')
            AddNativeTooltipLine(tip,'0/1 Custom item')
            ns.testDropChances.UnitTooltip(tip,{guid='Creature-0-1-0-0-10-000001'})
            assert(#tip.lines==1 and tip.lines[1]=='0/1 Custom item')
            tip:SetOwner(UIParent,'ANCHOR_NONE')
            local secret=setmetatable({},{__index=function() error('Read restricted tooltip data') end})
            issecretvalue=function(value) return value==secret or value=='SECRET' end
            ns.testDropChances.ItemTooltip(tip,secret)
            ns.testDropChances.ItemTooltip(tip,{id='SECRET'})
            ns.testDropChances.UnitTooltip(tip,{guid='SECRET'})
            IsInInstance=function() return true end
            ns.testDropChances.UnitTooltip(tip,setmetatable({},{__index=function() error('Read instance GUID') end}))
            assert(#tip.lines==0)
        """)

    def test_drop_rates_register_native_tooltip_pipeline(self):
        self.check("""
            nativeDropCallbacks={}
            GameTooltip=CreateFrame('GameTooltip'); ItemRefTooltip=CreateFrame('GameTooltip')
            GameTooltip.GetPrimaryTooltipData=function() end
            TooltipDataProcessor={AddTooltipPostCall=function(kind,callback) nativeDropCallbacks[kind]=callback end}
            Enum={TooltipDataType={Item=1,Unit=2}}
        """)
        self.lua.execute((ROOT / 'QuestLite/DropChances.lua').read_text(), 'QuestLite', self.ns)
        self.check("""
            ns.InitDropChances()
            assert(nativeDropCallbacks[1] and nativeDropCallbacks[2])
            quests[1]={objectives={[3]={{100}}}}; active[1]=1; Fire('QUEST_LOG_UPDATE')
            items[100]={name='Tooth',npcDrops={10}}
            GameTooltip:SetOwner(UIParent,'ANCHOR_NONE')
            AddNativeTooltipLine(GameTooltip,'0/1 Tooth')
            GameTooltip.GetName=function() return 'NativeDropTest' end
            NativeDropTestTextLeft1=GameTooltip.TextLeft1
            nativeDropCallbacks[2](GameTooltip,{guid='Creature-0-1-0-0-10-000001'})
            assert(#GameTooltip.lines==1 and GameTooltip.lines[1]=='0/1 Tooth (40%)')
            ItemRefTooltip:SetOwner(UIParent,'ANCHOR_NONE')
            nativeDropCallbacks[1](ItemRefTooltip,{id=100})
            assert(#ItemRefTooltip.lines==2)
            local other=CreateFrame('GameTooltip'); other:SetOwner(UIParent,'ANCHOR_NONE')
            nativeDropCallbacks[1](other,{id=100}); assert(#other.lines==0)
        """)

    def test_drop_rates_register_legacy_tooltip_scripts(self):
        self.check("""
            GameTooltip=CreateFrame('GameTooltip'); ItemRefTooltip=CreateFrame('GameTooltip')
            for _,tip in ipairs({GameTooltip,ItemRefTooltip}) do
                tip.hooks={}
                tip.HasScript=function() return true end
                tip.HookScript=function(self,name,callback) self.hooks[name]=callback end
                tip.GetItem=function() return 'Tooth','item:100:0:0:0' end
                tip.GetUnit=function() return 'Wolf','mouseover' end
            end
            UnitGUID=function() return 'Creature-0-1-0-0-10-000001' end
        """)
        self.lua.execute((ROOT / 'QuestLite/DropChances.lua').read_text(), 'QuestLite', self.ns)
        self.check("""
            ns.InitDropChances()
            quests[1]={objectives={[3]={{100}}}}; active[1]=1; Fire('QUEST_LOG_UPDATE')
            items[100]={name='Tooth',npcDrops={10}}
            npcs[10]={name='Wolf'}
            GameTooltip:SetOwner(UIParent,'ANCHOR_NONE')
            AddNativeTooltipLine(GameTooltip,'0/1 Tooth')
            GameTooltip.hooks.OnTooltipSetUnit(GameTooltip)
            assert(#GameTooltip.lines==1 and GameTooltip.lines[1]=='0/1 Tooth (40%)')
            GameTooltip.hooks.OnTooltipCleared(GameTooltip)
            assert(GameTooltip.QuestLiteDropToken==nil)
            GameTooltip:SetOwner(UIParent,'ANCHOR_NONE')
            GameTooltip.hooks.OnTooltipSetItem(GameTooltip)
            assert(GameTooltip.lines[2]=='Wolf  40%')
        """)

    def test_pin_template_is_self_contained_on_forever(self):
        frame = ET.parse(ROOT / 'QuestLite/Pins.xml').getroot()[0]
        self.assertEqual(frame.tag.rsplit('}', 1)[-1], 'Frame')
        self.assertNotIn('inherits', frame.attrib,
                         'Forever has MapCanvasPinMixin but no MapCanvasPinTemplate XML node')
        self.assertEqual(frame.attrib['mixin'], 'QuestLitePinMixin')
        self.assertEqual(frame.attrib['enableMouse'], 'true')
        self.assertEqual(frame.attrib['virtual'], 'true')
        self.assertTrue(self.lua.eval('type(QuestLitePinMixin.OnAcquired)=="function"'))

    def test_settings_and_cvar_restoration(self):
        self.check("""
            assert(ns.db.sparkleOther and ns.db.sparkleQuest)
            assert(cvars.SoftTargetInteract=='3')
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='1')
            SlashCmdList.QUESTLITE('off')
            assert(cvars.SoftTargetInteract=='0')
            assert(cvars.SoftTargetInteractRange=='10')
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='0')
            assert(ns.db.savedCVars==nil)
        """)

    def test_combat_shutdown_defers_writes(self):
        self.check("""
            Fire('PLAYER_REGEN_DISABLED'); combat=true
            local count=#writes
            SlashCmdList.QUESTLITE('off'); Tick(20)
            assert(#writes==count)
            combat=false; Fire('PLAYER_REGEN_ENABLED')
            assert(cvars.SoftTargetInteract=='0')
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='0')
        """)

    def test_eligibility(self):
        self.check("""
            local p={active={},skills={},level=10,race=1,class=1}
            quests[1]={requiredLevel=11}; assert(not ns.test.Eligible(1,p))
            quests[1]={requiredRaces=2}; assert(not ns.test.Eligible(1,p))
            quests[1]={requiredClasses=2}; assert(not ns.test.Eligible(1,p))
            quests[1]={preQuestSingle={2,3}}; assert(not ns.test.Eligible(1,p))
            completed[3]=true; assert(ns.test.Eligible(1,p))
            quests[1]={preQuestGroup={2,3}}; assert(not ns.test.Eligible(1,p))
            completed[2]=true; assert(ns.test.Eligible(1,p))
            quests[1]={preQuestGroup={-4}}; assert(not ns.test.Eligible(1,p))
            p.active[4]=true; assert(not ns.test.Eligible(1,p))
            completed[4]=true; assert(ns.test.Eligible(1,p))
            quests[1]={preQuestGroup={5}}; quests[5]={exclusiveTo={4}}
            assert(ns.test.Eligible(1,p))
            quests[1]={preQuestSingle={3},preQuestGroup={99}}; assert(ns.test.Eligible(1,p))
            quests[1]={inGroupWith={4}}; assert(ns.test.Eligible(1,p))
            quests[1]={requiredSpell=-100}; assert(ns.test.Eligible(1,p))
            quests[1]={requiredSpell=100}; assert(not ns.test.Eligible(1,p))
            quests[1]={requiredSkill={164,50}}; assert(not ns.test.Eligible(1,p))
            p.skills[164]=50; assert(ns.test.Eligible(1,p))
            quests[1]={parentQuest=4}; assert(ns.test.Eligible(1,p))
            quests[1]={exclusiveTo={4}}; assert(not ns.test.Eligible(1,p))
            quests[1]={requiredMaxLevel=9}; assert(not ns.test.Eligible(1,p))
            quests[1]={}; completed[1]=true; assert(not ns.test.Eligible(1,p))
        """)

    def test_confirmed_offer_cannot_skip_required_chain_steps(self):
        self.check("""
            local p={active={},confirmed={[900002]=true},skills={},skillsKnown=true,level=22,race=5,class=2}
            quests[900002]={preQuestSingle={900001}}
            assert(not ns.test.Eligible(900002,p),'NPC offer bypassed an unfinished prerequisite')
            p.active[900001]=true
            assert(not ns.test.Eligible(900002,p),'Accepting a prerequisite was treated as turning it in')
            done[900001]=true
            assert(not ns.test.Eligible(900002,p),'Completing objectives was treated as turning in the prerequisite')
            completed[900001]=true; p.active[900001]=nil
            assert(ns.test.Eligible(900002,p))
            quests[900002]={preQuestGroup={900001,900003}}
            assert(not ns.test.Eligible(900002,p),'Grouped prerequisite was bypassed')
            completed[900003]=true; assert(ns.test.Eligible(900002,p))
            quests[900002]={parentQuest=900004}
            assert(not ns.test.Eligible(900002,p))
            p.active[900004]=true; assert(ns.test.Eligible(900002,p))
            quests[900002]={availableStartingWith=900005}
            assert(not ns.test.Eligible(900002,p))
            p.active[900005]=true; assert(ns.test.Eligible(900002,p))
        """)

    def test_chain_unlocks_on_turnin_on_world_map_and_minimap(self):
        self.check("""
            npcs[10]={name='Chain giver',spawns={[12]={{22,30}}}}
            quests[900001]={name='Step one',startedBy={{10}}}
            quests[900002]={name='Step two',preQuestSingle={900001},startedBy={{10}},finishedBy={{10}}}
            quests[900003]={name='Step three',preQuestSingle={900002},startedBy={{10}}}
            UnitGUID=function() return 'Creature-0-1-0-0-10-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {{questID=900001},{questID=900002},{questID=900003}} end}
            EnableMinimapMock(); ns.InitMinimap(); Fire('GOSSIP_SHOW'); Tick(100)
            local function CheckPresent(id, expected)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==expected and mini==expected,'Wrong chain visibility for '..id)
            end
            CheckPresent(900001,true); CheckPresent(900002,false); CheckPresent(900003,false)
            active[1]=900001; done[900001]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            CheckPresent(900002,false); CheckPresent(900003,false)
            completed[900001]=true; active[1]=nil; Fire('QUEST_TURNED_IN',900001); Tick(100)
            CheckPresent(900002,true); CheckPresent(900003,false)
            active[1]=900002; done[900002]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            CheckPresent(900003,false)
            completed[900002]=true; active[1]=nil; Fire('QUEST_TURNED_IN',900002); Tick(100)
            CheckPresent(900003,true)
        """)

    def test_mankrik_missing_chain_link_is_corrected_locally(self):
        self.check("""
            npcs[3432]={name='Mankrik',spawns={[12]={{22,30}}}}
            quests[4921]={name='Lost in Battle',requiredLevel=14,startedBy={{3432}},finishedBy={{3432}}}
            quests[95774]={name='Her Name Is Olgra',requiredLevel=14,startedBy={{3432}}}
            UnitLevel=function() return 22 end
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function HasQuest(id)
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then return true end end
                return false
            end
            assert(HasQuest(4921) and not HasQuest(95774))
            active[1]=4921; done[4921]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            assert(not HasQuest(95774),'Objectives finished before turn-in unlocked Olgra')
            completed[4921]=true; active[1]=nil; Fire('QUEST_TURNED_IN',4921); Tick(100)
            assert(not HasQuest(4921) and HasQuest(95774))
            local found=false
            for _,pin in pairs(ns.testMinimapActive) do
                if pin.data.quests[95774] then found=true end
            end
            assert(found,'Olgra did not unlock on minimap')
            assert(quests[95774].preQuestSingle==nil and quests[95774].preQuestGroup==nil,
                'Local correction mutated provider data')
        """)

    def test_old_objective_setting_is_retired(self):
        self.check("""
            ns.db=nil; QuestLiteDB={objectives=true}; ns.LoadSettings()
            assert(ns.db.objectives==nil)
            assert(settings.objectives==nil)
        """)

    def test_availability_checkbox_invalidates_cache(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={requiredLevel=20,startedBy={{10}}}
            quests[2]={requiredClasses=2,startedBy={{10}}}
            assert(ns.db.filterAvailable and settings.filterAvailable)
            ns.RequestMap(); Tick(100); assert(#WorldMapFrame.pins==0)
            settings.filterAvailable:Change(false); Tick(100)
            assert(#WorldMapFrame.pins==1)
            assert(WorldMapFrame.pins[1].quests[1])
            assert(not WorldMapFrame.pins[1].quests[2],'Wrong class should stay hidden')
            settings.filterAvailable:Change(true); Tick(100)
            assert(#WorldMapFrame.pins==0,'Filtered view reused broad cache')
        """)

    def test_giver_faction_filter_preserves_hostile_item_drops(self):
        self.check("""
            UnitFactionGroup=function() return 'Alliance' end
            npcs[10]={name='Horde giver',friendlyToFaction='H',spawns={[12]={{20,30}}}}
            items[30]={name='Quest item',npcDrops={10}}
            quests[1]={startedBy={{10}}}
            quests[2]={startedBy={nil,nil,{30}}}
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1)
            assert(not WorldMapFrame.pins[1].quests[1])
            assert(WorldMapFrame.pins[1].quests[2],'Enemy drop sources were filtered as quest givers')
        """)

    def test_gossip_filters_only_the_checked_giver(self):
        self.check("""
            npcs[10]={name='First giver',spawns={[12]={{20,30}}}}
            npcs[11]={name='Other giver',spawns={[12]={{80,70}}}}
            quests[1]={startedBy={{10,11}}}; quests[2]={startedBy={{10}}}
            UnitGUID=function() return 'Creature-0-1-0-0-10-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {{questID=2}} end}
            Fire('GOSSIP_SHOW'); Tick(100)
            assert(#WorldMapFrame.pins==2)
            for _,pin in ipairs(WorldMapFrame.pins) do
                if pin.x==.2 then assert(pin.quests[2] and not pin.quests[1])
                else assert(pin.quests[1]) end
            end
            settings.filterAvailable:Change(false); Tick(100)
            for _,pin in ipairs(WorldMapFrame.pins) do
                if pin.x==.2 then assert(pin.quests[1] and pin.quests[2]) end
            end
            settings.filterAvailable:Change(true); Tick(100)
            for _,pin in ipairs(WorldMapFrame.pins) do
                if pin.x==.2 then assert(pin.quests[2] and not pin.quests[1]) end
            end
            SlashCmdList.QUESTLITE('refresh'); Tick(100)
            for _,pin in ipairs(WorldMapFrame.pins) do
                if pin.x==.2 then assert(pin.quests[1] and pin.quests[2]) end
            end
        """)

    def test_required_items_auto_rewards_and_breadcrumbs(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={requiredSourceItems={30},startedBy={{10}}}
            quests[2]={questFlags=1024,startedBy={{10}}}
            quests[3]={breadcrumbForQuestId=9,startedBy={{10}}}
            quests[4]={breadcrumbs={9},startedBy={{10}}}
            active[1]=9
            local count=0; C_Item={GetItemCount=function() return count end}
            ns.RequestMap(); Tick(100); assert(#WorldMapFrame.pins==0)
            count=1; Fire('BAG_UPDATE_DELAYED'); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[1])
            assert(not WorldMapFrame.pins[1].quests[2] and not WorldMapFrame.pins[1].quests[3])
        """)

    def test_screenshot_policies_for_undead_paladin(self):
        self.check("""
            UnitLevel=function() return 22 end
            UnitRace=function() return 'Undead','Scourge',5 end
            UnitClass=function() return 'Paladin','PALADIN',2 end
            UnitFactionGroup=function() return 'Horde' end
            npcs[10]={name='Library giver',spawns={[12]={{20,30}}}}
            for _,id in ipairs({78145,78150,84398,9265}) do
                quests[id]={requiredLevel=1,requiredClasses=0,questLevel=60,startedBy={{10}}}
            end
            quests[900001]={name='Valid undead paladin quest',requiredClasses=2,requiredRaces=16,startedBy={{10}}}
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[900001])
            for _,id in ipairs({78145,78150,84398,9265}) do assert(not WorldMapFrame.pins[1].quests[id]) end
            settings.filterAvailable:Change(false); Tick(100)
            for _,id in ipairs({78145,78150,84398,9265}) do assert(WorldMapFrame.pins[1].quests[id]) end
        """)

    def test_aq_signet_and_herb_donations_hidden_on_both_maps(self):
        self.check("""
            npcs[10]={name='AQ NPC',spawns={[12]={{22,30}}}}
            for _,id in ipairs({8811,8819,8580,8549,8550,900001}) do
                quests[id]={name='Quest '..id,requiredLevel=1,questLevel=60,startedBy={{10}}}
            end
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function CheckHidden()
                for _,pin in ipairs(WorldMapFrame.pins) do
                    for id in pairs(pin.quests) do assert(not ns.pickupPolicy.aq[id], 'AQ world map leak '..id) end
                end
                for _,pin in pairs(ns.testMinimapActive) do
                    for id in pairs(pin.data.quests) do assert(not ns.pickupPolicy.aq[id], 'AQ minimap leak '..id) end
                end
            end
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[900001])
            CheckHidden()
            settings.filterAvailable:Change(false); Tick(100)
            for _,id in ipairs({8811,8819,8580,8549,8550}) do assert(WorldMapFrame.pins[1].quests[id]) end
            settings.filterAvailable:Change(true); Tick(100); CheckHidden()
            UnitGUID=function() return 'Creature-0-1-0-0-10-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {{questID=8811}} end}
            Fire('GOSSIP_SHOW'); Tick(100)
            assert(WorldMapFrame.pins[1].quests[8811].confirmed, 'Real AQ offer was not restored')
        """)

    def test_all_reviewed_event_categories_reject_unlisted_new_quests(self):
        self.check("""
            local player={level=22,race=5,class=2,active={},skills={},skillsKnown=true}
            local count=0
            for sort in pairs(ns.pickupPolicy.eventSorts) do
                count=count+1
                local id=900000+count
                quests[id]={requiredLevel=1,zoneOrSort=sort}
                assert(not ns.pickupPolicy.hidden[id], 'Fixture should exercise category fallback, not static IDs')
                assert(not ns.test.Eligible(id,player),'Uncovered event category '..sort)
                ns.db.filterAvailable=false; assert(ns.test.Eligible(id,player))
                ns.db.filterAvailable=true
            end
            assert(count==15)
            for _,id in ipairs({98471,98977,98983}) do
                assert(ns.pickupPolicy.hidden[id], 'Missing new Forever event quest '..id)
            end
            quests[999999]={zoneOrSort=-25} -- permanent battleground category
            assert(ns.test.Eligible(999999,player),'Ordinary battleground quests were treated as holidays')
        """)

    def test_greeting_and_detail_restore_real_offers_without_inventing_absence(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={startedBy={{10}}}
            quests[2]={startedBy={{10}}}
            quests[9265]={startedBy={{10}}}; completed[9265]=true
            UnitGUID=function() return 'Creature-0-1-0-0-10-000001' end
            GetQuestID=function() return 9265 end
            Fire('QUEST_DETAIL'); Tick(100)
            local pin=WorldMapFrame.pins[1]
            assert(pin.quests[1] and pin.quests[2],'Single detail dialog hid unrelated quests')
            assert(pin.quests[9265] and pin.quests[9265].confirmed,'Explicit repeatable/event offer was ignored')
            GetNumAvailableQuests=function() return 1 end
            GetAvailableQuestInfo=function() return 'Real offer',8,false,0,9265 end
            Fire('QUEST_GREETING'); Tick(100)
            pin=WorldMapFrame.pins[1]
            assert(pin.quests[9265] and not pin.quests[1] and not pin.quests[2])
            pin:GetScript('OnEnter')(pin)
            assert(QuestLiteTooltip.lines[2]:find('Available',1,true))
        """)

    def test_profession_ranks_specialization_reputation_and_wide_masks(self):
        self.check("""
            local p={active={},skills={[164]=100},skillsKnown=true,level=22,race=5,class=2}
            local learned={[3100]=true}
            IsSpellKnown=function(id) return learned[id] or false end
            quests[900001]={requiredRanks={{164,2}}}
            assert(ns.test.Eligible(900001,p))
            quests[900001].requiredRanks={{164,3}}; assert(not ns.test.Eligible(900001,p))
            quests[900001].requiredRanks={{164,-2}}; assert(not ns.test.Eligible(900001,p))
            quests[900001]={requiredSpecialization=9788}
            assert(not ns.test.Eligible(900001,p)); learned[9788]=true
            assert(ns.test.Eligible(900001,p))
            LibQuestieDB.Enum={professionKeys={BLACKSMITHING=164},specializationKeys={BLACKSMITHING_ARMOR=9788}}
            quests[900001]={requiredSpecialization=164}
            assert(not ns.test.Eligible(900001,p)); learned[9788]=false
            assert(ns.test.Eligible(900001,p))
            quests[900001]={requiredMinRep={529,3000}}
            assert(not ns.test.Eligible(900001,p))
            C_Reputation={GetFactionDataByID=function() return {currentStanding=3000} end}
            assert(ns.test.Eligible(900001,p))
            p.race=34; quests[900001]={requiredRaces=2^33}
            assert(ns.test.Eligible(900001,p))
            p.race=5; assert(not ns.test.Eligible(900001,p))
        """)

    def test_daily_reset_changes_cache_key_without_objective_progress(self):
        self.check("""
            local serverTime,reset=1000,100
            GetServerTime=function() return serverTime end
            C_DateAndTime={GetSecondsUntilDailyReset=function() return reset end}
            local first=ns.GetMapStateKey()
            serverTime=1010; reset=90; assert(first==ns.GetMapStateKey())
            serverTime=1101; reset=86399; assert(first~=ns.GetMapStateKey())
        """)

    def test_other_hidden_policies_and_unverified_tooltip_status(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            npcs[8001]={name='Excluded giver',spawns={[12]={{80,70}}}}
            quests[787]={startedBy={{10}}} -- Known absent duplicate in reference policy
            quests[900001]={startedBy={{10}}}
            quests[900002]={startedBy={{8001}}}
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1)
            local pin=WorldMapFrame.pins[1]
            assert(not pin.quests[787] and pin.quests[900001])
            pin:GetScript('OnEnter')(pin)
            assert(QuestLiteTooltip.lines[2]:find('Pickup',1,true))
            assert(not QuestLiteTooltip.lines[2]:find('Available',1,true))
        """)

    def test_locations_drops_turnins_and_zone_filtering(self):
        self.check("""
            npcs[10]={name='Marshal',spawns={[12]={{20,30},{-1,20}},[14]={{50,50}}}}
            npcs[11]={name='Wolf',spawns={[12]={{60,70}}}}
            objects[20]={name='Chest',spawns={[12]={{40,50}}}}
            items[30]={name='Claw',npcDrops={11},objectDrops={20},itemDrops={30}}
            quests[1]={startedBy={{10}}}
            quests[2]={objectives={[3]={{30}}}}
            quests[3]={finishedBy={{10}}}
            active[1]=2; active[2]=3; done[3]=true
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1, #WorldMapFrame.pins)
            local kinds={}; for _,pin in ipairs(WorldMapFrame.pins) do
                for _,entry in pairs(pin.quests) do kinds[entry.kind]=true end
            end
            assert(kinds.pickup and kinds.turnin and not kinds.objective)
            assert(#invalidated>0)
            WorldMapFrame.mapID=1411; ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==0) -- provider override maps area 14 to 1412
            WorldMapFrame.mapID=947; ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==0)
        """)

    def test_scan_cancellation_and_bounded_pins(self):
        self.check("""
            ns.db.filterAvailable=false -- synthetic IDs overlap real holiday policy
            for i=1,1000 do
                npcs[i]={name='Dense',spawns={[12]={{i/10,(i%10)*10}}}}
                quests[i]={startedBy={{i}}}
            end
            ns.RequestMap(); Tick(200)
            assert(#WorldMapFrame.pins>0 and #WorldMapFrame.pins<=750)
            local represented={}; for _,pin in ipairs(WorldMapFrame.pins) do
                for id in pairs(pin.quests) do represented[id]=true end
            end
            for i=1,1000 do assert(represented[i], 'Missing quest '..i) end
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide(); Tick(10)
            assert(#WorldMapFrame.pins==0)
            WorldMapFrame:Show(); WorldMapFrame.mapID=1412
            WorldMapFrame.provider:OnShow(); Tick(100)
            assert(#WorldMapFrame.pins==0)
        """)

    def test_graphics_reset_reapplies_sparkles(self):
        self.check("""
            cvars.outlineModeShowLootEffectWhenDisabled='0'
            Fire('CVAR_UPDATE','graphicsQuality'); Tick(25)
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='1')
        """)

    def test_interactable_sparkle_and_combat_suspension(self):
        self.check("""
            local plate=CreateFrame()
            C_NamePlate={GetNamePlateForUnit=function() return plate end}
            UnitExists=function() return false end
            UnitIsGameObject=function() return true end
            UnitName=function() return 'Treasure Chest' end
            UnitIsInInteractRange=function() return true end
            SetUnitCursorTexture=function(texture)
                texture:SetTexture('Interface\\\\Cursor\\\\Interact'); return true
            end
            Fire('PLAYER_SOFT_INTERACT_CHANGED'); Tick(5)
            assert(cvars.SoftTargetNameplateInteract=='1')
            local animated
            for _,frame in ipairs(frames) do
                if frame.scripts.OnUpdate and frame.shown and frame.width==1 and frame.height==1 then
                    animated=frame
                end
            end
            assert(animated)
            Fire('PLAYER_REGEN_DISABLED'); combat=true
            assert(not animated:IsShown())
            local count=#writes; Tick(10); assert(#writes==count)
            combat=false; Fire('PLAYER_REGEN_ENABLED'); Tick(5)
            assert(cvars.SoftTargetNameplateInteract=='1')
            assert(animated:IsShown())
        """)

    def test_dungeon_sentinels_become_outdoor_entrances(self):
        self.check("""
            LibQuestieDB.Support.Get=function()
                return {private={areaIdToUiMapId='return {[12]=1429}',dungeons={
                    [99]={'Test Dungeon',{10099},12,{{12,50,60}}}
                }}}
            end
            assert(ns.InitDatabase())
            npcs[10]={name='Dungeon Boss',spawns={[10099]={{-1,-1}}}}
            quests[1]={startedBy={{10}}}
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1)
            local pin=WorldMapFrame.pins[1]
            assert(pin.x==.5 and pin.y==.6)
            assert(pin.quests[1].label:find('inside Test Dungeon'))
        """)

    def test_tooltip_lists_quests_and_expands_on_shift(self):
        self.check("""
            local pin=CreateFrame()
            for key,value in pairs(QuestLitePinMixin) do pin[key]=value end
            pin.Icon=pin:CreateTexture(); pin.Count=pin:CreateFontString()
            pin:OnLoad()
            local data={kind='pickup',x=.2,y=.3,quests={}}
            for i=1,20 do
                quests[i]={name='Quest '..i,questLevel=i,objectivesText={'Find things'}}
                data.quests[i]={kind='pickup',label='Giver',x=.2,y=.3}
            end
            pin:OnAcquired(data); pin:OnMouseEnter()
            assert(QuestLiteTooltip.anchor=='ANCHOR_CURSOR')
            assert(#QuestLiteTooltip.lines==21)
            assert(QuestLiteTooltip.lines[1]:find('Giver'))
            assert(QuestLiteTooltip.lines[2]:find('[1] Quest 1',1,true))
            assert(QuestLiteTooltip.lines[21]:find('[20] Quest 20',1,true))
            IsShiftKeyDown=function() return true end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',1)
            assert(QuestLiteTooltip.lines[3]=='Find things')
            pin:OnReleased(); assert(pin.data==nil)
        """)

    def test_native_mouse_events_open_and_close_tooltip(self):
        self.check("""
            npcs[10]={name='Quest giver',spawns={[12]={{20,30}}}}
            quests[1]={name='Visible Quest',questLevel=10,startedBy={{10}},objectivesText={'Quest details'}}
            ns.RequestMap(); Tick(100)
            local pin=WorldMapFrame.pins[1]
            assert(pin:GetScript('OnEnter'),'MapCanvas did not wire OnEnter from XML mouse flags')
            assert(pin:GetScript('OnLeave'),'MapCanvas did not wire OnLeave from XML mouse flags')
            pin:GetScript('OnEnter')(pin)
            assert(QuestLiteTooltip:IsShown())
            assert(QuestLiteTooltip.owner==pin)
            assert(QuestLiteTooltip.lines[2]:find('Visible Quest',1,true))
            IsShiftKeyDown=function() return true end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',1)
            assert(QuestLiteTooltip.lines[3]=='Quest details')
            pin:GetScript('OnLeave')(pin)
            assert(not QuestLiteTooltip:IsShown())
        """)

    def test_continent_projection_filter_tooltip_and_zone_cache(self):
        self.check("""
            local maps={
                [1414]={mapType=2,name='Kalimdor'},
                [1429]={mapType=3,parentMapID=1414,name='Test zone'},
                [1412]={mapType=3,parentMapID=1415,name='Other continent'},
                [1415]={mapType=2,name='Eastern Kingdoms'},
            }
            C_Map.GetMapInfo=function(id) return maps[id] end
            local calls=0
            C_Map.GetMapRectOnMap=function(id,ancestor)
                calls=calls+1
                assert(id==1429 and ancestor==1414,'Projected a zone on the wrong continent')
                return .2,.6,.1,.7
            end
            npcs[10]={name='Quest giver',spawns={[12]={{20,30},{21,30}},[14]={{50,50}}}}
            quests[1]={name='Open quest',questLevel=10,startedBy={{10}}}
            quests[2]={name='Locked quest',preQuestSingle={99},startedBy={{10}}}
            WorldMapFrame.mapID=1414
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1 and calls==1)
            local pin=WorldMapFrame.pins[1]
            assert(math.abs(pin.x-.28)<.00001 and math.abs(pin.y-.28)<.00001)
            assert(pin.quests[1] and not pin.quests[2],'Continent bypassed chain availability')
            assert(pin.quests[1].x==.2 and pin.quests[1].y==.3)
            pin:GetScript('OnEnter')(pin)
            assert(QuestLiteTooltip.lines[3]=='  Test zone')
            IsShiftKeyDown=function() return true end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',1)
            assert(QuestLiteTooltip.lines[#QuestLiteTooltip.lines]:find('20.0, 30.0',1,true))
            WorldMapFrame.mapID=1429; ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1)
            assert(WorldMapFrame.pins[1].x==.2 and WorldMapFrame.pins[1].y==.3)
            WorldMapFrame.mapID=1414; ns.RequestMap()
            assert(#WorldMapFrame.pins==1 and calls==1,'Continent snapshot did not reuse cache')
            ns.db.filterAvailable=false; ns.RequestMap(); Tick(100)
            assert(WorldMapFrame.pins[1].quests[2],'Filter toggle was ignored on continent')
        """)

    def test_continent_missing_or_invalid_geometry_never_uses_local_coordinates(self):
        self.check("""
            C_Map.GetMapInfo=function(id)
                return {mapType=id==1414 and 2 or 3,parentMapID=1414}
            end
            WorldMapFrame.mapID=1414
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={startedBy={{10}}}
            for _,projection in ipairs({
                function() end,
                function() error('unavailable geometry') end,
                function() return .6,.2,.1,.7 end,
                function() return 2,3,2,3 end,
                function() return 0/0,.6,.1,.7 end,
            }) do
                C_Map.GetMapRectOnMap=projection
                ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
                assert(#WorldMapFrame.pins==0,'Invalid geometry produced misplaced pins')
            end
        """)

    def test_repeated_events_finish_scan(self):
        self.check("""
            ns.db.filterAvailable=false
            for i=1,1000 do quests[i]={startedBy={{10}}} end
            npcs[10]={name='Questgiver',spawns={[12]={{20,30}}}}
            ns.RequestMap(); Tick(5)
            local finished=false
            for i=1,120 do
                Fire('QUEST_LOG_UPDATE'); Tick(1)
                if WorldMapFrame.pins[1] then
                    local count=0
                    for id in pairs(WorldMapFrame.pins[1].quests) do count=count+1 end
                    if count==1000 then finished=true end
                end
            end
            assert(finished,'Frequent events prevented scan completion')
        """)

    def test_hover_frame_survives_meaningful_refresh(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={name='First Quest',questLevel=10,startedBy={{10}}}
            quests[2]={name='Second Quest',questLevel=10,startedBy={{10}}}
            ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1)
            local pin=WorldMapFrame.pins[1]
            assert(pin.width==22 and pin.Count.text=='2')
            pin:OnMouseEnter()
            assert(#QuestLiteTooltip.lines==3)
            Fire('SKILL_LINES_CHANGED'); Tick(100)
            assert(WorldMapFrame.pins[1]==pin,'Refresh replaced the hovered frame')
            assert(QuestLiteTooltip.lines[2]:find('First Quest',1,true))
            assert(QuestLiteTooltip.lines[3]:find('Second Quest',1,true))
        """)

    def test_cache_reopens_without_scan_and_ignores_objective_counters(self):
        self.check("""
            local builds=0
            local original=ns.BuildMap
            ns.BuildMap=function(...) builds=builds+1; return original(...) end
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={name='First Quest',startedBy={{10}}}
            ns.RequestMap(); Tick(100); assert(builds==1)
            for i=1,100 do Fire('QUEST_LOG_UPDATE') end
            Tick(100); assert(builds==1,'Unchanged log triggered a database scan')
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            WorldMapFrame:Show(); WorldMapFrame.provider:OnShow()
            assert(#WorldMapFrame.pins==1,'Warm reopen did not restore immediately')
            Tick(100); assert(builds==1,'Warm reopen scanned the database')
            active[1]=1; Fire('QUEST_LOG_UPDATE'); Tick(100)
            assert(builds==2 and #WorldMapFrame.pins==0,'Accepted quest remained cached')
        """)

    def test_cold_scan_has_no_fixed_checkpoint_frame_delay(self):
        self.check("""
            for i=1,1000 do quests[i]={startedBy={{10}}} end
            npcs[10]={name='Questgiver',spawns={[12]={{20,30}}}}
            ns.RequestMap()
            local ticks=0
            while #WorldMapFrame.pins==0 and ticks<20 do Tick(1); ticks=ticks+1 end
            assert(ticks<=5,'Cold scan still limited to a small fixed batch per frame: '..ticks)
        """)

    def test_zone_changes_reuse_eligibility_and_cache_is_bounded(self):
        self.check("""
            local enumerations=0
            local original=LibQuestieDB.Quest.GetAllIds
            LibQuestieDB.Quest.GetAllIds=function(...) enumerations=enumerations+1; return original(...) end
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            quests[1]={startedBy={{10}}}
            ns.RequestMap(); Tick(100); assert(enumerations==1)
            for id=1500,1504 do
                WorldMapFrame.mapID=id; ns.RequestMap(); Tick(100)
            end
            assert(enumerations==1,'Changing zones repeated whole-database eligibility checks')
            local builds=0; local build=ns.BuildMap
            ns.BuildMap=function(...) builds=builds+1; return build(...) end
            WorldMapFrame.mapID=1429; ns.RequestMap(); Tick(100)
            assert(builds==1,'Oldest zone was not evicted from bounded cache')
            assert(enumerations==1)
            Fire('SKILL_LINES_CHANGED'); Tick(100)
            assert(enumerations==2,'Profession change did not invalidate eligibility')
        """)

    def test_bad_saved_variables_recover(self):
        self.check("""
            ns.db=nil; QuestLiteDB='invalid'; ns.LoadSettings()
            assert(type(ns.db)=='table' and ns.db.map==true)
        """)

    def test_legacy_settings_import_preserves_options_and_original_cvars(self):
        self.check("""
            ns.db=nil; QuestLiteDB=nil
            local legacy={map=false,showLowLevel=true,levelsBelow=12,
                savedCVars={SoftTargetInteract='2',SoftTargetInteractRange='10'}}
            ForeverGuideDB=legacy
            ns.LoadSettings()
            assert(QuestLiteDB==legacy and ForeverGuideDB==nil)
            assert(not ns.db.map and ns.db.showLowLevel and ns.db.levelsBelow==12)
            assert(ns.db.savedCVars.SoftTargetInteract=='2')
            assert(ns.db.dropChances and ns.db.minimap)
            ns.db=nil
            local existing={map=true,levelsBelow=3}
            QuestLiteDB=existing; ForeverGuideDB={map=false,levelsBelow=9}
            ns.LoadSettings()
            assert(QuestLiteDB==existing and ns.db.map and ns.db.levelsBelow==3)
            assert(ForeverGuideDB==nil,'Stale legacy settings should not be saved again')
            assert(SLASH_QUESTLITE1=='/ql' and SLASH_QUESTLITE2=='/questlite')
            assert(SLASH_QUESTLITE3=='/fg' and SLASH_QUESTLITE4=='/foreverguide')
        """)

    def test_level_filter_boundaries_unknown_levels_and_confirmed_offers(self):
        self.check("""
            ns.db.showLowLevel=false; ns.db.levelsBelow=5
            local p={active={},skills={},level=22,race=1,class=1,confirmed={}}
            for _,level in ipairs({17,22,25,26,60,0,-1}) do
                quests[900001]={questLevel=level}
                assert(ns.test.Eligible(900001,p),'Hidden in-range/scaling quest '..level)
            end
            quests[900001]={}; assert(ns.test.Eligible(900001,p))
            for _,level in ipairs({1,16}) do
                quests[900001]={questLevel=level}
                assert(not ns.test.Eligible(900001,p))
                p.confirmed[900001]=true; assert(not ns.test.Eligible(900001,p))
                ns.db.filterAvailable=false; assert(not ns.test.Eligible(900001,p))
                ns.db.showLowLevel=true; assert(ns.test.Eligible(900001,p))
                ns.db.filterAvailable=true; ns.db.showLowLevel=false; p.confirmed={}
            end
            quests[900001]={questLevel=30,requiredLevel=25}
            assert(not ns.test.Eligible(900001,p),'Quest cannot be picked up by this character')
            quests[900001]={questLevel=30,requiredLevel=22}
            assert(ns.test.Eligible(900001,p),'Higher level quest is available to this character')
            ns.db.showLowLevel=true
            quests[900001]={questLevel=1,preQuestSingle={900002}}
            assert(not ns.test.Eligible(900001,p),'Show low level quests bypassed availability')
        """)

    def test_level_settings_refresh_world_map_and_minimap_and_preserve_turnins(self):
        self.check("""
            UnitLevel=function() return 22 end
            npcs[10]={name='Giver',spawns={[12]={{20,30}}}}
            for id,level in pairs({[900001]=16,[900002]=17,[900003]=25,[900004]=26}) do
                quests[id]={questLevel=level,startedBy={{10}}}
            end
            quests[900005]={questLevel=1,finishedBy={{10}}}
            active[1]=900005; done[900005]=true
            EnableMinimapMock(); ns.InitMinimap()
            settings.showLowLevel:Change(false); settings.levelsBelow:Change(5); Tick(100)
            local function Check(expected)
                local function CheckQuests(quests)
                    for id,wanted in pairs(expected) do assert((quests[id]~=nil)==wanted,'Wrong level visibility '..id) end
                    assert(quests[900005] and quests[900005].kind=='turnin')
                end
                CheckQuests(WorldMapFrame.pins[1].quests)
                local found=false
                for _,frame in ipairs(frames) do
                    if frame.point and frame.point[2]==Minimap and frame:IsShown() and frame.data then
                        CheckQuests(frame.data.quests); found=true
                    end
                end
                assert(found,'No minimap marker')
            end
            Check({[900001]=false,[900002]=true,[900003]=true,[900004]=true})
            settings.levelsBelow:Change(6); Tick(100)
            Check({[900001]=true,[900002]=true,[900003]=true,[900004]=true})
            settings.levelsBelow:Change(0); Tick(100)
            Check({[900001]=false,[900002]=false,[900003]=true,[900004]=true})
            settings.showLowLevel:Change(true); Tick(100)
            Check({[900001]=true,[900002]=true,[900003]=true,[900004]=true})
            UnitLevel=function() return 23 end
            settings.showLowLevel:Change(false); settings.levelsBelow:Change(6)
            Fire('PLAYER_LEVEL_UP'); Tick(100)
            Check({[900001]=false,[900002]=true,[900003]=true,[900004]=true})
        """)

    def test_level_settings_saved_value_validation(self):
        self.check("""
            for _,bad in ipairs({'bad',false,-1,81,math.huge,0/0}) do
                ns.db=nil; QuestLiteDB={levelsBelow=bad,levelsAbove=bad}; ns.LoadSettings()
                assert(not ns.db.showLowLevel and ns.db.levelsBelow==5 and ns.db.levelsAbove==nil)
            end
            ns.db=nil; QuestLiteDB={levelsBelow=6.8,levelsAbove=0,showLowLevel=false}; ns.LoadSettings()
            assert(ns.db.levelsBelow==6 and ns.db.levelsAbove==nil and not ns.db.showLowLevel)
        """)

    def test_minimap_pickups_turnins_hover_and_toggle(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Nearby giver',spawns={[12]={{22,30}}}}
            npcs[11]={name='Nearby finisher',spawns={[12]={{20,32}}}}
            npcs[12]={name='Distant giver',spawns={[12]={{80,80}}}}
            quests[1]={name='Pickup',startedBy={{10}}}
            quests[2]={name='Turn-in',finishedBy={{11}}}
            quests[3]={name='Distant',startedBy={{12}}}
            quests[4]={name='Objective',objectives={[1]={{10}}}}
            active[1]=2; active[2]=4; done[2]=true
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            local count,kinds=0,{}
            for _,pin in pairs(ns.testMinimapActive) do
                count=count+1; kinds[pin.data.kind]=true
                assert(not pin.data.quests[3] and not pin.data.quests[4])
                assert(pin:GetScript('OnEnter') and pin:GetScript('OnLeave'))
                pin:GetScript('OnEnter')(pin)
                assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip.owner==pin)
                pin:GetScript('OnLeave')(pin)
                assert(not QuestLiteTooltip:IsShown())
            end
            assert(count==2 and kinds.pickup and kinds.turnin)
            settings.minimap:Change(false); Tick(10)
            assert(next(ns.testMinimapActive)==nil)
            settings.map:Change(false)
            settings.minimap:Change(true); Tick(100)
            assert(next(ns.testMinimapActive),'Minimap incorrectly depends on world-map toggle')
        """)

    def test_minimap_position_rotation_zoom_and_missing_coordinates(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='East giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            local pin=select(2,next(ns.testMinimapActive))
            assert(math.abs(pin.point[4]-14)<.001 and math.abs(pin.point[5])<.001)
            cvars.rotateMinimap='1'; miniFacing=math.pi/2; Tick(3)
            pin=select(2,next(ns.testMinimapActive))
            assert(math.abs(pin.point[4])<.001 and math.abs(pin.point[5]+14)<.001)
            miniRadius=200; Tick(3)
            pin=select(2,next(ns.testMinimapActive))
            assert(math.abs(pin.point[5]+7)<.001)
            miniPX=nil; Tick(3); assert(next(ns.testMinimapActive)==nil)
            miniPX=.2; Tick(3); assert(next(ns.testMinimapActive))
            miniMapID=1412; Fire('ZONE_CHANGED_NEW_AREA'); Tick(100)
            assert(next(ns.testMinimapActive)==nil,'Icons from old zone remained')
        """)

    def test_minimap_uses_availability_filter_without_rescanning_on_movement(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            quests[2]={requiredLevel=20,startedBy={{10}}}
            local builds=0; local build=ns.BuildMap
            ns.BuildMap=function(...) builds=builds+1; return build(...) end
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            assert(builds==1)
            local pin=select(2,next(ns.testMinimapActive))
            assert(pin.data.quests[1] and not pin.data.quests[2])
            local frameCount=#frames
            for i=1,30 do miniPX=.2+i*.0001; Tick(3) end
            assert(builds==1,'Movement caused database scans')
            assert(#frames==frameCount,'Movement allocated new marker frames instead of reusing the pool')
            settings.filterAvailable:Change(false); Tick(100)
            pin=select(2,next(ns.testMinimapActive))
            assert(pin.data.quests[1] and pin.data.quests[2])
            active[1]=1; Fire('QUEST_LOG_UPDATE'); Tick(100)
            pin=select(2,next(ns.testMinimapActive))
            assert(not pin.data.quests[1] and pin.data.quests[2])
        """)

    def test_minimap_projection_clips_round_and_square_edges(self):
        self.check("""
            local position=ns.testMinimapPosition
            local x,y=position(50,0,100,nil,70,70,false)
            assert(x==35 and y==0)
            assert(position(89,0,100,nil,70,70,false)==nil)
            assert(position(70,70,100,nil,70,70,false)==nil)
            assert(position(70,70,100,nil,70,70,true)~=nil)
            x,y=position(0,-50,100,nil,70,70,false)
            assert(x==0 and y==35)
        """)

    def test_marker_atlases_and_hover_keep_fixed_size(self):
        self.check("""
            C_Texture={GetAtlasInfo=function(name)
                if name=='QuestNormal' or name=='QuestTurnin' then return {width=32,height=32} end
            end}
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            ns.RequestMap(); Tick(100)
            local pin=WorldMapFrame.pins[1]
            assert(pin.Icon.atlas=='QuestNormal')
            pin:OnMouseEnter(); assert(pin.width==22)
            pin:OnMouseLeave(); assert(pin.width==22)
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            local mini=select(2,next(ns.testMinimapActive))
            assert(mini.Icon.atlas=='QuestNormal')
            mini:GetScript('OnEnter')(mini); assert(mini.width==18)
            mini:GetScript('OnLeave')(mini); assert(mini.width==18)
            ns.SetMarkerIcon(mini.Icon,'turnin'); assert(mini.Icon.atlas=='QuestTurnin')
            C_Texture.GetAtlasInfo=function() return nil end
            ns.SetMarkerIcon(mini.Icon,'pickup')
            assert(mini.Icon.texture=='Interface\\\\GossipFrame\\\\AvailableQuestIcon')
        """)

    def test_minimap_hover_modifier_keys_and_world_refresh_use_shared_tooltip(self):
        self.check("""
            npcs[10]={name='Nearby giver',spawns={[12]={{22,30}}}}
            quests[1]={name='Nearby quest',questLevel=10,startedBy={{10}},objectivesText={'Quest details'}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            local pin=select(2,next(ns.testMinimapActive))
            assert(pin and pin.OnMouseEnter==nil,'Minimap frame must not inherit the map pin mixin')
            pin:GetScript('OnEnter')(pin)
            assert(QuestLiteTooltip.owner==pin and #QuestLiteTooltip.lines==2)
            IsShiftKeyDown=function() return true end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',1)
            assert(QuestLiteTooltip.owner==pin and QuestLiteTooltip.lines[3]=='Quest details')
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip.owner==pin)
            assert(QuestLiteTooltip.lines[3]=='Quest details')
            IsShiftKeyDown=function() return false end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',0)
            assert(#QuestLiteTooltip.lines==2 and QuestLiteTooltip.owner==pin)
            pin:GetScript('OnLeave')(pin)
            Fire('MODIFIER_STATE_CHANGED','LCTRL',1)
            assert(not QuestLiteTooltip:IsShown())
        """)

    def test_world_map_close_does_not_dismiss_minimap_hover(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local pin=select(2,next(ns.testMinimapActive))
            pin:GetScript('OnEnter')(pin)
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            assert(QuestLiteTooltip:IsShown() and ns.IsMarkerHovered(pin))
            IsShiftKeyDown=function() return true end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',1)
            assert(QuestLiteTooltip.owner==pin)
        """)

    def test_minimap_quick_edge_exit_and_return_restores_visible_frame(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(102)
            local key,pin=next(ns.testMinimapActive)
            miniPX=-.1; Tick(1); assert(not pin:IsShown())
            miniPX=.2; Tick(1)
            assert(ns.testMinimapActive[key]==pin and pin:IsShown(),'Returning icon stayed hidden')
            Tick(12); assert(pin:IsShown(),'Stationary redraw left icon hidden')
        """)

    def test_minimap_hover_refreshes_same_id_pickup_to_turnin(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}},finishedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            local pin=select(2,next(ns.testMinimapActive))
            pin:GetScript('OnEnter')(pin)
            assert(QuestLiteTooltip.lines[2]:find('Pickup',1,true))
            active[1]=1; done[1]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            assert(QuestLiteTooltip.owner==pin and QuestLiteTooltip.lines[2]:find('Complete',1,true),
                'Hovered tooltip kept the previous quest status')
        """)

    def test_minimap_invalid_geometry_is_hidden_and_recovers(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            for _,bad in ipairs({0/0,math.huge,-math.huge}) do
                miniPX=bad; Tick(3)
                assert(next(ns.testMinimapActive)==nil,'Invalid player coordinates produced a marker')
                miniPX=.2; Tick(3); assert(next(ns.testMinimapActive))
                miniRadius=bad; Tick(3)
                assert(next(ns.testMinimapActive)==nil,'Invalid radius produced a marker')
                miniRadius=100; Tick(3); assert(next(ns.testMinimapActive))
            end
            C_Map.GetMapWorldSize=function() return math.huge,1000 end
            Tick(3); assert(next(ns.testMinimapActive)==nil)
            C_Map.GetMapWorldSize=function() return 1000,1000 end
            Tick(3); assert(next(ns.testMinimapActive))
        """)

    def test_cvar_restoration_ignores_unknown_keys_and_malformed_values(self):
        self.check("""
            cvars.unrelatedSetting='1'
            ns.db.savedCVars.unrelatedSetting='9'
            ns.db.savedCVars.SoftTargetInteract={invalid=true}
            SlashCmdList.QUESTLITE('off')
            assert(cvars.unrelatedSetting=='1','Restoration changed an unmanaged setting')
            assert(cvars.SoftTargetInteract=='3','Malformed saved value was written to the client')
            assert(cvars.SoftTargetInteractRange=='10')
        """)

    def test_inline_drop_chance_does_not_match_partial_item_names(self):
        self.check("""
            quests[1]={objectives={[3]={{100}}}}; active[1]=1
            items[100]={name='Tooth',npcDrops={10}}; Fire('QUEST_LOG_UPDATE')
            local tip=CreateFrame('GameTooltip'); tip:SetOwner(UIParent,'ANCHOR_NONE')
            AddNativeTooltipLine(tip,'0/1 Sharp Tooth')
            AddNativeTooltipLine(tip,'0/1 Tooth Fragment')
            AddNativeTooltipLine(tip,'0/1 Tooth')
            ns.testDropChances.UnitTooltip(tip,{guid='Creature-0-1-0-0-10-000001'})
            assert(tip.lines[1]=='0/1 Sharp Tooth' and tip.lines[2]=='0/1 Tooth Fragment')
            assert(tip.lines[3]=='0/1 Tooth (40%)')
        """)

    def test_earthen_echo_requires_elder_knowledge_turnin_on_both_maps(self):
        self.check("""
            UnitLevel=function() return 31 end
            npcs[9087]={name='Bashana Runetotem',spawns={[12]={{22,30}}}}
            quests[98823]={name='Earthen Echo',questLevel=31,requiredLevel=24,
                sourceItemId=287958,startedBy={{9087}}}
            -- A normal quest-provided item must not become a pickup requirement.
            quests[900001]={sourceItemId=900002,startedBy={{9087}}}
            C_Item={GetItemCount=function() return 1 end}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(wanted)
                assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[900001])
                assert((WorldMapFrame.pins[1].quests[98823]~=nil)==wanted)
                local pin=select(2,next(ns.testMinimapActive))
                assert(pin and pin.data.quests[900001])
                assert((pin.data.quests[98823]~=nil)==wanted)
            end
            Check(false)
            active[1]=95664; done[95664]=true; Fire('QUEST_LOG_UPDATE'); Tick(100); Check(false)
            completed[95664]=true; active={}
            C_Item.GetItemCount=function() return 0 end
            Fire('QUEST_TURNED_IN',95664); Tick(100); Check(true)
            completed[95664]=nil; Fire('FORCE_REFRESH'); ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100); Check(false)
            settings.filterAvailable:Change(false); Tick(100); Check(true)
            settings.filterAvailable:Change(true); Tick(100); Check(false)
            local player={active={},skills={},level=31,race=1,class=1,confirmed={[98823]=true}}
            assert(not ns.test.Eligible(98823,player),'NPC confirmation bypassed prerequisite turn-in')
            completed[95664]=true
            C_Item.GetItemCount=function() error('Restricted inventory query') end
            assert(ns.test.Eligible(98823,player),'Quest-provided relic incorrectly became a pickup requirement')
        """)

    def test_screenshot_season_class_and_chain_rules_on_both_maps(self):
        self.check("""
            UnitLevel=function() return 25 end
            UnitRace=function() return 'Undead','Scourge',5 end
            UnitClass=function() return 'Paladin','PALADIN',2 end
            UnitFactionGroup=function() return 'Horde' end
            npcs[210995]={name='Alonso',spawns={[12]={{20,30}}}}
            npcs[267214]={name="Va'xug Firefure",spawns={[12]={{22,30}}}}
            for _,id in ipairs({78132,78133,78134}) do
                quests[id]={name='Dragonslayer '..id,questLevel=25,requiredLevel=15,requiredClasses=0,startedBy={{210995}}}
            end
            quests[98251]={name='Never Coming Back',questLevel=23,requiredLevel=18,requiredClasses=0,
                requiredRaces=8589934770,startedBy={{267214}},finishedBy={{267214}}}
            quests[98252]={name='A Void Path',questLevel=23,requiredLevel=18,requiredClasses=0,
                requiredRaces=8589934770,startedBy={{267214}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local found=false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then found=true end end
                assert(found==wanted,'Wrong world map visibility '..id)
                found=false
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then found=true end end
                assert(found==wanted,'Wrong minimap visibility '..id)
            end
            for _,id in ipairs({78132,78133,78134,98252}) do Check(id,false) end
            Check(98251,true) -- A Warlock NPC does not make this Warlock-only.
            active[1]=98251; done[98251]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(98252,false); Check(98251,true) -- Ready turn-in remains visible.
            active={}; completed[98251]=true; Fire('QUEST_TURNED_IN',98251); Tick(100)
            Check(98251,false); Check(98252,true)
            settings.filterAvailable:Change(false); Tick(100)
            for _,id in ipairs({78132,78133,78134}) do Check(id,false) end -- Wrong class even in broad view.
            UnitClass=function() return 'Warrior','WARRIOR',1 end
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            for _,id in ipairs({78132,78133,78134}) do Check(id,true) end
            local classified=false
            for _,pin in ipairs(WorldMapFrame.pins) do
                if pin.quests[78132] then
                    pin:OnMouseEnter()
                    for _,line in ipairs(QuestLiteTooltip.lines) do
                        if line:find('Season of Discovery / Warrior',1,true) then classified=true end
                    end
                end
            end
            assert(classified,'Unfiltered seasonal quest was not labelled')
            settings.filterAvailable:Change(true); Tick(100)
            for _,id in ipairs({78132,78133,78134}) do Check(id,false) end
            local player={active={},skills={},level=25,race=5,class=1,confirmed={[78132]=true}}
            assert(not ns.test.Eligible(78132,player),'Confirmed offer restored unsupported SoD record')
            player.confirmed={}; player.race=1
            assert(not ns.test.Eligible(98251,player) and not ns.test.Eligible(98252,player),
                'Horde-only quest leaked for an Alliance race')
            player.confirmed={[98251]=true,[98252]=true}
            assert(not ns.test.Eligible(98251,player) and not ns.test.Eligible(98252,player),
                'Confirmed NPC offer bypassed faction restrictions')
            player.confirmed={}
            ns.db.filterAvailable=false
            assert(not ns.test.Eligible(98251,player) and not ns.test.Eligible(98252,player),
                'Broad view bypassed the faction race mask')
            ns.db.filterAvailable=true
            for _,race in ipairs({2,5,6,8,34}) do
                player.race=race
                assert(ns.test.Eligible(98252,player),'Eligible Horde race was rejected: '..race)
            end
            UnitClass=function() return 'Paladin','PALADIN',2 end
            UnitRace=function() return 'Human','Human',1 end
            UnitFactionGroup=function() return 'Alliance' end
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            Check(98251,false); Check(98252,false)
        """)

    def test_undead_paladin_chain_waits_for_each_turnin_on_both_maps(self):
        self.check("""
            UnitLevel=function() return 26 end
            UnitRace=function() return 'Undead','Scourge',5 end
            UnitClass=function() return 'Paladin','PALADIN',2 end
            UnitFactionGroup=function() return 'Horde' end
            local chain={91858,91859,91860,91861,91862,96204,95034,95036,95111,95125,95126,95140}
            npcs[10]={name='Chain giver',spawns={[12]={{22,30}}}}
            for _,id in ipairs(chain) do
                quests[id]={name='Paladin step '..id,questLevel=25,requiredLevel=20,
                    requiredClasses=2,requiredRaces=16,startedBy={{10}},finishedBy={{10}}}
            end
            quests[411]={name='Thule Ravenclaw',finishedBy={{10}}}
            active={411}; done[411]=true
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted,'Wrong world chain visibility '..id)
                assert(mini==wanted,'Wrong minimap chain visibility '..id)
            end
            for index,id in ipairs(chain) do
                for nextIndex,nextID in ipairs(chain) do Check(nextID,nextIndex==index) end
                Check(411,true)
                active={411,id}; Fire('QUEST_LOG_UPDATE'); Tick(100)
                Check(id,false)
                if chain[index+1] then Check(chain[index+1],false) end
                done[id]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
                Check(id,true) -- Ready turn-in remains visible, future pickup does not.
                if chain[index+1] then Check(chain[index+1],false) end
                completed[id]=true; active={411}; done[id]=nil
                Fire('QUEST_TURNED_IN',id); Tick(100)
                Check(id,false); Check(411,true)
            end
            completed={}; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            settings.filterAvailable:Change(false); Tick(100)
            for _,id in ipairs(chain) do Check(id,true) end
            settings.filterAvailable:Change(true); Tick(100)
            for index,id in ipairs(chain) do Check(id,index==1) end
            local player={active={},skills={},level=26,race=5,class=2,confirmed={}}
            for index=2,#chain do
                local id,previous=chain[index],chain[index-1]
                player.confirmed={[id]=true}
                assert(not ns.test.Eligible(id,player),'Confirmed offer bypassed chain '..id)
                completed[previous]=true
                assert(ns.test.Eligible(id,player),'Turn-in did not unlock '..id)
                player.class=1; assert(not ns.test.Eligible(id,player),'Wrong class accepted '..id)
                player.class=2; player.race=1
                assert(not ns.test.Eligible(id,player),'Wrong race accepted '..id)
                player.race=5; completed[previous]=nil
            end
        """)

    def test_verified_item_chain_corrections_require_turnin_not_objective_completion(self):
        self.check("""
            for _,pair in ipairs({{98823,95664},{98824,95810},{95883,95884},{95885,95883},
                {92458,92432},{92459,92458},{96984,92434},{97287,96984}}) do
                local id,previous=pair[1],pair[2]
                completed={}; done={}
                quests[id]={sourceItemId=999999}
                -- QuestieDB 1.0.13 supplies these two links natively.
                if id==95883 or id==95885 then quests[id].preQuestSingle={previous} end
                local player={active={},skills={},level=80,race=1,class=1,confirmed={[id]=true}}
                assert(not ns.test.Eligible(id,player),'Premature follow-up '..id)
                player.active[previous]=true; done[previous]=true
                assert(not ns.test.Eligible(id,player),'Objectives bypassed turn-in '..id)
                player.active[previous]=nil; completed[previous]=true
                C_Item={GetItemCount=function() return 0 end}
                assert(ns.test.Eligible(id,player),'Provided item incorrectly required for '..id)
            end
        """)

    def test_minimap_cancels_scan_when_returning_to_cached_zone(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(100)
            local original=ns.BuildMap
            local obsoleteFinished=false
            ns.BuildMap=function(id,...)
                coroutine.yield()
                if id==1412 then obsoleteFinished=true end
                return original(id,...)
            end
            miniMapID=1412; Fire('ZONE_CHANGED_NEW_AREA'); Tick(1)
            miniMapID=1429; Fire('ZONE_CHANGED_NEW_AREA'); Tick(6)
            assert(not obsoleteFinished,'Obsolete zone scan completed after returning to cached zone')
            assert(next(ns.testMinimapActive),'Returning to cached zone lost its icons')
        """)

    def test_database_scan_failures_stop_cleanly_and_explicit_refresh_recovers(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1 and next(ns.testMinimapActive))
            local original=ns.BuildMap
            local failures=0
            ns.BuildMap=function() failures=failures+1; error('Synthetic provider failure') end
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(20)
            assert(#WorldMapFrame.pins==0 and next(ns.testMinimapActive)==nil)
            assert(ns.mapStatus:find('scan stopped',1,true))
            local stoppedCount=failures
            Tick(100); assert(failures==stoppedCount,'Failed scans kept retrying every frame')
            ns.BuildMap=original; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(#WorldMapFrame.pins==1 and next(ns.testMinimapActive),'Refresh did not recover after provider failure')
        """)

    def test_minimap_group_identity_and_movement_between_range_updates(self):
        self.check("""
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); Tick(102)
            local key,pin=next(ns.testMinimapActive)
            local frameCount=#frames
            local startX=pin.point[4]
            -- One 50ms frame is shorter than the 120ms range/group interval.
            miniPX=miniPX+.0001; Tick(1)
            assert(pin.point[4]<startX,'Minimap position waited for a range/group update')
            assert(ns.testMinimapActive[key]==pin)
            pin:GetScript('OnEnter')(pin)
            for i=1,20 do
                miniPX=.2+i*.0002; Tick(3)
                assert(ns.testMinimapActive[key]==pin,'Movement changed marker group identity')
                assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip.owner==pin)
            end
            cvars.rotateMinimap='1'; miniFacing=.2; Tick(3)
            miniRadius=200; Tick(3)
            assert(ns.testMinimapActive[key]==pin and #frames==frameCount+1)
            assert(pin.width==18)
        """)

    def test_minimap_dense_hub_bounds_pool_without_losing_visible_quests(self):
        self.check("""
            ns.db.filterAvailable=false
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            local id=0
            for x=-8,8 do for y=-8,8 do
                id=id+1
                npcs[id]={name='Giver '..id,spawns={[12]={{20+x,30+y}}}}
                quests[id]={startedBy={{id}}}
            end end
            EnableMinimapMock(); GetMinimapShape=function() return 'SQUARE' end
            ns.InitMinimap(); Tick(150)
            local count,represented=0,{}
            for _,pin in pairs(ns.testMinimapActive) do
                count=count+1
                for questID in pairs(pin.data.quests) do represented[questID]=true end
            end
            assert(count<=64 and count>0)
            for questID=1,id do assert(represented[questID],'Visible quest was lost: '..questID) end
        """)


if __name__ == '__main__':
    unittest.main(verbosity=2)
