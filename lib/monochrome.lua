-- Project composed artwork into the four neutral shades used by Red.
return function(source,target)
  local width,height=source:getDimensions()
  for y=0,height-1 do for x=0,width-1 do
    local r,g,b,a=source:getPixel(x,y)
    local light=(54*r+183*g+19*b)*255/256
    local gray=light<80 and 0 or light<145 and 1/3 or light<210 and 2/3 or 1
    target:setPixel(x,y,gray,gray,gray,a)
  end end
  return target
end
