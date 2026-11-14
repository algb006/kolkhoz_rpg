local script = host.script "scene.elder.first_meeting"
local SCENE = "scene.elder.first_meeting"
local FACT = "start_reserve_field_removed"
-- Owner review hook, NOT an invented host API or story-input protocol.
-- Host binds its actual #1731 factual context before this can enter production.
local read_context = function() return nil end
local function gap(why) host.log("warn", SCENE .. ": " .. why) end

local STATE = "rpg.scenes.elder_first_meeting"
local LAYOUT = {housing=true, well=true, store=true, farmyard=true,
  collective_yard=true, livestock_yard=true, manure=true, access=true}
local AVATARS = {acting=true,dealer=true,ex_chairman=true,old_fighter=true,
  promoted=true,student=true,villager=true,worker=true}
read_context = function() return {} end
local function get(suffix) return host.story.get(STATE .. "." .. suffix) end
local function put(suffix, value) host.story.set(STATE .. "." .. suffix, value) end

local function play(who, input)
  local living = host.world.elder()
  assert(living and living.resident==who, "elder is no longer the actual living speaker")
  local function say(key) host.say {with=who,line=key} end
  if get("phase")=="layout" then
    if type(input.layout_lines)~="table" or #input.layout_lines==0 then
      gap("registered layout follow-up needs actual matching context"); return false
    end
    for _,name in ipairs(input.layout_lines) do
      assert(LAYOUT[name],"layout branch is not registered first_meeting content")
    end
    local index=get("layout_index") or 1
    while index<=#input.layout_lines do
      say(SCENE .. ".layout." .. input.layout_lines[index])
      index=index+1;put("layout_index",index)
    end
    put("phase","done");return true
  end
  if get("phase")=="done" then return true end
  if input.coat_topic==true then
    assert(AVATARS[input.avatar] and
      (input.coat_reply=="coat_worn" or input.coat_reply=="work_clothes"),
      "optional coat question needs actual avatar and clothing")
  end
  if not get("opening_done") then
    host.say {chairman=true,line=SCENE .. ".opening.chairman"}
    say(SCENE .. ".opening.elder")
    host.say {chairman=true,line=SCENE .. ".field.chairman"}
    if input.coat_topic==true then
      host.say {chairman=true,line=SCENE .. ".coat.question." .. input.avatar}
      say(SCENE .. ".coat.reply." .. input.coat_reply)
    end
    put("opening_done",true)
  end
  return host.dialogue {
    with=who,line=SCENE .. ".offer.elder",on_escape="cancel_part",
    options={
      {key=SCENE .. ".answer.see",kind="deal",on=function()
        put("choice","see");say(SCENE .. ".reply.see")
        put("phase","layout");put("layout_index",1)
      end},
      {key=SCENE .. ".answer.own",kind="deal",on=function()
        put("choice","own");say(SCENE .. ".reply.own");put("phase","done")
      end},
    },
    escaped=function() put("paused",true) end,
    missed=function() put("paused",true) end,
    after=function()
      if get("phase")=="layout" then put("paused",true) end
    end,
  }
end

script.on_fact(FACT,function(ev)
  local elder=host.world.elder()
  if not elder then gap("no living elder; no substitute actor");return end
  -- host.scene owns entry-day, repeat_policy, slot and queue. No private queue.
  host.scene {
    key=SCENE,participants={elder.resident},speaker=elder.resident,
    tier="low",opened_by_player=false,background=false,
    answer={keys={SCENE .. ".offer.elder"},lines={SCENE .. ".offer.elder"}},
    authored=function()
      play(elder.resident,read_context(ev) or {})
    end,
    -- As in the pilot: any model opening still leads to the PLAYER'S choice.
    on_answer=function(_,a)
      put("model_opening",a.key);play(elder.resident,read_context(ev) or {})
    end,
  }
end)

local function resume(ev)
  -- Host must hook this continuation to the actual elder interaction, not a timer.
  -- Do not re-request the once-only host.scene merely to resume one dialogue.
  if not get("paused") then return false end
  local input=read_context(ev)
  local elder=host.world.elder()
  if not elder or type(input)~="table" or input.resume~=true or
      input.resume_token==nil or input.resume_token==get("resume_token") then return false end
  put("resume_token",input.resume_token)
  return play(elder.resident,input)
end

-- Review-only export; production must bind the actual owner reader.
return {bind_context=function(reader) assert(type(reader)=="function"); read_context=reader end,resume=resume}
