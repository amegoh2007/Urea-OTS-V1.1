"""Unit operations, one sub-package per plant section.

    feed         321 NH3 pumping station
    synthesis    322 HP loop
    recirc       323 LP recirculation
    desorption   328 desorption and hydrolysis
    absorption   322C001 LP absorber
    evaporation  324 evaporation, vacuum train, finishing
    steam        329 steam network
    consequence  deviation-consequence physics shared by every vessel, valve and pump
    liquor_stage the species layer every 323 and 324 liquor stage integrates
    steam_chest  the condensing-steam chest of every LP-steam heater
"""
