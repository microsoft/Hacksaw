add_library(DevregPass MODULE
    Devreg.cpp
)

target_compile_features(DevregPass PRIVATE cxx_range_for cxx_auto_type)

set_target_properties(DevregPass PROPERTIES
    COMPILE_FLAGS "-fno-rtti"
)

if(APPLE)
    set_target_properties(DevregPass PROPERTIES
        LINK_FLAGS "-undefined dynamic_lookup"
    )
endif(APPLE)
