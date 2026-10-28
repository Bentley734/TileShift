-- Reviewed, source-fingerprinted rows; no gameplay changes.
local rows={}
local function add(batch)for _,r in ipairs(batch)do rows[#rows+1]=r end end
return rows
