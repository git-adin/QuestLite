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
        for name in ['Core.lua', 'QuestVisibility.lua', 'Diagnostics.lua', 'AvailabilityPolicy.lua', 'AvailabilityPolicyData.lua', 'ForeverDBCorrections.lua', 'Database.lua', 'Options.lua', 'DropChances.lua', 'Map.lua', 'Minimap.lua', 'MinimapButton.lua', 'SoftTargetCleanup.lua', 'LootSparkles.lua']:
            self.lua.execute((ROOT / 'QuestLite' / name).read_text(encoding='utf-8'), 'QuestLite', self.ns)
        self.lua.globals().ns = self.ns
        self.lua.execute("Fire('ADDON_LOADED','QuestLite'); Fire('PLAYER_LOGIN')")
        self.lua.execute("ns.db.showLowLevel=true")  # Existing cases isolate availability rules.

    def check(self, code):
        self.lua.execute(code)

    def test_repeatable_blue_icons_tooltips_and_reused_mixed_groups(self):
        self.check(r"""
            npcs[10]={name='Warsong Scout',spawns={[12]={{22,30}}}}
            quests[6547]={name='Warsong Scout Update',questLevel=21,specialFlags=1,
                startedBy={{10}},finishedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(blue,turnin)
                local world=WorldMapFrame.pins[1]
                local mini=select(2,next(ns.testMinimapActive))
                assert(world and mini)
                local expected=turnin and 'ActiveQuestIcon' or 'AvailableQuestIcon'
                for _,pin in ipairs({world,mini}) do
                    assert(pin.Icon.texture=='Interface\\GossipFrame\\'..expected, 'Wrong marker glyph')
                    assert(pin.Icon.desaturated==blue,'Wrong repeatable fallback colour')
                    assert(pin.Icon.vertexColor[1]==(blue and .2 or 1),'Stale pooled marker tint')
                end
                world:OnMouseEnter()
                assert(table.concat(QuestLiteTooltip.lines,' '):find('Repeatable | ',1,true))
                mini:GetScript('OnEnter')(mini)
                assert(table.concat(QuestLiteTooltip.lines,' '):find('Repeatable | ',1,true))
                return world,mini
            end
            local world,mini=Check(true,false)
            quests[2]={name='Regular quest',specialFlags=2,startedBy={{10}},finishedBy={{10}}}
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            local updatedWorld,updatedMini=Check(false,false)
            assert(updatedWorld==world and updatedMini==mini,'Mixed refresh replaced marker frames')
            active={6547}; done[6547]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(true,true) -- Regular pickup does not override the ready turn-in.
            active={6547,2}; done[2]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(false,true)
            active={2}; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(false,true) -- Regular turn-in wins over repeatable pickup.
            local texture=CreateFrame('Texture')
            C_Texture={GetAtlasInfo=function() return {} end}
            ns.SetMarkerIcon(texture,'pickup',{[1]={kind='pickup',repeatable=true}})
            assert(texture.atlas=='Recurringavailablequesticon' and not texture.desaturated)
            ns.SetMarkerIcon(texture,'turnin',{[1]={kind='turnin',repeatable=true}})
            assert(texture.atlas=='Recurringactivequesticon' and texture.vertexColor[1]==1)
            ns.SetMarkerIcon(texture,'pickup',{[2]={kind='pickup',repeatable=false}})
            assert(texture.atlas=='QuestNormal','Reused blue marker did not restore normal atlas')
            assert(ns.GetQuestSummary(6547).repeatable and not ns.GetQuestSummary(2).repeatable)
        """)

    def test_minimap_button_opens_options_saves_drag_and_hides_independently(self):
        self.check("""
            GameTooltip=CreateFrame("GameTooltip")
            EnableMinimapMock(); ns.InitMinimapButton()
            local button=ns.testMinimapButton
            assert(button and button:IsShown() and ns.db.minimapButtonAngle==225)
            local opened=0
            Settings.OpenToCategory=function() opened=opened+1 end
            button:GetScript('OnClick')(button)
            assert(QuestLiteOptions:IsShown() and QuestLiteOptions.tab=='filters')
            button:GetScript('OnEnter')(button)
            assert(GameTooltip:IsShown() and GameTooltip:GetOwner()==button)
            button:GetScript('OnLeave')(button)
            assert(not GameTooltip:IsShown())
            Minimap.GetEffectiveScale=function() return 2 end
            Minimap.GetCenter=function() return 100,100 end
            GetCursorPosition=function() return 200,400 end
            button:GetScript('OnDragStart')(button)
            button:GetScript('OnUpdate')(button)
            assert(math.abs(ns.db.minimapButtonAngle-90)<.001)
            button:GetScript('OnDragStop')(button)
            assert(not button:GetScript('OnUpdate'))
            settings.minimapButton:Change(false)
            assert(not button:IsShown() and ns.db.minimap)
            settings.minimapButton:Change(true)
            assert(button:IsShown() and ns.db.minimapButtonAngle==90)
            button:GetScript('OnDragStart')(button)
            GetCursorPosition=function() return 0/0,400 end
            button:GetScript('OnUpdate')(button)
            assert(ns.db.minimapButtonAngle==90)
            button:GetScript('OnHide')(button)
            assert(not button:GetScript('OnUpdate'))
            ns.db=nil; QuestLiteDB.minimapButtonAngle=0/0; ns.LoadSettings()
            assert(ns.db.minimapButtonAngle==225)
        """)

    def test_main_map_options_button_standalone_and_shared_stack(self):
        self.check("""
            GameTooltip=CreateFrame('GameTooltip')
            local button=WorldMapFrame.QuestLiteOptionsButton
            assert(button and button.point[1]=='TOPLEFT')
            local opened=0
            Settings.OpenToCategory=function() opened=opened+1 end
            button:GetScript('OnClick')(button)
            assert(QuestLiteOptions:IsShown() and QuestLiteOptions.tab=='filters')
            button:GetScript('OnEnter')(button)
            assert(GameTooltip:IsShown() and GameTooltip:GetOwner()==button)
            assert(#GameTooltip.lines==2,'World map tooltip advertised minimap dragging')
            button:GetScript('OnHide')(button)
            assert(not GameTooltip:IsShown())
            local count=#frames; ns.InitMap(); assert(#frames==count)
            settings.map:Change(false); settings.minimapButton:Change(false)
            assert(WorldMapFrame.QuestLiteOptionsButton==button)
            button:GetScript('OnClick')(button); assert(QuestLiteOptions:IsShown() and QuestLiteOptions.tab=='filters')
            sharedLibrary={IsForever=true,Add=function(self,template,kind)
                assert(template==nil and kind=='Button')
                self.added=(self.added or 0)+1
                self.button=CreateFrame(kind,nil,WorldMapFrame)
                return self.button
            end}
            LibStub=function(name,silent)
                assert(name=='Krowi_WorldMapButtons-1.4' and silent)
                return sharedLibrary
            end
        """)
        self.lua.execute((ROOT / 'QuestLite/Map.lua').read_text(encoding='utf-8'), 'QuestLite', self.ns)
        self.check("""
            ns.InitMap()
            assert(sharedLibrary.added==1 and WorldMapFrame.QuestLiteOptionsButton==sharedLibrary.button)
            assert(type(sharedLibrary.button.Refresh)=='function')
            sharedLibrary.button:Refresh()
        """)

    def test_custom_options_tabs_apply_settings_and_reuse_the_window(self):
        self.check("""
            SlashCmdList.QUESTLITE('')
            local panel=QuestLiteOptions
            assert(panel:IsShown() and panel.tab=='filters' and panel.pages.filters:IsShown())
            assert(not panel.pages.map:IsShown() and not panel.pages.guide:IsShown())
            panel.checks.hidePvPQuests:SetChecked(true)
            panel.checks.hidePvPQuests:GetScript('OnClick')(panel.checks.hidePvPQuests)
            assert(ns.db.hidePvPQuests and panel.checks.hidePvPQuests:GetChecked())
            panel.plus:GetScript('OnClick')(panel.plus); assert(ns.db.levelsBelow==6)
            ns.SetOption('levelsBelow',500); assert(ns.db.levelsBelow==80)
            ns.SetOption('levelsBelow',-1); assert(ns.db.levelsBelow==0)
            ns.SetOption('levelsBelow',0/0); assert(ns.db.levelsBelow==0)
            ns.SetOption('hiddenQuests',true); assert(type(ns.db.hiddenQuests)=='table')
            panel.tabs.map:GetScript('OnClick')(panel.tabs.map)
            assert(panel.pages.map:IsShown() and not panel.pages.filters:IsShown())
            ns.SetOption('enabled',false)
            assert(not ns.db.enabled and cvars.outlineModeShowLootEffectWhenDisabled=='0')
            assert(ns.db.map and ns.db.minimap,'Sparkle option disabled unrelated features')
            local count=#frames
            panel:Hide(); SlashCmdList.QUESTLITE('')
            assert(#frames==count and QuestLiteOptions==panel,'Options leaked frames')
            assert(panel.checks.hidePvPQuests.hitRectInsets[2]<0,'Checkbox label is not clickable')
        """)

    def test_clickable_marker_guide_partial_search_and_step_drilldown(self):
        self.check("""
            npcs[10]={name='Quest giver',spawns={[12]={{22,30}}}}
            quests[1]={name='Rock collection',preQuestSingle={2},startedBy={{10}}}
            quests[2]={name='Meet the ogres',startedBy={{10}}}
            ns.db.filterAvailable=false; ns.RequestMap(); Tick(120)
            local pin=WorldMapFrame.pins[1]
            pin:GetScript('OnMouseUp')(pin,'LeftButton')
            assert(QuestLiteQuestPicker.viewing and #QuestLiteQuestPicker.ids==2)
            for _,button in ipairs(QuestLiteQuestPicker.rows) do
                if button.questID==1 then button:GetScript('OnClick')(button); break end
            end
            local panel=QuestLiteOptions
            assert(panel.tab=='guide' and panel.selected==1 and not next(ns.db.hiddenQuests))
            assert(panel.rows[1].button.questID==2 and panel.rows[1].detail.text:find('Quest giver',1,true))
            panel.rows[1].button:GetScript('OnClick')(panel.rows[1].button)
            assert(panel.selected==2 and panel.guideInfo.text:find('No missing quest',1,true))
            panel.search:SetText('collection'); panel.search:GetScript('OnEnterPressed')(panel.search)
            assert(panel.selected==1,'Partial-name lookup failed')
            completed[2]=true; Fire('QUEST_TURNED_IN',2)
            assert(not panel.rows[1].button:IsShown(),'Visible guide did not refresh after turn-in')
            panel.search:SetText('|Hquest:1:10|h[Rock collection]|h')
            panel.search:GetScript('OnEnterPressed')(panel.search)
            assert(panel.selected==1,'Pasted quest link lookup failed')
            panel.search:SetText('no such quest'); panel.search:GetScript('OnEnterPressed')(panel.search)
            assert(not panel.selected and panel.guideInfo.text:find('No matching',1,true))
            EnableMinimapMock(); ns.InitMinimap(); Tick(120)
            local mini=select(2,next(ns.testMinimapActive))
            mini.data={quests={[1]={kind='pickup'}}}
            mini:GetScript('OnMouseUp')(mini,'LeftButton')
            assert(panel.selected==1,'Minimap click did not open guide')
        """)

    def test_guide_search_and_route_pages_are_bounded_and_alternatives_stay_choices(self):
        self.check("""
            for id=1,30 do quests[id]={name='Many matches '..id} end
            ns.OpenOptions('guide'); local panel=QuestLiteOptions
            panel.search:SetText('many matches'); panel.search:GetScript('OnEnterPressed')(panel.search)
            assert(#panel.results==20 and panel.more and #panel.rows==4)
            assert(panel.next:IsShown()); panel.next:GetScript('OnClick')(panel.next)
            assert(panel.page==2)
            local count=#frames
            for i=1,5 do ns.OpenOptions('guide') end
            assert(#frames==count,'Search allocated more UI rows')
            quests[100]={name='Choose a path',preQuestSingle={101,102}}
            quests[101]={name='First path',preQuestSingle={103}}
            quests[102]={name='Second path',preQuestSingle={104}}
            quests[103]={name='Earlier first'}; quests[104]={name='Earlier second'}
            ns.OpenQuestGuide(100)
            local hints,steps=ns.GetPrerequisiteHints(100)
            assert(#steps==2 and steps[1].alternative and steps[2].alternative,
                'Mutually alternative branches expanded as cumulative steps')
            local chosen=panel.rows[1].button.questID
            panel.rows[1].button:GetScript('OnClick')(panel.rows[1].button)
            assert(panel.selected==chosen and panel.rows[1].button:IsShown())
            local before=panel.selected
            panel.back:GetScript('OnClick')(panel.back)
            assert(panel.selected==nil and #panel.results==20)
        """)

    def test_betrayed_requires_current_offer_without_inventing_a_level_or_chain(self):
        self.check("""
            UnitLevel=function() return 45 end
            UnitRace=function() return 'Orc','Orc',2 end
            UnitFactionGroup=function() return 'Horde' end
            npcs[4485]={name='Belgrom Rockmaul',spawns={[12]={{22,30}}}}
            quests[3504]={name='Betrayed',requiredLevel=44,questLevel=53,requiredRaces=2,
                startedBy={{4485}},finishedBy={{4485}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local function Check(wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[3504] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[3504] then mini=true end end
                assert(world==wanted and mini==wanted,'Betrayed availability differs between maps')
            end
            Check(false)
            settings.filterAvailable:Change(false); Tick(120); Check(true)
            settings.filterAvailable:Change(true); Tick(120); Check(false)
            UnitGUID=function() return 'Creature-0-1-0-0-4485-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {{questID=3504}} end}
            Fire('GOSSIP_SHOW'); Tick(120); Check(true)
            local player={active={},skills={},level=45,race=1,class=1,confirmed={[3504]=true}}
            assert(not ns.test.Eligible(3504,player),'Offer bypassed Horde restriction')
            C_GossipInfo.GetAvailableQuests=function() return {} end
            Fire('GOSSIP_SHOW'); Tick(120); Check(false)
            active={3504}; done[3504]=true; Fire('QUEST_LOG_UPDATE'); Tick(120); Check(true)
            assert(quests[3504].requiredLevel==44 and quests[3504].questLevel==53)
            assert(not quests[3504].preQuestSingle and not quests[3504].preQuestGroup)
        """)

    def test_quest_guide_and_details_distinguish_pickup_level_from_difficulty(self):
        self.check("""
            quests[3504]={name='Betrayed',requiredLevel=44,questLevel=53}
            local description=ns.GetQuestLevelDescription(3504)
            assert(description=='Quest level 53 | Minimum pickup level: 44')
            ns.OpenQuestGuide(3504)
            local info=QuestLiteOptions.guideInfo.text
            assert(info:find(description,1,true) and info:find('Availability is unverified',1,true))
            for _,bodyOnly in ipairs({true,false}) do
                local tooltip=CreateFrame('GameTooltip')
                tooltip:SetOwner(UIParent,'ANCHOR_NONE')
                ns.ShowQuestDetails(tooltip,3504,bodyOnly)
                local text=table.concat(tooltip.lines,' ')
                assert(text:find(description,1,true) and text:find('current NPC offer',1,true))
            end
            quests[900001]={name='Unknown minimum',questLevel=53,requiredLevel=0}
            assert(ns.GetQuestLevelDescription(900001):find('Minimum pickup level: unknown',1,true))
        """)

    def test_zone_wide_starters_use_destinations_on_both_maps_and_keep_item_requirement(self):
        self.check("""
            npcs[10]={name='Source creature',spawns={[12]={{70,70}}}}
            npcs[11]={name='Homing robot',spawns={[12]={{22,30}}}}
            objects[12]={name='Crystal',spawns={[12]={{23,30}}}}
            items[20]={name='Beacon',npcDrops={10}}
            for _,id in ipairs({351,485,635,2766}) do
                quests[id]={name='Zone drop '..id,questLevel=10,startedBy={{},{},{20}},
                    finishedBy=id==635 and {{},{12}} or {{11}}}
            end
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local function Check(wanted,ready)
                for _,id in ipairs({351,485,635,2766}) do
                    local world,mini=false,false
                    for _,pin in ipairs(WorldMapFrame.pins) do
                        local entry=pin.quests[id]
                        if entry then
                            world=true
                            assert(entry.x<.3 and entry.label~='Source creature')
                            assert(entry.kind==(ready and 'turnin' or 'pickup'))
                            assert(ready and entry.dropStarter==nil or not ready and entry.dropStarter=='destination')
                            pin:OnMouseEnter()
                            local text=table.concat(QuestLiteTooltip.lines,' ')
                            if not ready then
                                assert(text:find('Item quest destination',1,true))
                                assert(text:find('obtain the zone-wide quest-starting drop first',1,true))
                                assert(not text:find('Possible source area',1,true))
                            end
                        end
                    end
                    for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                    assert(world==wanted and mini==wanted,'Zone-drop destination differs between maps')
                end
            end
            Check(true)
            -- The robot not offering the quest must not hide a reference destination.
            UnitGUID=function() return 'Creature-0-1-0-0-11-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {} end}
            Fire('GOSSIP_SHOW'); Tick(120); Check(true)
            settings.itemDropLocations:Change(false); Tick(120); Check(false)
            settings.itemDropLocations:Change(true); Tick(120); Check(true)
            for _,id in ipairs({351,485,635,2766}) do ns.SetQuestHidden(id,true) end
            Tick(120); Check(false)
            for _,id in ipairs({351,485,635,2766}) do ns.SetQuestHidden(id,false) end
            Tick(120); Check(true)
            active={351,485,635,2766}; Fire('QUEST_LOG_UPDATE'); Tick(120); Check(false)
            for _,id in ipairs(active) do done[id]=true end
            settings.itemDropLocations:Change(false); Tick(120); Check(true,true)
        """)

    def test_zone_drop_destination_does_not_follow_player_or_reselect_sources_on_refresh(self):
        self.check("""
            npcs[10]={name='Source',spawns={[12]={{20,30},{35,30},{70,30}}}}
            npcs[11]={name='Homing robot',spawns={[12]={{22,30}}}}
            items[20]={name='Beacon',npcDrops={10}}
            quests[2766]={name='Find OOX-22/FE!',startedBy={{},{},{20}},finishedBy={{11}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local function Check(visible)
                local seen=false
                for _,pin in pairs(ns.testMinimapActive) do
                    local entry=pin.data.quests[2766]
                    if entry then
                        seen=true
                        assert(entry.x==.22 and entry.y==.3 and entry.dropStarter=='destination')
                        assert(entry.label=='Homing robot')
                    end
                end
                assert(seen==visible,'Destination visibility did not follow its actual range')
                for _,pin in ipairs(WorldMapFrame.pins) do
                    if pin.quests[2766] then assert(pin.quests[2766].x==.22) end
                end
            end
            Check(true)
            miniPX=.21; Tick(10); Check(true)
            miniPX=.35; Tick(10); Check(false)
            miniPX=.70; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(120); Check(false)
            miniPX=.20; Tick(10); Check(true)
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(120); Check(true)
        """)

    def test_zone_drop_missing_finisher_falls_back_and_ordinary_drops_keep_sources(self):
        self.check("""
            npcs[10]={name='Source',spawns={[12]={{22,30}}}}
            items[20]={name='Starter',npcDrops={10}}
            quests[2766]={name='Missing destination',startedBy={{},{},{20}}}
            quests[900001]={name='Ordinary item quest',startedBy={{},{},{20}},finishedBy={{10}}}
            ns.RequestMap(); Tick(120)
            for _,id in ipairs({2766,900001}) do
                local entry=WorldMapFrame.pins[1].quests[id]
                assert(entry and entry.dropStarter==true and entry.label=='Starter')
            end
        """)

    def test_craftsmans_writ_requires_item_and_uses_delivery_reference_on_both_maps(self):
        self.check("""
            npcs[8379]={name='Archmage Xylem',spawns={[12]={{22,30}}}}
            items[264116]={name="Craftsman's Writ: Potion of Demonslaying"}
            quests[94316]={name="Craftsman's Writ: Potion of Demonslaying",questLevel=60,requiredLevel=1,
                startedBy={{8379},{},{264116}},finishedBy={{8379}},specialFlags=1}
            local owned=0
            C_Item={GetItemCount=function(id,includeBank)
                assert(id==264116 and includeBank==false)
                return owned
            end}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local function Check(wanted,ready)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do
                    local entry=pin.quests[94316]
                    if entry then
                        world=true
                        assert(entry.kind==(ready and 'turnin' or 'pickup'))
                        assert(ready and entry.dropStarter==nil or not ready and entry.dropStarter=='writ')
                        pin:OnMouseEnter()
                        local text=table.concat(QuestLiteTooltip.lines,' ')
                        if not ready then assert(text:find('Use writ',1,true) and text:find('use the writ item',1,true)) end
                    end
                end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[94316] then mini=true end end
                assert(world==wanted and mini==wanted,'Writ ownership mismatch between maps')
            end
            Check(false)
            owned=1; Fire('BAG_UPDATE_DELAYED'); Tick(120); Check(true)
            UnitGUID=function() return 'Creature-0-1-0-0-8379-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {} end}
            Fire('GOSSIP_SHOW'); Tick(120); Check(true)
            owned=0; Fire('BAG_UPDATE_DELAYED'); Tick(120); Check(false)
            ns.db.filterAvailable=false; ns.RequestMap(); Tick(120); Check(true)
            ns.db.filterAvailable=true; active={94316}; done[94316]=true
            ns.db.itemDropLocations=false; Fire('QUEST_LOG_UPDATE'); Tick(120); Check(true,true)
        """)

    def test_writ_unknown_inventory_is_not_an_available_pickup_and_other_quests_are_unchanged(self):
        self.check("""
            quests[94316]={startedBy={{8379},{},{264116}},requiredLevel=1}
            quests[900001]={startedBy={{8379},{},{264116}},sourceItemId=264116,requiredLevel=1}
            local player={level=60,race=96,class=3,active={},skills={}}
            C_Item={GetItemCount=function() error('Unavailable inventory') end}
            assert(not ns.test.Eligible(94316,player))
            assert(ns.test.Eligible(900001,player),'Generic mixed giver or provided item was reclassified')
            C_Item.GetItemCount=function() return 1 end
            assert(ns.test.Eligible(94316,player))
            assert(ns.test.Eligible(900001,player))
        """)

    def test_next_chain_merges_native_links_and_reverse_requirements_without_wrong_branches(self):
        self.check("""
            npcs[10]={name='Next giver',spawns={[12]={{22,30}}}}
            quests[1]={name='Current',nextQuestInChain=2}
            quests[2]={name='Explicit and reverse',preQuestSingle={1},startedBy={{10}}}
            quests[3]={name='Group branch',preQuestGroup={1,90},startedBy={{10}}}
            quests[4]={name='Alternative branch',preQuestSingle={1,91},startedBy={{10}}}
            quests[5]={name='Wrong class',preQuestSingle={1},requiredClasses=8}
            quests[6]={name='Wrong race',preQuestSingle={1},requiredRaces=2}
            quests[7]={name='Native single wins',preQuestSingle={90},preQuestGroup={1}}
            quests[8]={name='Grandchild only',preQuestSingle={2}}
            quests[9]={name='Unrelated'}
            quests[95183]={name='Local fallback rock',startedBy={{10}}}
            ns.chainPrerequisiteOverrides[95183]={1}
            local steps,more=ns.GetNextChainSteps(1)
            assert(#steps==4 and not more)
            local expected={2,3,4,95183}
            for index,entry in ipairs(steps) do
                assert(entry.id==expected[index] and entry.location:find('Next giver',1,true))
                assert(entry.action=='Follow-up')
            end
            quests[95183].preQuestSingle={90}
            assert(#ns.GetNextChainSteps(1)==3,'New native gate did not replace local fallback')
            active={2}; done[2]=true; completed[3]=true
            steps=ns.GetNextChainSteps(1)
            assert(steps[1].action=='Turn in' and steps[2].action=='Completed')
            assert(quests[2].preQuestSingle[1]==1 and #quests[3].preQuestGroup==2)
        """)

    def test_next_chain_ui_switches_drills_down_pages_and_handles_terminal_quests(self):
        self.check("""
            quests[1]={name='Start',nextQuestInChain=2}
            for id=2,26 do quests[id]={name='Branch '..id,preQuestSingle={1}} end
            quests[30]={name='End',preQuestSingle={2}}
            ns.OpenQuestGuide(1)
            local panel=QuestLiteOptions
            assert(panel.guideMode=='next' and #panel.chainSteps==20 and panel.chainMore)
            assert(panel.rows[1].button.questID==2 and panel.guideModes.next:IsShown())
            assert(panel.guideModes.next.text:find('|cffffd100',1,true))
            assert(panel.next:IsShown()); panel.next:GetScript('OnClick')(panel.next)
            assert(panel.page==2 and panel.rows[1].button.questID==6)
            panel.previous:GetScript('OnClick')(panel.previous)
            panel.rows[1].button:GetScript('OnClick')(panel.rows[1].button)
            assert(panel.selected==2 and panel.guideMode=='next' and panel.rows[1].button.questID==30)
            panel.guideModes.prereqs:GetScript('OnClick')(panel.guideModes.prereqs)
            assert(panel.rows[1].button.questID==1)
            panel.guideModes.next:GetScript('OnClick')(panel.guideModes.next)
            panel.rows[1].button:GetScript('OnClick')(panel.rows[1].button)
            assert(panel.selected==30 and panel.guideInfo.text:find('No known follow-up',1,true))
            assert(not panel.rows[1].button:IsShown())
            local count=#frames
            for i=1,5 do ns.OpenQuestGuide(1) end
            assert(#frames==count and #panel.rows==4,'Chain navigation allocated unbounded UI')
            active={2}; Fire('QUEST_LOG_UPDATE')
            assert(panel.chainSteps[1].action=='In quest log','Visible chain state did not refresh')
            done[2]=true; Fire('QUEST_LOG_UPDATE')
            assert(panel.chainSteps[1].action=='Turn in')
            completed[3]=true; Fire('QUEST_TURNED_IN',3)
            assert(panel.chainSteps[2].action=='Completed','Turn-in did not invalidate the guide cache')
        """)

    def test_step_one_rock_waits_for_might_makes_right_turnin_on_both_maps(self):
        self.check("""
            npcs[259988]={name='Gorgegut',spawns={[12]={{22,30}}}}
            npcs[263440]={name='Hamur',spawns={[12]={{24,30}}}}
            npcs[255829]={name='Clugfist',spawns={[12]={{26,30}}}}
            quests[95420]={name='Land of Giants',startedBy={{255829}},finishedBy={{255829}}}
            quests[95424]={name='Might Makes Right',startedBy={{255829}},finishedBy={{255829}},preQuestSingle={95420}}
            quests[95183]={name='Step One: Rock',startedBy={{259988,263440}},finishedBy={{263440}}}
            quests[96026]={name='Step Two: More Rock',startedBy={{263440}},preQuestSingle={95183}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local function Check(wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[95183] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[95183] then mini=true end end
                assert(world==wanted and mini==wanted,'Ogre introduction gating differs between maps')
            end
            Check(false)
            active={95420}; done[95420]=true; Fire('QUEST_LOG_UPDATE'); Tick(120); Check(false)
            local hints=table.concat(ns.GetPrerequisiteHints(95183),' ')
            assert(hints:find('Land of Giants',1,true) and hints:find('Clugfist',1,true))
            local player={active={},skills={},level=60,race=96,class=3,confirmed={[95183]=true}}
            assert(not ns.test.Eligible(95183,player),'Confirmed offer bypassed mandatory introduction')
            active={95424}; completed[95420]=true; Fire('QUEST_TURNED_IN',95420); Tick(120); Check(false)
            hints=table.concat(ns.GetPrerequisiteHints(95183),' ')
            assert(hints:find('Might Makes Right',1,true) and hints:find('Clugfist',1,true))
            done[95424]=true; Fire('QUEST_LOG_UPDATE'); Tick(120); Check(false)
            assert(not ns.test.Eligible(95183,player),'Confirmed offer bypassed unturned Might Makes Right')
            active={}; completed[95424]=true; Fire('QUEST_TURNED_IN',95424); Tick(120); Check(true)
            assert(not ns.test.Eligible(96026,player),'Second rock quest unlocked before first turn-in')
            completed[95420]=nil; completed[95424]=nil; active={95183}; done[95183]=true; Fire('QUEST_LOG_UPDATE'); Tick(120)
            Check(true) -- Ready turn-in remains visible even with an absent legacy prerequisite flag.
            active={}; done={}; ns.db.filterAvailable=false; ns.RequestMap(); Tick(120); Check(true)
            quests[95183].preQuestSingle={123}; completed[123]=true; ns.db.filterAvailable=true
            assert(ns.test.Eligible(95183,player),'Fallback overruled newer native requirement')
        """)

    def test_prerequisite_guidance_uses_faction_route_pickup_or_turnin_and_name_lookup(self):
        self.check("""
            npcs[10]={name='Kreza Darkthorn',spawns={[12]={{59.8,46.0}}}}
            npcs[11]={name='Friz Frazzlespark',spawns={[12]={{77.1,52.9}}}}
            npcs[12]={name='Watcher Cornelius',spawns={[12]={{59.5,63.9}}}}
            quests[93788]={name='Borrowed Blades',startedBy={{10}}}
            quests[93976]={name='The Goblin Trader',requiredRaces=8589934770,startedBy={{10}},finishedBy={{11}}}
            quests[94925]={name='A Fur Trade',startedBy={{12}}}
            quests[94928]={name='A Few Furs for Friz',requiredRaces=4294967373,startedBy={{12}},finishedBy={{11}}}
            quests[95288]={name="Smuggler's Paradise"}
            UnitRace=function() return 'Skyborne','Skyborne',96 end
            local lines=ns.GetPrerequisiteHints(95288)
            local text=table.concat(lines,' ')
            assert(#lines==2 and lines[1]:find('Borrowed Blades',1,true) and lines[2]:find('The Goblin Trader',1,true))
            assert(text:find('Kreza Darkthorn',1,true) and text:find('59.8, 46.0',1,true))
            assert(not text:find('A Few Furs',1,true),'Opposite faction branch suggested')
            completed[93788]=true; active={93976}; done[93976]=true
            text=table.concat(ns.GetPrerequisiteHints(95288),' ')
            assert(text:find('Turn in',1,true) and text:find('Friz Frazzlespark',1,true))
            completed[93976]=true; active={}
            assert(#ns.GetPrerequisiteHints(95288)==0,'Completed lead still listed')
            completed[93976]=nil; completed[93788]=nil
            UnitRace=function() return 'Skyborne','Skyborne',95 end
            text=table.concat(ns.GetPrerequisiteHints(95288),' ')
            assert(text:find('A Fur Trade',1,true) and text:find('A Few Furs for Friz',1,true))
            assert(not text:find('The Goblin Trader',1,true))
            messages={}; SlashCmdList.QUESTLITE("prereq Smuggler's Paradise")
            assert(table.concat(messages,' '):find('Watcher Cornelius',1,true))
            local tip=CreateFrame('GameTooltip'); tip.lines={}
            ns.ShowQuestDetails(tip,95288,true)
            assert(table.concat(tip.lines,' '):find('Missing quest turn%-ins:'))
        """)

    def test_prerequisite_guidance_bounds_cycles_and_honors_native_and_exclusive_groups(self):
        self.check("""
            quests[1]={name='First',preQuestSingle={2}}
            quests[2]={name='Second',preQuestSingle={1}}
            assert(#ns.GetPrerequisiteHints(1)<=11,'Cycle made an unbounded route')
            for id=1,30 do quests[id]={name='Step '..id,preQuestSingle={id+1}} end
            local hints=ns.GetPrerequisiteHints(1)
            assert(#hints<=11 and hints[#hints]:find('limit reached',1,true))
            quests[95288]={preQuestGroup={200,201}}
            quests[200]={name='Native first',exclusiveTo={202}}
            quests[201]={name='Native second'}
            completed[202]=true; completed[201]=true
            assert(#ns.GetPrerequisiteHints(95288)==0,'Completed exclusive alternative still listed')
            local player={active={},skills={},level=60,race=96,class=3,confirmed={[95288]=true}}
            assert(ns.test.Eligible(95288,player),'Native requirements lost precedence')
            completed[201]=nil
            hints=ns.GetPrerequisiteHints(95288)
            assert(#hints==1 and hints[1]:find('Native second',1,true))
            assert(not ns.test.Eligible(95288,player))
        """)

    def test_smugglers_paradise_requires_either_faction_lead_turned_in_and_yields_to_native(self):
        self.check("""
            quests[95288]={name="Smuggler's Paradise"}
            for _,race in ipairs({95,96}) do
                local player={active={},skills={},level=50,race=race,class=3,confirmed={[95288]=true}}
                assert(not ns.test.Eligible(95288,player),'Unintroduced character saw Smuggler pickup')
                local previous=race==96 and 93976 or 94928
                player.active[previous]=true; done[previous]=true
                assert(not ns.test.Eligible(95288,player),'Accepted/objective-ready lead bypassed turn-in')
                player.active={}; completed[previous]=true
                assert(ns.test.Eligible(95288,player),'One faction lead did not unlock Smuggler pickup')
                completed[previous]=nil; done[previous]=nil
            end
            quests[95288].preQuestSingle={123}; completed[123]=true
            local player={active={},skills={},level=50,race=96,class=3,confirmed={[95288]=true}}
            assert(ns.test.Eligible(95288,player),'Stale OR fallback overrode newer native predecessor')
            quests[95288].preQuestSingle=nil; quests[95288].preQuestGroup={123,124}
            assert(not ns.test.Eligible(95288,player),'Native AND lost second requirement')
            completed[124]=true; assert(ns.test.Eligible(95288,player))
        """)

    def test_smugglers_paradise_chain_transition_reaches_both_maps(self):
        self.check("""
            npcs[255897]={name='Friz Frazzlespark',spawns={[12]={{22,30}}}}
            quests[95288]={name="Smuggler's Paradise",startedBy={{255897}},finishedBy={{255897}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local function Check(wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[95288] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[95288] then mini=true end end
                assert(world==wanted and mini==wanted,'Smuggler chain differs between maps')
            end
            Check(false)
            active={93976}; done[93976]=true; Fire('QUEST_LOG_UPDATE'); Tick(120); Check(false)
            completed[93976]=true; active={}; Fire('QUEST_TURNED_IN',93976); Tick(120); Check(true)
            completed[93976]=nil; active={95288}; done[95288]=true; Fire('QUEST_LOG_UPDATE'); Tick(120)
            Check(true) -- Ready turn-ins are not filtered by pickup prerequisites.
            active={}; done={}; ns.db.filterAvailable=false; ns.RequestMap(); Tick(120); Check(true)
        """)

    def test_darkspear_pvp_variants_without_tags_hide_on_both_maps_and_keep_turnins(self):
        self.check("""
            local ids={98887,98888,98889,98890,98891,98893,98895,98896,98897,98898,98899,98901,
                98903,98904,98905,98906,98907,98908}
            C_QuestLog.GetQuestTagInfo=function() return {tagID=0} end
            npcs[15350]={name='Warbringer',spawns={[12]={{22,30}}}}
            for _,id in ipairs(ids) do
                quests[id]={name='Battleground quest '..id,startedBy={{15350}},finishedBy={{15350}}}
                assert(ns.IsPvPQuest(id),'Missing Darkspear variant '..id)
            end
            quests[1]={name='Ordinary quest from same NPC',startedBy={{15350}}}
            assert(not ns.IsPvPQuest(1),'NPC identity incorrectly inferred PvP')
            assert(not ns.IsPvPQuest(98913),'Unplaced care-package record classified by zone alone')
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            assert(WorldMapFrame.pins[1].quests[98890])
            ns.db.hidePvPQuests=true; ns.RequestMap(); Tick(120)
            for _,pin in ipairs(WorldMapFrame.pins) do
                assert(pin.quests[1]); for _,id in ipairs(ids) do assert(not pin.quests[id]) end
            end
            for _,pin in pairs(ns.testMinimapActive) do
                assert(pin.data.quests[1]); for _,id in ipairs(ids) do assert(not pin.data.quests[id]) end
            end
            local player={active={},skills={},level=60,race=96,class=3,confirmed={}}
            for _,strict in ipairs({true,false}) do
                ns.db.filterAvailable=strict
                for _,id in ipairs(ids) do
                    player.confirmed[id]=true
                    assert(not ns.test.Eligible(id,player),'Offer/broad shortcut restored PvP '..id)
                end
            end
            active={98890}; done[98890]=true; Fire('QUEST_LOG_UPDATE'); Tick(120)
            assert(WorldMapFrame.pins[1].quests[98890].kind=='turnin')
            active={}; done={}; Fire('QUEST_LOG_UPDATE'); Tick(120)
            ns.db.hidePvPQuests=false; ns.RequestMap(); Tick(120)
            for _,id in ipairs(ids) do assert(WorldMapFrame.pins[1].quests[id],'PvP re-enable lost '..id) end
        """)

    def test_cloth_donation_toggle_refreshes_both_maps_and_preserves_other_pickups_and_turnins(self):
        self.check("""
            npcs[10]={name='Cloth quartermaster',spawns={[12]={{22,30}}}}
            for _,id in ipairs({7791,7796,99191,99200}) do
                quests[id]={name='Donation '..id,startedBy={{10}},finishedBy={{10}}}
            end
            quests[1]={name='A cloth crafting task',startedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local key=ns.GetMapStateKey()
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Cloth toggle failed on a map '..id)
            end
            Check(7791,true); Check(7796,true); Check(99191,true); Check(99200,true)
            SlashCmdList.QUESTLITE('cloth'); Tick(120)
            assert(ns.db.hideClothQuests and ns.GetMapStateKey()~=key)
            Check(7791,false); Check(7796,false); Check(99191,false); Check(99200,false); Check(1,true)
            ns.db.filterAvailable=false
            local player={active={},skills={},level=60,race=96,class=3,confirmed={[7791]=true}}
            assert(not ns.test.Eligible(7791,player),'Broad mode or confirmed offer bypassed cloth setting')
            ns.db.filterAvailable=true
            active={7791}; done[7791]=true; Fire('QUEST_LOG_UPDATE'); Tick(120)
            Check(7791,true)
            active={}; done={}; Fire('QUEST_LOG_UPDATE'); Tick(120)
            SlashCmdList.QUESTLITE('cloth'); Tick(120)
            Check(7791,true); Check(7796,true); Check(99191,true); Check(99200,true)
        """)

    def test_pvp_pickup_option_updates_both_maps_keeps_turnins_and_rechecks_tags(self):
        self.check("""
            ns.questTagOverrides={[4]=81,[5]=41}
            local tags={[1]=41,[2]=81,[4]=41}
            C_QuestLog.GetQuestTagInfo=function(id) return tags[id] and {tagID=tags[id]} end
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            for id=1,5 do quests[id]={name='Quest '..id,startedBy={{10}},finishedBy={{10}}} end
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local key=ns.GetMapStateKey()
            local function Visible(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'PvP option failed on a map '..id)
            end
            Visible(1,true); Visible(5,true)
            SlashCmdList.QUESTLITE('pvp'); Tick(120)
            assert(ns.db.hidePvPQuests and ns.GetMapStateKey()~=key)
            Visible(1,false); Visible(2,true); Visible(3,true); Visible(4,true); Visible(5,false)
            local player={active={},skills={},level=10,race=1,class=1,confirmed={[1]=true}}
            ns.db.filterAvailable=false
            assert(not ns.test.Eligible(1,player),'Broad mode or offer bypassed PvP option')
            ns.db.filterAvailable=true
            tags[3]=41; Fire('QUEST_DATA_LOAD_RESULT',3,true); Tick(120)
            Visible(3,false)
            active={1}; done[1]=true; Fire('QUEST_LOG_UPDATE'); Tick(120)
            Visible(1,true)
            active={}; done={}; Fire('QUEST_LOG_UPDATE'); Tick(120)
            SlashCmdList.QUESTLITE('pvp'); Tick(120)
            Visible(1,true); Visible(3,true); Visible(5,true)
        """)

    def test_pvp_tag_legacy_unknown_errors_and_secret_values_are_safe(self):
        self.check("""
            ns.questTagOverrides={}
            GetQuestTagInfo=function(id) return id==1 and 41 or 81,'tag' end
            C_QuestLog.GetQuestTagInfo=nil
            assert(ns.IsPvPQuest(1) and not ns.IsPvPQuest(2))
            C_QuestLog.GetQuestTagInfo=function() return nil end
            assert(not ns.IsPvPQuest(1),'Nil modern tag was guessed from legacy data')
            C_QuestLog.GetQuestTagInfo=function() error('unavailable') end
            assert(not ns.IsPvPQuest(1))
            C_QuestLog.GetQuestTagInfo=function() return {tagID=41} end
            issecretvalue=function(value) return value==41 end
            assert(not ns.IsPvPQuest(1),'Secret tag used for a comparison')
        """)

    def test_marker_hide_and_restore_refresh_both_maps_keep_other_quests_and_turnins(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{22,30},{23,30}}}}
            quests[1]={name='Keep quest',startedBy={{10}}}
            quests[2]={name='Hide quest',startedBy={{10}},finishedBy={{10}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local pin=WorldMapFrame.pins[1]
            pin:GetScript('OnMouseUp')(pin,'RightButton')
            assert(QuestLiteQuestPicker:IsShown() and #QuestLiteQuestPicker.ids==2)
            for _,button in ipairs(QuestLiteQuestPicker.rows) do
                if button.questID==2 then button:GetScript('OnClick')(button); break end
            end
            Tick(120)
            assert(ns.db.hiddenQuests[2] and not ns.db.hiddenQuests[1])
            for _,p in ipairs(WorldMapFrame.pins) do assert(p.quests[1] and not p.quests[2]) end
            for _,p in pairs(ns.testMinimapActive) do assert(p.data.quests[1] and not p.data.quests[2]) end
            ns.db.filterAvailable=false; ns.RequestMap(); Tick(120)
            for _,p in ipairs(WorldMapFrame.pins) do assert(not p.quests[2],'Broad mode restored user-hidden quest') end
            active={2}; done[2]=true; Fire('QUEST_LOG_UPDATE'); Tick(120)
            local ready=false
            for _,p in ipairs(WorldMapFrame.pins) do if p.quests[2] then ready=true; assert(p.quests[2].kind=='turnin') end end
            assert(ready,'Manual pickup hiding removed a ready turn-in')
            active={}; done={}; Fire('QUEST_LOG_UPDATE'); Tick(120)
            SlashCmdList.QUESTLITE('hidden')
            assert(QuestLiteQuestPicker.rows[1].questID==2 and QuestLiteQuestPicker.restoring)
            QuestLiteQuestPicker.rows[1]:GetScript('OnClick')(QuestLiteQuestPicker.rows[1]); Tick(120)
            assert(not ns.db.hiddenQuests[2])
            local found=false
            for _,p in ipairs(WorldMapFrame.pins) do if p.quests[2] then found=true end end
            assert(found,'Restoring did not refresh cached markers')
            local mini=select(2,next(ns.testMinimapActive))
            mini:GetScript('OnMouseUp')(mini,'RightButton')
            assert(QuestLiteQuestPicker:IsShown(),'Minimap did not open picker')
        """)

    def test_hide_picker_pages_are_bounded_and_single_shift_click_has_undo(self):
        self.check("""
            npcs[10]={name='Crowded giver',spawns={[12]={{22,30}}}}
            for id=1,30 do quests[id]={name=string.format('Quest %02d',id),startedBy={{10}}} end
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(120)
            local pin=WorldMapFrame.pins[1]
            pin:GetScript('OnMouseUp')(pin,'RightButton')
            assert(#QuestLiteQuestPicker.rows==12 and #QuestLiteQuestPicker.ids==30)
            local nextButton
            for _,frame in ipairs(frames) do if frame.text=='Next' then nextButton=frame end end
            assert(nextButton); nextButton:GetScript('OnClick')(nextButton)
            assert(QuestLiteQuestPicker.page==2 and QuestLiteQuestPicker.rows[1].questID==13)
            local before=#frames
            pin:GetScript('OnMouseUp')(pin,'RightButton')
            assert(#frames==before,'Picker leaked frames')
            QuestLiteQuestPicker.rows[1]:GetScript('OnClick')(QuestLiteQuestPicker.rows[1]); Tick(120)
            SlashCmdList.QUESTLITE('unhide all'); Tick(120)
            assert(not next(ns.db.hiddenQuests))
            pin=WorldMapFrame.pins[1]
            pin.data={quests={[1]={kind='pickup'}}}
            IsShiftKeyDown=function() return true end
            pin:GetScript('OnMouseUp')(pin,'LeftButton'); Tick(120)
            assert(ns.db.hiddenQuests[1])
            SlashCmdList.QUESTLITE('unhide 1'); Tick(120)
            assert(not ns.db.hiddenQuests[1])
            pin=WorldMapFrame.pins[1]; pin.data={quests={[1]={kind='turnin'}}}
            pin:GetScript('OnMouseUp')(pin,'LeftButton')
            assert(not ns.db.hiddenQuests[1],'Turn-in click hid a pickup')
        """)

    def test_hidden_quest_settings_validate_persist_and_defer_map_mutation_in_combat(self):
        self.check("""
            ns.db=nil; QuestLiteDB={hiddenQuests={[635]=true,[2]=false,foo=true,[-1]=true,[1.5]=true}}
            ns.LoadSettings()
            assert(ns.db.hiddenQuests[635] and not ns.db.hiddenQuests.foo and not ns.db.hiddenQuests[2])
            assert(not ns.db.hiddenQuests[-1] and not ns.db.hiddenQuests[1.5])
            ns.db=nil; ns.LoadSettings(); assert(ns.db.hiddenQuests[635])
            npcs[10]={spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}; ns.RequestMap(); Tick(120)
            local acquire=WorldMapFrame.AcquirePin
            WorldMapFrame.AcquirePin=function(self,...) assert(not combat); return acquire(self,...) end
            combat=true; Fire('PLAYER_REGEN_DISABLED')
            ns.SetQuestHidden(1,true); Tick(120); assert(ns.db.hiddenQuests[1])
            combat=false; Fire('PLAYER_REGEN_ENABLED'); Tick(120)
            assert(#WorldMapFrame.pins==0)
            ns.SetQuestHidden(1,false); Tick(120); assert(#WorldMapFrame.pins==1)
        """)

    def test_item_drop_location_toggle_refreshes_both_maps_and_keeps_npc_turnins(self):
        self.check("""
            npcs[10]={name='Drop source',spawns={[12]={{22,30}}}}
            npcs[11]={name='Normal giver',spawns={[12]={{22,30}}}}
            items[4614]={name='Pendant of Myzrael',npcDrops={10}}
            items[100]={name='Contained starter',itemDrops={4614}}
            quests[635]={name='Crystal in the Mountains',startedBy={{},{},{4614}},finishedBy={{11}}}
            quests[2]={name='Mixed sources',startedBy={{11},{},{100}}}
            quests[3]={name='Ordinary pickup',startedBy={{11}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(150)
            local initialKey=ns.GetMapStateKey()
            local function Count(id)
                local world,mini=0,0
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=world+1 end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=mini+1 end end
                return world,mini
            end
            assert(Count(635)>0)
            SlashCmdList.QUESTLITE('drops'); Tick(150)
            assert(not ns.db.itemDropLocations and ns.GetMapStateKey()~=initialKey)
            local world,mini=Count(635); assert(world==0 and mini==0,'Drop markers survived cached refresh')
            world,mini=Count(2); assert(world>0 and mini>0,'Mixed quest lost its NPC pickup')
            world,mini=Count(3); assert(world>0 and mini>0,'Normal pickup disappeared')
            local dropReads=0; local original=LibQuestieDB.Item.npcDrops
            LibQuestieDB.Item.npcDrops=function(...) dropReads=dropReads+1; return original(...) end
            ns.BuildMap(1429,function() end,function() end)
            assert(dropReads==0,'Hidden item sources were still expanded')
            active={635}; done[635]=true; Fire('QUEST_LOG_UPDATE'); Tick(150)
            world,mini=Count(635); assert(world>0 and mini>0,'Ready turn-in hidden with drop sources')
            active={}; done={}; Fire('QUEST_LOG_UPDATE'); Tick(150)
            SlashCmdList.QUESTLITE('drops'); Tick(150)
            world,mini=Count(635); assert(world>0 and mini>0,'Re-enabled sources did not return')
        """)

    def test_item_drop_world_markers_are_bounded_without_losing_nearby_minimap_sources(self):
        self.check("""
            local coast,otherCoast={},{}
            for i=1,100 do coast[i]={20,i}; otherCoast[i]={70,i} end
            npcs[10]={name='Coastal murloc',spawns={[12]=coast}}
            npcs[11]={name='Other creature',spawns={[12]=otherCoast}}
            npcs[12]={name='Ordinary giver',spawns={[12]={{80,50}}}}
            items[1357]={name="Captain Sander's Treasure Map",npcDrops={10}}
            items[100]={name='Other starter',npcDrops={11}}
            quests[136]={name="Captain Sander's Hidden Treasure",startedBy={{},{},{1357}}}
            quests[137]={name='Other drop quest',startedBy={{},{},{100}}}
            quests[200]={name='Normal pickup',startedBy={{12}}}
            EnableMinimapMock(); miniPY=.9; ns.InitMinimap(); ns.RequestMap(); Tick(150)
            local counts={[136]=0,[137]=0,[200]=0}
            for _,pin in ipairs(WorldMapFrame.pins) do
                for id in pairs(pin.quests) do counts[id]=counts[id]+1 end
                if pin.quests[136] then
                    assert(pin.quests[136].dropStarter)
                    pin:OnMouseEnter()
                    assert(table.concat(QuestLiteTooltip.lines,' '):find('Item drop',1,true))
                end
            end
            assert(counts[136]>0 and counts[136]<=3 and counts[137]>0 and counts[137]<=3)
            assert(counts[200]==1,'Ordinary giver lost while compacting drop sources')
            local nearby=false
            for _,pin in pairs(ns.testMinimapActive) do
                if pin.data.quests[136] then nearby=true; assert(pin.data.quests[136].dropStarter) end
            end
            assert(nearby,'World-map representatives removed nearby minimap sources')
            local raw=0
            ns.BuildMap(1429,function(id,kind,label,x,y,confirmed,zone,sx,sy,drop)
                if id==136 then raw=raw+1; assert(drop) end
                if id==200 then assert(not drop,'Starter flag leaked into ordinary giver') end
            end,function() end)
            assert(raw==100,'Full source data was discarded before minimap range checks')
        """)

    def test_minimap_drop_starters_show_one_stable_in_range_source_per_quest(self):
        self.check("""
            local sources={}
            for i=1,100 do sources[i]={20+i/10,30} end
            sources[101]={80,30}
            npcs[10]={name='Murloc',spawns={[12]=sources}}
            npcs[11]={name='Regular giver',spawns={[12]={{23,32}}}}
            npcs[12]={name='Second drop source',spawns={[12]={{27,31}}}}
            items[100]={name='Treasure map',npcDrops={10}}
            items[101]={name='Other starter',npcDrops={12}}
            quests[1]={name='Treasure',startedBy={{},{},{100}}}
            quests[2]={name='Regular quest',startedBy={{11}}}
            quests[3]={name='Another drop quest',startedBy={{},{},{101}}}
            local scans=0; local original=ns.BuildMap
            ns.BuildMap=function(...) scans=scans+1; return original(...) end
            EnableMinimapMock(); ns.InitMinimap(); Tick(150)
            local function Find(id)
                local count,pin=0,nil
                for _,candidate in pairs(ns.testMinimapActive) do
                    if candidate.data.quests[id] then count=count+1; pin=candidate end
                end
                return count,pin
            end
            local count,pin=Find(1); assert(count==1,'Drop source swarm not condensed')
            assert(Find(2)==1 and Find(3)==1,'Other quests lost while compacting')
            pin:GetScript('OnEnter')(pin)
            local anchorX=pin.data.x; local scansBefore=scans
            miniPX=.245; Tick(6)
            local movedCount,moved=Find(1)
            assert(movedCount==1 and moved==pin and moved.data.x==anchorX,'Source switched despite visible anchor')
            assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip:GetOwner()==pin)
            cvars.rotateMinimap='1'; miniFacing=.5; miniRadius=120; Tick(6)
            assert(select(2,Find(1))==pin,'Rotation or zoom replaced visible source')
            cvars.rotateMinimap='0'; miniRadius=100; miniPX=.34; Tick(6)
            count,pin=Find(1)
            assert(count==1 and pin.data.x~=anchorX,'Did not replace out-of-range source')
            miniPX=.5; Tick(6); assert(Find(1)==0,'Out-of-range starter left an edge icon')
            miniPX=.8; Tick(6)
            count,pin=Find(1)
            assert(count==1 and pin.data.x==.8,'Distant local source lost to world-map reduction')
            assert(scans==scansBefore,'Movement triggered database scans')
        """)

    def test_skyborne_actual_race_ids_use_provider_masks_on_both_maps(self):
        self.check("""
            LibQuestieDB.Enum=LibQuestieDB.Enum or {}
            LibQuestieDB.Enum.raceMaskById={[1]=1,[5]=16,[95]=4294967296,[96]=8589934592}
            UnitLevel=function() return 10 end
            UnitClass=function() return 'Hunter','HUNTER',3 end
            local race=95
            UnitRace=function() return 'Skyborne','Skyborne',race end
            UnitFactionGroup=function() return race==95 and 'Alliance' or 'Horde' end
            npcs[252389]={name="Quel'ana Quickgale",friendlyToFaction='AH',spawns={[12]={{22,30}}}}
            quests[94978]={name='Taming the Beast',questLevel=10,requiredLevel=10,
                requiredClasses=4,requiredRaces=12884901888,startedBy={{252389}},finishedBy={{252389}}}
            quests[2]={name='Alliance quest',requiredRaces=4294967296,startedBy={{252389}}}
            quests[3]={name='Horde quest',requiredRaces=8589934592,startedBy={{252389}}}
            quests[94979]={name='Later taming step',requiredClasses=4,requiredRaces=12884901888,
                preQuestSingle={94978},startedBy={{252389}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Skyborne visibility wrong '..id..' race '..race)
            end
            Check(94978,true); Check(94979,false); Check(2,true); Check(3,false)
            race=96; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            Check(94978,true); Check(94979,false); Check(2,false); Check(3,true)
            for _,id in ipairs({95,96}) do
                local player={active={},skills={},level=10,race=id,class=3,confirmed={[94978]=true}}
                assert(ns.test.Eligible(94978,player),'Confirmed Skyborne hunter rejected')
                player.class=1; assert(not ns.test.Eligible(94978,player),'Wrong class admitted')
                player.class=3; player.race=1
                assert(not ns.test.Eligible(94978,player),'Non-Skyborne admitted')
            end
            settings.filterAvailable:Change(false); Tick(100)
            Check(94978,true); Check(2,false); Check(3,true)
            for _,raceID in ipairs({33,34,97}) do
                local player={active={},skills={},level=10,race=raceID,class=3}
                assert(not ns.test.Eligible(94978,player),'Bit position treated as a playable race ID')
            end
        """)

    def test_skyborne_hunter_referral_remains_valid_after_completed_pet_training(self):
        self.check("""
            UnitLevel=function() return 10 end
            UnitRace=function() return 'Skyborne','Skyborne',95 end
            UnitClass=function() return 'Hunter','HUNTER',3 end
            npcs[254084]={name='Elayaa Easewind',spawns={[12]={{22,30}}}}
            npcs[252389]={name="Quel'ana Quickgale",spawns={[12]={{24,30}}}}
            quests[94007]={name='Taming the Beast referral',requiredRaces=12884901888,requiredClasses=4,
                startedBy={{254084}},finishedBy={{252389}}}
            quests[94978]={name='Taming the Beast first tame',requiredRaces=12884901888,requiredClasses=4,
                startedBy={{252389}},finishedBy={{252389}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Wrong Hunter breadcrumb visibility '..id)
            end
            Check(94007,true); Check(94978,true) -- The referral may be skipped.
            active={94007}; done[94007]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(94007,true); Check(94978,true) -- No native restriction links the two.
            active={}; completed[94007]=true; Fire('QUEST_TURNED_IN',94007); Tick(100)
            Check(94007,false); Check(94978,true)
            completed={}; active={94978}; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(94007,true); Check(94978,false)
            local player={active={[94978]=true},skills={},level=10,race=95,class=3,confirmed={[94007]=true}}
            assert(ns.test.Eligible(94007,player),'Confirmed valid referral hidden during taming')
            player.active={}; completed[94978]=true
            assert(ns.test.Eligible(94007,player),'Completed tame incorrectly hid valid referral')
            completed[94979]=true; completed[94013]=true; completed[94050]=true
            active={}; Fire('QUEST_TURNED_IN',94978); Tick(100)
            Check(94007,true); Check(94978,false)
            settings.filterAvailable:Change(false); Tick(100)
            Check(94007,true)
            settings.filterAvailable:Change(true); Tick(100)
            Check(94007,true)
            completed={}; player.confirmed={[94978]=true}; player.active={[94007]=true}
            assert(ns.test.Eligible(94978,player),'Invented breadcrumb restriction blocked taming')
            player.active={}; assert(ns.test.Eligible(94978,player),'Referral incorrectly became mandatory')
        """)

    def test_legacy_soft_target_cleanup_restores_owned_values_and_late_sync(self):
        self.check("""
            ns.db.savedCVars={SoftTargetInteract='0',SoftTargetNameplateInteract='0',
                SoftTargetInteractRange='10',SoftTargetInteractArc='0',SoftTargetInteractOnlyInRange='1',
                SoftTargetIconGameObject='0'}
            ns.db.sparkleOre=true; ns.db.sparkleOther=true
            cvars.SoftTargetInteract='3'; cvars.SoftTargetNameplateInteract='1'
            cvars.SoftTargetInteractRange='60'; cvars.SoftTargetInteractArc='2'
            cvars.SoftTargetInteractOnlyInRange='0'; cvars.SoftTargetIconGameObject='1'
            ns.db=nil; ns.LoadSettings()
            assert(ns.db.sparkleOre==nil and ns.db.sparkleOther==nil)
            Fire('PLAYER_LOGIN')
            assert(cvars.SoftTargetInteract=='0' and cvars.SoftTargetInteractRange=='10')
            assert(cvars.SoftTargetNameplateInteract=='0' and cvars.SoftTargetIconGameObject=='0')
            assert(ns.db.savedCVars,'Originals discarded before delayed sync pass')
            cvars.SoftTargetInteract='3'; cvars.SoftTargetInteractRange='60'
            Tick(110)
            assert(cvars.SoftTargetInteract=='0' and cvars.SoftTargetInteractRange=='10')
            assert(ns.db.savedCVars==nil and cvars.outlineModeShowLootEffectWhenDisabled=='1')
            local before=#writes; Tick(200); assert(#writes==before,'Cleanup became persistent polling')
        """)

    def test_legacy_soft_target_cleanup_preserves_player_edits_and_retries_failed_writes(self):
        self.check("""
            ns.db.savedCVars={SoftTargetInteract='0',SoftTargetInteractRange='10',
                SoftTargetIconGameObject='0',unrelatedSetting='9'}
            cvars.SoftTargetInteract='2'; cvars.SoftTargetInteractRange='35'
            cvars.SoftTargetIconGameObject='1'; cvars.unrelatedSetting='1'
            local setter=C_CVar.SetCVar
            C_CVar.SetCVar=function() error('synthetic write failure') end
            ns.RestoreLegacySoftTargets(true)
            assert(cvars.SoftTargetInteract=='2' and cvars.SoftTargetInteractRange=='35')
            assert(ns.db.savedCVars.SoftTargetIconGameObject=='0','Failed restoration lost original')
            assert(cvars.unrelatedSetting=='1')
            C_CVar.SetCVar=setter; ns.RestoreLegacySoftTargets(true)
            assert(cvars.SoftTargetIconGameObject=='0' and ns.db.savedCVars==nil)
        """)

    def test_legacy_soft_target_cleanup_defers_until_combat_ends_even_with_loot_disabled(self):
        self.check("""
            ns.db.enabled=false; ns.db.savedCVars={SoftTargetInteract='0',SoftTargetNameplateInteract='0'}
            cvars.SoftTargetInteract='3'; cvars.SoftTargetNameplateInteract='1'
            combat=true; local before=#writes; Fire('PLAYER_LOGIN'); Tick(120)
            assert(#writes==before and ns.db.savedCVars)
            combat=false; Fire('PLAYER_REGEN_ENABLED')
            assert(cvars.SoftTargetInteract=='0' and cvars.SoftTargetNameplateInteract=='0')
            assert(ns.db.savedCVars==nil)
        """)

    def test_cleanup_final_pass_survives_disabling_builtin_sparkles(self):
        self.check("""
            ns.db.savedCVars={SoftTargetInteract='0'}; cvars.SoftTargetInteract='3'
            Fire('PLAYER_LOGIN')
            settings.enabled:Change(false)
            cvars.SoftTargetInteract='3'; Tick(110)
            assert(cvars.SoftTargetInteract=='0' and ns.db.savedCVars==nil)
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='0')
            ns.db.savedCVars={SoftTargetInteract=false,SoftTargetInteractRange=math.huge,
                SoftTargetInteractArc={},SoftTargetIconGameObject='SECRET',unrelatedSetting='2'}
            issecretvalue=function(value) return value=='SECRET' end
            cvars.unrelatedSetting='1'; local before=#writes
            ns.RestoreLegacySoftTargets(true)
            assert(#writes==before and ns.db.savedCVars==nil)
            assert(cvars.unrelatedSetting=='1')
        """)

    def test_walton_pickups_wait_for_delivery_and_investigation_turnins(self):
        self.check("""
            UnitLevel=function() return 18 end
            UnitRace=function() return 'Undead','Scourge',5 end
            npcs[261366]={name='Walton',spawns={[12]={{22,30}}}}
            quests[95495]={name='The Hermit Tanner',finishedBy={{261366}}}
            quests[95621]={name='Trouble in the Valley',questLevel=18,requiredLevel=14,
                requiredRaces=8589934770,startedBy={{261366}},finishedBy={{261366}}}
            quests[95508]={name='Unwelcome Guests',questLevel=18,requiredLevel=14,
                requiredRaces=8589934770,startedBy={{261366}},finishedBy={{261366}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Walton chain visibility wrong '..id)
            end
            Check(95621,false); Check(95508,false)
            active={95495}; done[95495]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(95495,true); Check(95621,false); Check(95508,false)
            completed[95495]=true; active={}; Fire('QUEST_TURNED_IN',95495); Tick(100)
            Check(95621,true); Check(95508,false)
            active={95621}; done[95621]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(95621,true); Check(95508,false)
            completed[95621]=true; active={}; Fire('QUEST_TURNED_IN',95621); Tick(100)
            Check(95621,false); Check(95508,true)
            completed={}; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            settings.filterAvailable:Change(false); Tick(100)
            Check(95621,true); Check(95508,true)
            settings.filterAvailable:Change(true); Tick(100)
            Check(95621,false); Check(95508,false)
            local player={active={},skills={},level=18,race=5,class=1,confirmed={[95621]=true,[95508]=true}}
            assert(not ns.test.Eligible(95621,player) and not ns.test.Eligible(95508,player))
        """)

    def test_foreverdb_level_corrections_are_guarded_and_used_by_both_maps(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            for id,row in pairs(ns.questFieldOverrides) do
                quests[id]={name='Observed quest '..id,questLevel=row.questLevel.was,startedBy={{10}}}
                assert(ns.GetQuestSummary(id).level==row.questLevel.value)
                assert(quests[id].questLevel==row.questLevel.was,'Provider row was mutated')
            end
            UnitLevel=function() return 15 end
            ns.db.showLowLevel=false; ns.db.levelsBelow=5
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Contains(id)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                return world and mini
            end
            assert(Contains(91732) and Contains(91723),'Updated level cutoff did not reach both maps')
            quests[91732].questLevel=6 -- A future provider changed its value again.
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(not Contains(91732),'Stale correction overrode a newer provider value')
            quests[91723].questLevel=-1
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(Contains(91723),'Scaling quest was assigned a fixed cutoff')
        """)

    def test_verified_character_mask_fallbacks_preserve_native_updates(self):
        self.check("""
            local cases={{96136,7,64},{93797,8,128},{98341,11,1024},{98404,11,1024},{98738,11,1024}}
            for _,case in ipairs(cases) do
                local id,wanted,mask=case[1],case[2],case[3]
                quests[id]={requiredClasses=0}
                for _,strict in ipairs({true,false}) do
                    ns.db.filterAvailable=strict
                    for _,confirmed in ipairs({true,false}) do
                        for _,class in ipairs({1,2,3,4,5,7,8,9,11}) do
                            local player={active={},skills={},level=60,race=96,class=class,confirmed={[id]=confirmed}}
                            assert(ns.test.Eligible(id,player)==(class==wanted),'Class fallback failed '..id..'/'..class)
                        end
                    end
                end
                assert(quests[id].requiredClasses==0,'Shared mask was mutated')
                quests[id].requiredClasses=4 -- Future native correction takes precedence.
                assert(ns.test.Eligible(id,{active={},skills={},level=60,race=96,class=3}))
                assert(not ns.test.Eligible(id,{active={},skills={},level=60,race=96,class=wanted}))
            end
            quests[8249]={requiredClasses=0,zoneOrSort=-162} -- Ravenholdt turn-in is open to all classes.
            assert(ns.test.Eligible(8249,{active={},skills={},level=60,race=96,class=3}))
        """)

    def test_compendium_race_fallback_preserves_forsaken_and_alliance_exclusions(self):
        self.check("""
            quests[1049]={requiredRaces=162,requiredLevel=28,questLevel=38}
            for _,strict in ipairs({true,false}) do
                ns.db.filterAvailable=strict
                for _,race in ipairs({1,2,3,4,5,6,7,8,95,96}) do
                    for _,class in ipairs({1,2,3,4,5,7,8,9,11}) do
                        local player={active={},skills={},level=38,race=race,class=class,confirmed={[1049]=true}}
                        local allowed=race==2 or race==6 or race==8 or race==96
                        assert(ns.test.Eligible(1049,player)==allowed,'Compendium mask failed '..race..'/'..class)
                    end
                end
            end
            assert(quests[1049].requiredRaces==162,'Shared race mask was mutated')
            quests[1049].requiredRaces=16 -- A later provider value must supersede the fallback.
            local player={active={},skills={},level=38,race=5,class=3}
            assert(ns.test.Eligible(1049,player)); player.race=96
            assert(not ns.test.Eligible(1049,player),'Stale fallback overrode new provider mask')
        """)

    def test_screenshot_pickups_respect_character_on_both_maps_and_ready_turnins(self):
        self.check("""
            npcs[259119]={name='Alaana Stormwalker',spawns={[12]={{22,30}}}}
            npcs[3978]={name='Sage Truthseeker',spawns={[12]={{22,30}}}}
            quests[96136]={name='Call of Air',requiredClasses=0,requiredRaces=8589934592,
                requiredLevel=30,questLevel=35,startedBy={{259119}},finishedBy={{259119}}}
            quests[1049]={name='Compendium of the Fallen',requiredRaces=162,requiredLevel=28,
                questLevel=38,startedBy={{3978}},finishedBy={{3978}}}
            UnitLevel=function() return 35 end
            UnitRace=function() return 'Skyborne','Skyborne',96 end
            UnitClass=function() return 'Hunter','HUNTER',3 end
            UnitFactionGroup=function() return 'Horde' end
            EnableMinimapMock(); ns.InitMinimap()
            local function Check(id,wanted)
                ns.RequestMap(nil,'FORCE_REFRESH'); Tick(120)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Character filter differs between maps '..id)
            end
            Check(96136,false); Check(1049,true)
            UnitClass=function() return 'Shaman','SHAMAN',7 end
            Check(96136,true)
            UnitRace=function() return 'Undead','Scourge',5 end
            Check(1049,false); Check(96136,false)
            active={1049}; done[1049]=true
            Check(1049,true) -- An already accepted ready turn-in remains visible.
        """)

    def test_native_prerequisite_expressions_replace_historical_fallbacks(self):
        self.check("""
            local player={active={},skills={},level=40,race=5,class=3,confirmed={[92459]=true}}
            quests[92459]={name='Friend of the Kirin Tor'}
            completed[96984]=true
            assert(not ns.test.Eligible(92459,player),'Missing native data lost legacy gate')
            quests[92459].preQuestSingle={92458,96984}
            assert(ns.test.Eligible(92459,player),'Legacy Alliance link overruled native Horde alternative')
            completed[96984]=nil; completed[92458]=true
            assert(ns.test.Eligible(92459,player),'Native Alliance alternative rejected')
            completed[92458]=nil; player.active[96984]=true; done[96984]=true
            assert(not ns.test.Eligible(92459,player),'Active alternative counted as turned in')
            quests[545]={preQuestGroup={544,93680}}
            completed[544]=true
            assert(not ns.test.Eligible(545,player),'Native AND list lost key requirement')
            completed[93680]=true
            assert(ns.test.Eligible(545,player),'Complete native AND list rejected')
            quests[92434]={preQuestSingle={545}}; completed[545]=true; completed[93680]=nil
            assert(ns.test.Eligible(92434,player),'Stale redundant key gate overrode native predecessor')
            assert(quests[92459].preQuestSingle[2]==96984 and quests[545].preQuestGroup[2]==93680)
        """)

    def test_sod_pvp_and_rekindle_quests_remain_season_restricted(self):
        self.check("""
            local player={active={},skills={},level=60,race=5,class=3,confirmed={}}
            for _,id in ipairs({79090,79098,80001}) do
                quests[id]={questLevel=25}
                player.confirmed[id]=true
                assert(not ns.test.Eligible(id,player),'SoD event restored by stale offer')
                ns.db.filterAvailable=false
                assert(ns.test.Eligible(id,player),'Broad view cannot browse labeled SoD quest')
                ns.db.filterAvailable=true
                player.confirmed[id]=nil
            end
        """)

    def test_missing_minimum_level_falls_back_without_overruling_server_offers(self):
        self.check("""
            quests[1]={questLevel=30,requiredLevel=0}
            quests[2]={questLevel=30,requiredLevel=20}
            quests[3]={questLevel=-1,requiredLevel=0}
            local player={active={},skills={},level=22,race=5,class=3}
            assert(not ns.test.Eligible(1,player),'Unknown minimum allowed a future quest')
            assert(ns.test.Eligible(2,player),'Known lower pickup level was overwritten')
            assert(ns.test.Eligible(3,player),'Scaling level became a fixed minimum')
            ns.db.showLowLevel=true
            assert(not ns.test.Eligible(1,player),'Low-level toggle bypassed minimum')
            player.confirmed={[1]=true}
            assert(ns.test.Eligible(1,player),'Actual server offer lost precedence')
            player.confirmed=nil; player.level=30
            assert(ns.test.Eligible(1,player),'Fallback did not unlock at quest level')
            player.level=22; ns.db.filterAvailable=false
            assert(ns.test.Eligible(1,player),'Broad browsing unexpectedly restricted')
        """)

    def test_missing_sulhasa_location_uses_fallback_until_provider_has_spawns(self):
        self.check("""
            UnitFactionGroup=function() return 'Horde' end
            UnitRace=function() return 'Undead','Scourge',5 end
            npcs[14242]={name='Sulhasa',friendlyToFaction='H'}
            quests[98093]={name='Field to Clear',requiredRaces=8589934770,
                startedBy={{14242}},finishedBy={{14242}}}
            LibQuestieDB.Support.Get=function()
                return {private={areaIdToUiMapId={[17]=1413,[12]=1429}}}
            end
            assert(ns.InitDatabase())
            WorldMapFrame.mapID=1413
            EnableMinimapMock(); miniMapID=1413; miniPX=.48; miniPY=.775
            ns.InitMinimap(); ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[98093])
            assert(WorldMapFrame.pins[1].x==.48 and WorldMapFrame.pins[1].y==.775)
            assert(next(ns.testMinimapActive),'Missing NPC fallback did not reach minimap')
            assert(npcs[14242].spawns==nil,'Shared NPC data was mutated')
            C_Map.GetMapInfo=function(id)
                if id==1414 then return {mapType=2,name='Kalimdor'} end
                return {mapType=3,parentMapID=1414,name='The Barrens'}
            end
            C_Map.GetMapRectOnMap=function() return .1,.9,.2,.8 end
            WorldMapFrame.mapID=1414; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(#WorldMapFrame.pins==1 and math.abs(WorldMapFrame.pins[1].x-.484)<.00001,
                'Observed fallback did not project to continent map')
            WorldMapFrame.mapID=1413
            active={98093}; done[98093]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            assert(WorldMapFrame.pins[1].quests[98093].kind=='turnin')
            npcs[14242].spawns={[17]={{49,78}}}
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].x==.49,'Fallback duplicated newer native spawn')
        """)

    def test_library_ready_turnins_route_to_character_capital_without_new_pickups(self):
        self.check("""
            npcs[211022]={name='Owen Thadd',friendlyToFaction='H',spawns={[12]={{22,30}}}}
            npcs[211033]={name='Garion Wendell',friendlyToFaction='A',spawns={[12]={{70,70}}}}
            quests[78127]={name='The Dalaran Digest',finishedBy={{211033}},startedBy={{211033}}}
            active={78127}; done[78127]=true
            UnitRace=function() return 'Undead','Scourge',5 end
            UnitFactionGroup=function() return 'Horde' end
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[78127].label=='Owen Thadd')
            assert(next(ns.testMinimapActive),'Horde library turn-in absent on minimap')
            assert(quests[78127].finishedBy[1][1]==211033,'Provider giver list was mutated')
            UnitRace=function() return 'Human','Human',1 end
            UnitFactionGroup=function() return 'Alliance' end
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[78127].label=='Garion Wendell')
            active={}; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(#WorldMapFrame.pins==0,'Turn-in correction restored hidden collection pickups')
        """)

    def test_world_map_combat_defers_cold_warm_and_zone_refreshes_but_minimap_runs(self):
        self.check("""
            local acquire,remove,removeAll=WorldMapFrame.AcquirePin,WorldMapFrame.RemovePin,WorldMapFrame.RemoveAllPinsByTemplate
            local acquired=0
            WorldMapFrame.AcquirePin=function(self,...)
                assert(not combat,'Protected map acquisition during combat')
                acquired=acquired+1; return acquire(self,...)
            end
            WorldMapFrame.RemovePin=function(self,...)
                assert(not combat,'Map release during combat'); return remove(self,...)
            end
            WorldMapFrame.RemoveAllPinsByTemplate=function(self,...)
                assert(not combat,'Map clear during combat'); return removeAll(self,...)
            end
            npcs[10]={name='First zone giver',spawns={[12]={{22,30}}}}
            npcs[11]={name='Other zone giver',spawns={[14]={{40,50}}}}
            quests[1]={startedBy={{10}}}; quests[2]={startedBy={{11}}}
            EnableMinimapMock(); ns.InitMinimap()
            combat=true; Fire('PLAYER_REGEN_DISABLED'); ns.RequestMap(); Tick(150)
            assert(acquired==0 and #WorldMapFrame.pins==0)
            assert(next(ns.testMinimapActive),'Combat gate incorrectly stopped plain minimap frames')
            combat=false; Fire('PLAYER_REGEN_ENABLED'); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[1])
            local before=acquired
            combat=true; Fire('PLAYER_REGEN_DISABLED')
            assert(not WorldMapFrame.pins[1]:IsShown())
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            WorldMapFrame:Show(); WorldMapFrame.provider:OnShow(); Tick(20)
            assert(acquired==before,'Warm cache acquired pins during combat')
            WorldMapFrame.mapID=1412; ns.RequestMap(); Fire('QUEST_LOG_UPDATE'); Tick(100)
            assert(acquired==before)
            combat=false; Fire('PLAYER_REGEN_ENABLED'); Tick(100)
            assert(#WorldMapFrame.pins==1 and WorldMapFrame.pins[1].quests[2])
        """)

    def test_combat_cancels_running_map_scan_and_hidden_map_resumes_safely(self):
        self.check("""
            npcs[10]={name='Giver',spawns={[12]={{22,30}}}}
            quests[1]={startedBy={{10}}}
            local original=ns.BuildMap; local finishes=0
            ns.BuildMap=function(...)
                coroutine.yield(); finishes=finishes+1; return original(...)
            end
            ns.RequestMap(); Tick(1)
            combat=true; Tick(10)
            assert(finishes==0 and #WorldMapFrame.pins==0,'Worker completed map publication in combat')
            WorldMapFrame:Hide(); WorldMapFrame.provider:OnHide()
            combat=false; Fire('PLAYER_REGEN_ENABLED'); Tick(10)
            assert(#WorldMapFrame.pins==0)
            WorldMapFrame:Show(); WorldMapFrame.provider:OnShow(); Tick(100)
            assert(finishes==1 and #WorldMapFrame.pins==1,'Map failed to rebuild after combat')
        """)

    def test_taint_report_only_reads_ownership_and_handles_unavailable_api(self):
        self.check("""
            SlashCmdList.QUESTLITE('taint')
            assert(messages[#messages]:find('unavailable',1,true))
            local handler=function() end; ActionButton_UpdateCooldown=handler
            MultiBarBottomRightButton2={OnEvent=handler}
            local calls=0
            issecurevariable=function(object,key)
                calls=calls+1
                if object=='ActionButton_UpdateCooldown' then return false,'ExampleAddon' end
                return true
            end
            local before=#writes
            SlashCmdList.QUESTLITE('taint')
            assert(calls>5 and #writes==before)
            assert(ActionButton_UpdateCooldown==handler and MultiBarBottomRightButton2.OnEvent==handler)
            local found=false
            for _,message in ipairs(messages) do if message:find('tainted by ExampleAddon',1,true) then found=true end end
            assert(found,'Tainted owner missing from diagnostic output')
        """)

    def test_goblin_lockpicks_is_rogue_only_on_both_maps_and_confirmed_offers(self):
        self.check("""
            UnitLevel=function() return 23 end
            UnitClass=function() return 'Hunter','HUNTER',3 end
            npcs[4086]={name='Veenix',spawns={[12]={{22,30}}}}
            quests[78270]={name='Goblin Lockpicks',questLevel=23,requiredClasses=0,
                startedBy={{4086}},finishedBy={{4086}}}
            quests[1]={name='Ordinary pickup',startedBy={{4086}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(wanted)
                local world=WorldMapFrame.pins[1]
                local mini=select(2,next(ns.testMinimapActive))
                assert(world and mini and world.quests[1] and mini.data.quests[1])
                assert((world.quests[78270]~=nil)==wanted and (mini.data.quests[78270]~=nil)==wanted)
            end
            Check(false)
            settings.filterAvailable:Change(false); Tick(100); Check(false)
            settings.filterAvailable:Change(true); Tick(100)
            UnitClass=function() return 'Rogue','ROGUE',4 end
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100); Check(true)
            WorldMapFrame.pins[1]:OnMouseEnter()
            assert(table.concat(QuestLiteTooltip.lines,' '):find('Rogue',1,true))
            for _,class in ipairs({1,2,3,5,7,8,9,11}) do
                local player={active={},skills={},level=23,race=5,class=class,confirmed={[78270]=true}}
                assert(not ns.test.Eligible(78270,player),'Wrong-class confirmed offer restored Rogue quest')
            end
            for _,race in ipairs({1,5,95,96}) do
                local player={active={},skills={},level=23,race=race,class=4}
                assert(ns.test.Eligible(78270,player),'Invented faction/chain restriction blocked Rogue')
            end
            assert(quests[78270].requiredClasses==0,'Shared provider mask was mutated')
        """)

    def test_dalaran_entry_waits_for_both_key_and_patrol_turnins_on_both_maps(self):
        self.check("""
            UnitLevel=function() return 34 end
            UnitRace=function() return 'Skyborne','Skyborne',96 end
            UnitClass=function() return 'Hunter','HUNTER',3 end
            UnitFactionGroup=function() return 'Horde' end
            npcs[2410]={name='Magus Wordeen Voidglare',spawns={[12]={{22,30}}}}
            for _,id in ipairs({544,93680,545,92434}) do
                quests[id]={name='Attunement step '..id,questLevel=34,requiredLevel=30,
                    requiredRaces=8589934770,startedBy={{2410}},finishedBy={{2410}}}
            end
            quests[545].preQuestSingle={544}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Dalaran visibility wrong '..id)
            end
            Check(545,false); Check(92434,false)
            active={544,93680}; done[544]=true; done[93680]=true
            Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(544,true); Check(93680,true); Check(545,false); Check(92434,false)
            completed[544]=true; active={93680}; Fire('QUEST_TURNED_IN',544); Tick(100)
            Check(545,false); Check(92434,false)
            completed[93680]=true; active={}; Fire('QUEST_TURNED_IN',93680); Tick(100)
            Check(545,true); Check(92434,false)
            active={545}; done[545]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(545,true); Check(92434,false)
            completed[545]=true; active={}; Fire('QUEST_TURNED_IN',545); Tick(100)
            Check(92434,true) -- No Bel'varil quest has been completed.
            local player={active={},skills={},level=34,race=96,class=3,confirmed={[545]=true,[92434]=true}}
            completed[93680]=nil
            assert(not ns.test.Eligible(545,player) and not ns.test.Eligible(92434,player),
                'Confirmed offers bypassed missing key turn-in')
            completed[93680]=true; completed[545]=nil
            player.active[545]=true
            assert(not ns.test.Eligible(92434,player),'Objectives bypassed Patrols turn-in')
            player.active={}; completed[545]=true
            C_Item={GetItemCount=function() return 0 end}
            assert(ns.test.Eligible(92434,player),'Provided Grimy Key became an inventory gate')
            ns.db.filterAvailable=false; completed={}
            assert(ns.test.Eligible(92434,player),'Broad browsing no longer permits locked quests')
            ns.db.filterAvailable=true; player.race=95
            assert(not ns.test.Eligible(92434,player),'Horde entry leaked to Alliance Skyborne')
        """)

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
            AddNativeTooltipLine(tip,'Custom item')
            AddNativeTooltipLine(tip,'Soulbound')
            AddNativeTooltipLine(tip,'Unique')
            local shown=0; tip.Show=function() shown=shown+1 end
            ns.testDropChances.ItemTooltip(tip,{id=999})
            ns.testDropChances.ItemTooltip(tip,{id=999})
            assert(table.concat(tip.lines,'|')=='Custom item|Soulbound|Unique')
            assert(shown==0 and tip.QuestLiteDropToken==nil,'Unknown rate mutated tooltip state')
            items[999].npcDrops={}
            ns.testDropChances.ItemTooltip(tip,{id=999})
            assert(#tip.lines==3 and shown==0,'Object-only item gained an empty section')
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
            assert(ns.db.sparkleOther==nil and ns.db.sparkleQuest==nil)
            assert(cvars.SoftTargetInteract=='0')
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

    def test_questie_12_11_conditional_pickups_and_new_pvp_tags(self):
        self.check("""
            local player={level=60,race=96,class=3,active={},skills={}}
            for _,id in ipairs({1374,1380,1381,78150,78917,79536,82208,93862}) do
                quests[id]={name='Conditional '..id,questLevel=60,requiredLevel=1}
                assert(ns.pickupPolicy.hidden[id] and not ns.test.Eligible(id,player))
                ns.db.filterAvailable=false; assert(ns.test.Eligible(id,player))
                ns.db.filterAvailable=true
            end
            for _,id in ipairs({98892,98894,98900,98902}) do
                quests[id]={name='Darkspear variant',questLevel=49,requiredLevel=1}
                assert(ns.IsPvPQuest(id),'New upstream PvP classification missing')
                ns.db.hidePvPQuests=true
                for _,strict in ipairs({true,false}) do
                    ns.db.filterAvailable=strict
                    assert(not ns.test.Eligible(id,player))
                end
                ns.db.hidePvPQuests=false
                assert(ns.test.Eligible(id,player))
            end
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
            p.race=96; LibQuestieDB.Enum.raceMaskById={[96]=2^33,[5]=16}
            quests[900001]={requiredRaces=2^33}
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

    def test_retired_custom_sparkles_never_enable_soft_targeting_or_poll_units(self):
        self.check("""
            assert(ns.defaults.sparkleOre==nil and ns.defaults.sparkleOther==nil)
            assert(settings.sparkleOre==nil and settings.sparkleOther==nil)
            local reads=0
            C_NamePlate={GetNamePlateForUnit=function() reads=reads+1 end}
            UnitIsGameObject=function() reads=reads+1; return true end
            local writesBefore=#writes
            Fire('PLAYER_SOFT_INTERACT_CHANGED'); Fire('NAME_PLATE_UNIT_ADDED','nameplate1'); Tick(200)
            assert(reads==0 and #writes==writesBefore,'Retired engine still polled or wrote settings')
            assert(cvars.SoftTargetInteract=='0' and cvars.SoftTargetNameplateInteract=='0')
            assert(cvars.outlineModeShowLootEffectWhenDisabled=='1')
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
            assert(#QuestLiteTooltip.lines==22)
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
            assert(#QuestLiteTooltip.lines==4)
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
            assert(QuestLiteTooltip.owner==pin and #QuestLiteTooltip.lines==3)
            IsShiftKeyDown=function() return true end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',1)
            assert(QuestLiteTooltip.owner==pin and QuestLiteTooltip.lines[3]=='Quest details')
            ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            assert(QuestLiteTooltip:IsShown() and QuestLiteTooltip.owner==pin)
            assert(QuestLiteTooltip.lines[3]=='Quest details')
            IsShiftKeyDown=function() return false end
            Fire('MODIFIER_STATE_CHANGED','LSHIFT',0)
            assert(#QuestLiteTooltip.lines==3 and QuestLiteTooltip.owner==pin)
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
            ns.db.savedCVars={unrelatedSetting='9'}
            cvars.SoftTargetInteract='3'
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
            for _,race in ipairs({2,5,6,8,96}) do
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

    def test_scout_support_and_valuable_vantages_require_turnins_on_both_maps(self):
        self.check("""
            UnitLevel=function() return 25 end
            UnitRace=function() return 'Undead','Scourge',5 end
            UnitClass=function() return 'Paladin','PALADIN',2 end
            UnitFactionGroup=function() return 'Horde' end
            npcs[2215]={name='High Executor Darthalia',spawns={[12]={{22,30}}}}
            quests[528]={name='Battle of Hillsbrad',finishedBy={{2215}}}
            quests[98094]={name='Scout Support',questLevel=25,requiredLevel=19,
                sourceItemId=279394,requiredRaces=8589934770,startedBy={{2215}},finishedBy={{2215}}}
            quests[98095]={name='Valuable Vantages',questLevel=25,requiredLevel=19,
                requiredRaces=8589934770,startedBy={{2215}},finishedBy={{2215}}}
            EnableMinimapMock(); ns.InitMinimap(); ns.RequestMap(); Tick(100)
            local function Check(id,wanted)
                local world,mini=false,false
                for _,pin in ipairs(WorldMapFrame.pins) do if pin.quests[id] then world=true end end
                for _,pin in pairs(ns.testMinimapActive) do if pin.data.quests[id] then mini=true end end
                assert(world==wanted and mini==wanted,'Scout chain visibility wrong '..id)
            end
            Check(98094,false); Check(98095,false)
            active={528}; done[528]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(528,true); Check(98094,false); Check(98095,false)
            C_Item={GetItemCount=function() return 0 end}
            UnitGUID=function() return 'Creature-0-1-0-0-2215-000001' end
            C_GossipInfo={GetAvailableQuests=function() return {} end}
            Fire('GOSSIP_SHOW'); Tick(100)
            completed[528]=true; active={}; Fire('QUEST_TURNED_IN',528); Tick(100)
            Check(98094,true); Check(98095,false)
            active={98094}; done[98094]=true; Fire('QUEST_LOG_UPDATE'); Tick(100)
            Check(98094,true); Check(98095,false)
            completed[98094]=true; active={}; Fire('QUEST_TURNED_IN',98094); Tick(100)
            Check(98094,false); Check(98095,true)
            completed={}; ns.RequestMap(nil,'FORCE_REFRESH'); Tick(100)
            settings.filterAvailable:Change(false); Tick(100)
            Check(98094,true); Check(98095,true)
            settings.filterAvailable:Change(true); Tick(100)
            Check(98094,false); Check(98095,false)
            local player={active={},skills={},level=25,race=5,class=2,confirmed={[98094]=true,[98095]=true}}
            assert(not ns.test.Eligible(98094,player) and not ns.test.Eligible(98095,player))
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
