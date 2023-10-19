add_library(BusClassPass MODULE
    BusClass.cpp
)

target_compile_features(BusClassPass PRIVATE cxx_range_for cxx_auto_type)

set_target_properties(BusClassPass PROPERTIES
    COMPILE_FLAGS "-fno-rtti"
)

if(APPLE)
    set_target_properties(BusClassPass PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif(APPLE)
