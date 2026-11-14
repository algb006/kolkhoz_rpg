local script = host.script "scene.elder.first_meeting"
local SCENE = "scene.elder.first_meeting"
local FACT = "start_reserve_field_removed"

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


local AVATARS = { acting=true, dealer=true, ex_chairman=true, old_fighter=true,
  promoted=true, student=true, villager=true, worker=true }
local LAYOUT = { housing=true, well=true, store=true, farmyard=true,
  collective_yard=true, livestock_yard=true, manure=true, access=true }
-- The initial registered exchange needs only the real elder and the received fact.
-- Optional factual branches/layout/resume await the owner's reviewed reader.
read_context = function() return {} end

play = function(slot, input, finish, pause)
  local elder = host.world.elder()
  if not elder then gap(slot, "no living elder supplied by core"); return false end
  if input.coat_topic == true and (not AVATARS[input.avatar] or
      (input.coat_reply ~= "coat_worn" and input.coat_reply ~= "work_clothes")) then
    gap(slot, "optional coat topic lacks actual avatar/clothing context"); return false
  end
  local who = elder.resident
  local function elder_says(key) host.say {with=who, line=key} end
  local function chairman_says(key) host.say {chairman=true, line=key} end
  if (get(slot .. ".step") or 0) == 0 then
    if not get(slot .. ".opening_done") then
      chairman_says(SCENE .. ".opening.chairman")
      elder_says(SCENE .. ".opening.elder")
      chairman_says(SCENE .. ".field.chairman")
      if input.coat_topic == true then
        chairman_says(SCENE .. ".coat.question." .. input.avatar)
        elder_says(SCENE .. ".coat.reply." .. input.coat_reply)
      end
      put(slot .. ".opening_done", true)
    end
    return host.dialogue {
      with=who, line=SCENE .. ".offer.elder", on_escape="cancel_part",
      escaped=function() pause() end, missed=function() pause() end,
      options={
        {key=SCENE .. ".answer.see", kind="deal", on=function()
          put(slot .. ".choice", "see")
          elder_says(SCENE .. ".reply.see")
          put(slot .. ".step", 1)
        end},
        {key=SCENE .. ".answer.own", kind="deal", on=function()
          put(slot .. ".choice", "own")
          elder_says(SCENE .. ".reply.own")
        end},
      },
      after=function()
        if get(slot .. ".choice") == "own" then finish() else
          -- No nine-step page, ghost placement, new options or imaginary map API.
          -- Await factual matches for the REGISTERED first_meeting layout lines.
          pause()
        end
      end,
    }
  end
  if type(input.layout_lines) ~= "table" or #input.layout_lines == 0 then
    gap(slot, "layout follow-up needs real matching recommendation context"); return false
  end
  for _, name in ipairs(input.layout_lines) do
    if not LAYOUT[name] then gap(slot, "unregistered layout branch"); return false end
  end
  local index = get(slot .. ".step") or 1
  while index <= #input.layout_lines do
    elder_says(SCENE .. ".layout." .. input.layout_lines[index])
    index = index + 1
    put(slot .. ".step", index)
  end
  -- This records delivered authored explanations, never accepts/builds a contour.
  finish()
  return true
end

-- Review-only seam: production reader is intentionally unbound until host approves it.
return { bind_context = function(reader) assert(type(reader) == "function"); read_context = reader end }
