local script = host.script "scene.district.failure_explanation"
local SCENE = "scene.district.failure_explanation"
local FACT = "district_face_asks_about_failed_year_plan"
-- Owner review hook, NOT an invented host API or story-input protocol.
-- Host binds its actual #1731 factual context before this can enter production.
local read_context = function() return nil end
local function gap(why) host.log("warn", SCENE .. ": " .. why) end

local FACES={korenev=true,stozharov=true,karasev=true,zhernova=true,polushkina=true}
local CAUSES={"weather","people","equipment","limit"}
script.on_fact(FACT,function(ev)
  local face=ev.district_face
  if not FACES[face] then gap("fact has no actual district face");return end
  local input=read_context(ev)
  if type(input)~="table" or input.district_say_ready~=true then
    gap("historical context and district speaker doors await owner review");return
  end
  local year,positions=input.failed_calendar_year,input.failed_positions
  if type(year)~="number" or year%1~=0 or type(positions)~="string" or positions=="" then
    gap("historical calendar year/positions are missing; no reconstruction");return
  end
  local allowed,count={},0
  for _,tag in ipairs(CAUSES) do
    allowed[tag]=type(input.causes)=="table" and input.causes[tag]==true
    if allowed[tag] then count=count+1 end
  end
  allowed.unfinished=count<4 and type(input.causes)=="table" and input.causes.unfinished==true
  if count+(allowed.unfinished and 1 or 0)<2 then
    gap("fewer than two factual answers; no invented cause");return
  end
  local function talk()
    local options={}
    for _,tag in ipairs({"weather","people","equipment","limit","unfinished"}) do
      local cause=tag
      options[#options+1]={
        key=SCENE .. ".answer." .. cause,kind="deal",show=function() return allowed[cause] end,
        on=function()
          host.story.set("rpg.failure_explanations." .. tostring(year) .. "." .. face .. "." .. cause,true)
          host.say {district_face=face,line=SCENE .. ".return." .. face}
        end,
      }
    end
    host.dialogue {
      district_face=face,line={SCENE .. ".opening." .. face,
        {failed_year=year,failed_positions=positions}},
      options=options,on_escape="cancel_all",
      escaped=function() end,missed=function() end,
    }
  end
  -- Closed opening form never lets a model select the chairman's explanation.
  local opening=SCENE .. ".opening." .. face
  host.scene {
    key=SCENE,district_face=face,tier="low",opened_by_player=false,background=false,
    answer={keys={opening},lines={opening}},authored=talk,on_answer=talk,
  }
end)

-- Review-only export; production must bind the actual owner reader.
return {bind_context=function(reader) assert(type(reader)=="function"); read_context=reader end}
