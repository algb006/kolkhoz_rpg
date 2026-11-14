local script = host.script "scene.district.polushkina.inspection_return"
local SCENE = "scene.district.polushkina.inspection_return"
local FACT = "polushkina_inspection_completed"

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

local CASES = { no_office=true, clean=true, uncovered_case=true, formal_doubt=true }

play = function(slot, input, finish)
  if get(slot .. ".face") ~= "polushkina" then
    gap(slot, "fact district face does not match this scene"); return false
  end
  if input.district_say_ready ~= true then
    gap(slot, "host.say district_face is pending host API approval"); return false
  end
  local case = input.case
  if not CASES[case] then
    gap(slot, "no authored result matches the supplied inspection context"); return false
  end
  -- PROPOSED extension, deliberately gated: current host.say rejects district_face.
  host.say { district_face="polushkina", line=SCENE .. ".reply." .. case }
  finish()
  return true
end

-- Review-only seam: production reader is intentionally unbound until host approves it.
return { bind_context = function(reader) assert(type(reader) == "function"); read_context = reader end }
