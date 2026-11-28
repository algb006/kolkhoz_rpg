local SCENE = "scene.district.trip"
local STORY = "rpg.district.trip."
local script = host.script(SCENE)

local TOPICS = {"materials", "plan"}
local TOPIC_LINES = {
  materials = {karasev = SCENE .. ".topic.materials.karasev"},
  plan = {
    karasev = SCENE .. ".topic.plan.karasev",
    korenev = SCENE .. ".topic.plan.korenev",
  },
}
local ROAD = SCENE .. "_departure"
local SUMMONS_ROAD = "scene.district.summon_departure"

local function current_trip()
  local chairman = host.chairman()
  if chairman.away then return chairman.trip end
end

local function say_topic(trip, topic, face)
  local key = STORY .. topic
  if host.story.get(key .. ".spoken") == trip.from_tick then return end
  host.story.set(key .. ".spoken", trip.from_tick)
  host.say {district_face = face, line = TOPIC_LINES[topic][face]}
end

script.on_fact("district_topic_opened", function(event)
  local trip = current_trip()
  local topic, face = event.district_topic, event.district_face
  if not trip or not TOPIC_LINES[topic] or not TOPIC_LINES[topic][face] then return end

  -- Host can deliver the fact at departure while the road cutscene is still playing.
  if host.story.get(STORY .. "road_finished") == trip.from_tick then
    say_topic(trip, topic, face)
  else
    local key = STORY .. topic
    host.story.set(key .. ".pending_trip", trip.from_tick)
    host.story.set(key .. ".pending_face", face)
  end
end)

script.on("cutscene_finished", function(event)
  local trip = current_trip()
  if not trip then return end
  local expected = trip.summoned and SUMMONS_ROAD or ROAD
  if event.scene ~= expected or host.story.get(STORY .. "road_finished") == trip.from_tick then
    return
  end

  host.story.set(STORY .. "road_finished", trip.from_tick)
  if not trip.summoned then
    host.say {district_face = "karasev", line = SCENE .. ".opening.voluntary.karasev"}
  end
  -- The summons sheet follows the summons conversation on the layer side.
  -- Its mid-trip topic facts already identify a selected, enabled topic.
  for _, topic in ipairs(TOPICS) do
    local key = STORY .. topic
    if host.story.get(key .. ".pending_trip") == trip.from_tick then
      local face = host.story.get(key .. ".pending_face")
      if TOPIC_LINES[topic][face] then say_topic(trip, topic, face) end
    end
  end
end)
