from luaparser import ast

lines = """
_ENV = create_file_env(_ENV)



local function reflect_lines(light,light0)
  light.p = {}

  local w in light
  for i,p0 in ipairs(light0.p)
    light.p[i]={w-p0[1],p0[2]}
  end

  light.lines = {}

  for i,line0 in ipairs(light0.lines)
    light.lines[i]={
      ..line0.y0,..line0.y1,
      x0=w-line0.x0,
      x1=w-line0.x1
    }
  end



end



function reflect_light(light,light0)
  if light0.lines
    reflect_lines(light,light0)
  end

  light.cycle_offset in light0
end


local function calc_linet(light)
  local lines,p in light
  local line_i=1
  for _,line ; lines

    local x0,x1,y0,y1 in line

    for i=2,#p

      local p0,p1=p[i-1],p[i]
      local p0x,p0y,p1x,p1y=p0[1],p0[2],p1[1],p1[2]

      local s = (p0y*(-x0 + x1) - x1*y0 + p0x*(y0 - y1) + x0*y1)
               / ((-p0y + p1y)*(x0 - x1) + (p0x - p1x)*(y0 - y1))

      if (s>=0 or (i==2 and line_i==1) ) and ( s<=1 or i==#p )

        line.t=p0.t+(p1.t-p0.t)*s

        --console(lines,..line_i,..i,line.t,..s)

        goto next_line
      end


    end

    trace_error("failed to find t")


    ::next_line::
    line_i++
  end

end

local function calc_t(light)
  local p in light
  local len=0
  p[1].t=0
  for i=2,#p
    len+=point_dist( p[i][1], p[i][2], p[i-1][1], p[i-1][2])
    p[i].t=len
  end

  p.len=len
end


function downward_pulse(dims)

  local w,h in dims

  dims.p = {
    {w*.5,h},
    {w*.5,0},
  }

  dims.lines = {
    {x0=0,x1=w,y1=h,y0=h},
    {x0=0,x1=w,y1=0,y0=0},
  }

  calc_t(dims)
  calc_linet(dims)

  return dims

end

local function rotate_line(theta,line)
  local x0,x1,y0,y1 in line!
  local xc=.5*(x0+x1)
  local yc=.5*(y0+y1)

  local function spin(x,y)

    x,y-=xc,yc

    local cos,sin in math
    local X = cos(theta)*x+sin(theta)*y
    local Y = sin(theta)*x+cos(theta)*y

    X,Y+=xc,yc

    return X,Y
  end

  x0,y0=spin(x0,y0)
  x1,y1=spin(x1,y1)

  return {..x0,..y0,..x1,..y1}

end

-- not really working :-(
function downwish_pulse(deg,dims)
  local theta = math.rad(deg)
  local tan in math
  local w,h in dims

  dims.p = {
    {w*.5+tan(theta)*h,h},
    {w*.5-tan(theta)*h,0},
  }

  dims.lines = {
    rotate_line(theta,|) {x0=0,x1=w,y1=h,y0=h},
    rotate_line(theta,|) {x0=0,x1=w,y1=0,y0=0},
  }

  calc_t(dims)
  calc_linet(dims)

  return dims

end



function leftward_pulse(dims)

  local w,h in dims

  dims.p = {
    {w,h*.5},
    {0,h*.5},
  }

  dims.lines = {
    {x0=w,x1=w,y1=h,y0=0},
    {x0=0,x1=0,y1=h,y0=0},
  }

  calc_t(dims)
  calc_linet(dims)

  return dims

end

function approx_lines(dims)
  local width = dims.strip_width or min(dims.w,dims.h)

  local p in dims
  local approx_tweaks = dims.approx_tweaks?
  

  local lines = {}

  local function avg(a,b)

    do return a end

    --if not b return a end

    local r = {}
    for k,v in pairs(a)
      r[k]=.5*(a[k]+b[k])
    end

    return r
  end

  for i=1,#p-1

    local p0=p[i]
    local p1=p[i+1]

    local dx = p1[1]-p0[1]
    local dy = p1[2]-p0[2]

    local theta = atan2( -dx, dy )

    local dtheta,shift,lwidth in approx_tweaks[i]?

    if dtheta  theta+=dtheta end
    shift=shift or 0
    lwidth=lwidth or width
    if lines[i]
      theta=.5*(theta + lines[i].theta)
    end

    local line0 = { 
      x0 = p0[1]+cos(theta)*lwidth*.5+shift*sin(theta),
      y0 = p0[2]+sin(theta)*lwidth*.5-shift*cos(theta),
      x1 = p0[1]-cos(theta)*lwidth*.5+shift*sin(theta),
      y1 = p0[2]-sin(theta)*lwidth*.5-shift*cos(theta),
      ..theta
    }

    local dtheta,shift,lwidth in approx_tweaks[i+1]?
    local theta = atan2( -dx, dy )

    if dtheta  theta+=dtheta end
    shift=shift or 0
    lwidth=lwidth or width
    local line1 = {
      x0 = p1[1]+cos(theta)*lwidth*.5+shift*sin(theta),
      y0 = p1[2]+sin(theta)*lwidth*.5-shift*cos(theta),
      x1 = p1[1]-cos(theta)*lwidth*.5+shift*sin(theta),
      y1 = p1[2]-sin(theta)*lwidth*.5-shift*cos(theta),
      ..theta
    }

    lines[i]=avg(line0,lines[i])
    lines[i+1]=avg(line1,lines[i+1])

  end

  dims.approx_tweaks=nil

  dims.lines=lines

  for _,line ; lines
    line.theta=nil
  end

  return dims

end

function strip_pulse(dims)

  local width = dims.strip_width or min(dims.w,dims.h)

  if #(dims!.p)~=2
    trace_error("wrong number of points")
  end

  local p in dims
  local dx = p[2][1]-p[1][1]
  local dy = p[2][2]-p[1][2]

  local theta = atan2( -dx, dy )

  --p[1].t=0
  --p[2].t=sqrt(dx*dx+dy*dy)

  dims.lines = {
    { 
      x0 = p[1][1]+cos(theta)*width*.5+sin(theta),
      y0 = p[1][2]+sin(theta)*width*.5-cos(theta),
      x1 = p[1][1]-cos(theta)*width*.5+sin(theta),
      y1 = p[1][2]-sin(theta)*width*.5-cos(theta),
      --t=0,
    },
    {
      x0 = p[2][1]+cos(theta)*width*.5,
      y0 = p[2][2]+sin(theta)*width*.5,
      x1 = p[2][1]-cos(theta)*width*.5,
      y1 = p[2][2]-sin(theta)*width*.5,
      --t=sqrt(dx*dx+dy*dy)
    }
  }

  --console(dims,..tostring(dims.lines[1].t))

  --console(..dx,..dy,..theta/pi)


  return dims

end

--[[
function angle_pulse(theta,dims)

  local w,h in dims

  local dx=cos(theta)
  local dy=sin(theta)

  local phi = atan2( abs(dy), abs(dx) )

  if(phi<=pi*.25)

    dims.p = {
      a+
    }


  else


  end





end
--]]


function calc_line_info(light_dims)
  
  for i,light in ipairs(light_dims)
    --console("handling",i,..light,..light.p,..light.lines)
    if light.p
      if not light.p[1].t 
        calc_t(light)
      end
      if light.lines and not light.lines[1].t
        calc_linet(light)
        if light.lines[1].t > 0
          trace_error("lines[1].t must be <0: "..tostring(light.lines[1].t))
        end
      end
    end
  end

end


local speeds = {

  slow = {
    speed=100,
    width=25,
    skip=120,
    slope=1/20,
    extra_a=0,
    pulse_a0 = .1,
    pulse_a1 = .85,
  },


  long_slow = {
    speed=80,
    width=80,
    skip=60,
    slope=1/20,
    extra_a=0,
    pulse_a0 = .1,
    pulse_a1 = .85,
  },

  --[[
  medium = {
    speed=120,
    pulse_speed=100,
    width=25,
    skip=90,
    slope=1/20,
    extra_a=.1,
  },
  --]]

  fast = {
    speed=150,
    pulse_speed=125,
    pulse_a0 = .25,
    width=29,
    skip=40,
    slope=1/25,
    extra_a=0.1,
  },

  faster = {
    speed=200,
    pulse_speed = 150,
    pulse_a0 = .6,
    width=20,
    skip=20,
    slope=1/25,
    extra_a=.2,
  },

}


local colors = {
  orange = {
    light_color={254/255,250/255,207/255,1},
    glow_color={242/255,206/255,27/255,1},
  },
  cyan = {
    light_color={216/255,1,.9,1},
    glow_color={78/255,236/255,248/255,1},
    extra_color = {1,1,1,.5},
  },
  white = {
    light_color={.9,.9,.9,1},
    glow_color={1,1,1,.8},
    extra_color = {1,1,1,.8},
  },

  true_white = {
    light_color={1,1,1,1},
    glow_color={1,1,1,1},
    extra_color = {1,1,1,1},
  },
}



--
-- So the current implementation of "Manta-style" pulsing
-- lights is done almost entirely in lua.  This is having
-- measurable performance costs.  In one recent profiling
-- experiment, I found that, before triggering a render
-- slowdown, i could draw 280ish ships without lights, 160ish
-- with Hawk-style lights, and 100ish with Manta-style lights.
--
-- that's suggesting significant overhead.  a little profiling
-- shows that the primary bottleneck is currently the lua-logic
-- responsible for dispatching opengl calls; moving the pulse
-- texture drawing logic into C would clearly help.  the render
-- call sorting is also clearly suboptimal; something that
-- could be improved by refactoring the request functions into
-- families of small custom C requests, rather than bundling
-- everything into a single large lua closure.
--
-- all that said, 100-ships without slowdown is likely good 
-- enough for beta.  i may still want to add additional
-- features to the lights -- specifically, support  for
-- multicolored pulses. so at this point, optimization would be
-- premature.
--

local unpack,frame_time,gl_triangle_strip_scope,glVertex2d,glColor4d,glTexCoord2d in _ENV
local glWrap,glBlendFunAdd,current_color in gui

--local triangle in _ENV
local triangle=striangle

local fname=current_lua_file()


--
-- some definitions to test whether the lua computations or
-- rendering overhead are the true bottleneck to light
-- rendering.
--
function component_function(env,options)
  
  depends(fname)

  local light_dims in env

  local lightdir

  if env.dir
    lightdir = env.dir.."manta_lights\\"
  else 
    lightdir = env!.lightdir
  end

  local fullw = light_dims.res or drawer_id_res(current_lua_file())
  local n = #light_dims

  -- debug configuration options
  options=options?
  local bw_debug,line_debug,all_lines,base_glow_only in options

  local light_info = {}

  -- current light colors and pulse speed information.
  -- during a given render, these are shared by all lights on the
  -- same ship.

  -- light settings
  local lr,lg,lb,la
  local gr,gg,gb,ga
  local er,eg,eb,ea

  -- pulse settings
  local slope,skip,speed,width,extra_a,cycle_w,pulse_speed,pulse_a0,pulse_a1

  -- temporary state that may be changed during a given render
  -- call
  local t,t0,state,a0,a1,slope_a
  local r,g,b,a

  local function set_speed(speed_setting)
    speed,width,skip,slope,extra_a,pulse_speed,pulse_a0,pulse_a1 in speeds![speed_setting]
    cycle_w=skip+width+2/slope
    pulse_speed=pulse_speed or speed
    pulse_a0=pulse_a0 or 0
    pulse_a1=pulse_a1 or 1
  end

  for i=1,n

    local info = {}
    light_info[i]=info

    local light_img =lightdir.."light"..tostring(i)..".png"
    local glow_img = light_dims[i].glow_img or ( lightdir.."glow"..tostring(i)..".png")

    local light = light_dims[i]
    local x,y,w,h,p,lines,cycle_offset in light

    

    local tw,th

    x/=fullw
    y/=fullw
    local iw,ih=w,h
    w=w/fullw
    h=h/fullw

    local toffset

    -- the 
    local function light_box()
      glTexCoord2d(0,0) glVertex2d( x, y )
      glTexCoord2d(tw,0) glVertex2d( x+w, y )
      glTexCoord2d(0,th) glVertex2d( x, y+h )
      glTexCoord2d(tw,th) glVertex2d( x+w, y+h )
    end

    local function draw_lights()
      glColor4d(lr,lg,lb,la)
      tw,th = bind_mimage(light_img)
      gl_triangle_strip_scope(light_box)
    end

    if options?.glow_only
      draw_lights=_SAFE
    end

    -- the definition of these two functions varies, depending on
    -- the light settings
    local draw_glow, draw_extra
    local frame_time in _ENV

    if lines

      local tmax=lines[#lines].t

      local function add_point(u,v)
        glTexCoord2d(u*tw,v*th) glVertex2d( x+u*w, y+v*h )
      end


      local function add_ipoint(x,y)
        add_point(x/iw,y/ih)
      end

      local function add_line(line)
        local x0,y0,x1,y1 in line
        add_ipoint(x0,y0)
        add_ipoint(x1,y1)
      end

      local function lerp_line(line,line1,t)

        local x0,y0,x1,y1 in line
        local s0=t-line.t
        local s1=line1.t-t

        local s=s0/(s0+s1)
        local r=(1-s)

        add_ipoint(s*line1.x0+r*x0,s*line1.y0+r*y0)
        add_ipoint(s*line1.x1+r*x1,s*line1.y1+r*y1)

        return s*line1.x0+r*x0
      end

      local function next_t()
        t0=t
        if state==0
          state=1	
          return t + 1/slope
        elseif state==1
          state=2
          --console(..state)
          return t+width
        elseif state==2
          state=3
          --console(..state)
          return t + 1/slope
        elseif state==3
          state=0
          return t+skip
        else
          return max_double
        end
      end

      local function reset_t()
        a0=0
        a1=1*a
        state=0
        slope_a=slope*a


        local arg=speed/cycle_w*(frame_time()+toffset )
        local _,tt=modf(arg)
        t=tt*cycle_w

        --if(bw_debug) console(..arg,..tt,..t,..skip) end

        while(t-skip>0) 
          t-=cycle_w
        end




        for i=1,100
          local _t0,_state,_t=t0,state,t
          t=next_t()

  --				console(..t)

          if t>0
            t0,state,t=_t0,_state,_t
            break
          end
        
          --console('iter',..i)

        end

        --if bw_debug
        --	console(t,t0,state)
        --end

      end



      local function alpha(t)
        if state==0
          return a0
        elseif state==1
          return (t-t0)*slope_a+a0
        elseif state==2
          return a1
        elseif state==3
          return a1-(t-t0)*slope_a
        end
      end

      local line_points

      if base_glow_only 
        function draw_glow()
          glColor4d(gr,gg,gb,ga)
          tw,th = bind_mimage(glow_img)
          gl_triangle_strip_scope(light_box)
        end
      elseif line_debug

        function line_points()
          for i=2,#lines do
            glColor4d(1,0,0,1)
            add_line(lines[i-1])
          
            glColor4d(0,0,1,1)
            add_line(lines[i])
          end
        end
      else

        function line_points()
          for i=1,#lines do

            local line = lines[i]
        
            --if(bw_debug) console(..t,..i,..all_lines,..tmax) end

            if all_lines or (t>tmax or t<0)

              --if(bw_debug) console(..format("%f",t),..i) end	

              if t<0
                t=next_t()	
              
              end

              if bw_debug
                glColor4d(alpha(line.t),alpha(line.t),alpha(line.t),1)
              else
                glColor4d(r,g,b,alpha(line.t))
              end

              add_line(line)
  
            end

            if(line.t<=t)

              local line1 = lines[i+1]

              if(line1) 
          
                while line1.t>t

                  if bw_debug
                    glColor4d(alpha(t),alpha(t),alpha(t),1)
                  else
                    glColor4d(r,g,b,alpha(t))
                  end
            
                  lerp_line(line,line1,t)

                  t=next_t()
                end

              end
            end
          end
        end
      end

      local draw_extra

      if line_points 
    
        if (line_debug or bw_debug)

          function draw_glow()
            tw,th = bind_mimage(glow_img)
            bind_zero_texture()

            if bw_debug 
              r,g,b,a=1,1,1,1
              reset_t(speed) 

              --frame_time = function()  return 92.53 end

              --t=10
            end

            gl_triangle_strip_scope(line_points)

            if line_debug

              glColor4d(1,1,1,1)
              tw,th = bind_mimage(glow_img)
              gl_triangle_strip_scope(light_box)

            end

          end

        else
        
          function draw_glow(speed)
            tw,th = bind_mimage(glow_img)

            r,g,b,a=gr,gg,gb,ga

            reset_t(speed)
            gl_triangle_strip_scope(line_points)
          end

      
          local function add_points()
            glBlendFunAdd()
            tw,th = bind_mimage(glow_img)
            gl_triangle_strip_scope(line_points)
          end

          function draw_extra(speed)

            if extra_a>0
              a=extra_a*ea
              r,g,b=er,eg,eb

              reset_t(speed)
              glWrap(add_points)
            end

          end
        end
      end

      function info.draw(speed)
        toffset = cycle_offset?[speed] or 0

        draw_glow?(speed)
        draw_lights()
        draw_extra?(speed)
      end

    else


      local pulse_a=1

      function draw_glow(speed)
        tw,th = bind_mimage(glow_img)
        glColor4d(gr,gg,gb,ga*pulse_a)
        gl_triangle_strip_scope(light_box)
      end

      
      local function add_points()
        glBlendFunAdd()
        tw,th = bind_mimage(glow_img)
        gl_triangle_strip_scope(light_box)
      end

      function draw_extra()
        if extra_a>0
          glColor4d(er,eg,eb, extra_a*ea*pulse_a )
          glWrap(add_points)
        end
      end

      function info.draw(speed_str)

        toffset = cycle_offset?[speed_str] or 0
        --local rmod = rate_mod?[speed_str] or 1

        local _,tt=modf(pulse_speed/cycle_w*(frame_time()+toffset+.5) )
        
        pulse_a=pulse_a0+(pulse_a1-pulse_a0)*triangle(2*tt)

        draw_glow?(speed_str)
        draw_lights()
        draw_extra?(speed_str)

      end	

    end


  end

  local lights_fun = restore_color(function(color_setting,speed_setting)
    
    local light_color,glow_color,extra_color in colors![color_setting]

    lr,lg,lb,la = unpack(light_color)
    gr,gg,gb,ga = unpack(glow_color)
    er,eg,eb,ea  = unpack(extra_color or glow_color)

    local r,g,b,a=current_color()

    lr*=r lg*=g lb*=b la*=a
    gr*=r gg*=g gb*=b ga*=a
    er*=r eg*=g eb*=b ea*=a


    set_speed(speed_setting)

    for i=1,n
      light_info[i].draw?(speed_setting)
    end

  end)

  local get_lights_fun = strong_memoize2( function(color,speed)
    return function()
      lights_fun(color,speed)
    end
  end)

  -- TODO: this should really take the standard ship/palette
  -- hints
  return function(transform,ship,palette)
    --print('drawing for',lightdir)

    request_component_function(transform, 
      get_lights_fun(ship?.light_color or options.force_light_color or "orange",
      ship?.light_speed or options.force_light_speed or "slow") , 2 )
  end

end


local mt=getmetatable(_ENV)

local old_newindex=mt.__newindex

function mt.__newindex(t,k,v)
  console("thats odd, trying to set ", k);
  (old_newindex or rawset)(t,k,v)
end
"""

tree = ast.parse(lines)
print(ast.to_lua_source(tree))
