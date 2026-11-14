local script = host.script "scene.district.stozharov.inspection_return"
local SCENE = "scene.district.stozharov.inspection_return"
local FACT = "stozharov_inspection_completed"
-- Owner review hook, NOT an invented host API or story-input protocol.
-- Host binds its actual #1731 factual context before this can enter production.
local read_context = function() return nil end
local function gap(why) host.log("warn", SCENE .. ": " .. why) end

local CASES={empty_club=true,staged_club=true,living_institution=true}

script.on_fact(FACT,function(ev)
  if ev.district_face~="stozharov" then gap("fact names another district face");return end
  local input=read_context(ev)
  if type(input)~="table" or not CASES[input.case] then
    gap("factual inspection case is not supplied; no invented result");return
  end
  if input.district_say_ready~=true then
    gap("district host.scene and host.say speaker doors await owner review");return
  end
  local key=SCENE .. ".reply." .. input.case
  host.scene {
    key=SCENE,district_face="stozharov",tier="low",opened_by_player=false,background=false,
    answer={keys={key},lines={key}},
    authored=function()
      -- Proposed district say field is gated above; host must land it before import.
      host.say {district_face="stozharov",line=key}
      host.story.set("rpg.scenes." .. SCENE .. ".last_line",key)
    end,
    on_answer=function(_,a)
      host.story.set("rpg.scenes." .. SCENE .. ".last_line",a.key)
    end,
  }
end)

-- Review-only export; production must bind the actual owner reader.
return {bind_context=function(reader) assert(type(reader)=="function"); read_context=reader end}
