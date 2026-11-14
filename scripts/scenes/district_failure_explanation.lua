local script = host.script "scene.district.failure_explanation"
local SCENE = "scene.district.failure_explanation"
local FACT = "district_face_asks_about_failed_year_plan"

-- Staged for host API review; see the accompanying input contract.
-- All durable state uses the existing scalar host.story API.
local STATE = "rpg.scenes." .. SCENE
local active = false
local play
-- GAP: host must bind its reviewed occurrence-context reader; no invented host API.
local read_context = function() return nil end

local function get(key) return host.story.get(key) end
local function put(key, value) host.story.set(key, value) end
local function gap(slot, why)
  if get(slot .. ".gap") ~= why then
    put(slot .. ".gap", why)
    host.log("warn", SCENE .. ": " .. why)
  end
end
local function pump()
  if active then return end
  local head = get(STATE .. ".head") or 1
  local tail = get(STATE .. ".tail") or 0
  if head > tail then return end
  local slot = STATE .. ".queue." .. tostring(head)
  local token = get(slot .. ".token")
  local input = read_context({tick=get(slot .. ".tick"), face=get(slot .. ".face"),
    amount=get(slot .. ".amount"), token=token, slot=slot})
  if type(input) ~= "table" then
    gap(slot, "waiting for reviewed occurrence context and registered lines")
    return
  end
  if get(slot .. ".status") == "paused" then
    if input.resume ~= true or input.resume_token == nil or
        get(slot .. ".resume_token") == input.resume_token then return end
    put(slot .. ".resume_token", input.resume_token)
  end
  local function finish(status)
    put(slot .. ".status", status or "done")
    put(STATE .. ".head", head + 1)
    active = false
    pump()
  end
  local function pause()
    put(slot .. ".status", "paused")
    active = false
  end
  active = true
  put(slot .. ".status", "running")
  local ok, started = pcall(play, slot, input, finish, pause)
  if not ok then
    active = false
    gap(slot, "scene call failed: " .. tostring(started))
  elseif started == false then
    active = false
    put(slot .. ".status", "queued")
  end
end

script.on_fact(FACT, function(ev)
  if type(ev.tick) ~= "number" then
    host.log("warn", SCENE .. ": fact has no tick; not inventing an occurrence")
    return
  end
  local face = ev.district_face or "none"
  local amount = ev.amount == nil and "none" or tostring(ev.amount)
  local token = tostring(ev.tick) .. "." .. face .. "." .. amount
  if get(STATE .. ".seen." .. token) then return end
  local tail = (get(STATE .. ".tail") or 0) + 1
  local slot = STATE .. ".queue." .. tostring(tail)
  put(slot .. ".token", token)
  put(slot .. ".tick", ev.tick)
  put(slot .. ".face", face)
  put(slot .. ".status", "queued")
  if ev.amount ~= nil then put(slot .. ".amount", ev.amount) end
  put(STATE .. ".tail", tail)
  put(STATE .. ".seen." .. token, true)
  pump()
end)
-- Retry only durable jobs already received, never poll or re-raise a world fact.
script.on_day(function() pump() end)


local FACES = { korenev=true, stozharov=true, karasev=true, zhernova=true, polushkina=true }
local CAUSES = { "weather", "people", "equipment", "limit" }

play = function(slot, input, finish, pause)
  local face = get(slot .. ".face")
  if not FACES[face] then gap(slot, "failure fact names no district face"); return false end
  if input.district_say_ready ~= true then
    gap(slot, "district return line waits for host.say district_face"); return false
  end
  local year = input.failed_calendar_year
  local positions = input.failed_positions
  if type(year) ~= "number" or year % 1 ~= 0 or
      type(positions) ~= "string" or positions == "" then
    gap(slot, "historical failed year and localized failed positions are required"); return false
  end
  local allowed, count = {}, 0
  for _, cause in ipairs(CAUSES) do
    allowed[cause] = type(input.causes) == "table" and input.causes[cause] == true
    if allowed[cause] then count = count + 1 end
  end
  allowed.unfinished = count < 4 and type(input.causes) == "table" and input.causes.unfinished == true
  local visible = count + (allowed.unfinished and 1 or 0)
  if visible < 2 then gap(slot, "fewer than two factual answers; not inventing a cause"); return false end
  local options = {}
  local all = { "weather", "people", "equipment", "limit", "unfinished" }
  for _, tag in ipairs(all) do
    local cause = tag
    options[#options+1] = {
      key=SCENE .. ".answer." .. cause, kind="deal",
      show=function() return allowed[cause] end,
      on=function()
        -- Narrative testimony only. No plan, reputation or truth predicate is changed.
        put("rpg.failure_explanations." .. tostring(year) .. "." .. face .. "." .. cause, true)
        put(slot .. ".choice", cause)
        host.say {district_face=face, line=SCENE .. ".return." .. face}
      end,
    }
  end
  return host.dialogue {
    district_face=face,
    line={SCENE .. ".opening." .. face, {failed_year=year, failed_positions=positions}},
    options=options, on_escape="cancel_all",
    escaped=function() finish("cancelled") end,
    missed=function() pause() end,
    after=function() finish() end,
  }
end

-- Review-only seam: production reader is intentionally unbound until host approves it.
return { bind_context = function(reader) assert(type(reader) == "function"); read_context = reader end }
