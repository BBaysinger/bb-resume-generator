-- Pandoc Lua filter: move a date-only paragraph immediately following an H3
-- into the H3 itself, wrapped in a span.date-range for right alignment.
--
-- Intended for resume formatting like:
--   ### Company — Role
--   _2021 – 2024_
--
-- Output becomes roughly:
--   <h3 class="with-date">Company — Role <span class="date-range"><em>2021 – 2024</em></span></h3>

local function is_date_only_para(block)
  if not block or block.t ~= "Para" then
    return false
  end

  if not block.content or #block.content ~= 1 then
    return false
  end

  local only = block.content[1]
  if only.t ~= "Emph" and only.t ~= "Strong" then
    return false
  end

  local text = pandoc.utils.stringify(only)
  if not text or text == "" then
    return false
  end

  -- Heuristic: must contain a digit and a dash (hyphen or en-dash)
  -- Keep it intentionally strict to avoid accidentally moving prose.
  local hasDigit = string.match(text, "%d") ~= nil
  local hasDash = (string.find(text, "-", 1, true) ~= nil) or
    (string.find(text, "–", 1, true) ~= nil)

  return hasDigit and hasDash
end

local function ensure_class(attr, className)
  if not attr then
    return pandoc.Attr("", { className }, {})
  end

  attr.classes = attr.classes or {}
  for _, c in ipairs(attr.classes) do
    if c == className then
      return attr
    end
  end

  table.insert(attr.classes, className)
  return attr
end

function Pandoc(doc)
  local blocks = doc.blocks or {}
  local out = {}

  local i = 1
  while i <= #blocks do
    local block = blocks[i]

    if block.t == "Header" and block.level == 3 then
      local nextBlock = blocks[i + 1]

      if is_date_only_para(nextBlock) then
        block.attr = ensure_class(block.attr, "with-date")

        local dateSpan = pandoc.Span(nextBlock.content, pandoc.Attr("", { "date-range" }, {}))

        table.insert(block.content, pandoc.Space())
        table.insert(block.content, dateSpan)

        table.insert(out, block)
        i = i + 2
      else
        table.insert(out, block)
        i = i + 1
      end
    else
      table.insert(out, block)
      i = i + 1
    end
  end

  doc.blocks = out
  return doc
end
