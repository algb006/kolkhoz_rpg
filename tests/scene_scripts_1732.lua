-- One isolated source-contract fixture, not a native host integration test.
local checks=0
local function check(ok,msg) assert(ok,msg);checks=checks+1 end
local function fixture(file)
  local store,calls,handlers,queue={},{},{},{}
  local h={extended=false,elder=42,day=0,current=nil,played={}}
  local host={story={get=function(k)return store[k]end,set=function(k,v)
      check(type(v)=="string" or type(v)=="number" or type(v)=="boolean","scalar story state")
      check(not k:find(".queue.",1,true),"no shadow scene queue")
      store[k]=v
    end},world={elder=function()if h.elder then return{resident=h.elder}end end},log=function()end}
  host.script=function(key)
    h.key=key
    return{on_fact=function(f,fn)h.fact=f;handlers[f]=fn end,
      on_day=function()error("scene timing/queue must belong to host.scene")end}
  end
  local function key_exists(key)check(type(key)=="string" and SCENE_TEST_KEYS[key]~=nil,"known/proposed string key "..tostring(key))end
  local function textref(ref)
    local key=type(ref)=="table" and ref[1] or ref;key_exists(key)
    local params=type(ref)=="table" and ref[2] or {}
    for _,name in ipairs(SCENE_TEST_KEYS[key])do check(params[name]~=nil,"missing text parameter "..name)end
    for name in pairs(params)do
      local found=false;for _,v in ipairs(SCENE_TEST_KEYS[key])do if v==name then found=true end end
      check(found,"undeclared text parameter "..name)
    end
    return key
  end
  host.say=function(r)
    for k in pairs(r)do check(k=="with"or k=="chairman"or k=="line"or(h.extended and k=="district_face"),"current say speaker API")end
    check((r.with and 1 or 0)+(r.chairman and 1 or 0)+(r.district_face and 1 or 0)==1,"one say speaker")
    calls[#calls+1]={kind="say",key=textref(r.line),request=r}
  end
  host.dialogue=function(r)
    check(h.current==nil,"one modal at a time")
    check((r.with and 1 or 0)+(r.district_face and 1 or 0)==1,"one dialogue speaker")
    textref(r.line);local visible={}
    for _,o in ipairs(r.options)do key_exists(o.key);if not o.show or o.show()then visible[#visible+1]=o end end
    check(#visible>=2 and #visible<=4,"two to four factual answers")
    h.current={request=r,visible=visible};calls[#calls+1]={kind="dialogue",request=r};return true
  end
  host.scene=function(r)
    check(SCENE_TEST_SCENES[r.key]~=nil,"registered scene gate")
    check(r.background==false and r.opened_by_player==false,"explicit staged unsolicited scene")
    check(r.tier=="low" and type(r.authored)=="function","complete authored fallback")
    check(type(r.on_answer)=="function","same player-choice route after model opening")
    if r.district_face then
      check(h.extended,"district scene speaker is a proposed owner extension")
      check(r.participants==nil and r.speaker==nil,"district face is not a counterfeit resident")
    else
      check(r.speaker==42 and r.participants[1]==42,"canonical living elder as scene participant")
    end
    check(r.answer and #r.answer.keys>=1 and #r.answer.lines>=1,"complete closed answer shape")
    for _,k in ipairs(r.answer.keys)do key_exists(k)end
    for _,k in ipairs(r.answer.lines)do key_exists(k)end
    if SCENE_TEST_SCENES[r.key]=="once" and h.played[r.key]then return 0 end
    queue[#queue+1]=r;h.scene_requests=(h.scene_requests or 0)+1;return h.scene_requests
  end
  local env=setmetatable({host=host},{__index=_G})
  function h.reload()h.module=assert(loadfile(SCENE_TEST_ROOT.."/scenes/epoch1/"..file,"t",env))()end
  h.reload()
  function h.bind(c)h.module.bind_context(function()return c end)end
  function h.emit(ev)handlers[h.fact](ev)end
  function h.run_next(model)
    if h.day<12 or h.current or #queue==0 then return false end
    local r=table.remove(queue,1)
    if SCENE_TEST_SCENES[r.key]=="once" and h.played[r.key]then return false end
    local ok,why=pcall(function()
      if model then r.on_answer({expired=false},{key=r.answer.keys[1],line=r.answer.lines[1]})else r.authored({expired=false})end
    end)
    if ok then h.played[r.key]=true else h.error=why end
    return ok
  end
  function h.choose(suffix)
    local cur=assert(h.current);h.current=nil;local chosen
    for _,o in ipairs(cur.visible)do if o.key:sub(-#suffix)==suffix then chosen=o end end
    assert(chosen,"choice not visible");if chosen.on then chosen.on(true)end
    if cur.request.after then cur.request.after(chosen.key)end
  end
  function h.escape()local cur=assert(h.current);h.current=nil;cur.request.escaped(cur.request.on_escape)end
  function h.missed()local cur=assert(h.current);h.current=nil;cur.request.missed()end
  h.store=store;h.calls=calls;h.queue=queue;return h
end

do
  local h=fixture("elder_first_meeting.lua");h.emit({tick=1})
  check(h.scene_requests==1 and #h.calls==0,"fact goes through registry, not a bare dialogue")
  check(not h.run_next(),"source cannot bypass the owner's entry-day queue")
  h.day=12;check(h.run_next() and h.current~=nil,"authored fallback opens the registered exchange")
  h.choose("answer.own");check(h.store['rpg.scenes.elder_first_meeting.choice']=="own","chosen outcome recorded")
  local n=#h.calls;h.reload();h.emit({tick=2});h.run_next();check(#h.calls==n,"native once policy, no shadow replay state")
end
do
  local h=fixture("elder_first_meeting.lua");h.day=12;h.emit({tick=3});h.run_next();h.escape()
  check(h.store['rpg.scenes.elder_first_meeting.choice']==nil,"cancel_part never chooses own")
  local c={resume=true,resume_token="actual-contact1"};h.reload();h.bind(c)
  check(h.module.resume({tick=4}),"owner hook resumes confirmed phase without re-requesting once scene")
  h.choose("answer.see");check(h.store['rpg.scenes.elder_first_meeting.phase']=="layout","see records pending registered layout")
  check(not h.module.resume({tick=4}),"sticky resume token is not a new contact")
  c.resume_token="actual-contact2";c.layout_lines={"housing","well"}
  check(h.module.resume({tick=5}),"actual verified registered layout can continue")
  check(h.store['rpg.scenes.elder_first_meeting.phase']=="done","delivered explanations complete without a build order")
  check(h.scene_requests==1,"resume does not bypass registry by staging once scene again")
end
do
  local h=fixture("elder_first_meeting.lua");h.elder=nil;h.emit({tick=6});check(not h.scene_requests,"no invented elder")
end
do
  local h=fixture("elder_first_meeting.lua");h.day=12;h.bind({coat_topic=true});h.emit({tick=7});h.run_next()
  check(h.error~=nil and #h.calls==0,"invalid optional context emits no partial opening")
end
do
  local h=fixture("elder_first_meeting.lua");h.day=12;h.emit({tick=8});h.run_next(true)
  check(h.current~=nil and h.store['rpg.scenes.elder_first_meeting.choice']==nil,"model opening does not choose for player")
end
local cases={stozharov={"empty_club","staged_club","living_institution"},karasev={"formal_present","empty_event","true_report","false_report"},polushkina={"no_office","clean","uncovered_case","formal_doubt"}}
for face,list in pairs(cases)do
  for i,case in ipairs(list)do
    local h=fixture(face.."_inspection_return.lua");h.day=12
    h.emit({tick=100+i,district_face=face});check(not h.scene_requests,"unbound factual reader names a gap")
    local c={case=case,district_say_ready=false};h.bind(c)
    h.emit({tick=200+i,district_face=face});check(not h.scene_requests,"no unreviewed district scene/say call")
    h.extended=true;c.district_say_ready=true;h.emit({tick=300+i,district_face=face})
    check(h.run_next(),"reviewed proposed extension admits scene")
    check(#h.calls==1 and h.calls[1].key=='scene.district.'..face..'.inspection_return.reply.'..case,"actual authored branch")
    h.emit({tick=400+i,district_face=face});h.run_next();check(#h.calls==2,"repeatable policy remains native")
  end
end
do
  local h=fixture("zhernova_inspection_question.lua");h.day=12;h.extended=true
  local c={district_say_ready=true,case="discrepancy"};h.bind(c);h.emit({tick=500,district_face="zhernova"})
  check(not h.scene_requests,"generic discrepancy cannot prove seasonal question")
  c.case="impossible_season_loss";c.resource_name="Рожь";h.emit({tick=501,district_face="zhernova"});h.run_next()
  check(#h.calls==1 and h.calls[1].request.line[2].resource=="Рожь" and h.current==nil,"choiceless question, real resource")
end
do
  local h=fixture("zhernova_inspection_question.lua");h.day=12;h.extended=true
  local c={district_say_ready=true,case="surplus"};h.bind(c)
  h.emit({tick=502,district_face="zhernova"})
  check(not h.scene_requests,"surplus without localized seized resource cannot play")
  c.resource_name="Рожь";h.emit({tick=503,district_face="zhernova"});h.run_next()
  check(#h.calls==1 and h.calls[1].key=="scene.district.zhernova.inspection_question.opening.surplus",
    "seized accumulation surplus never asks about seasonal loss")
  check(h.calls[1].request.line[2].resource=="Рожь" and h.current==nil,
    "one choiceless surplus question carries the actual resource")
end
local function failure(c)
  local h=fixture("district_failure_explanation.lua");h.day=12;h.extended=true;h.bind(c)
  h.emit({tick=600,amount=2,district_face="polushkina"});h.run_next();return h
end
do
  local h=failure({district_say_ready=true,failed_calendar_year=1931,failed_positions="Рожь — 95,0 %",causes={weather=true,people=true,equipment=true,limit=true,unfinished=true}})
  check(#h.current.visible==4,"hide fifth answer when four specific causes hold")
  check(h.current.request.line[2].failed_year==1931,"historical calendar year, not fact amount/current year")
  h.escape();for k in pairs(h.store)do check(not k:find('rpg.failure_explanations.',1,true),"Esc writes no testimony")end
end
do
  local h=failure({district_say_ready=true,failed_calendar_year=1931,failed_positions="Молоко — 97,7 %",causes={weather=true,people=true,unfinished=true}})
  check(#h.current.visible==3,"unfinished only if factual and fewer than four specifics")
  h.choose('answer.people');check(h.store['rpg.failure_explanations.1931.polushkina.people']==true,"only chosen testimony stored")
  check(h.calls[#h.calls].key=='scene.district.failure_explanation.return.polushkina',"actual same face returns")
end
do
  local h=failure({district_say_ready=true,failed_calendar_year=1931,failed_positions="Рожь — 95,0 %",causes={weather=true}})
  check(not h.scene_requests,"do not invent a second cause")
end
do
  local h=failure({district_say_ready=true,failed_calendar_year=1931,failed_positions="",causes={weather=true,people=true}})
  check(not h.scene_requests,"no reconstructed historical positions")
end
print('scene_scripts_1732: PASS ('..checks..' checks; registry-shaped isolated fixture, not native host integration)')
