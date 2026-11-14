local script = host.script "scene.district.zhernova.inspection_question"
local SCENE = "scene.district.zhernova.inspection_question"
local FACT = "zhernova_discrepancy_found"
-- Owner review hook, NOT an invented host API or story-input protocol.
-- Host binds its actual #1731 factual context before this can enter production.
local read_context = function() return nil end
local function gap(why) host.log("warn", SCENE .. ": " .. why) end

-- Boss-approved mapping: core's seized accumulation surplus is NOT a loss.
-- The loss branch remains reserved for a future world fact that actually proves it.
local OPENINGS = {
  surplus = SCENE .. ".opening.surplus",
  impossible_season_loss = SCENE .. ".opening.era1",
}

script.on_fact(FACT,function(ev)
  if ev.district_face~="zhernova" then gap("fact names another district face");return end
  local input=read_context(ev)
  if type(input)~="table" or not OPENINGS[input.case] or
      type(input.resource_name)~="string" or input.resource_name=="" then
    gap("discrepancy needs a proven surplus or loss case and localized resource");return
  end
  if input.district_say_ready~=true then gap("district speaker doors await owner review");return end
  local key=OPENINGS[input.case]
  local function present()
    host.say {district_face="zhernova",line={key,{resource=input.resource_name}}}
  end
  host.scene {
    key=SCENE,district_face="zhernova",tier="low",opened_by_player=false,background=false,
    answer={keys={key},lines={key}},
    authored=present,
    -- Same factual text and substitution, no invented player answer options.
    on_answer=present,
  }
end)

-- Review-only export; production must bind the actual owner reader.
return {bind_context=function(reader) assert(type(reader)=="function"); read_context=reader end}
