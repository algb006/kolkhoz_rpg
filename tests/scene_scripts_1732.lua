-- Isolated authoring checks, not a host integration run or a simulation.
local ROOT = SCENE_TEST_ROOT
local checks = 0
local function check(ok, message)
  assert(ok, message)
  checks = checks + 1
end
local function fixture(file)
  local store, calls, handlers = {}, {}, {}
  local h = { extended=false, elder=42, current=nil, day=nil }
  local host = {
    story={ get=function(k) return store[k] end,
      set=function(k,v)
        check(type(v)=="string" or type(v)=="number" or type(v)=="boolean", "scalar story value")
        store[k]=v
      end },
    world={elder=function() if h.elder then return {resident=h.elder} end end},
    log=function() end,
  }
  host.script=function(key)
    h.key=key
    return {on_fact=function(f,fn) h.fact=f;handlers[f]=fn end,
      on_day=function(fn) h.day=fn end}
  end
  local function textref(ref)
    local key = type(ref)=="table" and ref[1] or ref
    check(type(key)=="string" and SCENE_TEST_KEYS[key]~=nil, "registered or explicitly proposed line key: "..tostring(key))
    local expected=SCENE_TEST_KEYS[key]
    local params=type(ref)=="table" and ref[2] or {}
    for _,name in ipairs(expected) do check(params[name]~=nil, "missing text param "..name) end
    for name in pairs(params) do
      local found=false; for _,want in ipairs(expected) do if want==name then found=true end end
      check(found,"extra text param "..name)
    end
    return key
  end
  host.say=function(r)
    for k in pairs(r) do
      check(k=="with" or k=="chairman" or k=="line" or (h.extended and k=="district_face"), "current host rejects unsupported say field")
    end
    check((r.with and 1 or 0)+(r.chairman and 1 or 0)+(r.district_face and 1 or 0)==1,"one say speaker")
    calls[#calls+1]={kind="say",key=textref(r.line),request=r}
  end
  host.dialogue=function(r)
    check(h.current==nil,"no overlapping modal request")
    check((r.with and 1 or 0)+(r.district_face and 1 or 0)==1,"one dialogue speaker")
    textref(r.line)
    local visible={}
    for _,o in ipairs(r.options) do
      textref(o.key)
      if not o.show or o.show() then visible[#visible+1]=o end
    end
    check(#visible>=2 and #visible<=4,"two to four actual visible answers")
    h.current={request=r,visible=visible}
    calls[#calls+1]={kind="dialogue",request=r,visible=visible}
    return true
  end
  local env=setmetatable({host=host},{__index=_G})
  function h.reload()
    h.module=assert(loadfile(ROOT.."/scripts/scenes/"..file,"t",env))()
  end
  h.reload()
  function h.emit(ev) assert(handlers[h.fact])(ev) end
  function h.tick() h.day() end
  function h.bind(ctx) h.module.bind_context(function() return ctx end) end
  function h.choose(suffix)
    local cur=assert(h.current);h.current=nil
    local chosen
    for _,o in ipairs(cur.visible) do if o.key:sub(-#suffix)==suffix then chosen=o end end
    assert(chosen,"visible choice not found: "..suffix)
    if chosen.on then chosen.on(true) end
    if cur.request.after then cur.request.after(chosen.key) end
  end
  function h.escape()
    local cur=assert(h.current);h.current=nil
    check(cur.request.on_escape=="cancel_all" or cur.request.on_escape=="cancel_part","explicit non-default-outcome Esc")
    cur.request.escaped(cur.request.on_escape)
  end
  function h.missed()
    local cur=assert(h.current);h.current=nil;cur.request.missed()
  end
  h.store=store;h.calls=calls
  return h
end

-- The existing elder API starts without a speculative context adapter.
do
  local h=fixture("elder_first_meeting.lua")
  local ev={tick=10,field=4}
  h.emit(ev);check(h.current~=nil,"elder initial question appears")
  h.choose("answer.own")
  local count=#h.calls;h.emit(ev);h.tick();check(#h.calls==count,"duplicate fact does not replay")
  h.reload();h.tick();check(#h.calls==count,"completed exchange does not replay after reload")
  check(h.store['rpg.scenes.scene.elder.first_meeting.queue.1.choice']=="own","own choice recorded")
end
do
  local h=fixture("elder_first_meeting.lua");h.emit({tick=11})
  h.escape();local count=#h.calls;h.tick();check(#h.calls==count,"Esc does not auto-reopen")
  check(h.store['rpg.scenes.scene.elder.first_meeting.queue.1.choice']==nil,"Esc does not choose own")
  h.reload();h.tick();check(#h.calls==count,"paused exchange survives reload without reopening")
  local c={resume=true,resume_token="contact1"};h.bind(c);h.tick();check(h.current~=nil,"explicit contact resumes")
  check(#h.calls==count+1,"opening lines not repeated")
  h.choose("answer.see");check(h.current==nil,"no nine-step page invented")
  local after=#h.calls;h.tick();check(#h.calls==after,"same contact cannot advance paused phase twice")
  c.resume_token="contact2";c.layout_lines={"housing","well"};h.tick()
  check(h.calls[#h.calls-1].key:sub(-14)=="layout.housing","only verified registered housing branch")
  check(h.calls[#h.calls].key:sub(-11)=="layout.well","only verified registered well branch")
end
do
  local h=fixture("elder_first_meeting.lua");h.elder=nil;h.emit({tick=12})
  check(#h.calls==0,"no substitute resident when elder is absent")
  h.elder=42;h.tick();check(h.current~=nil,"pending fact retries after real elder available")
end

local cases={
 stozharov={"empty_club","staged_club","living_institution"},
 karasev={"formal_present","empty_event","true_report","false_report"},
 polushkina={"no_office","clean","uncovered_case","formal_doubt"},
}
for face,list in pairs(cases) do
  for i,case in ipairs(list) do
    local h=fixture(face.."_inspection_return.lua")
    local ev={tick=100+i,district_face=face}
    h.emit(ev);check(#h.calls==0,"no guessed context")
    local c={case=case,district_say_ready=false};h.bind(c);h.tick()
    check(#h.calls==0,"no unsupported district say before API approval")
    -- From here the fixture models the PROPOSED reviewed extension, not current host.
    h.extended=true;c.district_say_ready=true;h.tick()
    check(#h.calls==1 and h.calls[1].key=='scene.district.'..face..'.inspection_return.reply.'..case,"factual branch selected")
    h.emit(ev);h.reload();h.bind(c);h.tick();check(#h.calls==1,"completed visit stays consumed across reload")
    h.emit({tick=200+i,district_face=face});check(#h.calls==2,"later genuine visit remains repeatable")
  end
end
do
  local h=fixture("stozharov_inspection_return.lua");h.extended=true
  h.bind({case="empty_club",district_say_ready=true})
  h.emit({tick=300,district_face="karasev"});check(#h.calls==0,"never substitute a different district face")
end
do
  local h=fixture("zhernova_inspection_question.lua");h.extended=true
  local c={district_say_ready=true,case="discrepancy"};h.bind(c)
  h.emit({tick=400,district_face="zhernova"});check(#h.calls==0,"generic discrepancy does not prove impossible season")
  c.case="impossible_season_loss";h.tick();check(#h.calls==0,"no invented resource")
  c.resource_name="Рожь";h.tick();check(#h.calls==1 and h.current==nil,"authored choiceless question, no invented answers")
  check(h.calls[1].request.line[2].resource=="Рожь","resource from verified context")
end

local function failure(c)
  local h=fixture("district_failure_explanation.lua");h.extended=true;h.bind(c)
  h.emit({tick=500,amount=2,district_face="polushkina"});return h
end
do
  local c={district_say_ready=true,failed_calendar_year=1931,failed_positions="Рожь — 95,0 %",
    causes={weather=true,people=true,equipment=true,limit=true,unfinished=true}}
  local h=failure(c);check(h.current~=nil and #h.current.visible==4,"four factual causes, fifth hidden")
  check(h.current.request.line[2].failed_year==1931,"historical calendar year, not campaign index 2")
  h.escape();local count=#h.calls;h.tick();check(#h.calls==count,"cancel_all consumes no answer and no reopening")
  for k in pairs(h.store) do check(k:sub(1,25)~="rpg.failure_explanations.","Esc stores no explanation") end
end
do
  local c={district_say_ready=true,failed_calendar_year=1931,failed_positions="Молоко — 97,7 %",
    causes={weather=true,people=true,unfinished=true}}
  local h=failure(c);check(#h.current.visible==3,"unfinished is allowed below four specific causes")
  h.choose("answer.people")
  check(h.store['rpg.failure_explanations.1931.polushkina.people']==true,"only selected testimony remembered")
  check(h.calls[#h.calls].key=='scene.district.failure_explanation.return.polushkina',"same face returns")
end
do
  local c={district_say_ready=true,failed_calendar_year=1931,failed_positions="Рожь — 95,0 %",causes={weather=true}}
  local h=failure(c);check(h.current==nil,"one factual answer never manufactures a second")
  c.causes.people=true;h.tick();check(#h.current.visible==2,"late genuine context can supply second cause")
  h.missed();local count=#h.calls;h.tick();check(#h.calls==count,"watchdog loss does not choose or auto-retry")
  c.resume=true;c.resume_token="retry1";h.tick();check(h.current~=nil,"explicit retry after watchdog")
end
do
  local h=failure({district_say_ready=true,failed_calendar_year=1931,failed_positions="",causes={weather=true,people=true}})
  check(h.current==nil,"no fabricated historical failed positions")
end
-- A second occurrence waits behind an unanswered dialogue, then starts immediately.
do
  local c={district_say_ready=true,failed_calendar_year=1931,failed_positions="Рожь — 95,0 %",
    causes={weather=true,people=true}}
  local h=failure(c)
  h.emit({tick=501,amount=2,district_face="zhernova"})
  check(h.current.request.district_face=="polushkina","queued occurrence does not replace current speaker")
  h.choose("answer.people")
  check(h.current~=nil and h.current.request.district_face=="zhernova","next actual occurrence starts after completion")
  h.choose("answer.weather")
  check(h.store['rpg.failure_explanations.1931.zhernova.weather']==true,"queued face keeps its own testimony")
end
do
  local h=fixture("elder_first_meeting.lua")
  h.bind({coat_topic=true})
  h.emit({tick=900})
  check(#h.calls==0,"invalid optional coat context does not emit partial repeated opening")
end
do
  local h=fixture("karasev_inspection_return.lua")
  h.bind({case="true_report",district_say_ready=true})
  h.emit({tick=901,district_face="karasev"})
  check(#h.calls==0,"current native API rejection cannot mark the job done")
  h.extended=true;h.tick()
  check(#h.calls==1,"failed API attempt remains pending for a real reviewed door")
end
print("scene_scripts_1732: PASS ("..checks.." checks; isolated review fixture, not host integration)")
