from luaparser import ast
lines = """EventCardFile | function(event_card, dialog_context)

function calculate_player_foils(player)

  local tude = strong_memoize_1_to_1 | function(empire)
    return empire : attitude_number_for(player)
  end

 push | empire

  -- then we sort them by power
  table.sort(list, |) function(e1,e2)
    return lexical_compare(powerfun(e2),powerfun(e1),e1._ikey,e2._ikey)
  end


  -- then we walk through the power-ordered list, and for each
  -- empire, remove any empires that appear later in the list
  -- that are at war with that empire.
  local checked={}
  for i=1,100 do
    local to_check
    for _,empire in spairs(list)
      if not checked[empire]
        to_check=empire
        break
      end
    end
    if not to_check
      break
    end
    for k,empire in pairs(list)
      if at_war(empire,to_check)
        list[k]=nil
      end
    end
  end

  -- thus, you end up counting as a "foil" if you don't like the
  -- player, and you're not at war with a stronger player that
  -- also doesn't like the player.
  local foils = {}
  for i,empire ; list
    foils[empire]=true
  end

  return foils
end

function event_card.on_end_year()
  for _,empire in ipairs | all_empires
    if empire.started_player_controlled 
      galaxy.foils = calculate_player_foils | empire
      return
    end
  end
  galaxy.foils={}
end

end

if lua_load_complete
  local player = gui_player()
  for _, empire in candidate_foils | player
    print(empire.name, galaxy.foils[empire], empire : attitude_number_for(player), AI.total_navy_power(player)*.8 < AI.total_navy_power(empire), AI.total_navy_power(empire), empire.global_tech_discount, empire.global_ship_cost_mult)
  end

end
"""

lines = """
EventCardFile | function(event_card, dialog_context)

  function calculate_player_foils(player)

    local tude = strong_memoize_1_to_1 | function(empire)
      return empire : attitude_number_for(player)
    end

    push | some_value

    -- then we sort them by power
    table.sort(list, |) function(e1,e2)
      return lexical_compare(powerfun(e2),powerfun(e1),e1._ikey,e2._ikey)
    end
  end
end
"""

tree = ast.parse(lines)

# print(ast.to_pretty_str(tree))

print(ast.to_lua_source(tree))
