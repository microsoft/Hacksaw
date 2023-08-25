add_library(BusClassAssignPass MODULE
    BusClassAssign.cpp
)

target_compile_features(BusClassAssignPass PRIVATE cxx_range_for cxx_auto_type)

set_target_properties(BusClassAssignPass PROPERTIES
    COMPILE_FLAGS "-fno-rtti"
)

if(APPLE)
    set_target_properties(BusClassAssignPass PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif(APPLE)
